"""Tests for Slice 74: Ad Copy Prompt Templates.

Covers:
- SYSTEM and USER prompt constants exist and are non-empty
- USER template has all required placeholders
- No missing format fields
- Ad copy JSON schema expectations
- Writing style integration
"""

from __future__ import annotations


class TestAdCopyPromptConstants:
    """Test that ad copy prompt templates are well-formed."""

    def test_system_prompt_exists(self):
        from worker.graph.prompts.ad_copy import SYSTEM

        assert isinstance(SYSTEM, str)
        assert len(SYSTEM) > 100

    def test_user_prompt_exists(self):
        from worker.graph.prompts.ad_copy import USER

        assert isinstance(USER, str)
        assert len(USER) > 100

    def test_system_includes_writing_rules(self):
        from worker.graph.prompts.ad_copy import SYSTEM

        assert "WRITING RULES" in SYSTEM or "Human Writing Style" in SYSTEM

    def test_user_has_all_placeholders(self):
        from worker.graph.prompts.ad_copy import USER

        required = [
            "{topic_title}",
            "{audience_pain}",
            "{voice}",
            "{brand_context}",
            "{offer_context}",
        ]
        for placeholder in required:
            assert placeholder in USER, f"Missing placeholder: {placeholder}"

    def test_user_template_formats_cleanly(self):
        from worker.graph.prompts.ad_copy import USER

        result = USER.format(
            topic_title="Test Topic",
            audience_pain="They struggle with X",
            voice='{"tone": "conversational"}',
            brand_context="Brand statement: Test",
            offer_context="Offer: Test product",
        )
        assert "Test Topic" in result
        assert "They struggle with X" in result

    def test_user_requests_json_output(self):
        from worker.graph.prompts.ad_copy import USER

        assert '"ad_copy"' in USER

    def test_user_describes_three_ad_formats(self):
        from worker.graph.prompts.ad_copy import USER

        assert "single_image" in USER.lower() or "single image" in USER.lower()
        assert "carousel" in USER.lower()
        assert "video" in USER.lower()

    def test_system_mentions_character_limits(self):
        from worker.graph.prompts.ad_copy import SYSTEM

        assert "40" in SYSTEM  # headline max
        assert "125" in SYSTEM  # body max
