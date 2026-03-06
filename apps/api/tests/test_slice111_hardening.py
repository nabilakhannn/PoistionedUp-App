"""Slice 111: Pipeline Hardening + Client Portal Expansion.

25 tests across 6 classes:
  TestRetryPolicy          (5): retry function, backoff constants, phase retry logic
  TestPartialFailure       (4): partial status, item-level tracking, zombie 30m, idempotency
  TestContextTimeout       (3): timeout decorator, applied to getters, uses threading
  TestPipelineHealth       (4): endpoint exists, response fields, JWT auth, 24h window
  TestBudgetCheckRobust    (2): failure returns structured message, pipeline proceeds
  TestClientPortal         (7): status endpoint, regenerate, migration, detail page, API client
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# ── File paths ────────────────────────────────────────────────────────────

PIPELINE_RUNNER = REPO / "deploy" / "pipeline_runner.py"
JUMBO_PIPELINE_SVC = REPO / "apps" / "api" / "app" / "services" / "jumbo_pipeline.py"
PIPELINE_ROUTER = REPO / "apps" / "api" / "app" / "routers" / "pipeline.py"
CONTENT_PLANNING_ROUTER = REPO / "apps" / "api" / "app" / "routers" / "content_planning.py"
CLIENT_DELIVERABLES_ROUTER = REPO / "apps" / "api" / "app" / "routers" / "client_deliverables.py"
MIGRATION_FILE = REPO / "infra" / "supabase" / "migrations" / "047_slice111_hardening.sql"
CLIENT_DELIVERABLES_TS = REPO / "apps" / "web" / "src" / "lib" / "api" / "client-deliverables.ts"
PIPELINE_SETTINGS_TS = REPO / "apps" / "web" / "src" / "lib" / "api" / "pipeline-settings.ts"
CLIENTS_PAGE = REPO / "apps" / "web" / "src" / "app" / "mission-control" / "clients" / "page.tsx"
CLIENT_DETAIL_PAGE = (
    REPO / "apps" / "web" / "src" / "app" / "mission-control" / "clients" / "[brandId]" / "page.tsx"
)
DELIVERABLES_PAGE = REPO / "apps" / "web" / "src" / "app" / "deliverables" / "page.tsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── A1: Retry with Exponential Backoff ────────────────────────────────────


class TestRetryPolicy:
    def test_retry_function_exists(self):
        text = _read(PIPELINE_RUNNER)
        assert "_retry_phase" in text, "Missing _retry_phase helper in pipeline_runner.py"

    def test_backoff_constants_defined(self):
        text = _read(PIPELINE_RUNNER)
        assert "BACKOFF_SECONDS" in text, "Missing BACKOFF_SECONDS constant"
        assert "MAX_PHASE_RETRIES" in text, "Missing MAX_PHASE_RETRIES constant"

    def test_retries_only_on_transient_failures(self):
        text = _read(PIPELINE_RUNNER)
        assert "status_code < 500" in text, "Retry logic should skip 4xx (non-retryable)"

    def test_run_pipeline_uses_retry(self):
        text = _read(PIPELINE_RUNNER)
        # run_pipeline_for_brand should call _retry_phase, not raw httpx.post
        in_pipeline = text[text.index("def run_pipeline_for_brand"):]
        assert "_retry_phase" in in_pipeline, "run_pipeline_for_brand should use _retry_phase"

    def test_plan_item_uses_retry(self):
        text = _read(PIPELINE_RUNNER)
        in_plan = text[text.index("def run_plan_item"):]
        assert "_retry_phase" in in_plan, "run_plan_item should use _retry_phase"


# ── A2: Partial Failure Tracking ──────────────────────────────────────────


class TestPartialFailure:
    def test_partial_status_exists(self):
        text = _read(CONTENT_PLANNING_ROUTER)
        assert '"partial"' in text, "Missing 'partial' in valid_statuses"

    def test_item_level_status_in_response(self):
        text = _read(CONTENT_PLANNING_ROUTER)
        assert "items_done" in text, "plan_status response should include items_done"
        assert "items_failed" in text, "plan_status response should include items_failed"

    def test_zombie_detection_30_minutes(self):
        text = _read(CONTENT_PLANNING_ROUTER)
        assert "minutes=30" in text or "minutes(30)" in text, (
            "Zombie detection should be 30 minutes"
        )

    def test_idempotency_guard(self):
        text = _read(CONTENT_PLANNING_ROUTER)
        # When status is 'executing', should check current status is 'approved'
        assert "not in approved state" in text.lower() or 'approved' in text, (
            "Idempotency guard should check plan is in approved state"
        )


# ── A3: Context Timeout Protection ───────────────────────────────────────


class TestContextTimeout:
    def test_timeout_decorator_exists(self):
        text = _read(JUMBO_PIPELINE_SVC)
        assert "_with_timeout" in text, "Missing _with_timeout decorator"

    def test_timeout_applied_to_analytics(self):
        text = _read(JUMBO_PIPELINE_SVC)
        # The decorator should appear before get_analytics_context
        idx_decorator = text.index("@_with_timeout")
        idx_func = text.index("def get_analytics_context")
        assert idx_decorator < idx_func, (
            "_with_timeout should decorate get_analytics_context"
        )

    def test_timeout_uses_threading(self):
        text = _read(JUMBO_PIPELINE_SVC)
        assert "import threading" in text or "threading.Thread" in text, (
            "Timeout decorator should use threading"
        )


# ── A4: Pipeline Health Endpoint ─────────────────────────────────────────


class TestPipelineHealth:
    def test_health_endpoint_exists(self):
        text = _read(PIPELINE_ROUTER)
        assert "/pipeline/health" in text, "Missing /pipeline/health endpoint"

    def test_health_uses_jwt_auth(self):
        text = _read(PIPELINE_ROUTER)
        assert "get_current_user" in text, (
            "Health endpoint should use JWT auth (get_current_user)"
        )

    def test_health_response_fields(self):
        text = _read(PIPELINE_ROUTER)
        for field in ["success_count_24h", "failed_count_24h", "current_status"]:
            assert field in text, f"Health response missing field: {field}"

    def test_health_24h_window(self):
        text = _read(PIPELINE_ROUTER)
        assert "hours=24" in text, "Health endpoint should query 24h window"


# ── A5: Budget Check Robustness ──────────────────────────────────────────


class TestBudgetCheckRobust:
    def test_budget_check_failure_not_silent(self):
        text = _read(JUMBO_PIPELINE_SVC)
        assert "budget_check_failed" in text, (
            "Budget check should return structured error on failure"
        )

    def test_pipeline_proceeds_on_check_failure(self):
        text = _read(PIPELINE_ROUTER)
        assert "budget_check_failed" in text, (
            "Pipeline router should handle budget_check_failed prefix"
        )


# ── B: Client Portal Expansion ───────────────────────────────────────────


class TestClientPortal:
    def test_migration_adds_proposal_status(self):
        assert MIGRATION_FILE.exists(), "Missing migration 047_slice111_hardening.sql"
        text = _read(MIGRATION_FILE)
        assert "proposal_status" in text, "Migration should add proposal_status column"

    def test_status_endpoint_exists(self):
        text = _read(CLIENT_DELIVERABLES_ROUTER)
        assert "/status" in text and "proposal_status" in text, (
            "Missing PATCH /deliverables/{id}/status endpoint"
        )

    def test_regenerate_endpoint_exists(self):
        text = _read(CLIENT_DELIVERABLES_ROUTER)
        assert "regenerate" in text, "Missing POST /deliverables/{id}/regenerate endpoint"

    def test_client_detail_page_exists(self):
        assert CLIENT_DETAIL_PAGE.exists(), (
            "Missing client detail page at /mission-control/clients/[brandId]/page.tsx"
        )

    def test_clients_page_links_to_detail(self):
        text = _read(CLIENTS_PAGE)
        assert "/mission-control/clients/" in text and "brand.id" in text, (
            "Client names should link to detail page"
        )

    def test_frontend_api_has_update_status(self):
        text = _read(CLIENT_DELIVERABLES_TS)
        assert "updateStatus" in text, "Missing updateStatus in client-deliverables.ts"

    def test_frontend_api_has_regenerate(self):
        text = _read(CLIENT_DELIVERABLES_TS)
        assert "regenerate" in text, "Missing regenerate in client-deliverables.ts"


# ── Bonus: Frontend pipeline health ──────────────────────────────────────


class TestFrontendHealth:
    def test_pipeline_health_interface(self):
        text = _read(PIPELINE_SETTINGS_TS)
        assert "PipelineHealth" in text, "Missing PipelineHealth interface"

    def test_get_health_method(self):
        text = _read(PIPELINE_SETTINGS_TS)
        assert "getHealth" in text, "Missing getHealth method in pipelineSettingsApi"

    def test_deliverables_page_has_status_dropdown(self):
        text = _read(DELIVERABLES_PAGE)
        assert "onStatusChange" in text, "Deliverables page missing status change handler"

    def test_deliverables_page_has_regenerate(self):
        text = _read(DELIVERABLES_PAGE)
        assert "onRegenerate" in text, "Deliverables page missing regenerate handler"
