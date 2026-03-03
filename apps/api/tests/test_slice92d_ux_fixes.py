"""
Slice 92d: UX Fixes — Notion Sidebar + Kanban Error Handling

8 tests across 3 classes:
  TestMarketingPageSidebar  (3) — sidebar layout replaces tab bar, all 6 sections present, NoBrand helper
  TestContentKanbanErrors   (3) — loadError state, actionError state, retry button
  TestNoTabBarOverflow      (2) — no 6-tab flex bar in marketing page, competitors accessible in sidebar
"""

from pathlib import Path

REPO = Path(__file__).parents[3]
WEB = REPO / "apps" / "web" / "src"

MARKETING_PAGE = WEB / "app" / "marketing" / "page.tsx"
CONTENT_KANBAN = WEB / "components" / "content-kanban.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# TestMarketingPageSidebar
# ═══════════════════════════════════════════════════════════════════════════


class TestMarketingPageSidebar:
    """Marketing page uses a left sidebar, not a horizontal tab bar."""

    def test_sidebar_element_present(self):
        text = read(MARKETING_PAGE)
        assert "<aside" in text, (
            "marketing/page.tsx must use <aside> for the left sidebar navigation"
        )

    def test_all_six_sections_present(self):
        text = read(MARKETING_PAGE)
        for key in ("content", "calendar", "ads", "images", "competitors", "analytics"):
            assert key in text, (
                f"Section '{key}' missing from marketing/page.tsx sidebar sections list"
            )

    def test_no_brand_helper_component_present(self):
        text = read(MARKETING_PAGE)
        assert "NoBrand" in text, (
            "marketing/page.tsx must define/use a NoBrand fallback component for brand-less state"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestContentKanbanErrors
# ═══════════════════════════════════════════════════════════════════════════


class TestContentKanbanErrors:
    """content-kanban.tsx shows visible errors instead of silently swallowing them."""

    def test_load_error_state_present(self):
        text = read(CONTENT_KANBAN)
        assert "loadError" in text, (
            "ContentKanban must have a loadError state to show when stages fail to load"
        )

    def test_action_error_state_present(self):
        text = read(CONTENT_KANBAN)
        assert "actionError" in text, (
            "ContentKanban must have an actionError state to show when rename/delete/toggle fails"
        )

    def test_no_silent_catch_ignore(self):
        text = read(CONTENT_KANBAN)
        # The old pattern was: catch {\n      // ignore
        assert "// ignore" not in text, (
            "ContentKanban must not silently swallow errors with '// ignore' — "
            "show error banners so users know what went wrong"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestNoTabBarOverflow
# ═══════════════════════════════════════════════════════════════════════════


class TestNoTabBarOverflow:
    """Horizontal 6-tab bar replaced — competitors section no longer gets cut off."""

    def test_no_horizontal_tab_bar(self):
        text = read(MARKETING_PAGE)
        # Old pattern: border-b-2 tab buttons in a flex row
        assert "border-b-2" not in text, (
            "marketing/page.tsx still contains horizontal tab bar styling (border-b-2). "
            "Tabs must be replaced with the left sidebar."
        )

    def test_competitors_accessible_in_sidebar(self):
        text = read(MARKETING_PAGE)
        assert "competitors" in text, (
            "Competitors section must be present in the sidebar so it's always accessible"
        )
        assert "CompetitorIntelEmbed" in text, (
            "marketing/page.tsx must render <CompetitorIntelEmbed> for the competitors section"
        )
