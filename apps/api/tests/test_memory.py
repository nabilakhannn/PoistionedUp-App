"""Tests for Agent Memory system (Slice 13).

Unit tests for:
  - Memory creation (with and without embedding)
  - Memory listing and filtering
  - Memory update and re-embedding
  - Approval workflow (approve, dismiss, supersede)
  - Semantic search (get_relevant_memories)
  - Fallback search when embeddings unavailable
  - Context formatting for LLM injection
  - Auto-observation from performance metrics
  - Auto-observation from user edits
  - Memory synthesis
  - Schema validation
  - Pipeline integration (memory context injection in nodes + brand_chat)
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

def _make_memory(
    memory_id="mem-1",
    user_id="user-456",
    memory_type="observation",
    content="Story hooks outperform question hooks on YouTube",
    confidence=0.7,
    status="active",
    platform="youtube",
    category="hooks",
    source="metrics",
    evidence=None,
    related_post_ids=None,
    supersedes_id=None,
    embedding=None,
    last_used_at=None,
    created_at="2026-02-01T10:00:00+00:00",
    updated_at="2026-02-01T10:00:00+00:00",
    **kwargs,
):
    """Create a fake agent_memory row."""
    return {
        "id": memory_id,
        "user_id": user_id,
        "memory_type": memory_type,
        "content": content,
        "confidence": confidence,
        "status": status,
        "platform": platform,
        "category": category,
        "source": source,
        "evidence": evidence or [],
        "related_post_ids": related_post_ids or [],
        "supersedes_id": supersedes_id,
        "embedding": embedding,
        "last_used_at": last_used_at,
        "created_at": created_at,
        "updated_at": updated_at,
        **kwargs,
    }


def _make_sample_memories(count=5):
    """Create a diverse set of sample memories for testing."""
    types = ["observation", "preference", "lesson", "content_pattern", "voice_note"]
    platforms = ["youtube", "linkedin", None, "youtube", "linkedin"]
    categories = ["hooks", "topics", None, "structure", "voice"]
    confidences = [0.9, 0.8, 0.6, 0.7, 0.5]
    contents = [
        "Story hooks get 2x engagement on YouTube",
        "Never use rhetorical questions in hooks",
        "AI tools content outperforms other topics by 3x",
        "Story -> Insight -> CTA structure works best",
        "User writes in conversational, first-person style",
    ]

    return [
        _make_memory(
            memory_id=f"mem-{i}",
            memory_type=types[i],
            content=contents[i],
            confidence=confidences[i],
            platform=platforms[i],
            category=categories[i],
            source="metrics" if i < 3 else "auto",
        )
        for i in range(count)
    ]


def _mock_supabase_table(mock_admin, data):
    """Set up a mock Supabase table chain that returns given data."""
    mock_table = MagicMock()
    mock_admin.return_value.table.return_value = mock_table

    # Make all chained calls return the same mock table
    for method in ["select", "eq", "insert", "update", "delete", "order", "limit", "is_"]:
        getattr(mock_table, method).return_value = mock_table

    mock_table.execute.return_value.data = data
    return mock_table


# ── Schema Tests ─────────────────────────────────────────

class TestSchemas:
    """Test Pydantic schema validation."""

    def test_create_schema_valid(self):
        from app.schemas.memory import AgentMemoryCreate
        m = AgentMemoryCreate(
            memory_type="observation",
            content="Test content",
        )
        assert m.memory_type == "observation"
        assert m.confidence == 0.5

    def test_create_schema_with_all_fields(self):
        from app.schemas.memory import AgentMemoryCreate
        m = AgentMemoryCreate(
            memory_type="preference",
            content="No rhetorical questions",
            confidence=0.9,
            platform="youtube",
            category="hooks",
            source="user",
            related_post_ids=["post-1", "post-2"],
        )
        assert m.confidence == 0.9
        assert len(m.related_post_ids) == 2

    def test_create_schema_empty_content_rejected(self):
        from app.schemas.memory import AgentMemoryCreate
        with pytest.raises(Exception):
            AgentMemoryCreate(memory_type="observation", content="")

    def test_create_schema_confidence_bounds(self):
        from app.schemas.memory import AgentMemoryCreate
        with pytest.raises(Exception):
            AgentMemoryCreate(memory_type="observation", content="test", confidence=1.5)
        with pytest.raises(Exception):
            AgentMemoryCreate(memory_type="observation", content="test", confidence=-0.1)

    def test_update_schema(self):
        from app.schemas.memory import AgentMemoryUpdate
        u = AgentMemoryUpdate(content="Updated content", confidence=0.8)
        assert u.content == "Updated content"
        assert u.platform is None

    def test_summary_schema(self):
        from app.schemas.memory import AgentMemorySummary
        s = AgentMemorySummary(
            id="mem-1",
            memory_type="observation",
            content="Test",
            confidence=0.5,
            status="active",
            created_at="2026-01-01T00:00:00",
        )
        assert s.platform is None
        assert s.last_used_at is None

    def test_detail_schema(self):
        from app.schemas.memory import AgentMemoryDetail
        d = AgentMemoryDetail(
            id="mem-1",
            memory_type="lesson",
            content="Important lesson",
            confidence=0.8,
            status="pending_approval",
            evidence=[{"post": "post-1", "result": "viral"}],
            related_post_ids=["post-1"],
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        assert len(d.evidence) == 1
        assert d.supersedes_id is None

    def test_approval_action_schema(self):
        from app.schemas.memory import MemoryApprovalAction
        a = MemoryApprovalAction(action="approve")
        assert a.edited_content is None

        with pytest.raises(Exception):
            MemoryApprovalAction(action="invalid")

    def test_synthesis_response_schema(self):
        from app.schemas.memory import MemorySynthesisResponse
        r = MemorySynthesisResponse(
            new_memories_created=3,
            memories_superseded=5,
            patterns_detected=["hooks", "topics"],
            message="Synthesized 3 lessons",
        )
        assert r.new_memories_created == 3


# ── Context Formatting Tests ─────────────────────────────

class TestFormatMemoriesAsContext:
    """Test memory context formatting for LLM injection."""

    def test_empty_memories(self):
        from app.services.agent_memory import format_memories_as_context
        assert format_memories_as_context([]) == ""

    def test_single_observation(self):
        from app.services.agent_memory import format_memories_as_context
        memories = [_make_memory(
            memory_type="observation",
            content="Story hooks work best",
            confidence=0.9,
            platform="youtube",
        )]
        result = format_memories_as_context(memories)
        assert "OBSERVATIONS" in result
        assert "Story hooks work best" in result
        assert "[youtube]" in result
        assert "high" in result

    def test_grouped_by_type(self):
        from app.services.agent_memory import format_memories_as_context
        memories = _make_sample_memories(5)
        result = format_memories_as_context(memories)
        assert "OBSERVATIONS" in result
        assert "PREFERENCES" in result
        assert "STRATEGIC LESSONS" in result
        assert "CONTENT PATTERNS" in result
        assert "VOICE NOTES" in result

    def test_confidence_labels(self):
        from app.services.agent_memory import format_memories_as_context
        memories = [
            _make_memory(memory_id="m1", content="High conf", confidence=0.9),
            _make_memory(memory_id="m2", content="Medium conf", confidence=0.6),
            _make_memory(memory_id="m3", content="Low conf", confidence=0.3),
        ]
        result = format_memories_as_context(memories)
        assert "high" in result
        assert "medium" in result
        assert "low" in result

    def test_header_present(self):
        from app.services.agent_memory import format_memories_as_context
        memories = [_make_memory()]
        result = format_memories_as_context(memories)
        assert "AGENT MEMORY" in result
        assert "personalize" in result.lower()

    def test_no_platform_tag_when_none(self):
        from app.services.agent_memory import format_memories_as_context
        memories = [_make_memory(platform=None, content="Generic memory")]
        result = format_memories_as_context(memories)
        # The line with "Generic memory" should not have a platform tag
        for line in result.split("\n"):
            if "Generic memory" in line:
                assert "[" not in line.split("confidence:")[0]
                break


# ── Auto-Observation from Metrics Tests ──────────────────

class TestCreateObservationFromMetrics:
    """Test auto-memory creation from post performance."""

    @patch("app.services.agent_memory.create_memory")
    def test_viral_post_creates_observation(self, mock_create):
        from app.services.agent_memory import create_observation_from_metrics
        mock_create.return_value = _make_memory()

        post = {
            "id": "post-1",
            "performance_tier": "viral",
            "hook_type": "story",
            "topic_category": "ai_tools",
            "platform": "youtube",
            "engagement_rate": 0.15,
            "title": "AI Tools That Changed My Life",
        }

        result = create_observation_from_metrics("user-1", post)
        assert result is not None
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["memory_type"] == "observation"
        assert call_kwargs["source"] == "metrics"
        assert "post-1" in call_kwargs["related_post_ids"]

    @patch("app.services.agent_memory.create_memory")
    def test_flop_post_creates_observation(self, mock_create):
        from app.services.agent_memory import create_observation_from_metrics
        mock_create.return_value = _make_memory()

        post = {
            "id": "post-2",
            "performance_tier": "flop",
            "hook_type": "question",
            "topic_category": "general",
            "platform": "linkedin",
            "engagement_rate": 0.001,
            "title": "Random Question Post",
        }

        result = create_observation_from_metrics("user-1", post)
        assert result is not None
        mock_create.assert_called_once()
        assert mock_create.call_args[1]["memory_type"] == "observation"

    def test_average_post_no_observation(self):
        from app.services.agent_memory import create_observation_from_metrics
        post = {
            "id": "post-3",
            "performance_tier": "average",
            "hook_type": "story",
            "topic_category": "ai_tools",
            "platform": "youtube",
        }
        result = create_observation_from_metrics("user-1", post)
        assert result is None

    def test_no_tier_no_observation(self):
        from app.services.agent_memory import create_observation_from_metrics
        post = {"id": "post-4", "performance_tier": None}
        result = create_observation_from_metrics("user-1", post)
        assert result is None


# ── Auto-Observation from Edits Tests ────────────────────

class TestCreateObservationFromEdits:
    """Test auto-memory creation from user editing patterns."""

    def test_trivial_edit_no_observation(self):
        from app.services.agent_memory import create_observation_from_edits
        original = "This is a short hook"
        edited = "This is a short hook!"
        result = create_observation_from_edits("user-1", original, edited)
        assert result is None

    def test_empty_texts_no_observation(self):
        from app.services.agent_memory import create_observation_from_edits
        assert create_observation_from_edits("user-1", "", "hello") is None
        assert create_observation_from_edits("user-1", "hello", "") is None

    @patch("app.services.agent_memory.create_memory")
    def test_significant_edit_creates_observation(self, mock_create):
        from app.services.agent_memory import create_observation_from_edits
        mock_create.return_value = _make_memory(memory_type="preference")

        original = "Have you ever wondered why most content creators fail to build an audience?"
        edited = "Most content creators fail to build an audience."

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {
            "content": json.dumps({
                "preference": "User removes rhetorical questions and prefers direct statements",
                "confidence": 0.7,
            })
        }

        with patch("worker.graph.llm.get_llm_client", return_value=mock_llm):
            result = create_observation_from_edits("user-1", original, edited)

        assert result is not None
        mock_create.assert_called_once()
        assert mock_create.call_args[1]["memory_type"] == "preference"
        assert mock_create.call_args[1]["source"] == "user_edit"


# ── Memory CRUD Tests ───────────────────────────────────

class TestMemoryCRUD:
    """Test create, read, update, delete operations."""

    @patch("app.deps.get_admin_client")
    def test_create_memory_without_embedding(self, mock_admin):
        from app.services.agent_memory import create_memory

        mock_table = _mock_supabase_table(mock_admin, [_make_memory()])

        result = create_memory(
            user_id="user-1",
            memory_type="observation",
            content="Test memory",
            generate_embedding=False,
        )

        assert result["memory_type"] == "observation"
        insert_data = mock_table.insert.call_args[0][0]
        assert "embedding" not in insert_data

    @patch("app.services.embeddings.generate_embedding")
    @patch("app.deps.get_admin_client")
    def test_create_memory_with_embedding(self, mock_admin, mock_gen_emb):
        from app.services.agent_memory import create_memory

        mock_gen_emb.return_value = [0.1] * 1536
        mock_table = _mock_supabase_table(mock_admin, [_make_memory()])

        result = create_memory(
            user_id="user-1",
            memory_type="observation",
            content="Test memory",
            generate_embedding=True,
        )

        assert result is not None
        insert_data = mock_table.insert.call_args[0][0]
        assert "embedding" in insert_data
        assert len(insert_data["embedding"]) == 1536

    @patch("app.deps.get_admin_client")
    def test_list_memories_with_filters(self, mock_admin):
        from app.services.agent_memory import list_memories

        mock_table = _mock_supabase_table(mock_admin, _make_sample_memories(2))

        result = list_memories("user-1", memory_type="observation", status="active")
        assert len(result) == 2

    @patch("app.deps.get_admin_client")
    def test_get_memory_by_id(self, mock_admin):
        from app.services.agent_memory import get_memory_by_id

        mock_table = _mock_supabase_table(mock_admin, [_make_memory()])

        result = get_memory_by_id("mem-1", "user-1")
        assert result["id"] == "mem-1"

    @patch("app.deps.get_admin_client")
    def test_get_memory_by_id_not_found(self, mock_admin):
        from app.services.agent_memory import get_memory_by_id

        _mock_supabase_table(mock_admin, [])

        result = get_memory_by_id("nonexistent", "user-1")
        assert result is None

    @patch("app.deps.get_admin_client")
    def test_delete_memory(self, mock_admin):
        from app.services.agent_memory import delete_memory

        _mock_supabase_table(mock_admin, [_make_memory()])

        result = delete_memory("mem-1", "user-1")
        assert result is True

    @patch("app.deps.get_admin_client")
    def test_delete_memory_not_found(self, mock_admin):
        from app.services.agent_memory import delete_memory

        _mock_supabase_table(mock_admin, [])

        result = delete_memory("nonexistent", "user-1")
        assert result is False


# ── Approval Workflow Tests ──────────────────────────────

class TestApprovalWorkflow:
    """Test approve, dismiss, supersede operations."""

    @patch("app.services.agent_memory.update_memory")
    def test_approve_memory(self, mock_update):
        from app.services.agent_memory import approve_memory

        mock_update.return_value = _make_memory(status="active")
        result = approve_memory("mem-1", "user-1")
        assert result["status"] == "active"
        mock_update.assert_called_once_with("mem-1", "user-1", {"status": "active"})

    @patch("app.services.agent_memory.update_memory")
    def test_approve_with_edit(self, mock_update):
        from app.services.agent_memory import approve_memory

        mock_update.return_value = _make_memory(status="active", content="Edited lesson")
        result = approve_memory("mem-1", "user-1", edited_content="Edited lesson")
        mock_update.assert_called_once_with("mem-1", "user-1", {
            "status": "active",
            "content": "Edited lesson",
        })

    @patch("app.services.agent_memory.update_memory")
    def test_dismiss_memory(self, mock_update):
        from app.services.agent_memory import dismiss_memory

        mock_update.return_value = _make_memory(status="dismissed")
        result = dismiss_memory("mem-1", "user-1")
        assert result["status"] == "dismissed"
        mock_update.assert_called_once_with("mem-1", "user-1", {"status": "dismissed"})

    @patch("app.services.agent_memory.create_memory")
    @patch("app.services.agent_memory.update_memory")
    @patch("app.services.agent_memory.get_memory_by_id")
    def test_supersede_memory(self, mock_get, mock_update, mock_create):
        from app.services.agent_memory import supersede_memory

        old_memory = _make_memory(memory_id="old-1", content="Old observation")
        mock_get.return_value = old_memory
        mock_update.return_value = _make_memory(status="superseded")
        mock_create.return_value = _make_memory(memory_id="new-1", content="New lesson")

        result = supersede_memory("old-1", "user-1", "New lesson")

        assert result["id"] == "new-1"
        mock_update.assert_called_once_with("old-1", "user-1", {"status": "superseded"})
        mock_create.assert_called_once()
        assert mock_create.call_args[1]["source"] == "synthesis"

    @patch("app.services.agent_memory.get_memory_by_id")
    def test_supersede_not_found(self, mock_get):
        from app.services.agent_memory import supersede_memory

        mock_get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            supersede_memory("nonexistent", "user-1", "New content")


# ── Semantic Search Tests ────────────────────────────────

class TestGetRelevantMemories:
    """Test semantic search across memories."""

    def test_empty_user_id(self):
        from app.services.agent_memory import get_relevant_memories
        result = get_relevant_memories("", "hooks and content")
        assert result == []

    def test_empty_query(self):
        from app.services.agent_memory import get_relevant_memories
        result = get_relevant_memories("user-1", "")
        assert result == []

    @patch("app.deps.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_semantic_search_returns_memories(self, mock_gen_emb, mock_admin):
        from app.services.agent_memory import get_relevant_memories

        mock_gen_emb.return_value = [0.1] * 1536

        mock_admin.return_value.rpc.return_value.execute.return_value.data = [
            _make_memory(memory_id="mem-1", content="Story hooks work best"),
            _make_memory(memory_id="mem-2", content="AI tools content outperforms"),
        ]

        # Mock table for last_used_at update
        mock_table = MagicMock()
        mock_admin.return_value.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = get_relevant_memories("user-1", "hooks for YouTube content")
        assert len(result) == 2
        mock_gen_emb.assert_called_once()
        mock_admin.return_value.rpc.assert_called_once_with("match_agent_memories", {
            "query_embedding": [0.1] * 1536,
            "match_user_id": "user-1",
            "match_count": 10,
            "match_threshold": 0.6,
        })

    @patch("app.services.agent_memory._fallback_memory_search")
    @patch("app.services.embeddings.generate_embedding")
    def test_falls_back_on_embedding_error(self, mock_gen_emb, mock_fallback):
        from app.services.agent_memory import get_relevant_memories

        mock_gen_emb.side_effect = Exception("OpenAI unavailable")
        mock_fallback.return_value = [_make_memory()]

        result = get_relevant_memories("user-1", "hooks")
        assert len(result) == 1
        mock_fallback.assert_called_once()

    @patch("app.deps.get_admin_client")
    @patch("app.services.embeddings.generate_embedding")
    def test_platform_filter_applied(self, mock_gen_emb, mock_admin):
        from app.services.agent_memory import get_relevant_memories

        mock_gen_emb.return_value = [0.1] * 1536
        mock_admin.return_value.rpc.return_value.execute.return_value.data = [
            _make_memory(memory_id="m1", platform="youtube"),
            _make_memory(memory_id="m2", platform="linkedin"),
            _make_memory(memory_id="m3", platform=None),
        ]
        mock_table = MagicMock()
        mock_admin.return_value.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = get_relevant_memories("user-1", "hooks", platform="youtube")
        # Should filter to youtube and platform=None memories
        assert len(result) == 2
        platforms = [m.get("platform") for m in result]
        assert "linkedin" not in platforms


# ── Fallback Search Tests ────────────────────────────────

class TestFallbackSearch:
    """Test fallback when semantic search is unavailable."""

    @patch("app.deps.get_admin_client")
    def test_fallback_returns_by_confidence(self, mock_admin):
        from app.services.agent_memory import _fallback_memory_search

        _mock_supabase_table(mock_admin, [
            _make_memory(memory_id="m1", confidence=0.9),
            _make_memory(memory_id="m2", confidence=0.7),
        ])

        result = _fallback_memory_search("user-1")
        assert len(result) == 2

    @patch("app.deps.get_admin_client")
    def test_fallback_with_platform_filter(self, mock_admin):
        from app.services.agent_memory import _fallback_memory_search

        _mock_supabase_table(mock_admin, [
            _make_memory(memory_id="m1", platform="youtube"),
        ])

        result = _fallback_memory_search("user-1", platform="youtube")
        assert len(result) == 1

    @patch("app.deps.get_admin_client")
    def test_fallback_handles_db_error(self, mock_admin):
        from app.services.agent_memory import _fallback_memory_search

        mock_admin.return_value.table.side_effect = Exception("DB down")
        result = _fallback_memory_search("user-1")
        assert result == []


# ── Memory Update Tests ──────────────────────────────────

class TestMemoryUpdate:
    """Test update operations including re-embedding."""

    @patch("app.deps.get_admin_client")
    def test_update_without_content_change(self, mock_admin):
        from app.services.agent_memory import update_memory

        _mock_supabase_table(mock_admin, [_make_memory(confidence=0.9)])

        result = update_memory("mem-1", "user-1", {"confidence": 0.9})
        assert result is not None

    @patch("app.services.embeddings.generate_embedding")
    @patch("app.deps.get_admin_client")
    def test_update_with_content_re_embeds(self, mock_admin, mock_gen_emb):
        from app.services.agent_memory import update_memory

        mock_gen_emb.return_value = [0.2] * 1536
        mock_table = _mock_supabase_table(mock_admin, [_make_memory(content="Updated content")])

        result = update_memory("mem-1", "user-1", {"content": "Updated content"})
        assert result is not None
        update_data = mock_table.update.call_args[0][0]
        assert "embedding" in update_data
        assert len(update_data["embedding"]) == 1536


# ── Synthesis Tests ──────────────────────────────────────

class TestSynthesis:
    """Test memory synthesis (consolidate observations into lessons)."""

    @patch("app.services.agent_memory.list_memories")
    def test_not_enough_observations(self, mock_list):
        from app.services.agent_memory import synthesize_memories

        mock_list.return_value = [_make_memory(), _make_memory(memory_id="m2")]  # Only 2
        result = synthesize_memories("user-1")
        assert result["new_memories_created"] == 0
        assert "Not enough" in result["message"]

    @patch("app.services.agent_memory.create_memory")
    @patch("app.deps.get_admin_client")
    @patch("app.services.agent_memory.list_memories")
    def test_synthesis_groups_and_creates_lessons(self, mock_list, mock_admin, mock_create):
        from app.services.agent_memory import synthesize_memories

        # 3 observations in same category
        observations = [
            _make_memory(memory_id=f"obs-{i}", category="hooks", platform="youtube")
            for i in range(3)
        ]
        mock_list.return_value = observations
        mock_create.return_value = _make_memory(memory_type="lesson", status="pending_approval")

        mock_table = _mock_supabase_table(mock_admin, [])

        mock_llm = MagicMock()
        mock_llm.chat.return_value = {
            "content": json.dumps({
                "lesson": "Story hooks consistently outperform on YouTube",
                "confidence": 0.8,
                "pattern": "story_hooks_youtube",
            })
        }

        with patch("worker.graph.llm.get_llm_client", return_value=mock_llm):
            result = synthesize_memories("user-1")

        assert result["new_memories_created"] == 1
        assert result["memories_superseded"] == 3
        assert len(result["patterns_detected"]) == 1
        mock_create.assert_called_once()
        create_kwargs = mock_create.call_args[1]
        assert create_kwargs["status"] == "pending_approval"
        assert create_kwargs["memory_type"] == "lesson"


# ── Pipeline Integration Tests ───────────────────────────

class TestPipelineIntegration:
    """Test memory context injection in pipeline nodes and brand_chat."""

    def test_gap_analysis_fetch_memory_context_empty_user(self):
        from worker.graph.nodes.gap_analysis import _fetch_memory_context
        result = _fetch_memory_context("")
        assert result == ""

    @patch("app.services.agent_memory.format_memories_as_context")
    @patch("app.services.agent_memory.get_relevant_memories")
    def test_gap_analysis_fetch_memory_context_success(self, mock_get, mock_format):
        from worker.graph.nodes.gap_analysis import _fetch_memory_context

        mock_get.return_value = [_make_memory()]
        mock_format.return_value = "--- AGENT MEMORY ---\nStory hooks work best"

        result = _fetch_memory_context("user-1", "AI tools content")
        assert "AGENT MEMORY" in result
        mock_get.assert_called_once()

    def test_hook_lab_fetch_memory_context_empty_user(self):
        from worker.graph.nodes.hook_lab import _fetch_memory_context
        result = _fetch_memory_context("")
        assert result == ""

    @patch("app.services.agent_memory.format_memories_as_context")
    @patch("app.services.agent_memory.get_relevant_memories")
    def test_hook_lab_fetch_memory_context_success(self, mock_get, mock_format):
        from worker.graph.nodes.hook_lab import _fetch_memory_context

        mock_get.return_value = [_make_memory()]
        mock_format.return_value = "--- AGENT MEMORY ---\nPrefer bold claims"

        result = _fetch_memory_context("user-1", "hooks for AI tools video")
        assert "AGENT MEMORY" in result

    def test_script_gen_fetch_memory_context_empty_user(self):
        from worker.graph.nodes.script_generation import _fetch_memory_context
        result = _fetch_memory_context("")
        assert result == ""

    @patch("app.services.agent_memory.format_memories_as_context")
    @patch("app.services.agent_memory.get_relevant_memories")
    def test_script_gen_fetch_memory_context_success(self, mock_get, mock_format):
        from worker.graph.nodes.script_generation import _fetch_memory_context

        mock_get.return_value = [_make_memory()]
        mock_format.return_value = "--- AGENT MEMORY ---\nConversational style"

        result = _fetch_memory_context("user-1", "script writing")
        assert "AGENT MEMORY" in result

    def test_brand_chat_fetch_memory_context_empty_user(self):
        from app.services.brand_chat import _fetch_memory_context
        result = _fetch_memory_context("")
        assert result == ""

    @patch("app.services.agent_memory.format_memories_as_context")
    @patch("app.services.agent_memory.get_relevant_memories")
    def test_brand_chat_fetch_memory_context_success(self, mock_get, mock_format):
        from app.services.brand_chat import _fetch_memory_context

        mock_get.return_value = [_make_memory()]
        mock_format.return_value = "--- AGENT MEMORY ---\nBrand coaching notes"

        result = _fetch_memory_context("user-1")
        assert "AGENT MEMORY" in result

    def test_build_chat_messages_with_memory(self):
        from app.services.brand_chat import build_chat_messages

        messages = build_chat_messages(
            module="ica",
            conversation=[{"role": "user", "content": "Tell me about my audience"}],
            memory_context="--- AGENT MEMORY ---\nUser prefers concise answers",
        )
        system = messages[0]["content"]
        assert "AGENT MEMORY" in system
        assert "concise answers" in system

    def test_build_chat_messages_without_memory(self):
        from app.services.brand_chat import build_chat_messages

        messages = build_chat_messages(
            module="ica",
            conversation=[{"role": "user", "content": "Hello"}],
        )
        system = messages[0]["content"]
        assert "AGENT MEMORY" not in system

    @patch("app.services.agent_memory.format_memories_as_context")
    @patch("app.services.agent_memory.get_relevant_memories")
    def test_pipeline_graceful_fallback_on_error(self, mock_get, mock_format):
        from worker.graph.nodes.gap_analysis import _fetch_memory_context

        mock_get.side_effect = Exception("DB connection failed")
        result = _fetch_memory_context("user-1", "anything")
        assert result == ""
