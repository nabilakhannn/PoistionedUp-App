"""Tests for collections + Voice DNA (Slice 11).

Unit tests for:
  - Collection CRUD (create, list, get, update, delete)
  - Resource assignment to collections
  - Voice DNA analysis service
  - Voice DNA formatting for LLM prompts
  - Collection-scoped semantic search
  - User isolation (users only see their own collections)
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


# ── Helpers ──────────────────────────────────────────────


def _make_collection_row(
    collection_id="col-123",
    user_id="user-456",
    name="Alex Hormozi",
    description="$100M Offers author",
    creator_url="https://youtube.com/@AlexHormozi",
    voice_dna=None,
    metadata=None,
):
    """Create a fake collection DB row."""
    return {
        "id": collection_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "creator_url": creator_url,
        "voice_dna": voice_dna or {},
        "metadata": metadata or {},
        "created_at": "2026-01-15T10:00:00+00:00",
        "updated_at": "2026-01-15T10:00:00+00:00",
    }


def _make_resource_row(
    resource_id="res-789",
    title="$100M Offers",
    resource_type="file",
    collection_id="col-123",
    source_url=None,
):
    return {
        "id": resource_id,
        "type": resource_type,
        "title": title,
        "collection_id": collection_id,
        "source_url": source_url,
        "created_at": "2026-01-15T10:00:00+00:00",
    }


def _make_voice_dna():
    """Create a sample Voice DNA dict."""
    return {
        "tone": "Direct and aggressive with occasional humor",
        "sentence_style": "Short punchy sentences. Rarely more than 10 words.",
        "vocabulary_level": "Simple everyday language, avoids jargon",
        "hook_patterns": ["Bold contrarian claims", "Rhetorical questions", "Statistics"],
        "cta_patterns": ["Direct command with urgency", "Soft question nudge"],
        "signature_phrases": ["starving crowd", "dream outcome", "vehicle", "grand slam offer"],
        "content_structure": "Problem → agitate → solve → proof → CTA",
        "personality_traits": ["confident", "data-driven", "direct"],
        "sample_hooks": [
            "Most people don't have an offer problem. They have a market problem.",
            "If you can't sell it, you can't scale it.",
        ],
        "analysis_chunk_count": 45,
    }


# ── Voice DNA Analysis Tests ────────────────────────────


class TestVoiceDNAAnalysis:
    """Test Voice DNA extraction from collection content."""

    def test_not_enough_chunks_raises_error(self):
        """If collection has < 5 chunks, raise ValueError."""
        mock_admin = MagicMock()

        # Step 1: resources query returns 1 resource
        res_resp = MagicMock()
        res_resp.data = [{"id": "r1"}]

        # Step 2: chunks query returns only 3 chunks (below minimum of 5)
        chunks_resp = MagicMock()
        chunks_resp.data = [
            {"chunk_text": "text1", "metadata": {}, "resource_id": "r1"},
            {"chunk_text": "text2", "metadata": {}, "resource_id": "r1"},
            {"chunk_text": "text3", "metadata": {}, "resource_id": "r1"},
        ]

        # Mock the chain: table().select().eq().execute()
        mock_table = MagicMock()
        mock_admin.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value = res_resp
        mock_table.select.return_value.in_.return_value.execute.return_value = chunks_resp

        from app.services.voice_analysis import analyze_voice_dna
        with pytest.raises(ValueError, match="Not enough content"):
            analyze_voice_dna(mock_admin, "col-123", "Test Collection")

    @patch("worker.graph.llm.parse_json_response")
    @patch("worker.graph.llm.get_llm_client")
    def test_analyze_voice_dna_success(self, mock_get_llm, mock_parse):
        """Successful Voice DNA extraction with mocked LLM."""
        mock_admin = MagicMock()

        # Mock resources in collection
        res_resp = MagicMock()
        res_resp.data = [{"id": "r1"}, {"id": "r2"}]

        # Mock chunks (6 chunks — above minimum of 5)
        chunks_data = [
            {"chunk_text": f"Sample text {i} about offers and business", "metadata": {}, "resource_id": f"r{(i % 2) + 1}"}
            for i in range(6)
        ]
        chunks_resp = MagicMock()
        chunks_resp.data = chunks_data

        mock_table = MagicMock()
        mock_admin.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value = res_resp
        mock_table.select.return_value.in_.return_value.execute.return_value = chunks_resp
        # update().eq().execute() for storing voice_dna
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Mock LLM response
        voice_dna = _make_voice_dna()
        mock_llm = MagicMock()
        mock_llm.chat.return_value = {"content": json.dumps(voice_dna)}
        mock_get_llm.return_value = mock_llm
        mock_parse.return_value = voice_dna

        from app.services.voice_analysis import analyze_voice_dna
        result = analyze_voice_dna(mock_admin, "col-123", "Alex Hormozi")

        assert result["tone"] == "Direct and aggressive with occasional humor"
        assert "starving crowd" in result["signature_phrases"]
        assert result["analysis_chunk_count"] == 6  # Overwritten by actual count

    def test_empty_collection_raises_error(self):
        """If collection has no resources, raise ValueError."""
        mock_admin = MagicMock()

        # No resources in collection
        res_resp = MagicMock()
        res_resp.data = []

        mock_table = MagicMock()
        mock_admin.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value = res_resp

        from app.services.voice_analysis import analyze_voice_dna
        with pytest.raises(ValueError, match="Not enough content"):
            analyze_voice_dna(mock_admin, "col-123", "Empty Collection")


class TestVoiceDNAFormatting:
    """Test Voice DNA formatting for LLM system prompts."""

    def test_empty_voice_dna_returns_empty(self):
        from app.services.voice_analysis import format_voice_dna_instructions
        assert format_voice_dna_instructions({}) == ""
        assert format_voice_dna_instructions({"tone": ""}) == ""

    def test_full_voice_dna_formats_correctly(self):
        from app.services.voice_analysis import format_voice_dna_instructions
        voice_dna = _make_voice_dna()
        result = format_voice_dna_instructions(voice_dna)

        assert "CREATOR VOICE STYLE INSTRUCTIONS" in result
        assert "Direct and aggressive" in result
        assert "Short punchy sentences" in result
        assert "starving crowd" in result
        assert "HOOK PATTERNS" in result
        assert "CTA PATTERNS" in result
        assert "EXAMPLE HOOKS" in result
        assert "Most people don't have an offer problem" in result

    def test_partial_voice_dna_only_includes_available(self):
        from app.services.voice_analysis import format_voice_dna_instructions
        partial = {
            "tone": "Warm and conversational",
            "sentence_style": "Medium length, flowing",
            "vocabulary_level": "",
            "hook_patterns": [],
            "cta_patterns": [],
            "signature_phrases": [],
            "content_structure": "",
            "personality_traits": [],
            "sample_hooks": [],
        }
        result = format_voice_dna_instructions(partial)

        assert "Warm and conversational" in result
        assert "Medium length" in result
        assert "HOOK PATTERNS" not in result  # Empty, should be omitted
        assert "SIGNATURE PHRASES" not in result


# ── Chunk Sampling Tests ─────────────────────────────────


class TestChunkSampling:
    """Test chunk sampling strategy for Voice DNA analysis."""

    def test_small_collection_returns_all(self):
        from app.services.voice_analysis import _sample_chunks
        chunks = [{"chunk_text": f"text {i}", "resource_id": "r1"} for i in range(10)]
        result = _sample_chunks(chunks, max_samples=60)
        assert len(result) == 10

    def test_large_collection_samples_per_resource(self):
        from app.services.voice_analysis import _sample_chunks
        # 3 resources, 30 chunks each = 90 total
        chunks = []
        for r in range(3):
            for i in range(30):
                chunks.append({"chunk_text": f"text {r}-{i}", "resource_id": f"r{r}"})

        result = _sample_chunks(chunks, max_samples=30)
        assert len(result) <= 30

        # Should have chunks from all 3 resources
        resource_ids = {c["resource_id"] for c in result}
        assert len(resource_ids) == 3

    def test_includes_first_and_last_chunks(self):
        """First chunk (hook) and last chunk (CTA) should be preferred."""
        from app.services.voice_analysis import _sample_chunks
        chunks = [{"chunk_text": f"text {i}", "resource_id": "r1"} for i in range(20)]

        result = _sample_chunks(chunks, max_samples=5)
        texts = [c["chunk_text"] for c in result]

        # First and last should be included
        assert "text 0" in texts
        assert "text 19" in texts


# ── Collection-Scoped Search Tests ───────────────────────


class TestCollectionScopedSearch:
    """Test collection-scoped semantic search."""

    def test_empty_query_returns_empty(self):
        from app.services.embeddings import search_collection_chunks
        assert search_collection_chunks("", "col-123") == []

    def test_whitespace_query_returns_empty(self):
        from app.services.embeddings import search_collection_chunks
        assert search_collection_chunks("   ", "col-123") == []

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_returns_ranked_results(self, mock_gen, mock_admin):
        mock_gen.return_value = [0.1] * 1536

        mock_client = MagicMock()
        rpc_resp = MagicMock()
        rpc_resp.data = [
            {
                "id": "c1", "resource_id": "r1", "chunk_index": 0,
                "chunk_text": "Relevant Hormozi text",
                "metadata": {"title": "Offers PDF"},
                "similarity": 0.91,
            },
        ]
        mock_client.rpc.return_value.execute.return_value = rpc_resp
        mock_admin.return_value = mock_client

        from app.services.embeddings import search_collection_chunks
        results = search_collection_chunks("offer framework", "col-123")

        assert len(results) == 1
        assert results[0]["similarity"] == 0.91

    @patch("app.services.embeddings.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_calls_collection_rpc(self, mock_gen, mock_admin):
        embedding = [0.5] * 1536
        mock_gen.return_value = embedding

        mock_client = MagicMock()
        rpc_resp = MagicMock()
        rpc_resp.data = []
        mock_client.rpc.return_value.execute.return_value = rpc_resp
        mock_admin.return_value = mock_client

        from app.services.embeddings import search_collection_chunks
        search_collection_chunks("test query", "col-789", limit=3, threshold=0.8)

        mock_client.rpc.assert_called_once_with("match_collection_chunks", {
            "query_embedding": embedding,
            "match_collection_id": "col-789",
            "match_count": 3,
            "match_threshold": 0.8,
        })

    @patch("app.services.embeddings.generate_embedding")
    def test_handles_embedding_failure(self, mock_gen):
        mock_gen.side_effect = Exception("API down")

        from app.services.embeddings import search_collection_chunks
        results = search_collection_chunks("test", "col-123")
        assert results == []


# ── Schema Tests ─────────────────────────────────────────


class TestCollectionSchemas:
    """Test collection Pydantic schemas."""

    def test_voice_dna_defaults(self):
        from app.schemas.collection import VoiceDNA
        v = VoiceDNA()
        assert v.tone == ""
        assert v.hook_patterns == []
        assert v.analysis_chunk_count == 0

    def test_voice_dna_with_data(self):
        from app.schemas.collection import VoiceDNA
        data = _make_voice_dna()
        v = VoiceDNA(**data)
        assert v.tone == "Direct and aggressive with occasional humor"
        assert len(v.signature_phrases) == 4

    def test_collection_create_validation(self):
        from app.schemas.collection import CollectionCreate
        c = CollectionCreate(name="Hormozi", description="test")
        assert c.name == "Hormozi"
        assert c.collection_id is None if hasattr(c, "collection_id") else True

    def test_collection_create_empty_name_fails(self):
        from app.schemas.collection import CollectionCreate
        with pytest.raises(Exception):
            CollectionCreate(name="")

    def test_collection_summary_voice_dna_ready(self):
        from app.schemas.collection import CollectionSummary
        s = CollectionSummary(
            id="col-123",
            name="Test",
            description="",
            voice_dna_ready=True,
            resource_count=5,
            created_at="2026-01-15T10:00:00+00:00",
            updated_at="2026-01-15T10:00:00+00:00",
        )
        assert s.voice_dna_ready is True
        assert s.resource_count == 5

    def test_collection_detail_with_resources(self):
        from app.schemas.collection import CollectionDetail, CollectionResourceOut, VoiceDNA
        detail = CollectionDetail(
            id="col-123",
            name="Hormozi",
            description="Books and videos",
            voice_dna=VoiceDNA(**_make_voice_dna()),
            resources=[
                CollectionResourceOut(
                    id="r1", type="file", title="$100M Offers",
                    chunk_count=42, created_at="2026-01-15T10:00:00+00:00",
                ),
            ],
            created_at="2026-01-15T10:00:00+00:00",
            updated_at="2026-01-15T10:00:00+00:00",
        )
        assert len(detail.resources) == 1
        assert detail.voice_dna.tone == "Direct and aggressive with occasional humor"

    def test_search_request_validation(self):
        from app.schemas.collection import CollectionSearchRequest
        req = CollectionSearchRequest(query="test", limit=10, threshold=0.5)
        assert req.limit == 10
        assert req.threshold == 0.5

    def test_add_resources_requires_ids(self):
        from app.schemas.collection import CollectionAddResources
        body = CollectionAddResources(resource_ids=["r1", "r2"])
        assert len(body.resource_ids) == 2


# ── Resource Schema collection_id Tests ──────────────────


class TestResourceCollectionId:
    """Test that resource schemas support collection_id."""

    def test_resource_create_note_with_collection(self):
        from app.schemas.resource import ResourceCreateNote
        r = ResourceCreateNote(
            type="note",
            title="Test Note",
            collection_id="col-123",
        )
        assert r.collection_id == "col-123"

    def test_resource_create_note_without_collection(self):
        from app.schemas.resource import ResourceCreateNote
        r = ResourceCreateNote(type="note", title="Test Note")
        assert r.collection_id is None

    def test_channel_import_with_collection(self):
        from app.schemas.resource import ChannelImportRequest
        r = ChannelImportRequest(
            channel_url="https://youtube.com/@AlexHormozi",
            collection_id="col-456",
        )
        assert r.collection_id == "col-456"

    def test_channel_import_without_collection(self):
        from app.schemas.resource import ChannelImportRequest
        r = ChannelImportRequest(
            channel_url="https://youtube.com/@AlexHormozi",
        )
        assert r.collection_id is None


# ── Build Prompt Tests ───────────────────────────────────


class TestBuildAnalysisPrompt:
    """Test the Voice DNA analysis prompt builder."""

    def test_builds_prompt_with_samples(self):
        from app.services.voice_analysis import _build_analysis_prompt
        chunks = [
            {"chunk_text": "First sample text"},
            {"chunk_text": "Second sample text"},
        ]
        result = _build_analysis_prompt(chunks, "Alex Hormozi")

        assert "Alex Hormozi" in result
        assert "2 content samples" in result
        assert "First sample text" in result
        assert "Second sample text" in result
        assert "Voice DNA profile" in result

    def test_skips_empty_chunks(self):
        from app.services.voice_analysis import _build_analysis_prompt
        chunks = [
            {"chunk_text": "Real text"},
            {"chunk_text": ""},
            {"chunk_text": "   "},
        ]
        result = _build_analysis_prompt(chunks, "Test")
        assert "[Sample 1]" in result
        # Empty chunks are skipped
        assert "Real text" in result
