"""Tests for the LangGraph content pipeline (Slice 6).

Tests use a mock LLM client (no OpenAI calls) and MemorySaver
(no Postgres needed). Verifies:
  - Individual node execution (signal_research, gap_analysis, etc.)
  - Graph compilation (with and without checkpointer)
  - Full pipeline with 3 interrupt/resume cycles
  - State flow between nodes (selected_topic reaches hook_lab, etc.)
  - Edge cases (invalid IDs fall back, rejection flow)
  - LLM utility functions (JSON parsing with code fences)
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Mock LLM ──────────────────────────────────────────────


class MockLLMClient:
    """Mock LLM that returns pre-configured responses in order."""

    def __init__(self):
        self.calls: List[List[Dict[str, str]]] = []
        self._responses: List[str] = []

    def add_response(self, data: Any) -> None:
        """Queue a JSON response."""
        self._responses.append(json.dumps(data))

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        self.calls.append(messages)
        if not self._responses:
            raise RuntimeError(
                f"MockLLMClient: no more responses queued "
                f"(call #{len(self.calls)})"
            )
        content = self._responses.pop(0)
        return {
            "content": content,
            "usage": {"input_tokens": 100, "output_tokens": 200},
        }


# ── Canned Responses ─────────────────────────────────────

MOCK_SIGNALS = {
    "signals": [
        {
            "type": "trending_topic",
            "title": "AI agents for content creation",
            "description": "Growing interest in using AI agents",
            "source": "youtube",
            "relevance_score": 85,
        },
        {
            "type": "pain_point",
            "title": "Content consistency is hard",
            "description": "Creators struggle with posting regularly",
            "source": "reddit",
            "relevance_score": 90,
        },
    ]
}

MOCK_TOPICS = {
    "topic_candidates": [
        {
            "id": "topic-1",
            "title": "How AI Agents Will Replace Your Content Team",
            "audience_pain": "Content creation takes too long",
            "why_now": "AI agent technology just reached usable quality",
            "novelty_angle": "Show real cost comparison",
            "hooks": ["What if you could 10x your content output?"],
            "suggested_structure": "Problem > Solution > Proof > CTA",
            "required_proof": "Show actual time savings",
            "risk_flags": [],
            "opportunity_score": 92,
            "score_breakdown": {
                "novelty": 20, "demand": 25, "creator_fit": 22,
                "saturation": 10, "proof_available": 15,
            },
            "sources": ["youtube", "reddit"],
        },
        {
            "id": "topic-2",
            "title": "The Content Creation Stack Nobody Talks About",
            "audience_pain": "Too many tools, no integration",
            "why_now": "Tool fatigue is at an all-time high",
            "novelty_angle": "Single system vs 5 tools",
            "hooks": ["I replaced 5 tools with one system"],
            "suggested_structure": "Story > Problem > Solution > Demo",
            "required_proof": "Tool cost comparison",
            "risk_flags": ["may feel like an ad"],
            "opportunity_score": 78,
            "score_breakdown": {
                "novelty": 15, "demand": 20, "creator_fit": 18,
                "saturation": 15, "proof_available": 10,
            },
            "sources": ["reddit"],
        },
    ]
}

MOCK_HOOKS = {
    "hook_candidates": [
        {
            "id": "hook-1",
            "hook_text": "I spent $50,000 on content tools last year.",
            "hook_type": "data",
            "score_breakdown": {
                "clarity": 22, "curiosity_gap": 20,
                "specificity": 23, "credibility": 20,
            },
            "total_score": 85,
        },
        {
            "id": "hook-2",
            "hook_text": "Every content creator is making the same mistake.",
            "hook_type": "contrarian",
            "score_breakdown": {
                "clarity": 20, "curiosity_gap": 22,
                "specificity": 15, "credibility": 18,
            },
            "total_score": 75,
        },
    ]
}

MOCK_LONG_SCRIPT = {
    "youtube_long": {
        "title_used": "How AI Agents Will Replace Your Content Team",
        "hook": "I spent $50,000 on content tools last year.",
        "sections": [
            {
                "heading": "The Problem",
                "body": "Content creation is broken.",
                "visual_cue": "Show tool screenshots",
            },
            {
                "heading": "The Solution",
                "body": "AI agents that actually work.",
                "visual_cue": "Demo the workflow",
            },
            {
                "heading": "The Results",
                "body": "Here are real numbers.",
                "visual_cue": "Show analytics",
            },
        ],
        "cta": "Try the system using the link below",
        "estimated_duration_min": 12,
    }
}

MOCK_SHORTS = {
    "youtube_shorts": [
        {
            "title": "The $50K content tool mistake",
            "script": "I wasted $50K on content tools.",
            "hook": "Stop wasting money on tools",
            "duration_sec": 58,
        },
        {
            "title": "One AI agent vs 5 tools",
            "script": "What if I told you one agent could do it all?",
            "hook": "Replace your entire stack",
            "duration_sec": 45,
        },
        {
            "title": "Content creation in 2024",
            "script": "The game has changed.",
            "hook": "Everything you know is wrong",
            "duration_sec": 52,
        },
    ]
}

MOCK_METADATA = {
    "titles": [
        "How AI Agents Will Replace Your Content Team in 2024",
        "I Replaced 5 Content Tools With ONE AI Agent",
        "The AI Content System That Actually Works",
    ],
    "description": "In this video, I break down the exact AI agent system...",
    "tags": ["AI agents", "content creation", "productivity", "AI tools"],
    "pinned_comment": "Want to try this system? Link in description!",
    "thumbnail_brief": [
        {
            "concept": "Split screen: 5 tool logos vs 1 AI",
            "text_overlay": "5 Tools > 1 Agent",
        },
    ],
}

MOCK_EDITED_PACK = {
    "edited_pack": {
        "youtube_long": MOCK_LONG_SCRIPT["youtube_long"],
        "youtube_shorts": MOCK_SHORTS["youtube_shorts"],
        "titles": MOCK_METADATA["titles"],
        "description": "Improved: In this video, I break down...",
        "tags": MOCK_METADATA["tags"],
        "pinned_comment": MOCK_METADATA["pinned_comment"],
        "thumbnail_brief": MOCK_METADATA["thumbnail_brief"],
    },
    "edit_summary": "Tightened the hook, removed filler words.",
}

MOCK_TEST_RESULTS = {
    "test_results": [
        {
            "asset_type": "youtube_long",
            "passed": True,
            "issues": [],
            "risk_flags": [],
        },
        {
            "asset_type": "youtube_short_1",
            "passed": True,
            "issues": [],
            "risk_flags": [],
        },
        {
            "asset_type": "youtube_short_2",
            "passed": True,
            "issues": [],
            "risk_flags": [],
        },
        {
            "asset_type": "youtube_short_3",
            "passed": True,
            "issues": [],
            "risk_flags": [],
        },
    ],
    "overall_passed": True,
}


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    """Create and install a mock LLM client, reset after test."""
    from worker.graph.llm import set_llm_client

    client = MockLLMClient()
    set_llm_client(client)
    yield client
    set_llm_client(None)


@pytest.fixture
def initial_state():
    """Create a basic initial state for pipeline tests."""
    from worker.graph.pipeline import create_initial_state

    return create_initial_state(
        workflow_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        goal_text="Create content about AI agents replacing content teams",
        profile_snapshot={
            "channel_name": "TestCreator",
            "brand_voice": {"tone": "conversational", "formality": "casual"},
            "audience": {"age_range": "25-35", "interests": ["AI", "content"]},
            "constraints": {"max_video_length_min": 15},
        },
        workflow_settings={
            "sources": {"youtube": True, "reddit": True},
        },
    )


# ── Individual Node Tests ─────────────────────────────────


class TestSignalResearch:
    """Node 1: signal_research generates research signals from LLM."""

    def test_returns_signals(self, mock_llm, initial_state):
        from worker.graph.nodes.signal_research import signal_research

        mock_llm.add_response(MOCK_SIGNALS)
        result = signal_research(initial_state)

        assert "research_signals" in result
        assert len(result["research_signals"]) == 2
        assert result["current_step"] == "signal_research"
        assert len(mock_llm.calls) == 1

    def test_includes_sources_in_prompt(self, mock_llm, initial_state):
        from worker.graph.nodes.signal_research import signal_research

        mock_llm.add_response(MOCK_SIGNALS)
        signal_research(initial_state)

        user_msg = mock_llm.calls[0][1]["content"]
        assert "youtube" in user_msg
        assert "reddit" in user_msg

    def test_handles_empty_signals(self, mock_llm, initial_state):
        from worker.graph.nodes.signal_research import signal_research

        mock_llm.add_response({"signals": []})
        result = signal_research(initial_state)

        assert result["research_signals"] == []


class TestGapAnalysis:
    """Node 2: gap_analysis generates scored topic candidates."""

    def test_returns_sorted_candidates(self, mock_llm, initial_state):
        from worker.graph.nodes.gap_analysis import gap_analysis

        state = {**initial_state, "research_signals": MOCK_SIGNALS["signals"]}
        mock_llm.add_response(MOCK_TOPICS)
        result = gap_analysis(state)

        assert "topic_candidates" in result
        assert len(result["topic_candidates"]) == 2
        # Should be sorted by opportunity_score desc
        scores = [t["opportunity_score"] for t in result["topic_candidates"]]
        assert scores == sorted(scores, reverse=True)
        assert result["current_step"] == "gap_analysis_topic_candidates"

    def test_handles_empty_candidates(self, mock_llm, initial_state):
        from worker.graph.nodes.gap_analysis import gap_analysis

        state = {**initial_state, "research_signals": []}
        mock_llm.add_response({"topic_candidates": []})
        result = gap_analysis(state)

        assert result["topic_candidates"] == []


class TestScriptGeneration:
    """Node 5: script_generation makes 3 LLM calls for the full pack."""

    def test_generates_full_content_pack(self, mock_llm, initial_state):
        from worker.graph.nodes.script_generation import script_generation

        state = {
            **initial_state,
            "selected_topic": MOCK_TOPICS["topic_candidates"][0],
            "selected_hook": MOCK_HOOKS["hook_candidates"][0],
        }

        mock_llm.add_response(MOCK_LONG_SCRIPT)
        mock_llm.add_response(MOCK_SHORTS)
        mock_llm.add_response(MOCK_METADATA)

        result = script_generation(state)

        assert "content_pack" in result
        pack = result["content_pack"]
        assert "youtube_long" in pack
        assert len(pack["youtube_shorts"]) == 3
        assert len(pack["titles"]) == 3
        assert pack["description"]
        assert len(pack["tags"]) > 0
        assert pack["pinned_comment"]
        assert len(pack["thumbnail_brief"]) > 0
        assert result["current_step"] == "script_generation"
        # 3 LLM calls: long script, shorts, metadata
        assert len(mock_llm.calls) == 3


class TestEditor:
    """Node 6: editor refines the content pack."""

    def test_returns_edited_pack(self, mock_llm, initial_state):
        from worker.graph.nodes.editor import editor

        state = {
            **initial_state,
            "content_pack": {
                "youtube_long": MOCK_LONG_SCRIPT["youtube_long"],
                "youtube_shorts": MOCK_SHORTS["youtube_shorts"],
            },
        }

        mock_llm.add_response(MOCK_EDITED_PACK)
        result = editor(state)

        assert "edited_pack" in result
        assert result["current_step"] == "editor"
        assert len(mock_llm.calls) == 1


class TestTestingNode:
    """Node 7: testing runs quality checks."""

    def test_returns_test_report(self, mock_llm, initial_state):
        from worker.graph.nodes.testing import testing

        state = {
            **initial_state,
            "edited_pack": MOCK_EDITED_PACK["edited_pack"],
        }

        mock_llm.add_response(MOCK_TEST_RESULTS)
        result = testing(state)

        assert "test_report" in result
        assert "tests_passed" in result
        assert result["tests_passed"] is True
        assert len(result["test_report"]) == 4
        assert result["current_step"] == "testing"

    def test_failed_tests(self, mock_llm, initial_state):
        from worker.graph.nodes.testing import testing

        state = {**initial_state, "edited_pack": {}}
        mock_llm.add_response({
            "test_results": [
                {
                    "asset_type": "youtube_long",
                    "passed": False,
                    "issues": ["Missing CTA"],
                    "risk_flags": ["incomplete"],
                },
            ],
            "overall_passed": False,
        })
        result = testing(state)

        assert result["tests_passed"] is False
        assert result["test_report"][0]["passed"] is False


# ── Graph Compilation Tests ───────────────────────────────


class TestGraphCompilation:
    """Verify the graph builds and has the correct structure."""

    def test_graph_builds_without_checkpointer(self):
        from worker.graph.pipeline import build_graph

        graph = build_graph(checkpointer=None)
        assert graph is not None

    def test_graph_builds_with_memory_saver(self):
        from langgraph.checkpoint.memory import MemorySaver
        from worker.graph.pipeline import build_graph

        graph = build_graph(checkpointer=MemorySaver())
        assert graph is not None

    def test_initial_state_has_all_keys(self):
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-123",
            user_id="user-456",
            goal_text="Test goal",
            profile_snapshot={"channel_name": "Test"},
            workflow_settings={"sources": {}},
        )

        assert state["workflow_id"] == "wf-123"
        assert state["user_id"] == "user-456"
        assert state["goal_text"] == "Test goal"
        assert state["research_signals"] == []
        assert state["topic_candidates"] == []
        assert state["selected_topic"] is None
        assert state["hook_candidates"] == []
        assert state["selected_hook"] is None
        assert state["content_pack"] is None
        assert state["edited_pack"] is None
        assert state["test_report"] == []
        assert state["tests_passed"] is False
        assert state["approval_decision"] is None
        assert state["rejection_feedback"] is None
        assert state["resources_used"] == []
        assert state["current_step"] == ""


# ── Full Pipeline Tests (with interrupt/resume) ──────────


class TestFullPipeline:
    """Test the complete pipeline flow with 3 interrupt/resume cycles.

    Pipeline flow:
        signal_research → gap_analysis → topic_selection(INTERRUPT)
        → hook_lab(LLM + INTERRUPT)
        → script_generation → editor → testing → approval(INTERRUPT)
        → DONE

    Each phase is a separate graph.invoke() call.
    """

    def _queue_phase1_responses(self, mock_llm):
        """Phase 1 (fresh run → topic interrupt): 2 LLM calls."""
        mock_llm.add_response(MOCK_SIGNALS)       # signal_research
        mock_llm.add_response(MOCK_TOPICS)         # gap_analysis

    def _queue_phase2_responses(self, mock_llm):
        """Phase 2 (resume topic → hook interrupt): 1 LLM call."""
        mock_llm.add_response(MOCK_HOOKS)          # hook_lab

    def _queue_phase3_responses(self, mock_llm):
        """Phase 3 (resume hook → approval interrupt): 6 LLM calls.

        hook_lab re-executes its LLM call on resume (node replays
        from start, interrupt() returns resume value immediately).
        """
        mock_llm.add_response(MOCK_HOOKS)          # hook_lab replay
        mock_llm.add_response(MOCK_LONG_SCRIPT)    # script_generation (1/3)
        mock_llm.add_response(MOCK_SHORTS)          # script_generation (2/3)
        mock_llm.add_response(MOCK_METADATA)         # script_generation (3/3)
        mock_llm.add_response(MOCK_EDITED_PACK)     # editor
        mock_llm.add_response(MOCK_TEST_RESULTS)    # testing

    def _build_graph_and_config(self, workflow_id):
        from langgraph.checkpoint.memory import MemorySaver
        from worker.graph.pipeline import build_graph

        checkpointer = MemorySaver()
        graph = build_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": workflow_id}}
        return graph, config

    def test_phase1_interrupts_at_topic_selection(self, mock_llm, initial_state):
        """Fresh run stops at topic_selection interrupt."""
        graph, config = self._build_graph_and_config(initial_state["workflow_id"])
        self._queue_phase1_responses(mock_llm)

        graph.invoke(initial_state, config=config)

        state = graph.get_state(config)
        assert len(state.tasks) > 0
        task = state.tasks[0]
        assert hasattr(task, "interrupts") and len(task.interrupts) > 0
        assert task.name == "topic_selection"

        # 2 LLM calls were made
        assert len(mock_llm.calls) == 2

    def test_phase2_resume_topic_interrupts_at_hook_lab(self, mock_llm, initial_state):
        """After topic selection, pipeline resumes and stops at hook_lab."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        # Phase 2: resume with topic selection
        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        state = graph.get_state(config)
        assert len(state.tasks) > 0
        task = state.tasks[0]
        assert hasattr(task, "interrupts") and len(task.interrupts) > 0
        assert task.name == "hook_lab"

        # 2 (phase 1) + 1 (phase 2 hook_lab) = 3 total
        assert len(mock_llm.calls) == 3

    def test_phase3_resume_hook_interrupts_at_approval(self, mock_llm, initial_state):
        """After hook selection, pipeline runs through to approval interrupt."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        # Phase 2
        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        # Phase 3: resume with hook selection
        self._queue_phase3_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_hook_id": "hook-1"}),
            config=config,
        )

        state = graph.get_state(config)
        assert len(state.tasks) > 0
        task = state.tasks[0]
        assert hasattr(task, "interrupts") and len(task.interrupts) > 0
        assert task.name == "approval"

    def test_full_pipeline_completes_with_approval(self, mock_llm, initial_state):
        """Full run: 3 interrupt/resume cycles → approved."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1: run → topic interrupt
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        # Phase 2: resume topic → hook interrupt
        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        # Phase 3: resume hook → approval interrupt
        self._queue_phase3_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_hook_id": "hook-1"}),
            config=config,
        )

        # Phase 4: approve
        graph.invoke(
            Command(resume={"decision": "approved", "feedback": ""}),
            config=config,
        )

        # Pipeline should be complete
        state = graph.get_state(config)
        has_interrupt = any(
            hasattr(t, "interrupts") and t.interrupts
            for t in getattr(state, "tasks", [])
        )
        assert not has_interrupt

        # Final state should have approval decision
        values = state.values
        assert values.get("approval_decision") == "approved"
        assert values.get("current_step") == "approval"

    def test_selected_topic_flows_through_pipeline(self, mock_llm, initial_state):
        """Verify selected topic propagates to subsequent nodes."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1: run → topic interrupt
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        # Check state after topic interrupt — topics should be present
        state = graph.get_state(config)
        values = state.values
        assert len(values.get("topic_candidates", [])) == 2
        assert values["topic_candidates"][0]["id"] == "topic-1"

        # Phase 2: select topic-1 → hook interrupt
        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        # selected_topic should be committed (topic_selection completed)
        state = graph.get_state(config)
        values = state.values
        assert values.get("selected_topic") is not None
        assert values["selected_topic"]["id"] == "topic-1"
        assert values["selected_topic"]["title"] == "How AI Agents Will Replace Your Content Team"

    def test_rejection_flow(self, mock_llm, initial_state):
        """User rejects at approval — state reflects rejection."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Run all phases to approval
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        self._queue_phase3_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_hook_id": "hook-1"}),
            config=config,
        )

        # Reject
        graph.invoke(
            Command(resume={"decision": "rejected", "feedback": "Too promotional"}),
            config=config,
        )

        state = graph.get_state(config)
        values = state.values
        assert values.get("approval_decision") == "rejected"
        assert values.get("rejection_feedback") == "Too promotional"

    def test_content_pack_in_final_state(self, mock_llm, initial_state):
        """Verify the full content pack exists in final state."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Run through all 4 phases
        self._queue_phase1_responses(mock_llm)
        graph.invoke(initial_state, config=config)

        self._queue_phase2_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        self._queue_phase3_responses(mock_llm)
        graph.invoke(
            Command(resume={"selected_hook_id": "hook-1"}),
            config=config,
        )

        graph.invoke(
            Command(resume={"decision": "approved", "feedback": ""}),
            config=config,
        )

        state = graph.get_state(config)
        values = state.values

        # Content pack (from script_generation)
        assert values.get("content_pack") is not None
        assert "youtube_long" in values["content_pack"]
        assert len(values["content_pack"]["youtube_shorts"]) == 3

        # Edited pack (from editor)
        assert values.get("edited_pack") is not None

        # Test report (from testing)
        assert len(values.get("test_report", [])) == 4
        assert values.get("tests_passed") is True


# ── Edge Case Tests ───────────────────────────────────────


class TestEdgeCases:
    """Test fallback behavior and edge cases."""

    def _build_graph_and_config(self, workflow_id):
        from langgraph.checkpoint.memory import MemorySaver
        from worker.graph.pipeline import build_graph

        checkpointer = MemorySaver()
        graph = build_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": workflow_id}}
        return graph, config

    def test_topic_fallback_on_invalid_id(self, mock_llm, initial_state):
        """Invalid selected_topic_id falls back to first candidate."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1
        mock_llm.add_response(MOCK_SIGNALS)
        mock_llm.add_response(MOCK_TOPICS)
        graph.invoke(initial_state, config=config)

        # Resume with bogus topic ID
        mock_llm.add_response(MOCK_HOOKS)  # hook_lab still needs a response
        graph.invoke(
            Command(resume={"selected_topic_id": "nonexistent-id"}),
            config=config,
        )

        state = graph.get_state(config)
        values = state.values
        # Should fall back to first candidate (topic-1, highest score)
        assert values["selected_topic"]["id"] == "topic-1"

    def test_hook_fallback_on_invalid_id(self, mock_llm, initial_state):
        """Invalid selected_hook_id falls back to top-scored hook."""
        from langgraph.types import Command

        graph, config = self._build_graph_and_config(initial_state["workflow_id"])

        # Phase 1
        mock_llm.add_response(MOCK_SIGNALS)
        mock_llm.add_response(MOCK_TOPICS)
        graph.invoke(initial_state, config=config)

        # Phase 2
        mock_llm.add_response(MOCK_HOOKS)
        graph.invoke(
            Command(resume={"selected_topic_id": "topic-1"}),
            config=config,
        )

        # Phase 3 with bogus hook ID
        mock_llm.add_response(MOCK_HOOKS)       # hook_lab replay
        mock_llm.add_response(MOCK_LONG_SCRIPT)  # script_generation
        mock_llm.add_response(MOCK_SHORTS)
        mock_llm.add_response(MOCK_METADATA)
        mock_llm.add_response(MOCK_EDITED_PACK)  # editor
        mock_llm.add_response(MOCK_TEST_RESULTS)  # testing

        graph.invoke(
            Command(resume={"selected_hook_id": "nonexistent-hook"}),
            config=config,
        )

        state = graph.get_state(config)
        values = state.values
        # Should fall back to highest-scored hook (hook-1)
        assert values["selected_hook"]["id"] == "hook-1"

    def test_empty_sources_defaults(self, mock_llm):
        """Pipeline handles missing sources gracefully."""
        from worker.graph.nodes.signal_research import signal_research
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-no-sources",
            user_id="user-1",
            goal_text="Test with no sources",
            profile_snapshot={},
            workflow_settings={},  # no sources key
        )

        mock_llm.add_response(MOCK_SIGNALS)
        result = signal_research(state)

        # Should still work — defaults to "general web research"
        assert len(result["research_signals"]) == 2
        user_msg = mock_llm.calls[0][1]["content"]
        assert "general web research" in user_msg


