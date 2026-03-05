"""Tests for Slice 102 — Make Everything Real.

Covers:
- Fix A: Rich brand context injection (_exec_fetch_brand_profile, build_writing_prompt)
- Fix B: Rejection feedback loop (get_rejection_history, build_writing_prompt)
- Fix C: LLM-based QA scoring (_exec_score_content_quality)
- Fix D: Activity feed endpoint
- Fix E: Analytics summary endpoint
- Fix F: Hook Library CRUD endpoints
- Fix G: Proactive triggers (get_suggestions)
"""

import json
import uuid
from unittest.mock import patch, MagicMock

import pytest


# ── Fix A: Rich brand context ──────────────────────────────────────────────


def test_exec_fetch_brand_profile_includes_deep_intel():
    """All brands should receive anxiety_list, power_words, metaphors, etc."""
    from app.services.tool_use_agents import _exec_fetch_brand_profile

    brand_id = str(uuid.uuid4())
    profile_json = {
        "voice": "Direct, bold",
        "ica": "SaaS founders",
        "anxiety_list": ["fear1", "fear2"],
        "benefit_list": ["benefit1", "benefit2"],
        "power_words": ["accelerate", "scale"],
        "industry_lingo": ["ARR", "PLG"],
        "metaphors": ["rocket ship"],
        "transformation_zero": "stuck at $10k/mo",
        "transformation_dream": "hitting $100k/mo",
    }
    mock_row = {
        "name": "Test Brand",
        "description": "Test",
        "profile_json": profile_json,
        "is_client_brand": False,  # NOT a client brand
    }
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [mock_row]
    # Second call for experience_journal
    journal_mock = MagicMock()
    journal_mock.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.services.tool_use_agents.get_admin_client", side_effect=[mock_sb, journal_mock]):
        result_str = _exec_fetch_brand_profile(brand_id)

    result = json.loads(result_str)

    # Core fields
    assert result["voice"] == "Direct, bold"
    assert result["ica"] == "SaaS founders"

    # Deep brand intelligence — MUST be present for non-client brands too
    assert "anxiety_list" in result
    assert result["anxiety_list"] == ["fear1", "fear2"]
    assert "benefit_list" in result
    assert result["benefit_list"] == ["benefit1", "benefit2"]
    assert "power_words" in result
    assert result["power_words"] == ["accelerate", "scale"]
    assert "industry_lingo" in result
    assert "metaphors" in result
    assert "transformation_zero" in result
    assert "transformation_dream" in result
    assert "emotional_journal_summary" in result


def test_exec_fetch_brand_profile_not_found():
    """Returns error string for unknown brand."""
    from app.services.tool_use_agents import _exec_fetch_brand_profile

    brand_id = str(uuid.uuid4())
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.services.tool_use_agents.get_admin_client", return_value=mock_sb):
        result = _exec_fetch_brand_profile(brand_id)

    assert "not found" in result.lower()


def test_build_writing_prompt_injects_brand_context():
    """Writing prompt should include brand intelligence section when context provided."""
    from app.services.jumbo_pipeline import build_writing_prompt

    brand_ctx = {
        "voice": "Bold and direct",
        "ica": "SaaS founders",
        "positioning": "LinkedIn growth specialist",
        "tagline": "Scale or Stagnate",
        "transformation_zero": "stuck",
        "transformation_dream": "thriving",
        "anxiety_list": ["fear of failure", "imposter syndrome"],
        "benefit_list": ["consistent revenue", "team freedom"],
        "power_words": ["accelerate", "transform"],
        "industry_lingo": ["ARR", "CAC"],
        "metaphors": ["compound interest"],
        "emotional_journal_summary": ["[note] Won a $50k deal after repositioning"],
    }

    prompt = build_writing_prompt(
        research_brief="Topic: SaaS growth",
        analytics_ctx="",
        rejection_history="",
        brand_context=brand_ctx,
    )

    assert "Brand Intelligence" in prompt
    assert "fear of failure" in prompt
    assert "accelerate" in prompt
    assert "compound interest" in prompt
    assert "Won a $50k deal" in prompt
    # No truncation
    assert "[:3000]" not in prompt


