"""Tests for Slice 79: Polish Sprint — Nav, Pipeline Status, Model Fix.

Covers:
- Pipeline status endpoint exists in agent_bridge (~2 tests)
- Copywriter model matches openclaw.json (openai/gpt-4o) (~2 tests)
- MC_SUB_NAV constant has 8 entries (~2 tests)
- NotificationBell component file exists (~1 test)
- DEFAULT_AGENTS still has 8 agents (~1 test)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Pipeline Status Endpoint ────────────────────────────────────

class TestPipelineStatusEndpoint:
    """Test that the pipeline status GET endpoint exists."""

    def test_pipeline_status_route_exists(self):
        import inspect
        from app.routers import agent_bridge

        source = inspect.getsource(agent_bridge)
        assert '"/pipeline/{workflow_id}"' in source or "'/pipeline/{workflow_id}'" in source

    def test_pipeline_status_is_get(self):
        """Verify it's a GET endpoint, not POST."""
        import inspect
        from app.routers import agent_bridge

        source = inspect.getsource(agent_bridge)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "pipeline/{workflow_id}" in line:
                # Check surrounding lines for @router.get
                context = "\n".join(lines[max(0, i - 3) : i + 1])
                assert "router.get" in context, (
                    f"Expected @router.get for pipeline status, got: {context}"
                )
                return
        pytest.fail("Could not find pipeline/{workflow_id} route")


# ── Copywriter Model Match ──────────────────────────────────────

class TestCopywriterModelMatch:
    """Test that copywriter in DEFAULT_AGENTS matches openclaw.json."""

    def test_copywriter_uses_openai(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        copywriter = next(a for a in DEFAULT_AGENTS if a["id"] == "copywriter")
        assert copywriter["model_provider"] == "openai", (
            f"Expected openai, got {copywriter['model_provider']}"
        )

    def test_copywriter_uses_gpt4o(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        copywriter = next(a for a in DEFAULT_AGENTS if a["id"] == "copywriter")
        assert copywriter["model_name"] == "gpt-4o", (
            f"Expected gpt-4o, got {copywriter['model_name']}"
        )


# ── MC_SUB_NAV Constant ────────────────────────────────────────

CONSTANTS_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "apps"
    / "web"
    / "src"
    / "app"
    / "mission-control"
    / "constants.ts"
)


class TestMCSubNavConstant:
    """Test that MC_SUB_NAV exists in the shared constants file."""

    def test_constants_file_has_mc_sub_nav(self):
        assert CONSTANTS_FILE.exists(), f"constants.ts not found at {CONSTANTS_FILE}"
        content = CONSTANTS_FILE.read_text()
        assert "MC_SUB_NAV" in content

    def test_mc_sub_nav_has_eight_entries(self):
        content = CONSTANTS_FILE.read_text()
        # Count entries by counting 'href:' occurrences after MC_SUB_NAV
        mc_section = content[content.index("MC_SUB_NAV"):]
        # Count items by finding href entries
        href_count = mc_section.count("href:")
        assert href_count == 8, f"Expected 8 MC_SUB_NAV entries, found {href_count}"


# ── Notification Bell Component ─────────────────────────────────

BELL_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "apps"
    / "web"
    / "src"
    / "app"
    / "mission-control"
    / "components"
    / "notification-bell.tsx"
)


class TestNotificationBellComponent:
    """Test that the NotificationBell component exists."""

    def test_notification_bell_file_exists(self):
        assert BELL_FILE.exists(), f"notification-bell.tsx not found at {BELL_FILE}"
        content = BELL_FILE.read_text()
        assert "NotificationBell" in content


# ── DEFAULT_AGENTS Still Eight ──────────────────────────────────

class TestDefaultAgentsStillEight:
    """Verify DEFAULT_AGENTS count hasn't changed after model fix."""

    def test_eight_default_agents(self):
        from app.routers.mission_control import DEFAULT_AGENTS

        assert len(DEFAULT_AGENTS) == 8, (
            f"Expected 8 DEFAULT_AGENTS, got {len(DEFAULT_AGENTS)}"
        )
