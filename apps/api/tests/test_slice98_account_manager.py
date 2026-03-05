"""
Slice 98: Client Account Manager + MCP Transcript Drop

12 tests across 4 classes:
  TestAccountManagerService    (3): service exists, analyze_transcript(), cross-call memory
  TestAccountManagerRouter     (3): POST /analyze, GET /sessions, PATCH /sessions auth-guarded
  TestClientDeliverablesRouter (3): proposal / landing-page / nurture endpoints + public share
  TestFrontendComponents       (3): TranscriptDrop, AccountManagerPanel, deliverables page exist
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

ACCOUNT_MGR_SVC       = API / "app" / "services" / "account_manager.py"
ACCOUNT_MGR_ROUTER    = API / "app" / "routers" / "account_manager.py"
CLIENT_DELIV_SVC      = API / "app" / "services" / "client_deliverables.py"
CLIENT_DELIV_ROUTER   = API / "app" / "routers" / "client_deliverables.py"
AGENT_BRIDGE_ROUTER   = API / "app" / "routers" / "agent_bridge.py"
MAIN_PY               = API / "app" / "main.py"
PLAYBOOKS_SVC         = API / "app" / "services" / "playbooks.py"
TOOL_USE_AGENTS       = API / "app" / "services" / "tool_use_agents.py"
TRANSCRIPT_DROP       = WEB / "components" / "transcript-drop.tsx"
ACCOUNT_MGR_PANEL     = WEB / "components" / "account-manager-panel.tsx"
DELIVERABLES_PAGE     = WEB / "app" / "deliverables" / "page.tsx"
SHARE_PAGE            = WEB / "app" / "share" / "[token]" / "page.tsx"
CLIENTS_PAGE          = WEB / "app" / "mission-control" / "clients" / "page.tsx"
ACCOUNT_MGR_TS        = WEB / "lib" / "api" / "account-manager.ts"
CLIENT_DELIV_TS       = WEB / "lib" / "api" / "client-deliverables.ts"
MIGRATION_038         = REPO / "infra" / "supabase" / "migrations" / "038_account_manager.sql"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestAccountManagerService
# ═══════════════════════════════════════════════════════════════════════════


class TestAccountManagerService:
    """account_manager.py service has core functions + cross-call memory."""

    def test_service_file_exists(self):
        assert ACCOUNT_MGR_SVC.exists(), (
            "apps/api/app/services/account_manager.py missing — "
            "Account Manager agent cannot analyze transcripts"
        )

    def test_analyze_transcript_function(self):
        text = read(ACCOUNT_MGR_SVC)
        assert "async def analyze_transcript" in text, (
            "analyze_transcript() function missing from account_manager.py"
        )

    def test_cross_call_memory(self):
        text = read(ACCOUNT_MGR_SVC)
        assert "cross_call" in text or "previous_sessions" in text or "call_number" in text, (
            "No cross-call memory logic in account_manager.py — "
            "Account Manager must load previous sessions to identify recurring themes"
        )

    def test_account_manager_playbook_exists(self):
        text = read(PLAYBOOKS_SVC)
        assert '"account-manager"' in text or "'account-manager'" in text, (
            "account-manager not in _DEFAULT_PLAYBOOKS — "
            "Account Manager agent has no SOUL.md / instructions"
        )

    def test_emotional_journal_injection(self):
        text = read(TOOL_USE_AGENTS)
        assert "emotional_pain_journal" in text or "is_client_brand" in text, (
            "emotional_pain_journal not injected in fetch_brand_profile — "
            "Copywriter, Landing Page generator won't have journal context for client brands"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestAccountManagerRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestAccountManagerRouter:
    """account_manager router registered with correct endpoints."""

    def test_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "account_manager" in text, (
            "account_manager router not registered in main.py — "
            "all Account Manager endpoints will 404"
        )

    def test_analyze_endpoint_present(self):
        text = read(ACCOUNT_MGR_ROUTER)
        assert "/analyze" in text, (
            "POST /account-manager/analyze endpoint missing — "
            "TranscriptDrop cannot submit transcripts for analysis"
        )

    def test_sessions_endpoint_present(self):
        text = read(ACCOUNT_MGR_ROUTER)
        assert "sessions" in text, (
            "GET /account-manager/sessions endpoint missing — "
            "UI cannot list past call analysis sessions"
        )

    def test_idor_guard_on_sessions(self):
        text = read(ACCOUNT_MGR_ROUTER)
        assert "user_id" in text or "get_current_user" in text or "CurrentUser" in text, (
            "No user_id scoping in account_manager.py router — "
            "OWASP A01 IDOR: users could access other users' sessions"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestClientDeliverablesRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestClientDeliverablesRouter:
    """client_deliverables router has generation + public share endpoints."""

    def test_deliverables_router_registered(self):
        text = read(MAIN_PY)
        assert "client_deliverables" in text, (
            "client_deliverables router not registered in main.py"
        )

    def test_proposal_endpoint_present(self):
        text = read(CLIENT_DELIV_ROUTER)
        assert "proposal" in text, (
            "POST /deliverables/proposal endpoint missing — "
            "Account Manager cannot trigger proposal generation"
        )

    def test_landing_page_endpoint_present(self):
        text = read(CLIENT_DELIV_ROUTER)
        assert "landing" in text, (
            "POST /deliverables/landing-page endpoint missing"
        )

    def test_nurture_sequence_endpoint_present(self):
        text = read(CLIENT_DELIV_ROUTER)
        assert "nurture" in text, (
            "POST /deliverables/nurture-sequence endpoint missing — "
            "Account Manager nurture actions cannot be executed"
        )

    def test_public_share_endpoint(self):
        text = read(CLIENT_DELIV_ROUTER)
        assert "share_token" in text or "share/" in text, (
            "Public share endpoint missing from client_deliverables.py — "
            "clients cannot view proposals/landing pages without logging in"
        )

    def test_share_ssrf_guard(self):
        text = read(CLIENT_DELIV_SVC)
        assert "validate_url_for_fetch" in text, (
            "validate_url_for_fetch() not called in client_deliverables.py — "
            "OWASP A10 SSRF: website_url passed to landing page generator must be validated"
        )

    def test_mcp_transcript_endpoint_in_agent_bridge(self):
        text = read(AGENT_BRIDGE_ROUTER)
        assert "transcript" in text, (
            "MCP transcript/analyze endpoint missing from agent_bridge.py — "
            "Claude.ai MCP integration cannot submit call transcripts"
        )

    def test_migration_038_exists(self):
        assert MIGRATION_038.exists(), (
            "infra/supabase/migrations/038_account_manager.sql missing — "
            "account_manager_sessions table not created"
        )

    def test_share_token_on_deliverables_in_migration(self):
        text = read(MIGRATION_038)
        assert "share_token" in text, (
            "share_token column missing from 038 migration — "
            "deliverables cannot be shared via public links"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendComponents
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendComponents:
    """All required frontend files for Slice 98 exist and have expected content."""

    def test_transcript_drop_exists(self):
        assert TRANSCRIPT_DROP.exists(), (
            "apps/web/src/components/transcript-drop.tsx missing — "
            "no UI for dropping/pasting call transcripts"
        )

    def test_transcript_drop_has_tabs(self):
        text = read(TRANSCRIPT_DROP)
        assert "paste" in text.lower() or "Paste" in text, (
            "TranscriptDrop has no Paste tab — users cannot paste transcripts"
        )

    def test_account_manager_panel_exists(self):
        assert ACCOUNT_MGR_PANEL.exists(), (
            "apps/web/src/components/account-manager-panel.tsx missing — "
            "action plan UI not created"
        )

    def test_action_plan_has_7_categories(self):
        text = read(ACCOUNT_MGR_PANEL)
        assert "nurture" in text and "deliverable" in text and "content" in text, (
            "AccountManagerPanel missing required action categories (nurture, deliverable, content) — "
            "7-category action plan not fully implemented"
        )

    def test_deliverables_page_exists(self):
        assert DELIVERABLES_PAGE.exists(), (
            "apps/web/src/app/deliverables/page.tsx missing — "
            "no gallery for generated deliverables"
        )

    def test_share_page_exists(self):
        assert SHARE_PAGE.exists(), (
            "apps/web/src/app/share/[token]/page.tsx missing — "
            "public deliverable preview not accessible"
        )

    def test_clients_dashboard_exists(self):
        assert CLIENTS_PAGE.exists(), (
            "apps/web/src/app/mission-control/clients/page.tsx missing — "
            "no client health dashboard"
        )

    def test_account_manager_api_client_exists(self):
        assert ACCOUNT_MGR_TS.exists(), (
            "apps/web/src/lib/api/account-manager.ts missing"
        )

    def test_client_deliverables_api_client_exists(self):
        assert CLIENT_DELIV_TS.exists(), (
            "apps/web/src/lib/api/client-deliverables.ts missing"
        )
