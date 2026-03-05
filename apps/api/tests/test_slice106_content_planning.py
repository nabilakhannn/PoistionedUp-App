"""
Slice 106: Plan with Jumbo — Content Planning Conversation

10 tests across 4 classes:
  TestContentPlanningRouter  (4): file exists, endpoints registered, IDOR pattern, pipeline-key auth
  TestJumboPipelineChanges   (2): topic_focus parameter, conditional research_brief
  TestPipelineWriteRequest   (2): topic_focus in WriteRequest, source field
  TestFrontendContentPlanning (2): API client exists, component exists
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

CONTENT_PLANNING_ROUTER = API / "app" / "routers" / "content_planning.py"
PIPELINE_ROUTER         = API / "app" / "routers" / "pipeline.py"
JUMBO_PIPELINE_SVC      = API / "app" / "services" / "jumbo_pipeline.py"
MAIN_PY                 = API / "app" / "main.py"
CONTENT_PLANNING_TS     = WEB / "lib" / "api" / "content-planning.ts"
CONTENT_PLAN_CHAT_TSX   = WEB / "components" / "content-plan-chat.tsx"
PIPELINE_RUNNER         = REPO / "deploy" / "pipeline_runner.py"
MIGRATION_SQL           = REPO / "infra" / "supabase" / "migrations" / "041_content_plans.sql"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestContentPlanningRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestContentPlanningRouter:
    """apps/api/app/routers/content_planning.py exists with correct endpoints."""

    def test_router_file_exists(self):
        assert CONTENT_PLANNING_ROUTER.exists(), (
            "apps/api/app/routers/content_planning.py missing — "
            "Slice 106 content planning router not created"
        )

    def test_all_user_endpoints_registered(self):
        text = read(CONTENT_PLANNING_ROUTER)
        for endpoint in [
            "/plan/brainstorm",
            "/plan/chat",
            "/plan/approve",
            "/plan/status/",
        ]:
            assert endpoint in text, (
                f"Endpoint {endpoint!r} missing from content_planning.py — "
                "user planning endpoints not complete"
            )

    def test_vps_runner_endpoints_registered(self):
        text = read(CONTENT_PLANNING_ROUTER)
        assert "/plan/approved-for-runner" in text, (
            "/plan/approved-for-runner missing — "
            "VPS runner cannot fetch approved plans"
        )
        assert "/plan/{plan_id}/status" in text or "plan_id}/status" in text, (
            "PATCH plan status endpoint missing — "
            "VPS runner cannot update plan status"
        )

    def test_idor_protection_present(self):
        text = read(CONTENT_PLANNING_ROUTER)
        assert "_verify_brand_ownership" in text, (
            "_verify_brand_ownership() missing — "
            "user endpoints must verify brand belongs to caller (OWASP A01)"
        )
        assert "get_current_user" in text, (
            "get_current_user dependency missing — "
            "user endpoints must be JWT-authenticated"
        )

    def test_pipeline_key_auth_on_runner_endpoints(self):
        text = read(CONTENT_PLANNING_ROUTER)
        assert "_require_pipeline_key" in text, (
            "_require_pipeline_key missing — "
            "VPS runner endpoints must use pipeline-key auth, not JWT"
        )

    def test_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "content_planning" in text, (
            "content_planning router not imported/registered in main.py — "
            "endpoints will return 404"
        )

    def test_db_migration_exists(self):
        assert MIGRATION_SQL.exists(), (
            "infra/supabase/migrations/041_content_plans.sql missing — "
            "content_plans table not created"
        )

    def test_migration_creates_content_plans_table(self):
        text = read(MIGRATION_SQL)
        assert "content_plans" in text, (
            "content_plans table missing from migration — "
            "approved plans have nowhere to be stored"
        )
        assert "approved_at" in text, (
            "approved_at column missing from content_plans — "
            "VPS runner orders by approval time"
        )
        assert "last_updated_at" in text, (
            "last_updated_at missing — "
            "zombie detection requires this column"
        )

    def test_source_column_added_to_deliverables(self):
        text = read(MIGRATION_SQL)
        assert "agent_deliverables" in text and "source" in text, (
            "source column not added to agent_deliverables — "
            "approval queue cannot distinguish autonomous vs planned posts"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestJumboPipelineChanges
# ═══════════════════════════════════════════════════════════════════════════


class TestJumboPipelineChanges:
    """jumbo_pipeline.py: build_writing_prompt() updated for content plans."""

    def test_topic_focus_parameter_exists(self):
        text = read(JUMBO_PIPELINE_SVC)
        assert "topic_focus" in text, (
            "topic_focus parameter missing from build_writing_prompt() — "
            "user-approved topics cannot be passed to the copywriter"
        )

    def test_research_brief_conditional(self):
        text = read(JUMBO_PIPELINE_SVC)
        # The research_brief section should only be included when non-empty
        # Look for either an 'if' guard or conditional expression around it
        assert (
            "research_brief.strip()" in text or
            "if research_brief" in text or
            "research_section" in text
        ), (
            "Research Brief section is not conditional — "
            "empty research_brief will hallucinate content in the prompt"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineWriteRequest
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineWriteRequest:
    """pipeline.py WriteRequest schema includes topic_focus and source fields."""

    def test_topic_focus_in_write_request(self):
        text = read(PIPELINE_ROUTER)
        assert "topic_focus" in text, (
            "topic_focus field missing from WriteRequest in pipeline.py — "
            "VPS runner cannot pass user-planned topics to the write endpoint"
        )

    def test_source_field_in_write_request(self):
        text = read(PIPELINE_ROUTER)
        assert "source" in text and "autonomous" in text, (
            "source field missing from WriteRequest — "
            "deliverables cannot be tagged as 'autonomous' vs 'planned'"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestVpsPipelineRunner
# ═══════════════════════════════════════════════════════════════════════════


class TestVpsPipelineRunner:
    """deploy/pipeline_runner.py: approved plan execution functions added."""

    def test_runner_file_exists(self):
        assert PIPELINE_RUNNER.exists(), (
            "deploy/pipeline_runner.py missing — "
            "VPS pipeline runner not found"
        )

    def test_run_approved_plans_function(self):
        text = read(PIPELINE_RUNNER)
        assert "run_approved_plans" in text, (
            "run_approved_plans() function missing from pipeline_runner.py — "
            "approved plans will never be executed"
        )

    def test_run_plan_item_function(self):
        text = read(PIPELINE_RUNNER)
        assert "run_plan_item" in text, (
            "run_plan_item() function missing — "
            "individual plan items have no execution handler"
        )

    def test_approved_plans_called_before_autonomous_pipeline(self):
        text = read(PIPELINE_RUNNER)
        run_plans_pos = text.find("run_approved_plans")
        run_user_pos = text.find("run_for_user")
        assert run_plans_pos != -1 and run_user_pos != -1, (
            "run_approved_plans() or run_for_user() missing from runner"
        )
        assert run_plans_pos < run_user_pos, (
            "run_approved_plans() must be called BEFORE run_for_user() — "
            "user-planned content takes priority over autonomous pipeline"
        )

    def test_threadpoolexecutor_used_for_parallel_execution(self):
        text = read(PIPELINE_RUNNER)
        assert "ThreadPoolExecutor" in text, (
            "ThreadPoolExecutor missing — "
            "plan items must run in parallel (not sequentially)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendContentPlanning
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendContentPlanning:
    """Frontend: API client and chat component exist."""

    def test_api_client_exists(self):
        assert CONTENT_PLANNING_TS.exists(), (
            "apps/web/src/lib/api/content-planning.ts missing — "
            "frontend has no way to call the planning endpoints"
        )

    def test_api_client_has_all_methods(self):
        text = read(CONTENT_PLANNING_TS)
        for method in ["brainstorm", "chat", "approve", "status"]:
            assert method in text, (
                f"contentPlanningApi.{method}() missing from content-planning.ts — "
                "frontend planning flow is incomplete"
            )

    def test_component_exists(self):
        assert CONTENT_PLAN_CHAT_TSX.exists(), (
            "apps/web/src/components/content-plan-chat.tsx missing — "
            "no planning UI to embed in Today screen"
        )

    def test_component_has_plan_parser(self):
        text = read(CONTENT_PLAN_CHAT_TSX)
        assert "parsePlan" in text, (
            "parsePlan() missing from content-plan-chat.tsx — "
            "PLAN: section from Jumbo cannot be parsed into approval cards"
        )

    def test_component_has_manual_fallback(self):
        text = read(CONTENT_PLAN_CHAT_TSX)
        assert "manual" in text.lower(), (
            "Manual topic entry fallback missing — "
            "users need a way to enter topics if Jumbo deviates from PLAN: format"
        )

    def test_today_screen_imports_component(self):
        mc_page = REPO / "apps" / "web" / "src" / "app" / "mission-control" / "page.tsx"
        assert mc_page.exists(), "mission-control/page.tsx not found"
        text = read(mc_page)
        assert "ContentPlanChat" in text, (
            "ContentPlanChat not imported in mission-control/page.tsx — "
            "Plan Content section not visible on Today screen"
        )

    def test_today_screen_polls_plan_status(self):
        mc_page = REPO / "apps" / "web" / "src" / "app" / "mission-control" / "page.tsx"
        text = read(mc_page)
        assert "activePlan" in text, (
            "activePlan state missing — "
            "Today screen cannot show 'Jumbo is writing...' status"
        )
        assert "contentPlanningApi.status" in text or "status(activePlan" in text, (
            "Plan status polling missing — "
            "Today screen won't update when plan execution completes"
        )