# ── LLM Utility Tests ────────────────────────────────────


class TestLLMUtils:
    """Test the parse_json_response helper and client management."""

    def test_parse_clean_json(self):
        from worker.graph.llm import parse_json_response

        result = parse_json_response('{"foo": "bar"}')
        assert result == {"foo": "bar"}

    def test_parse_json_with_json_fence(self):
        from worker.graph.llm import parse_json_response

        text = '```json\n{"foo": "bar"}\n```'
        result = parse_json_response(text)
        assert result == {"foo": "bar"}

    def test_parse_json_with_bare_fence(self):
        from worker.graph.llm import parse_json_response

        text = '```\n{"foo": "bar"}\n```'
        result = parse_json_response(text)
        assert result == {"foo": "bar"}

    def test_parse_json_with_whitespace(self):
        from worker.graph.llm import parse_json_response

        text = '  \n  {"foo": "bar"}  \n  '
        result = parse_json_response(text)
        assert result == {"foo": "bar"}

    def test_parse_invalid_json_raises(self):
        from worker.graph.llm import parse_json_response, LLMResponseParseError

        with pytest.raises(LLMResponseParseError):
            parse_json_response("not json at all")

    def test_set_and_get_client(self):
        from worker.graph.llm import get_llm_client, set_llm_client

        mock = MockLLMClient()
        set_llm_client(mock)
        assert get_llm_client() is mock

        set_llm_client(None)
        # After reset, get_llm_client returns a new OpenAIClient
        # (we don't test that to avoid needing a real API key)


