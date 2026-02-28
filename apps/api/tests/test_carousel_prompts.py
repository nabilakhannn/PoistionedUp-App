"""Tests for Slice 74: Carousel Prompt Templates.

Covers:
- SYSTEM and USER prompt constants exist and are non-empty
- USER template has all required placeholders
- Writing style integration
- Platform variant descriptions
"""

from __future__ import annotations


class TestCarouselPromptConstants:
    """Test that carousel prompt templates are well-formed."""

    def test_system_prompt_exists(self):
        from worker.graph.prompts.carousel import SYSTEM

        assert isinstance(SYSTEM, str)
        assert len(SYSTEM) > 100

    def test_user_prompt_exists(self):
        from worker.graph.prompts.carousel import USER

        assert isinstance(USER, str)
        assert len(USER) > 100

    def test_system_includes_writing_rules(self):
        from worker.graph.prompts.carousel import SYSTEM

        assert "WRITING RULES" in SYSTEM or "Human Writing Style" in SYSTEM

    def test_user_has_all_placeholders(self):
        from worker.graph.prompts.carousel import USER

        required = [
            "{topic_title}",
            "{audience_pain}",
            "{voice}",
            "{brand_context}",
        ]
        for placeholder in required:
            assert placeholder in USER, f"Missing placeholder: {placeholder}"

    def test_user_template_formats_cleanly(self):
        from worker.graph.prompts.carousel import USER

        result = USER.format(
            topic_title="Test Topic",
            audience_pain="They need help with Y",
            voice='{"tone": "professional"}',
            brand_context="Brand statement: Test",
        )
        assert "Test Topic" in result
        assert "They need help with Y" in result

    def test_user_requests_json_output(self):
        from worker.graph.prompts.carousel import USER

        assert '"carousel_slides"' in USER

    def test_user_describes_two_platforms(self):
        from worker.graph.prompts.carousel import USER

        lower = USER.lower()
        assert "linkedin" in lower
        assert "instagram" in lower

    def test_slide_structure_described(self):
        from worker.graph.prompts.carousel import USER

        assert "slide_number" in USER
        assert "title" in USER
        assert "body" in USER
        assert "visual_cue" in USER