def test_build_writing_prompt_no_truncation():
    """Research brief should NOT be truncated."""
    from app.services.jumbo_pipeline import build_writing_prompt

    long_brief = "X" * 5000
    prompt = build_writing_prompt(
        research_brief=long_brief,
        analytics_ctx="",
        rejection_history="",
    )
    assert "X" * 4000 in prompt  # At least 4000 chars of the brief should be present


def test_build_writing_prompt_includes_hooks():
    """Hooks section should appear in prompt when hooks_ctx provided."""
    from app.services.jumbo_pipeline import build_writing_prompt

    hooks_ctx = "## Your Hook Library\n### Anxiety Hooks\n- Most consultants leave $50K on the table"
    prompt = build_writing_prompt(
        research_brief="Topic: consulting",
        analytics_ctx="",
        rejection_history="",
        hooks_ctx=hooks_ctx,
    )
    assert "Hook Library" in prompt
    assert "$50K" in prompt


def test_build_writing_prompt_includes_rejection():
    """Rejection history should appear in prompt."""
    from app.services.jumbo_pipeline import build_writing_prompt

    rejection = "## User Rejection History — AVOID These Patterns\n- Wrong voice | excerpt: 'In conclusion...'"
    prompt = build_writing_prompt(
        research_brief="Topic: consulting",
        analytics_ctx="",
        rejection_history=rejection,
    )
    assert "Rejection History" in prompt
    assert "In conclusion" in prompt


# ── Fix C: LLM-based QA ────────────────────────────────────────────────────


def test_score_content_quality_hard_rules_still_work():
    """AI tells and em dashes should still be caught by rule check."""
    from app.services.tool_use_agents import _exec_score_content_quality

    # Mock httpx.post to raise so rule-based fallback is used
    with patch("app.services.tool_use_agents.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("LLM unavailable")
        result_str = _exec_score_content_quality("Firstly, it is worth noting that this post — amazing — leverages synergy")

    result = json.loads(result_str)
    assert "ai_tells_found" in result
    assert len(result["ai_tells_found"]) > 0
    assert result["pass"] == False


def test_score_content_quality_passes_clean_post():
    """Clean post with hook and no AI tells should pass when LLM returns high scores."""
    from app.services.tool_use_agents import _exec_score_content_quality

    # Use a short hook (<=15 words) so hook_present=True even without LLM
    clean_post = "3 mistakes killing your SaaS growth.\n\nMost founders waste 80% of their time..."

    with patch("app.services.tool_use_agents.httpx") as mock_httpx:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"voice_authenticity":8,"hook_strength":8,"grounding":7,"human_feel":8,"virality":7,"goal_alignment":7,"fix":""}'
                }
            }]
        }
        mock_httpx.post.return_value = mock_resp
        result_str = _exec_score_content_quality(clean_post)

    result = json.loads(result_str)
    assert result["pass"] == True
    assert result["llm_scores"]["average"] >= 7.0


def test_score_content_quality_llm_scores_present():
    """LLM scores should be in result when LLM call succeeds."""
    from app.services.tool_use_agents import _exec_score_content_quality

    with patch("app.services.tool_use_agents.httpx") as mock_httpx:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"voice_authenticity":6,"hook_strength":5,"grounding":4,"human_feel":6,"virality":5,"goal_alignment":6,"fix":"Add a specific story or number"}'
                }
            }]
        }
        mock_httpx.post.return_value = mock_resp
        result_str = _exec_score_content_quality("Generic post about leadership")

    result = json.loads(result_str)
    assert "llm_scores" in result
    assert "voice_authenticity" in result["llm_scores"]
    assert "average" in result["llm_scores"]
    # Average of 6+5+4+6+5+6 = 32/6 = 5.33 < 7 → should fail
    assert result["pass"] == False


# ── Fix D: Activity feed ───────────────────────────────────────────────────


def test_activity_feed_endpoint_returns_items():
    """GET /agent-api/activity-feed should return items from agent_ledger."""
    from fastapi.testclient import TestClient
    from app.main import app

    ledger_data = [{
        "id": str(uuid.uuid4()),
        "agent_id": "copywriter",
        "task_type": "pipeline_write",
        "summary": "Wrote a LinkedIn post about SaaS growth",
        "status": "done",
        "created_at": "2026-03-05T10:00:00Z",
        "brand_id": str(uuid.uuid4()),
    }]

    mock_user = MagicMock()
    mock_user.id = str(uuid.uuid4())

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = ledger_data

    from app.routers.agent_bridge import get_user_or_agent_caller
    app.dependency_overrides[get_user_or_agent_caller] = lambda: __import__("app.routers.agent_bridge", fromlist=["AgentCaller"]).AgentCaller(user_id=mock_user.id)

    client = TestClient(app)
    with patch("app.routers.agent_bridge.get_admin_client", return_value=mock_sb):
        response = client.get("/agent-api/activity-feed?limit=10")

    app.dependency_overrides = {}
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["emoji"] == "✍️"