# ── Executor Constant Tests ──────────────────────────────


class TestExecutorConstants:
    """Verify executor constants match the pipeline structure."""

    def test_interrupt_status_map(self):
        from worker.executor import INTERRUPT_STATUS

        assert INTERRUPT_STATUS["topic_selection"] == "awaiting_topic"
        assert INTERRUPT_STATUS["hook_lab"] == "awaiting_hook"
        assert INTERRUPT_STATUS["approval"] == "awaiting_approval"
        assert len(INTERRUPT_STATUS) == 3

    def test_pipeline_steps_order(self):
        from worker.executor import PIPELINE_STEPS

        assert PIPELINE_STEPS[0] == "signal_research"
        assert PIPELINE_STEPS[-1] == "approval"
        assert len(PIPELINE_STEPS) == 8


# ── Brand Data Pipeline Integration Tests ────────────────


BRAND_PROFILE = {
    "channel_name": "TestCreator",
    "brand_voice": {"tone": "conversational"},
    "audience": {"age_range": "25-35"},
    "constraints": {},
    "ica": {
        "demographics": {"occupation": "Tech Startup Founder", "location": "North America"},
        "big_need": "Lack time to build personal brand",
        "big_want": "Thought leadership and revenue",
        "pains": [{"pain": "No time for content"}, {"pain": "Inconsistent posting"}],
        "desires": [{"desire": "Authority in niche"}],
        "buying_motivations": {
            "money": "Increase revenue",
            "time": "No time to write content",
        },
    },
    "offer": {
        "what": "LinkedIn personal branding service",
        "target_audience": "Tech founders doing $1M-$10M revenue",
        "differentiator": "AI + human ghostwriting combo",
        "past_results": "Client X got 50 leads in 30 days",
        "first_move": "Book a discovery call",
        "market": {
            "niche_statement": "I help tech founders build authority on LinkedIn",
            "massive_pains": ["No time for content", "Inconsistent posting"],
        },
    },
    "brand": {
        "statement": "We help tech founders achieve inbound leads by building their personal brand on LinkedIn",
        "it_factor": {
            "unfair_advantage": "Lost 20kg, understand compounding",
            "leverage_for_brand": "Storytell about transformation",
        },
        "content_pillars": ["Personal branding", "LinkedIn growth", "AI tools"],
    },
}


