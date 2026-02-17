"""Tests for embedding service (Slice 10).

Unit tests for:
  - generate_embedding / generate_embeddings (mocked OpenAI)
  - embed_and_store_chunks (mocked Supabase)
  - search_similar_chunks (mocked Supabase RPC)
  - format_chunks_as_context
  - backfill_embeddings
  - Brand chat context retrieval (get_relevant_context)
  - Pipeline node resource fetch (_fetch_relevant_resources)
No external dependencies needed — all API calls are mocked.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Helpers ──────────────────────────────────────────────────


def _make_embedding(dim: int = 1536, seed: float = 0.1) -> list:
    """Create a fake embedding vector."""
    return [seed] * dim


def _mock_openai_embedding_response(input=None, model=None, **kwargs):
    """Create a mock OpenAI embedding response matching OpenAI API signature."""
    mock_resp = MagicMock()
    texts = input if isinstance(input, list) else [input]
    data = []
    for i, text in enumerate(texts):
        item = MagicMock()
        item.index = i
        item.embedding = _make_embedding(seed=0.1 * (i + 1))
        data.append(item)
    mock_resp.data = data
    return mock_resp


# ── Embedding Generation Tests ───────────────────────────────


class TestGenerateEmbedding:
    """Test single embedding generation."""

    def test_empty_text_returns_zeros(self):
        from app.services.embeddings import generate_embedding
        result = generate_embedding("")
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    def test_whitespace_only_returns_zeros(self):
        from app.services.embeddings import generate_embedding
        result = generate_embedding("   ")
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    @patch("app.services.embeddings._get_openai_client")
    def test_real_text_calls_openai(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.embeddings.create = _mock_openai_embedding_response
        mock_get_client.return_value = mock_client

        from app.services.embeddings import generate_embedding
        result = generate_embedding("Test text about branding")

        assert len(result) == 1536
        assert result[0] == 0.1

    @patch("app.services.embeddings._get_openai_client")
    def test_uses_correct_model(self, mock_get_client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        item = MagicMock()
        item.index = 0
        item.embedding = _make_embedding()
        mock_resp.data = [item]
        mock_client.embeddings.create.return_value = mock_resp
        mock_get_client.return_value = mock_client

        from app.services.embeddings import generate_embedding
        generate_embedding("test")

        mock_client.embeddings.create.assert_called_once()
        call_kwargs = mock_client.embeddings.create.call_args
        assert call_kwargs[1]["model"] == "text-embedding-3-small"


class TestGenerateEmbeddings:
    """Test batch embedding generation."""

    def test_empty_list(self):
        from app.services.embeddings import generate_embeddings
        result = generate_embeddings([])
        assert result == []

    @patch("app.services.embeddings._get_openai_client")
    def test_batch_of_three(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.embeddings.create = _mock_openai_embedding_response
        mock_get_client.return_value = mock_client

        from app.services.embeddings import generate_embeddings
        result = generate_embeddings(["text1", "text2", "text3"])

        assert len(result) == 3
        assert len(result[0]) == 1536

    @patch("app.services.embeddings._get_openai_client")
    def test_handles_empty_strings_in_batch(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.embeddings.create = _mock_openai_embedding_response
        mock_get_client.return_value = mock_client

        from app.services.embeddings import generate_embeddings
        result = generate_embeddings(["real text", "", "  "])

        assert len(result) == 3


# ── Storage Tests ────────────────────────────────────────────


class TestEmbedAndStoreChunks:
    """Test embedding and storing chunks in the database."""

    def test_empty_chunks_returns_zero(self):
        from app.services.embeddings import embed_and_store_chunks
        assert embed_and_store_chunks("resource-123", []) == 0

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embeddings")
    def test_stores_embeddings_for_chunks(self, mock_gen, mock_admin):
        mock_gen.return_value = [_make_embedding(seed=0.1), _make_embedding(seed=0.2)]

        # Mock Supabase: select returns chunk IDs, update succeeds
        mock_client = MagicMock()
        select_resp = MagicMock()
        select_resp.data = [
            {"id": "chunk-1", "chunk_index": 0},
            {"id": "chunk-2", "chunk_index": 1},
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = select_resp
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_admin.return_value = mock_client

        from app.services.embeddings import embed_and_store_chunks
        result = embed_and_store_chunks("resource-123", ["chunk text 1", "chunk text 2"])

        assert result == 2
        mock_gen.assert_called_once_with(["chunk text 1", "chunk text 2"])

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embeddings")
    def test_handles_embedding_failure_gracefully(self, mock_gen, mock_admin):
        mock_gen.side_effect = Exception("API error")

        from app.services.embeddings import embed_and_store_chunks
        result = embed_and_store_chunks("resource-123", ["text"])

        assert result == 0


# ── Search Tests ─────────────────────────────────────────────


class TestSearchSimilarChunks:
    """Test semantic search functionality."""

    def test_empty_query_returns_empty(self):
        from app.services.embeddings import search_similar_chunks
        assert search_similar_chunks("", "user-123") == []

    def test_whitespace_query_returns_empty(self):
        from app.services.embeddings import search_similar_chunks
        assert search_similar_chunks("   ", "user-123") == []

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_returns_ranked_results(self, mock_gen, mock_admin):
        mock_gen.return_value = _make_embedding()

        mock_client = MagicMock()
        rpc_resp = MagicMock()
        rpc_resp.data = [
            {
                "id": "c1", "resource_id": "r1", "chunk_index": 0,
                "chunk_text": "Relevant text about offers",
                "metadata": {"title": "Hormozi PDF"},
                "similarity": 0.92,
            },
            {
                "id": "c2", "resource_id": "r2", "chunk_index": 3,
                "chunk_text": "Another relevant chunk",
                "metadata": {"title": "MAGIC Framework"},
                "similarity": 0.85,
            },
        ]
        mock_client.rpc.return_value.execute.return_value = rpc_resp
        mock_admin.return_value = mock_client

        from app.services.embeddings import search_similar_chunks
        results = search_similar_chunks("offer framework", "user-123", limit=5)

        assert len(results) == 2
        assert results[0]["similarity"] == 0.92
        assert results[0]["chunk_text"] == "Relevant text about offers"

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_calls_rpc_with_correct_params(self, mock_gen, mock_admin):
        embedding = _make_embedding(seed=0.5)
        mock_gen.return_value = embedding

        mock_client = MagicMock()
        rpc_resp = MagicMock()
        rpc_resp.data = []
        mock_client.rpc.return_value.execute.return_value = rpc_resp
        mock_admin.return_value = mock_client

        from app.services.embeddings import search_similar_chunks
        search_similar_chunks("test query", "user-456", limit=3, threshold=0.8)

        mock_client.rpc.assert_called_once_with("match_resource_chunks", {
            "query_embedding": embedding,
            "match_user_id": "user-456",
            "match_count": 3,
            "match_threshold": 0.8,
        })

    @patch("app.services.embeddings.generate_embedding")
    def test_handles_embedding_failure(self, mock_gen):
        mock_gen.side_effect = Exception("API down")

        from app.services.embeddings import search_similar_chunks
        results = search_similar_chunks("test", "user-123")

        assert results == []


# ── Format Tests ─────────────────────────────────────────────


class TestFormatChunksAsContext:
    """Test formatting search results for LLM context."""

    def test_empty_chunks_returns_empty_string(self):
        from app.services.embeddings import format_chunks_as_context
        assert format_chunks_as_context([]) == ""

    def test_single_chunk_formatted(self):
        from app.services.embeddings import format_chunks_as_context
        chunks = [{
            "chunk_text": "Value equation is dream outcome times likelihood...",
            "metadata": {"title": "$100M Offers"},
            "similarity": 0.95,
        }]
        result = format_chunks_as_context(chunks)
        assert "$100M Offers" in result
        assert "95%" in result
        assert "Value equation" in result

    def test_multiple_chunks_separated(self):
        from app.services.embeddings import format_chunks_as_context
        chunks = [
            {"chunk_text": "Chunk 1", "metadata": {"title": "A"}, "similarity": 0.9},
            {"chunk_text": "Chunk 2", "metadata": {"title": "B"}, "similarity": 0.8},
        ]
        result = format_chunks_as_context(chunks)
        assert "---" in result
        assert "Chunk 1" in result
        assert "Chunk 2" in result

    def test_missing_metadata_uses_default(self):
        from app.services.embeddings import format_chunks_as_context
        chunks = [{"chunk_text": "text", "metadata": None, "similarity": 0.7}]
        result = format_chunks_as_context(chunks)
        assert "Resource" in result


# ── Backfill Tests ───────────────────────────────────────────


class TestBackfillEmbeddings:
    """Test backfilling embeddings for existing chunks."""

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embeddings")
    def test_backfills_unembedded_chunks(self, mock_gen, mock_admin):
        mock_gen.return_value = [_make_embedding(seed=0.1), _make_embedding(seed=0.2)]

        mock_client = MagicMock()
        # First call returns 2 unembedded chunks, second returns empty
        select_resp1 = MagicMock()
        select_resp1.data = [
            {"id": "c1", "chunk_text": "text 1"},
            {"id": "c2", "chunk_text": "text 2"},
        ]
        select_resp2 = MagicMock()
        select_resp2.data = []

        mock_client.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.side_effect = [
            select_resp1, select_resp2,
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_admin.return_value = mock_client

        from app.services.embeddings import backfill_embeddings
        result = backfill_embeddings(batch_size=100)

        assert result == 2

    @patch("app.services.embeddings.get_admin_client")
    def test_no_chunks_to_backfill(self, mock_admin):
        mock_client = MagicMock()
        select_resp = MagicMock()
        select_resp.data = []
        mock_client.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value = select_resp
        mock_admin.return_value = mock_client

        from app.services.embeddings import backfill_embeddings
        result = backfill_embeddings()

        assert result == 0


# ── Brand Chat Context Tests ────────────────────────────────


class TestBrandChatContext:
    """Test that brand chat retrieves resource context."""

    @patch("app.services.embeddings.search_similar_chunks")
    @patch("app.services.embeddings.format_chunks_as_context")
    def test_get_relevant_context_returns_formatted(self, mock_format, mock_search):
        mock_search.return_value = [{"chunk_text": "test", "metadata": {}, "similarity": 0.9}]
        mock_format.return_value = "Formatted context"

        from app.services.brand_chat import get_relevant_context
        result = get_relevant_context("offer question", "user-123")

        assert result == "Formatted context"
        mock_search.assert_called_once_with("offer question", "user-123", limit=3, threshold=0.7)

    @patch("app.services.embeddings.search_similar_chunks", side_effect=Exception("no module"))
    def test_get_relevant_context_handles_import_error(self, mock_search):
        """If embedding service is unavailable, returns empty string."""
        from app.services.brand_chat import get_relevant_context
        result = get_relevant_context("test", "user-123")
        assert result == ""

    def test_build_chat_messages_without_context(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages("ica", [{"role": "user", "content": "hello"}])
        assert messages[0]["role"] == "system"
        assert "RELEVANT KNOWLEDGE" not in messages[0]["content"]

    def test_build_chat_messages_with_context(self):
        from app.services.brand_chat import build_chat_messages
        messages = build_chat_messages(
            "ica",
            [{"role": "user", "content": "hello"}],
            resource_context="Hormozi says starving crowd is key...",
        )
        assert messages[0]["role"] == "system"
        assert "RELEVANT KNOWLEDGE" in messages[0]["content"]
        assert "Hormozi says starving crowd" in messages[0]["content"]


# ── Pipeline Node Resource Fetch Tests ──────────────────────


class TestPipelineResourceFetch:
    """Test that pipeline nodes fetch relevant resources."""

    def test_gap_analysis_fetch_no_user_id(self):
        from worker.graph.nodes.gap_analysis import _fetch_relevant_resources
        result = _fetch_relevant_resources("test query", "")
        assert "No user context" in result

    @patch("app.services.embeddings.search_similar_chunks")
    @patch("app.services.embeddings.format_chunks_as_context")
    def test_gap_analysis_fetch_with_results(self, mock_format, mock_search):
        mock_search.return_value = [{"chunk_text": "text"}]
        mock_format.return_value = "Relevant context"

        from worker.graph.nodes.gap_analysis import _fetch_relevant_resources
        result = _fetch_relevant_resources("LinkedIn growth", "user-123")

        assert result == "Relevant context"

    def test_script_generation_fetch_no_user_id(self):
        from worker.graph.nodes.script_generation import _fetch_relevant_resources
        result = _fetch_relevant_resources("test query", "")
        assert "No user context" in result

    def test_testing_fetch_no_user_id(self):
        from worker.graph.nodes.testing import _fetch_relevant_resources
        result = _fetch_relevant_resources("test query", "")
        assert "No user context" in result

    @patch("app.services.embeddings.search_similar_chunks")
    @patch("app.services.embeddings.format_chunks_as_context")
    def test_fetch_handles_empty_results(self, mock_format, mock_search):
        mock_search.return_value = []
        mock_format.return_value = ""

        from worker.graph.nodes.gap_analysis import _fetch_relevant_resources
        result = _fetch_relevant_resources("test", "user-123")

        assert result == "No relevant resources found."

    def test_fetch_handles_import_error_gracefully(self):
        """If embedding service is unavailable, returns fallback."""
        from worker.graph.nodes.gap_analysis import _fetch_relevant_resources

        with patch("app.services.embeddings.search_similar_chunks", side_effect=ImportError("no module")):
            result = _fetch_relevant_resources("test", "user-123")
            assert "No relevant resources found." in result
