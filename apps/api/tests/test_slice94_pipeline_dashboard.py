"""
Slice 94: Pipeline Dashboard + Research Brief Live Feed

8 tests across 4 classes:
  TestResearchBriefsEndpoint (3): endpoint present, UUID guard, returns null when empty
  TestMCHomeChanges          (2): pipeline funnel section, latest research card
  TestIntelligenceResearch   (2): real data path, CTA when no brief
  TestBriefApiClient         (1): research-briefs.ts API client follows project pattern
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API  = REPO / "apps" / "api"
WEB  = REPO / "apps" / "web" / "src"

RESEARCH_ROUTER  = API / "app" / "routers" / "research.py"
MC_HOME          = WEB / "app" / "mission-control" / "page.tsx"
INTEL_PAGE       = WEB / "app" / "intelligence" / "page.tsx"
BRIEF_CLIENT     = WEB / "lib" / "api" / "research-briefs.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestResearchBriefsEndpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestResearchBriefsEndpoint:
    """GET /research/briefs/latest is in research.py with auth + IDOR guard."""

    def test_endpoint_present(self):
        text = read(RESEARCH_ROUTER)
        assert "/briefs/latest" in text, (
            "GET /research/briefs/latest endpoint missing from research.py — "
            "Intelligence page needs this to fetch the real research brief"
        )

    def test_uuid_validation(self):
        text = read(RESEARCH_ROUTER)
        assert "_UUID_RE" in text, (
            "_UUID_RE pattern missing from research.py — "
            "brand_id must be validated as UUID (OWASP A03)"
        )

    def test_user_id_idor_guard(self):
        text = read(RESEARCH_ROUTER)
        assert "user.id" in text and "research_briefs" in text, (
            "research_briefs query must filter by user.id (IDOR guard) — "
            "users must not see each other's research briefs"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestMCHomeChanges
# ═══════════════════════════════════════════════════════════════════════════


class TestMCHomeChanges:
    """Mission Control home shows pipeline funnel and research brief card."""

    def test_pipeline_funnel_present(self):
        text = read(MC_HOME)
        assert "Content Pipeline" in text, (
            "Mission Control home must show 'Content Pipeline' funnel section — "
            "users need to see how many items are in each stage"
        )
        assert "StageCard" in text, (
            "StageCard component must be used in mission-control/page.tsx — "
            "renders each pipeline stage (Research/Writing/QA/Review/Scheduled)"
        )

    def test_latest_research_card_present(self):
        text = read(MC_HOME)
        assert "Latest Research" in text, (
            "'Latest Research' card missing from Mission Control home — "
            "users must see the last research brief snippet with 'View full brief →' link"
        )
        assert "researchBriefsApi" in text, (
            "researchBriefsApi must be imported and used in mission-control/page.tsx"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestIntelligenceResearch
# ═══════════════════════════════════════════════════════════════════════════


class TestIntelligenceResearch:
    """Intelligence Research tab fetches real data and handles empty state."""

    def test_fetches_real_brief(self):
        text = read(INTEL_PAGE)
        assert "researchBriefsApi" in text, (
            "Intelligence page must import researchBriefsApi — "
            "Research tab must fetch real data from research_briefs table"
        )
        assert "getLatest" in text, (
            "Intelligence page must call researchBriefsApi.getLatest() — "
            "fetches the latest brief for the current brand"
        )

    def test_cta_when_no_brief(self):
        text = read(INTEL_PAGE)
        assert "Run the pipeline" in text or "Run Now" in text, (
            "Intelligence Research tab must show a 'Run pipeline' CTA "
            "when no brief exists yet — guide users to trigger their first run"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestBriefApiClient
# ═══════════════════════════════════════════════════════════════════════════


class TestBriefApiClient:
    """research-briefs.ts follows the project's API client pattern."""

    def test_api_client_exists_and_correct(self):
        assert BRIEF_CLIENT.exists(), (
            "apps/web/src/lib/api/research-briefs.ts not found — "
            "must be created to call GET /research/briefs/latest"
        )
        text = read(BRIEF_CLIENT)
        assert "researchBriefsApi" in text, (
            "research-briefs.ts must export researchBriefsApi object"
        )
        assert "apiFetch" in text, (
            "research-briefs.ts must use apiFetch from ./client (project pattern)"
        )
        assert "getLatest" in text, (
            "researchBriefsApi must have a getLatest(brandId) method"
        )
