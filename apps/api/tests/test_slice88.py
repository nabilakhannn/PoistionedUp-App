"""
Slice 88: UX Overhaul — Onboarding + Home Inbox + 5-Tab Nav

18 tests across 5 classes:
  TestNavRestructure   — 3  (MC_SUB_NAV is 5 tabs with correct labels)
  TestOnboarding       — 5  (wizard exists, steps, redirect guard)
  TestHomeInbox        — 4  (approval section, 7-day strip, agents, briefing)
  TestContentTab       — 3  (pipeline, trending, queue filters)
  TestSettingsExpansion — 3 (4 sub-tabs, old routes still work)
"""

import re
import pytest
from pathlib import Path

REPO = Path(__file__).parents[3]
WEB = REPO / "apps" / "web" / "src"
MC = WEB / "app" / "mission-control"


# ── Helper ──────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════
# TestNavRestructure
# ═══════════════════════════════════════════════════════════

class TestNavRestructure:
    """MC_SUB_NAV has exactly 5 user-friendly tabs."""

    def _nav_entries(self):
        text = read(MC / "constants.ts")
        # Extract MC_SUB_NAV block
        m = re.search(r"MC_SUB_NAV\s*=\s*\[(.*?)\];", text, re.DOTALL)
        assert m, "MC_SUB_NAV not found in constants.ts"
        block = m.group(1)
        hrefs = re.findall(r'href:\s*"(/[^"]+)"', block)
        labels = re.findall(r'label:\s*"([^"]+)"', block)
        return hrefs, labels

    def test_mc_sub_nav_has_exactly_five_entries(self):
        hrefs, _ = self._nav_entries()
        assert len(hrefs) == 5, f"Expected 5 MC_SUB_NAV entries, got {len(hrefs)}: {hrefs}"

    def test_mc_sub_nav_has_correct_labels(self):
        _, labels = self._nav_entries()
        expected = {"Home", "Content", "My Team", "Results", "Settings"}
        assert set(labels) == expected, f"Expected {expected}, got {set(labels)}"

    def test_mc_sub_nav_home_points_to_mission_control(self):
        hrefs, labels = self._nav_entries()
        nav = dict(zip(labels, hrefs))
        assert nav.get("Home") == "/mission-control", (
            f"Home tab should point to /mission-control, got {nav.get('Home')}"
        )


# ═══════════════════════════════════════════════════════════
# TestOnboarding
# ═══════════════════════════════════════════════════════════

class TestOnboarding:
    """4-step onboarding wizard exists and is correctly structured."""

    def test_onboarding_page_exists(self):
        page = WEB / "app" / "onboarding" / "page.tsx"
        assert page.exists(), "/app/onboarding/page.tsx not found"

    def test_onboarding_has_four_steps(self):
        text = read(WEB / "app" / "onboarding" / "page.tsx")
        # Should reference steps 1 through 4
        for step in [1, 2, 3, 4]:
            assert f"step === {step}" in text or f"Step {step}" in text, (
                f"Step {step} not found in onboarding page"
            )

    def test_onboarding_step1_calls_brands_create(self):
        text = read(WEB / "app" / "onboarding" / "page.tsx")
        assert "personalBrandsApi" in text, "personalBrandsApi not imported"
        assert "create" in text, "personalBrandsApi.create not referenced"

    def test_onboarding_step2_saves_foundation(self):
        text = read(WEB / "app" / "onboarding" / "page.tsx")
        assert "updateFoundation" in text, "updateFoundation not referenced in onboarding"
        assert "beliefs" in text, "'beliefs' key not found in voice sample save"

    def test_onboarding_guard_exists_and_checks_brands(self):
        guard = WEB / "app" / "onboarding-guard.tsx"
        assert guard.exists(), "onboarding-guard.tsx not found"
        text = read(guard)
        assert "onboarding_done" in text, "onboarding_done localStorage key not in guard"
        assert "brands.length" in text or "brands.length === 0" in text, (
            "Guard must check brands.length"
        )


# ═══════════════════════════════════════════════════════════
# TestHomeInbox
# ═══════════════════════════════════════════════════════════

class TestHomeInbox:
    """Redesigned /mission-control shows approval inbox, calendar strip, agents, briefing."""

    def _page(self):
        return read(MC / "page.tsx")

    def test_home_has_needs_your_approval_section(self):
        text = self._page()
        assert "approval" in text.lower() or "Needs your approval" in text, (
            "Home page missing 'Needs your approval' section"
        )

    def test_home_shows_agent_office(self):
        text = self._page()
        # Slice 90: 7-day strip replaced by visual Agent Office component
        assert "AgentOffice" in text, (
            "Home page must import and render <AgentOffice /> (Slice 90 replaced 7-day strip)"
        )

    def test_home_shows_agent_status(self):
        text = self._page()
        # Slice 90: agents now shown via AgentOffice component (imported from components/)
        assert "agent-office" in text or "AgentOffice" in text, (
            "AgentOffice import missing from Home page"
        )

    def test_home_shows_reject_tags(self):
        text = self._page()
        for tag in ["Wrong voice", "Bad hook", "Needs research", "Off-topic"]:
            assert tag in text, f"Reject tag '{tag}' not found in Home page"


# ═══════════════════════════════════════════════════════════
# TestContentTab
# ═══════════════════════════════════════════════════════════

class TestContentTab:
    """New /mission-control/content page has pipeline, trending, and queue."""

    def _page(self):
        page = MC / "content" / "page.tsx"
        assert page.exists(), "/mission-control/content/page.tsx not found"
        return read(page)

    def test_content_tab_exists(self):
        page = MC / "content" / "page.tsx"
        assert page.exists(), "/mission-control/content/page.tsx must exist"

    def test_content_tab_has_pipeline_section(self):
        text = self._page()
        assert "Pipeline" in text or "pipeline" in text.lower(), (
            "Pipeline section missing from Content tab"
        )
        # Should show Researching, Writing, QA, Ready stages
        for stage in ["Researching", "Writing", "QA", "Ready"]:
            assert stage in text, f"Pipeline stage '{stage}' not found"

    def test_content_tab_has_queue_filter_tabs(self):
        text = self._page()
        for tab in ["draft", "scheduled", "published"]:
            assert tab in text, f"Queue filter tab '{tab}' not found"


# ═══════════════════════════════════════════════════════════
# TestSettingsExpansion
# ═══════════════════════════════════════════════════════════

class TestSettingsExpansion:
    """Settings page has 4 sub-tabs and old routes are unchanged."""

    def _settings(self):
        return read(MC / "settings" / "page.tsx")

    def test_settings_has_four_sub_tabs(self):
        text = self._settings()
        # Slice 90: tabs updated to Connectors / Pipeline / Knowledge Base / Team & System
        for tab in ["Connectors", "Pipeline", "Knowledge Base", "Team"]:
            assert tab in text, f"Settings sub-tab '{tab}' not found"

    def test_settings_connectors_tab_is_default(self):
        text = self._settings()
        # Should default to connectors via state
        assert "connectors" in text and ("activeTab" in text or "useState" in text), (
            "Settings should manage activeTab state defaulting to connectors"
        )

    def test_old_playbooks_route_still_exists(self):
        playbooks = MC / "playbooks" / "page.tsx"
        assert playbooks.exists(), (
            "/mission-control/playbooks/page.tsx must still exist as direct route"
        )