class TestBrandDataInPrompts:
    """Verify brand data (ICA, offer, brand) flows into pipeline prompts."""

    def test_signal_research_includes_ica(self, mock_llm):
        from worker.graph.nodes.signal_research import signal_research
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-brand-1",
            user_id="user-1",
            goal_text="Content about personal branding",
            profile_snapshot=BRAND_PROFILE,
            workflow_settings={"sources": {"youtube": True}},
        )

        mock_llm.add_response(MOCK_SIGNALS)
        signal_research(state)

        user_msg = mock_llm.calls[0][1]["content"]
        assert "Tech Startup Founder" in user_msg
        assert "Lack time to build personal brand" in user_msg
        assert "No time for content" in user_msg
        assert "Increase revenue" in user_msg

    def test_signal_research_includes_offer(self, mock_llm):
        from worker.graph.nodes.signal_research import signal_research
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-brand-2",
            user_id="user-1",
            goal_text="Content about personal branding",
            profile_snapshot=BRAND_PROFILE,
            workflow_settings={"sources": {"youtube": True}},
        )

        mock_llm.add_response(MOCK_SIGNALS)
        signal_research(state)

        user_msg = mock_llm.calls[0][1]["content"]
        assert "LinkedIn personal branding service" in user_msg
        assert "tech founders build authority on LinkedIn" in user_msg
        assert "Personal branding" in user_msg

    def test_gap_analysis_includes_brand_data(self, mock_llm):
        from worker.graph.nodes.gap_analysis import gap_analysis
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-brand-3",
            user_id="user-1",
            goal_text="Content about personal branding",
            profile_snapshot=BRAND_PROFILE,
            workflow_settings={},
        )
        state["research_signals"] = MOCK_SIGNALS["signals"]

        mock_llm.add_response(MOCK_TOPICS)
        gap_analysis(state)

        user_msg = mock_llm.calls[0][1]["content"]
        assert "Tech Startup Founder" in user_msg
        assert "LinkedIn personal branding service" in user_msg

    def test_script_generation_includes_brand_context(self, mock_llm):
        from worker.graph.nodes.script_generation import script_generation
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-brand-4",
            user_id="user-1",
            goal_text="Content about personal branding",
            profile_snapshot=BRAND_PROFILE,
            workflow_settings={},
        )
        state["selected_topic"] = MOCK_TOPICS["topic_candidates"][0]
        state["selected_hook"] = MOCK_HOOKS["hook_candidates"][0]

        mock_llm.add_response(MOCK_LONG_SCRIPT)
        mock_llm.add_response(MOCK_SHORTS)
        mock_llm.add_response(MOCK_METADATA)
        script_generation(state)

        # Long script prompt (call 0) should have brand + offer
        long_user_msg = mock_llm.calls[0][1]["content"]
        assert "tech founders achieve inbound leads" in long_user_msg
        assert "LinkedIn personal branding service" in long_user_msg
        assert "Lost 20kg" in long_user_msg

        # Shorts prompt (call 1) should have brand context
        shorts_user_msg = mock_llm.calls[1][1]["content"]
        assert "tech founders achieve inbound leads" in shorts_user_msg

    def test_empty_brand_data_uses_fallbacks(self, mock_llm):
        from worker.graph.nodes.signal_research import signal_research
        from worker.graph.pipeline import create_initial_state

        state = create_initial_state(
            workflow_id="wf-no-brand",
            user_id="user-1",
            goal_text="General content",
            profile_snapshot={"channel_name": "Test"},
            workflow_settings={"sources": {"youtube": True}},
        )

        mock_llm.add_response(MOCK_SIGNALS)
        signal_research(state)

        user_msg = mock_llm.calls[0][1]["content"]
        assert "No ICA defined yet" in user_msg
        assert "No offer defined yet" in user_msg