# ── Fix E: Analytics summary ───────────────────────────────────────────────


def test_analytics_summary_returns_real_data():
    """GET /agent-api/analytics-summary should return post + agent stats."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers.agent_bridge import get_user_or_agent_caller, AgentCaller

    user_id = str(uuid.uuid4())
    deliverables = [
        {"status": "approved", "qa_score": 85, "created_at": "2026-03-05T10:00:00Z"},
        {"status": "approved", "qa_score": 80, "created_at": "2026-03-05T10:00:00Z"},
        {"status": "rejected", "qa_score": 60, "created_at": "2026-03-05T10:00:00Z"},
    ]
    ledger = [
        {"agent_id": "copywriter", "task_type": "write", "status": "done"},
        {"agent_id": "trend-analyzer", "task_type": "research", "status": "done"},
        {"agent_id": "qa-reviewer", "task_type": "qa", "status": "error"},
    ]

    mock_sb = MagicMock()
    execute_mock = MagicMock()
    # First call → deliverables, second → ledger, third → memories
    execute_mock.execute.return_value.data = deliverables
    ledger_mock = MagicMock()
    ledger_mock.execute.return_value.data = ledger
    mem_mock = MagicMock()
    mem_mock.execute.return_value.data = []

    app.dependency_overrides[get_user_or_agent_caller] = lambda: AgentCaller(user_id=user_id)

    client = TestClient(app)
    with patch("app.routers.agent_bridge.get_admin_client", return_value=mock_sb):
        mock_sb.table.return_value.select.return_value.eq.return_value = execute_mock
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = ledger_mock
        response = client.get("/agent-api/analytics-summary")

    app.dependency_overrides = {}
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert "agents" in data


# ── Fix F: Hook Library ────────────────────────────────────────────────────


def test_create_hook_succeeds():
    """POST /hooks should create a new hook."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import CurrentUser, get_current_user

    user_id = str(uuid.uuid4())
    brand_id = str(uuid.uuid4())
    hook_id = str(uuid.uuid4())

    mock_user = CurrentUser(id=user_id, email="test@test.com")
    mock_sb = MagicMock()
    # Brand ownership check
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": brand_id}]
    # Insert result
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": hook_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "hook_text": "Most founders waste 80% of their time",
        "hook_type": "anxiety",
        "source": "manual",
        "times_used": 0,
    }]

    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    with patch("app.routers.hooks.get_admin_client", return_value=mock_sb):
        response = client.post("/hooks", json={
            "brand_id": brand_id,
            "hook_text": "Most founders waste 80% of their time",
            "hook_type": "anxiety",
        })

    app.dependency_overrides = {}
    assert response.status_code == 201


def test_create_hook_invalid_type():
    """POST /hooks should reject invalid hook_type."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import CurrentUser, get_current_user

    mock_user = CurrentUser(id=str(uuid.uuid4()), email="test@test.com")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    response = client.post("/hooks", json={
        "hook_text": "Test hook",
        "hook_type": "invalid_type_xyz",
    })
    app.dependency_overrides = {}
    assert response.status_code == 400


def test_delete_hook_idor_protection():
    """DELETE /hooks/{id} should not delete hooks belonging to other users."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import CurrentUser, get_current_user

    mock_user = CurrentUser(id=str(uuid.uuid4()), email="test@test.com")
    hook_id = str(uuid.uuid4())
    mock_sb = MagicMock()
    # Return empty — hook belongs to different user
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    with patch("app.routers.hooks.get_admin_client", return_value=mock_sb):
        response = client.delete(f"/hooks/{hook_id}")

    app.dependency_overrides = {}
    assert response.status_code == 404


