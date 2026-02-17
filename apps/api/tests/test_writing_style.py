"""Tests for human writing style integration (Slice 7A).

Pure unit tests — no external dependencies, no API calls.
Verifies that anti-AI-tell rules are properly injected into all
content-generating prompt templates.
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Writing Style Module Tests ──────────────────────────────


class TestWritingStyleModule:
    """Verify the writing_style.py module exports the right constants."""

    def test_hard_bans_contains_em_dash_rule(self):
        from worker.graph.prompts.writing_style import HARD_BANS
        assert "em dash" in HARD_BANS.lower()

    def test_hard_bans_contains_reversal_rule(self):
        from worker.graph.prompts.writing_style import HARD_BANS
        assert "not just X, it is Y" in HARD_BANS

    def test_hard_bans_contains_triplet_rule(self):
        from worker.graph.prompts.writing_style import HARD_BANS
        assert "sets of three" in HARD_BANS

    def test_hard_bans_contains_modular_writing_rule(self):
        from worker.graph.prompts.writing_style import HARD_BANS
        assert "modular writing" in HARD_BANS.lower()

    def test_forbidden_words_list(self):
        from worker.graph.prompts.writing_style import FORBIDDEN_WORDS
        for word in [
            "elevate", "delve", "robust", "innovative", "groundbreaking",
            "supercharge", "unleash", "empower", "boost", "unlock",
        ]:
            assert word in FORBIDDEN_WORDS.lower(), f"'{word}' not in forbidden list"

    def test_human_signals_contains_anchor(self):
        from worker.graph.prompts.writing_style import HUMAN_SIGNALS
        assert "personal anchor" in HUMAN_SIGNALS.lower()

    def test_human_signals_contains_platform_norms(self):
        from worker.graph.prompts.writing_style import HUMAN_SIGNALS
        assert "platform norms" in HUMAN_SIGNALS.lower()

    def test_combined_rules_includes_all_sections(self):
        from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES
        assert "WRITING RULES" in HUMAN_WRITING_RULES
        assert "FORBIDDEN WORDS" in HUMAN_WRITING_RULES
        assert "HUMAN WRITING SIGNALS" in HUMAN_WRITING_RULES

    def test_ai_tells_checklist_has_scan_items(self):
        from worker.graph.prompts.writing_style import AI_TELLS_CHECKLIST
        assert "Red Flag Scan" in AI_TELLS_CHECKLIST
        assert "em dash" in AI_TELLS_CHECKLIST.lower()
        assert "forbidden list" in AI_TELLS_CHECKLIST.lower()

    def test_platform_styles_has_required_platforms(self):
        from worker.graph.prompts.writing_style import PLATFORM_STYLES
        assert "youtube_script" in PLATFORM_STYLES
        assert "linkedin_post" in PLATFORM_STYLES
        assert "linkedin_comment" in PLATFORM_STYLES
        assert "email" in PLATFORM_STYLES
        assert "dm" in PLATFORM_STYLES


# ── Prompt Integration Tests ────────────────────────────────


class TestScriptGenerationPrompts:
    """Verify writing rules are injected into script_generation prompts."""

    def test_system_long_contains_writing_rules(self):
        from worker.graph.prompts.script_generation import SYSTEM_LONG
        assert "WRITING RULES" in SYSTEM_LONG
        assert "FORBIDDEN WORDS" in SYSTEM_LONG

    def test_system_shorts_contains_writing_rules(self):
        from worker.graph.prompts.script_generation import SYSTEM_SHORTS
        assert "WRITING RULES" in SYSTEM_SHORTS
        assert "FORBIDDEN WORDS" in SYSTEM_SHORTS

    def test_system_metadata_contains_writing_rules(self):
        from worker.graph.prompts.script_generation import SYSTEM_METADATA
        assert "WRITING RULES" in SYSTEM_METADATA
        assert "FORBIDDEN WORDS" in SYSTEM_METADATA

    def test_user_long_not_modified(self):
        """USER prompts should not have rules (rules go in SYSTEM)."""
        from worker.graph.prompts.script_generation import USER_LONG
        assert "WRITING RULES" not in USER_LONG


class TestHookLabPrompts:
    """Verify writing rules are injected into hook_lab prompts."""

    def test_system_contains_writing_rules(self):
        from worker.graph.prompts.hook_lab import SYSTEM
        assert "WRITING RULES" in SYSTEM
        assert "FORBIDDEN WORDS" in SYSTEM

    def test_user_not_modified(self):
        from worker.graph.prompts.hook_lab import USER
        assert "WRITING RULES" not in USER


class TestEditorPrompts:
    """Verify writing rules AND AI-tells checklist in editor prompts."""

    def test_system_contains_writing_rules(self):
        from worker.graph.prompts.editor import SYSTEM
        assert "WRITING RULES" in SYSTEM
        assert "FORBIDDEN WORDS" in SYSTEM

    def test_system_contains_ai_tells_checklist(self):
        from worker.graph.prompts.editor import SYSTEM
        assert "AI-Tell Red Flag Scan" in SYSTEM
        assert "forbidden list" in SYSTEM.lower()

    def test_user_contains_red_flag_scan_step(self):
        from worker.graph.prompts.editor import USER
        assert "Red Flag Scan" in USER

    def test_editor_has_both_rules_and_checklist(self):
        """Editor should have both the writing rules AND the scan checklist."""
        from worker.graph.prompts.editor import SYSTEM
        assert "HUMAN WRITING SIGNALS" in SYSTEM
        assert "Red Flag Scan" in SYSTEM
