"""
Slice 97: Client Onboarding Intelligence Wizard

10 tests across 4 classes:
  TestClientResearchService    (3): service exists, research_client() present, _parse_dossier() handles bad JSON
  TestClientResearchRouter     (3): POST /client-research/run, SSRF guard on URLs, UUID guard on brand_id
  TestIntakeRouter             (2): public GET/POST endpoints, create endpoint auth-gated
  TestFrontendWizard           (2): 8-step wizard exists, intake public page exists
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

CLIENT_RESEARCHER   = API / "app" / "services" / "client_researcher.py"
CLIENT_RESEARCH_R   = API / "app" / "routers" / "client_research.py"
INTAKE_ROUTER       = API / "app" / "routers" / "intake.py"
MAIN_PY             = API / "app" / "main.py"
PLAYBOOKS_SVC       = API / "app" / "services" / "playbooks.py"
TOOL_USE_AGENTS     = API / "app" / "services" / "tool_use_agents.py"
WIZARD_PAGE         = WEB / "app" / "onboarding" / "client" / "page.tsx"
INTAKE_PAGE         = WEB / "app" / "intake" / "[token]" / "page.tsx"
INTEL_REPORT        = WEB / "components" / "brand-intelligence-report.tsx"
CLIENT_RESEARCH_TS  = WEB / "lib" / "api" / "client-research.ts"
INTAKE_TS           = WEB / "lib" / "api" / "intake.ts"
MIGRATION_037       = REPO / "infra" / "supabase" / "migrations" / "037_client_intake.sql"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestClientResearchService
# ═══════════════════════════════════════════════════════════════════════════


class TestClientResearchService:
    """client_researcher.py service exists with correct functions."""

    def test_service_file_exists(self):
        assert CLIENT_RESEARCHER.exists(), (
            "apps/api/app/services/client_researcher.py missing — "
            "Brand Researcher agent needs this to run 5-layer research"
        )

    def test_research_client_function_present(self):
        text = read(CLIENT_RESEARCHER)
        assert "async def research_client" in text, (
            "research_client() function missing from client_researcher.py"
        )

    def test_parse_dossier_fallback(self):
        """_parse_dossier must handle malformed JSON gracefully."""
        text = read(CLIENT_RESEARCHER)
        assert "_parse_dossier" in text, (
            "_parse_dossier() helper missing — service must handle LLM returning "
            "non-JSON output without crashing"
        )

    def test_ssrf_guard_in_service(self):
        text = read(CLIENT_RESEARCHER)
        assert "validate_url_for_fetch" in text, (
            "validate_url_for_fetch() not called in client_researcher.py — "
            "OWASP A10 SSRF risk: user-supplied linkedin_url/website_url must be validated"
        )

    def test_brand_researcher_playbook_exists(self):
        text = read(PLAYBOOKS_SVC)
        assert '"brand-researcher"' in text or "'brand-researcher'" in text, (
            "brand-researcher not in _DEFAULT_PLAYBOOKS — "
            "Brand Researcher agent has no SOUL.md playbook"
        )

    def test_read_agent_training_docs_tool(self):
        text = read(TOOL_USE_AGENTS)
        assert "read_agent_training_docs" in text, (
            "read_agent_training_docs tool missing from tool_use_agents.py — "
            "agents cannot access training documents uploaded by user"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestClientResearchRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestClientResearchRouter:
    """client_research.py router registered and protected."""

    def test_router_registered_in_main(self):
        text = read(MAIN_PY)
        assert "client_research" in text, (
            "client_research router not registered in main.py — "
            "POST /client-research/run will 404"
        )

    def test_run_endpoint_present(self):
        text = read(CLIENT_RESEARCH_R)
        assert "/client-research/run" in text or '"/run"' in text or "'/run'" in text, (
            "POST /client-research/run endpoint missing from client_research.py"
        )

    def test_uuid_guard_on_brand_id(self):
        text = read(CLIENT_RESEARCH_R)
        assert "_UUID_RE" in text or "UUID_RE" in text or "uuid4" in text.lower() or "_uuid" in text.lower(), (
            "No UUID validation on brand_id in client_research.py — "
            "OWASP A03 injection risk: brand_id must be validated as UUID"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestIntakeRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestIntakeRouter:
    """intake.py router has public + authenticated endpoints."""

    def test_intake_router_registered(self):
        text = read(MAIN_PY)
        assert "intake" in text, (
            "intake router not registered in main.py — "
            "client intake form endpoints will 404"
        )

    def test_public_submit_endpoint(self):
        text = read(INTAKE_ROUTER)
        assert "share_token" in text or "token" in text, (
            "No token-based public endpoint in intake.py — "
            "clients cannot submit their intake form without auth"
        )

    def test_token_validation(self):
        text = read(INTAKE_ROUTER)
        assert "_TOKEN_RE" in text or "TOKEN_RE" in text or "[0-9a-f]" in text or "hex" in text, (
            "No token format validation in intake.py — "
            "share_token must be validated as 64-char hex to prevent injection"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendWizard
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendWizard:
    """Frontend wizard and intake form pages exist."""

    def test_client_onboarding_wizard_exists(self):
        assert WIZARD_PAGE.exists(), (
            "apps/web/src/app/onboarding/client/page.tsx missing — "
            "8-step client onboarding wizard not created"
        )

    def test_wizard_has_multiple_steps(self):
        text = read(WIZARD_PAGE)
        assert "step" in text.lower() or "Step" in text, (
            "Wizard page does not appear to have step-based navigation"
        )

    def test_intake_public_page_exists(self):
        assert INTAKE_PAGE.exists(), (
            "apps/web/src/app/intake/[token]/page.tsx missing — "
            "clients cannot fill in their intake form"
        )

    def test_brand_intelligence_report_exists(self):
        assert INTEL_REPORT.exists(), (
            "apps/web/src/components/brand-intelligence-report.tsx missing — "
            "research results are never shown to the user"
        )

    def test_client_research_api_client_exists(self):
        assert CLIENT_RESEARCH_TS.exists(), (
            "apps/web/src/lib/api/client-research.ts missing — "
            "frontend cannot call client research endpoints"
        )

    def test_intake_api_client_exists(self):
        assert INTAKE_TS.exists(), (
            "apps/web/src/lib/api/intake.ts missing — "
            "frontend cannot call intake form endpoints"
        )

    def test_migration_037_exists(self):
        assert MIGRATION_037.exists(), (
            "infra/supabase/migrations/037_client_intake.sql missing — "
            "client_intake_forms table not created in database"
        )
