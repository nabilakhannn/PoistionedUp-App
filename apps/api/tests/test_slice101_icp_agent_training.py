"""
Slice 101: Gemini-Style Agent Training + ICP Research Pipeline

12 tests across 3 classes:
  TestIcpResearchService    (4): function exists, stage structure, IDOR guard, fallback
  TestIcpResearchRouter     (4): endpoints registered, UUID guard, methodology endpoint, auth
  TestFrontendAgentTraining (4): component exists, ICP panel exists, leads API updated, knowledge-docs type
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

LEAD_GEN_SVC        = API / "app" / "services" / "lead_gen.py"
LEADS_ROUTER        = API / "app" / "routers" / "leads.py"
KNOWLEDGE_DOCS_RTR  = API / "app" / "routers" / "knowledge_docs.py"
AGENT_TRAINING_TSX  = WEB / "components" / "agent-training-panel.tsx"
ICP_PANEL_TSX       = WEB / "components" / "icp-research-panel.tsx"
LEADS_TS            = WEB / "lib" / "api" / "leads.ts"
KNOWLEDGE_DOCS_TS   = WEB / "lib" / "api" / "knowledge-docs.ts"
INTELLIGENCE_PAGE   = WEB / "app" / "intelligence" / "page.tsx"
SALES_PAGE          = WEB / "app" / "sales" / "page.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestIcpResearchService
# ═══════════════════════════════════════════════════════════════════════════


class TestIcpResearchService:
    """apps/api/app/services/lead_gen.py — research_icp() function and ICP_METHODOLOGY."""

    def test_research_icp_function_exists(self):
        text = read(LEAD_GEN_SVC)
        assert "def research_icp" in text, (
            "research_icp() function missing from lead_gen.py — "
            "ICP Research Stage 3 cannot run"
        )

    def test_icp_methodology_constant_exists(self):
        text = read(LEAD_GEN_SVC)
        assert "ICP_METHODOLOGY" in text, (
            "ICP_METHODOLOGY constant missing from lead_gen.py — "
            "GET /leads/icp-methodology endpoint has nothing to return"
        )

    def test_idor_guard_in_service(self):
        text = read(LEAD_GEN_SVC)
        # research_icp() must filter by both id AND user_id
        assert ".eq(\"user_id\", user_id)" in text or ".eq('user_id', user_id)" in text, (
            "IDOR guard missing from research_icp() — "
            "any authenticated user can read any brand's ICP data (A01)"
        )

    def test_four_stages_returned(self):
        text = read(LEAD_GEN_SVC)
        assert "Stage 1" in text and "Stage 2" in text and "Stage 3" in text and "Stage 4" in text, (
            "Not all 4 ICP stages present in lead_gen.py comments/code — "
            "frontend expects stages 1-4 in response"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestIcpResearchRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestIcpResearchRouter:
    """apps/api/app/routers/leads.py — ICP Research endpoints."""

    def test_icp_research_post_endpoint_exists(self):
        text = read(LEADS_ROUTER)
        assert "/leads/icp-research" in text, (
            "POST /leads/icp-research endpoint missing from leads.py — "
            "ICP Research panel has no backend to call"
        )

    def test_icp_methodology_get_endpoint_exists(self):
        text = read(LEADS_ROUTER)
        assert "/leads/icp-methodology" in text, (
            "GET /leads/icp-methodology endpoint missing from leads.py — "
            "methodology collapsible won't load"
        )

    def test_uuid_guard_in_icp_router(self):
        text = read(LEADS_ROUTER)
        assert "_UUID_RE" in text or "UUID_RE" in text, (
            "UUID regex guard missing from leads router — "
            "brand_id injection vulnerability (A03)"
        )

    def test_instructions_doc_type_in_knowledge_docs_router(self):
        text = read(KNOWLEDGE_DOCS_RTR)
        assert "instructions" in text, (
            "'instructions' not added to VALID_DOC_TYPES in knowledge_docs.py — "
            "AgentTrainingPanel cannot persist instructions as knowledge doc"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestFrontendAgentTraining
# ═══════════════════════════════════════════════════════════════════════════


class TestFrontendAgentTraining:
    """Frontend: AgentTrainingPanel, IcpResearchPanel, leads.ts, knowledge-docs.ts."""

    def test_agent_training_panel_exists(self):
        assert AGENT_TRAINING_TSX.exists(), (
            "apps/web/src/components/agent-training-panel.tsx missing — "
            "Intelligence page Train buttons have no expandable panel"
        )

    def test_icp_research_panel_exists(self):
        assert ICP_PANEL_TSX.exists(), (
            "apps/web/src/components/icp-research-panel.tsx missing — "
            "Sales → ICP Research tab has no component"
        )

    def test_leads_api_has_icp_methods(self):
        text = read(LEADS_TS)
        assert "icpResearch" in text and "icpMethodology" in text, (
            "icpResearch() or icpMethodology() missing from leads.ts — "
            "IcpResearchPanel cannot call the backend"
        )

    def test_instructions_type_in_knowledge_docs_ts(self):
        text = read(KNOWLEDGE_DOCS_TS)
        assert '"instructions"' in text or "'instructions'" in text, (
            "'instructions' not added to DocType union in knowledge-docs.ts — "
            "TypeScript will reject AgentTrainingPanel's doc_type assignment"
        )
