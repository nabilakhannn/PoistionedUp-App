"""
Slice 93: Landing Page Generator

12 tests across 5 classes:
  TestLandingPageService   (3): service file, structure_page fn, generate_page fn
  TestLandingPageRouter    (3): router file, /structure endpoint, /generate endpoint
  TestLandingPageStudio    (3): component file, imports landingPageApi, has download
  TestMarketingPageUpdate  (2): landing section in sidebar, LandingPageStudio imported
  TestMigration            (1): migration file + generated_landing_pages table
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
API = REPO / "apps" / "api"
WEB = REPO / "apps" / "web" / "src"

SERVICE = API / "app" / "services" / "landing_page.py"
ROUTER = API / "app" / "routers" / "landing_page.py"
STUDIO = WEB / "components" / "landing-page-studio.tsx"
MARKETING_PAGE = WEB / "app" / "marketing" / "page.tsx"
MIGRATION = REPO / "infra" / "supabase" / "migrations" / "035_landing_page.sql"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestLandingPageService
# ═══════════════════════════════════════════════════════════════════════════


class TestLandingPageService:
    """landing_page.py service exists and has both pipeline functions."""

    def test_service_file_exists(self):
        assert SERVICE.exists(), (
            "apps/api/app/services/landing_page.py not found — "
            "landing page generation service must be created"
        )

    def test_structure_page_function_present(self):
        text = read(SERVICE)
        assert "def structure_page(" in text, (
            "structure_page() function missing from landing_page.py service — "
            "Phase 1 (Haiku blueprint) must be implemented"
        )
        assert "claude-haiku" in text, (
            "structure_page must use Claude Haiku (cheap) for blueprint generation"
        )

    def test_generate_page_function_present(self):
        text = read(SERVICE)
        assert "def generate_page(" in text, (
            "generate_page() function missing from landing_page.py service — "
            "Phase 2 (Sonnet HTML generation) must be implemented"
        )
        assert "claude-sonnet" in text, (
            "generate_page must use Claude Sonnet for full HTML generation"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestLandingPageRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestLandingPageRouter:
    """landing_page.py router exists and has the correct endpoints."""

    def test_router_file_exists(self):
        assert ROUTER.exists(), (
            "apps/api/app/routers/landing_page.py not found — "
            "router must be created"
        )

    def test_structure_endpoint_present(self):
        text = read(ROUTER)
        assert "/landing-page/structure" in text, (
            "POST /landing-page/structure endpoint missing from router — "
            "frontend calls this for Phase 1 blueprint (near-free)"
        )

    def test_generate_endpoint_present(self):
        text = read(ROUTER)
        assert "/landing-page/generate" in text, (
            "POST /landing-page/generate endpoint missing from router — "
            "frontend calls this for Phase 2 full HTML generation"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestLandingPageStudio
# ═══════════════════════════════════════════════════════════════════════════


class TestLandingPageStudio:
    """landing-page-studio.tsx component exists and has required features."""

    def test_studio_file_exists(self):
        assert STUDIO.exists(), (
            "apps/web/src/components/landing-page-studio.tsx not found — "
            "LandingPageStudio component must be created"
        )

    def test_imports_landing_page_api(self):
        text = read(STUDIO)
        assert "landingPageApi" in text, (
            "landing-page-studio.tsx must import landingPageApi from @/lib/api/landing-page"
        )
        assert "structurePage" in text, (
            "LandingPageStudio must call landingPageApi.structurePage() for Phase 1"
        )
        assert "generatePage" in text, (
            "LandingPageStudio must call landingPageApi.generatePage() for Phase 2"
        )

    def test_has_download_functionality(self):
        text = read(STUDIO)
        assert "Download HTML" in text or "download" in text.lower(), (
            "LandingPageStudio must have a Download HTML button for exporting the page"
        )
        assert "Blob" in text, (
            "Download must use client-side Blob (not a separate API endpoint)"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestMarketingPageUpdate
# ═══════════════════════════════════════════════════════════════════════════


class TestMarketingPageUpdate:
    """Marketing page has Landing Pages section in sidebar."""

    def test_landing_section_in_sidebar(self):
        text = read(MARKETING_PAGE)
        assert "landing" in text, (
            "marketing/page.tsx must have 'landing' in Section type and SECTIONS array"
        )
        assert "Landing Pages" in text, (
            "Marketing sidebar must show 'Landing Pages' as a section label"
        )

    def test_landing_page_studio_imported(self):
        text = read(MARKETING_PAGE)
        assert "LandingPageStudio" in text, (
            "marketing/page.tsx must import and render <LandingPageStudio> "
            "for the landing pages section"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestMigration
# ═══════════════════════════════════════════════════════════════════════════


class TestMigration:
    """Migration 035 exists and creates the generated_landing_pages table."""

    def test_migration_file_exists_with_table(self):
        assert MIGRATION.exists(), (
            "infra/supabase/migrations/035_landing_page.sql not found — "
            "migration must be created for generated_landing_pages table"
        )
        text = read(MIGRATION)
        assert "generated_landing_pages" in text, (
            "Migration 035 must create the generated_landing_pages table"
        )
        assert "ROW LEVEL SECURITY" in text or "ENABLE ROW LEVEL SECURITY" in text, (
            "Migration must enable RLS on generated_landing_pages for user isolation"
        )