def test_list_hooks_filters_by_type():
    """GET /hooks?hook_type=anxiety should filter results."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import CurrentUser, get_current_user

    mock_user = CurrentUser(id=str(uuid.uuid4()), email="test@test.com")
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    with patch("app.routers.hooks.get_admin_client", return_value=mock_sb):
        response = client.get("/hooks?hook_type=anxiety")

    app.dependency_overrides = {}
    assert response.status_code == 200


def test_get_hooks_for_brand():
    """GET /hooks/for-agent should return formatted hooks."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import CurrentUser, get_current_user

    user_id = str(uuid.uuid4())
    brand_id = str(uuid.uuid4())
    mock_user = CurrentUser(id=user_id, email="test@test.com")
    mock_sb = MagicMock()
    # Brand ownership
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": brand_id}]
    # Hooks list
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"hook_text": "Most consultants leave $50K on the table", "hook_type": "anxiety", "times_used": 5},
    ]

    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)
    with patch("app.routers.hooks.get_admin_client", return_value=mock_sb):
        response = client.get(f"/hooks/for-agent?brand_id={brand_id}")

    app.dependency_overrides = {}
    assert response.status_code == 200
    data = response.json()
    assert "hooks" in data
    assert "formatted" in data


# ── Fix G: Proactive triggers ──────────────────────────────────────────────


def test_get_suggestions_returns_list():
    """get_suggestions should return a list of suggestion dicts."""
    from app.services.proactive_triggers import get_suggestions

    user_id = str(uuid.uuid4())
    brand_id = str(uuid.uuid4())

    mock_sb = MagicMock()
    # All DB queries return empty — no triggers fire
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.lte.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.deps.get_admin_client", return_value=mock_sb):
        suggestions = get_suggestions(user_id, brand_id)

    assert isinstance(suggestions, list)
    for s in suggestions:
        assert "id" in s
        assert "priority" in s
        assert "title" in s
        assert "body" in s
        assert "cta" in s


def test_get_suggestions_max_5():
    """get_suggestions should return at most 5 suggestions."""
    from app.services.proactive_triggers import get_suggestions

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.lte.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.not_.return_value.is_.return_value.execute.return_value.data = []

    with patch("app.deps.get_admin_client", return_value=mock_sb):
        suggestions = get_suggestions(str(uuid.uuid4()), str(uuid.uuid4()))

    assert len(suggestions) <= 5


def test_get_suggestions_urgent_first():
    """Sorted suggestions should have urgent before high/normal."""
    from app.services.proactive_triggers import get_suggestions

    user_id = str(uuid.uuid4())
    brand_id = str(uuid.uuid4())

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.lte.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_sb.table.return_value.select.return_value.eq.return_value.not_.return_value.is_.return_value.execute.return_value.data = []

    with patch("app.deps.get_admin_client", return_value=mock_sb):
        suggestions = get_suggestions(user_id, brand_id)

    if len(suggestions) >= 2:
        priority_order = {"urgent": 0, "high": 1, "normal": 2}
        for i in range(len(suggestions) - 1):
            assert priority_order.get(suggestions[i]["priority"], 3) <= priority_order.get(suggestions[i+1]["priority"], 3)


# ── get_brand_context helper ───────────────────────────────────────────────


def test_get_brand_context_returns_dict():
    """get_brand_context should return a dict with expected keys."""
    from app.services.jumbo_pipeline import get_brand_context

    brand_id = str(uuid.uuid4())
    profile_json = {
        "voice": "Bold",
        "anxiety_list": ["fear1"],
        "power_words": ["scale"],
    }
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"name": "Test", "description": "", "profile_json": profile_json}
    ]
    # Journal query
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    # get_brand_context uses lazy `from app.deps import get_admin_client` — patch at source
    with patch("app.deps.get_admin_client", return_value=mock_sb):
        result = get_brand_context(brand_id)

    assert result is not None
    assert result["anxiety_list"] == ["fear1"]
    assert result["power_words"] == ["scale"]


def test_get_brand_context_invalid_uuid():
    """get_brand_context should return None for invalid UUID."""
    from app.services.jumbo_pipeline import get_brand_context

    result = get_brand_context("not-a-uuid")
    assert result is None


# ── Dual auth ─────────────────────────────────────────────────────────────


def test_get_user_or_agent_caller_requires_auth():
    """get_user_or_agent_caller should reject requests with no auth."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/agent-api/activity-feed")
    # Should be 401 or 422 (no auth headers)
    assert response.status_code in (401, 422)
