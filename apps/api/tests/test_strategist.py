"""Tests for Brand Strategist v2 (Slices 49-55).

Tests for:
  - Brand Fields Registry (brand_fields.py)
  - Sequencing Engine (brand_sequencing.py)
  - Strategist Service (brand_strategist.py): parsing, saving, prompts
  - Strategist Router endpoints (strategist.py)
"""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load .env so app.config.settings can initialize
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Brand Fields Registry ─────────────────────────────────────────


class TestBrandFieldsRegistry:
    """Test the brand fields registry and lookup functions."""

    def test_all_fields_count(self):
        from app.services.brand_fields import ALL_FIELDS, TOTAL_FIELDS
        # Should have fields across 8 modules
        assert len(ALL_FIELDS) > 30
        assert TOTAL_FIELDS == len(ALL_FIELDS)

    def test_modules_list(self):
        from app.services.brand_fields import MODULES
        assert len(MODULES) == 8
        assert MODULES[0] == "foundation"
        assert "authority" in MODULES
        assert "ica" in MODULES
        assert "positioning" in MODULES
        assert "voice" in MODULES
        assert "offer" in MODULES
        assert "content_pillars" in MODULES
        assert "competitive" in MODULES

    def test_fields_by_key_lookup(self):
        from app.services.brand_fields import get_field
        field = get_field("foundation.what_you_do")
        assert field is not None
        assert field.module == "foundation"
        assert field.key == "what_you_do"
        assert field.base_weight == 10  # Highest priority

    def test_unknown_field_returns_none(self):
        from app.services.brand_fields import get_field
        assert get_field("nonexistent.field") is None

    def test_module_fields(self):
        from app.services.brand_fields import get_module_fields
        foundation = get_module_fields("foundation")
        assert len(foundation) >= 5
        keys = [f.key for f in foundation]
        assert "what_you_do" in keys
        assert "90_day_goal" in keys
        assert "current_clients" in keys

    def test_empty_module_returns_empty_list(self):
        from app.services.brand_fields import get_module_fields
        assert get_module_fields("nonexistent") == []

    def test_module_labels(self):
        from app.services.brand_fields import MODULE_LABELS
        assert MODULE_LABELS["foundation"] == "Foundation"
        assert MODULE_LABELS["ica"] == "Ideal Client Avatar"
        assert MODULE_LABELS["competitive"] == "Competitive Positioning"

    def test_required_fields(self):
        from app.services.brand_fields import get_required_fields, TOTAL_REQUIRED_FIELDS
        required = get_required_fields()
        assert len(required) == TOTAL_REQUIRED_FIELDS
        assert all(f.is_required for f in required)

    def test_foundation_what_you_do_has_no_dependencies(self):
        from app.services.brand_fields import get_field
        field = get_field("foundation.what_you_do")
        assert field.dependencies == ()

    def test_ica_depends_on_foundation(self):
        from app.services.brand_fields import get_field
        field = get_field("ica.one_sentence_identity")
        assert "foundation.what_you_do" in field.dependencies
        assert "foundation.current_clients" in field.dependencies

    def test_positioning_depends_on_authority_and_ica(self):
        from app.services.brand_fields import get_field
        field = get_field("positioning.positioning_statement")
        assert "authority.unfair_advantage" in field.dependencies
        assert "ica.one_sentence_identity" in field.dependencies

    def test_fields_by_module_dict(self):
        from app.services.brand_fields import FIELDS_BY_MODULE
        assert "foundation" in FIELDS_BY_MODULE
        assert "authority" in FIELDS_BY_MODULE
        assert len(FIELDS_BY_MODULE) == 8


# ── Sequencing Engine ────────────────────────────────────────────


class TestSequencingEngine:
    """Test the smart sequencing engine."""

    def test_empty_profile_returns_what_you_do(self):
        from app.services.brand_sequencing import get_next_field
        next_f = get_next_field({})
        assert next_f is not None
        assert next_f.module == "foundation"
        assert next_f.key == "what_you_do"

    def test_filled_fields_empty_profile(self):
        from app.services.brand_sequencing import get_filled_fields
        filled = get_filled_fields({})
        assert len(filled) == 0

    def test_filled_fields_with_data(self):
        from app.services.brand_sequencing import get_filled_fields
        profile = {
            "foundation": {
                "what_you_do": "I help coaches build personal brands",
                "90_day_goal": "Get 5 clients at $3000",
            },
            "authority": {
                "unfair_advantage": "10 years experience",
            },
        }
        filled = get_filled_fields(profile)
        assert "foundation.what_you_do" in filled
        assert "foundation.90_day_goal" in filled
        assert "authority.unfair_advantage" in filled
        assert len(filled) == 3

    def test_filled_fields_ignores_empty_values(self):
        from app.services.brand_sequencing import get_filled_fields
        profile = {
            "foundation": {
                "what_you_do": "I help coaches",
                "90_day_goal": "",  # Empty string
                "current_clients": None,  # None
            },
        }
        filled = get_filled_fields(profile)
        assert "foundation.what_you_do" in filled
        assert "foundation.90_day_goal" not in filled
        assert "foundation.current_clients" not in filled

    def test_next_field_after_what_you_do(self):
        from app.services.brand_sequencing import get_next_field
        profile = {
            "foundation": {
                "what_you_do": "I help coaches build personal brands",
            },
        }
        next_f = get_next_field(profile)
        assert next_f is not None
        # Sequencing engine picks the highest-scoring unfilled field.
        # authority.unfair_advantage has base_weight=8 + dependency bonus
        # that can beat foundation.current_clients (base_weight=9).
        # The key assertion: it must NOT re-ask what_you_do.
        full_key = f"{next_f.module}.{next_f.key}"
        assert full_key != "foundation.what_you_do"

    def test_dependencies_block_ica(self):
        from app.services.brand_sequencing import get_next_field, score_field, get_filled_fields
        from app.services.brand_fields import get_field
        # ICA.one_sentence_identity depends on foundation.what_you_do + current_clients
        # With empty profile, ICA should not be recommended
        profile = {}
        filled = get_filled_fields(profile)
        ica_field = get_field("ica.one_sentence_identity")
        score = score_field(ica_field, filled)
        assert score == 0.0  # Dependencies not met

    def test_dependencies_unblock_ica(self):
        from app.services.brand_sequencing import score_field, get_filled_fields
        from app.services.brand_fields import get_field
        profile = {
            "foundation": {
                "what_you_do": "Coach",
                "current_clients": "Small business owners",
            },
        }
        filled = get_filled_fields(profile)
        ica_field = get_field("ica.one_sentence_identity")
        score = score_field(ica_field, filled)
        assert score > 0.0  # Dependencies met

    def test_calculate_field_completeness_empty(self):
        from app.services.brand_sequencing import calculate_field_completeness
        result = calculate_field_completeness({})
        assert result["overall_percent"] == 0
        assert result["overall_filled"] == 0
        assert result["overall_total"] > 0
        assert len(result["modules"]) == 8
        assert len(result["filled_fields"]) == 0
        assert len(result["unfilled_fields"]) > 0

    def test_calculate_field_completeness_partial(self):
        from app.services.brand_sequencing import calculate_field_completeness
        from app.services.brand_fields import TOTAL_FIELDS
        profile = {
            "foundation": {
                "what_you_do": "I help coaches",
                "current_clients": "Small biz owners",
                "90_day_goal": "5 clients",
                "online_presence_status": "Active but no traction",
                "previous_attempts": "Tried courses",
            },
        }
        result = calculate_field_completeness(profile)
        assert result["overall_filled"] == 5
        assert result["overall_percent"] == int(5 / TOTAL_FIELDS * 100)
        assert "foundation" in result["modules"]
        foundation_mod = result["modules"]["foundation"]
        assert foundation_mod["filled"] == 5

    def test_module_completeness_bonus(self):
        from app.services.brand_sequencing import _module_completeness_bonus, get_filled_fields
        from app.services.brand_fields import get_field, get_module_fields

        # Fill 80%+ of a module to trigger bonus
        # Foundation has ~10 fields (5 required, 5 optional)
        foundation_fields = get_module_fields("foundation")
        profile = {"foundation": {}}
        # Fill first 80% of foundation fields
        num_to_fill = max(1, int(len(foundation_fields) * 0.85))
        for i, f in enumerate(foundation_fields[:num_to_fill]):
            profile["foundation"][f.key] = f"value_{i}"

        filled = get_filled_fields(profile)
        # Get an unfilled foundation field
        unfilled = None
        for f in foundation_fields:
            if f"{f.module}.{f.key}" not in filled:
                unfilled = f
                break

        if unfilled:
            bonus = _module_completeness_bonus(unfilled, filled)
            assert bonus >= 3.0  # Should get 80%+ bonus

    def test_get_next_n_fields(self):
        from app.services.brand_sequencing import get_next_n_fields
        result = get_next_n_fields({}, n=3)
        assert len(result) <= 3
        assert result[0].module == "foundation"
        assert result[0].key == "what_you_do"

    def test_context_hint_boosts_score(self):
        from app.services.brand_sequencing import score_field, get_filled_fields
        from app.services.brand_fields import get_field
        profile = {
            "foundation": {
                "what_you_do": "Coach",
            },
        }
        filled = get_filled_fields(profile)
        field = get_field("foundation.online_presence_status")
        # Score without context
        score_no_ctx = score_field(field, filled)
        # Score with matching context
        score_with_ctx = score_field(field, filled, context_hint="my online_presence_status is bad")
        assert score_with_ctx > score_no_ctx

    def test_skipped_fields(self):
        from app.services.brand_sequencing import get_next_field
        profile = {
            "foundation": {
                "what_you_do": "Coach",
            },
        }
        # Skip all other foundation fields
        skipped = {
            "foundation.online_presence_status",
            "foundation.90_day_goal",
            "foundation.current_clients",
            "foundation.previous_attempts",
        }
        next_f = get_next_field(profile, skipped=skipped)
        assert next_f is not None
        # Should pick a non-skipped field (could be logistics or authority)

    def test_transition_message(self):
        from app.services.brand_sequencing import get_transition_message
        msg = get_transition_message("foundation", "authority")
        assert msg is not None
        assert "authority" in msg.lower() or "credible" in msg.lower()

    def test_transition_same_module_returns_none(self):
        from app.services.brand_sequencing import get_transition_message
        msg = get_transition_message("foundation", "foundation")
        assert msg is None

    def test_resume_message_empty(self):
        from app.services.brand_sequencing import get_resume_message
        completeness = {"overall_percent": 0, "overall_filled": 0, "modules": {}}
        msg = get_resume_message(completeness)
        assert msg == ""  # First visit uses welcome instead

    def test_resume_message_partial(self):
        from app.services.brand_sequencing import get_resume_message
        completeness = {"overall_percent": 30, "overall_filled": 12, "modules": {}}
        msg = get_resume_message(completeness)
        assert "30%" in msg

    def test_resume_message_complete(self):
        from app.services.brand_sequencing import get_resume_message
        completeness = {"overall_percent": 100, "overall_filled": 43, "modules": {}}
        msg = get_resume_message(completeness)
        assert "complete" in msg.lower()

    def test_all_fields_done_returns_none(self):
        from app.services.brand_sequencing import get_next_field
        from app.services.brand_fields import ALL_FIELDS
        # Fill every field
        profile = {}
        for field in ALL_FIELDS:
            if field.module not in profile:
                profile[field.module] = {}
            profile[field.module][field.key] = "value"
        result = get_next_field(profile)
        assert result is None


# ── Strategist Service ───────────────────────────────────────────


class TestStrategistService:
    """Test the brand strategist service functions."""

    def test_parse_options_response(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "type": "options",
            "module": "foundation",
            "field": "what_you_do",
            "message": "What do you do?",
            "options": [
                {"id": "A", "label": "Coach", "text": "I coach people"},
                {"id": "B", "label": "Consultant", "text": "I consult"},
            ],
            "allow_custom": True,
            "allow_skip": True,
        })
        result = parse_strategist_response(raw)
        assert len(result) == 1
        assert result[0]["type"] == "options"
        assert len(result[0]["options"]) == 2

    def test_parse_save_response(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "type": "save",
            "module": "foundation",
            "field": "what_you_do",
            "value": "I help coaches build personal brands",
            "message": "Saved to Foundation.",
        })
        result = parse_strategist_response(raw)
        assert len(result) == 1
        assert result[0]["type"] == "save"
        assert result[0]["value"] == "I help coaches build personal brands"

    def test_parse_array_response(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps([
            {"type": "save", "module": "foundation", "field": "what_you_do",
             "value": "Coach", "message": "Saved."},
            {"type": "options", "module": "foundation", "field": "90_day_goal",
             "message": "What is your 90-day goal?",
             "options": [{"id": "A", "label": "Revenue", "text": "$10k"}],
             "allow_custom": True, "allow_skip": True},
        ])
        result = parse_strategist_response(raw)
        assert len(result) == 2
        assert result[0]["type"] == "save"
        assert result[1]["type"] == "options"

    def test_parse_plain_text_fallback(self):
        from app.services.brand_strategist import parse_strategist_response
        result = parse_strategist_response("Just a plain coaching message")
        assert len(result) == 1
        assert result[0]["type"] == "message"
        assert "coaching message" in result[0]["message"]

    def test_parse_legacy_response(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "reply": "Good answer!",
            "extracted": {"what_you_do": "Coach"},
        })
        result = parse_strategist_response(raw)
        assert len(result) >= 1
        # Should have a message for the reply
        assert any(r["type"] == "message" for r in result)

    def test_parse_markdown_code_fence(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = '```json\n{"type": "message", "message": "Hello"}\n```'
        result = parse_strategist_response(raw)
        assert len(result) == 1
        assert result[0]["type"] == "message"

    def test_parse_wrapper_format_single(self):
        """Test the new {"responses": [...]} wrapper format with single item."""
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "responses": [
                {"type": "message", "message": "Hello from wrapped format"},
            ]
        })
        result = parse_strategist_response(raw)
        assert len(result) == 1
        assert result[0]["type"] == "message"
        assert "Hello from wrapped format" in result[0]["message"]

    def test_parse_wrapper_format_save_and_options(self):
        """Test wrapper format with save + auto-continue options."""
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "responses": [
                {
                    "type": "save",
                    "module": "foundation",
                    "field": "what_you_do",
                    "value": "I coach SaaS founders",
                    "message": "Good. That gives me something to work with."
                },
                {
                    "type": "options",
                    "module": "foundation",
                    "field": "who_you_help",
                    "message": "Now tell me about your ideal client.",
                    "options": [
                        {"id": "A", "label": "SaaS founders", "text": "Early-stage SaaS founders"},
                        {"id": "B", "label": "Tech leads", "text": "Tech leads transitioning"},
                    ],
                    "allow_custom": True,
                    "allow_skip": True,
                }
            ]
        })
        result = parse_strategist_response(raw)
        assert len(result) == 2
        assert result[0]["type"] == "save"
        assert result[0]["value"] == "I coach SaaS founders"
        assert result[1]["type"] == "options"
        assert result[1]["field"] == "who_you_help"
        assert len(result[1]["options"]) == 2

    def test_save_field_to_profile(self):
        from app.services.brand_strategist import save_field_to_profile
        profile = {}
        updated = save_field_to_profile(profile, "foundation", "what_you_do", "Coach")
        assert updated["foundation"]["what_you_do"] == "Coach"

    def test_save_field_preserves_existing(self):
        from app.services.brand_strategist import save_field_to_profile
        profile = {"foundation": {"what_you_do": "Coach"}}
        updated = save_field_to_profile(profile, "foundation", "90_day_goal", "5 clients")
        assert updated["foundation"]["what_you_do"] == "Coach"
        assert updated["foundation"]["90_day_goal"] == "5 clients"

    def test_save_fields_from_responses(self):
        from app.services.brand_strategist import save_fields_from_responses
        profile = {}
        responses = [
            {"type": "save", "module": "foundation", "field": "what_you_do",
             "value": "Coach", "message": "Saved"},
            {"type": "message", "message": "Great!"},
            {"type": "save", "module": "foundation", "field": "90_day_goal",
             "value": "5 clients", "message": "Saved"},
        ]
        updated, saved_keys = save_fields_from_responses(profile, responses)
        assert len(saved_keys) == 2
        assert "foundation.what_you_do" in saved_keys
        assert "foundation.90_day_goal" in saved_keys
        assert updated["foundation"]["what_you_do"] == "Coach"
        assert updated["foundation"]["90_day_goal"] == "5 clients"

    def test_save_fields_skips_missing_value(self):
        from app.services.brand_strategist import save_fields_from_responses
        profile = {}
        responses = [
            {"type": "save", "module": "foundation", "field": "what_you_do",
             "value": None, "message": ""},
        ]
        updated, saved_keys = save_fields_from_responses(profile, responses)
        assert len(saved_keys) == 0

    def test_get_welcome_message(self):
        from app.services.brand_strategist import get_welcome_message
        msg = get_welcome_message()
        assert msg["type"] == "message"
        assert "strategist" in msg["message"].lower() or "$100K" in msg["message"]

    def test_get_welcome_with_first_question(self):
        from app.services.brand_strategist import get_welcome_with_first_question
        responses = get_welcome_with_first_question()
        assert len(responses) == 2
        assert responses[0]["type"] == "message"
        assert responses[1]["type"] == "options"
        assert responses[1]["module"] == "foundation"
        assert responses[1]["field"] == "what_you_do"

    def test_build_resume_responses(self):
        from app.services.brand_strategist import build_resume_responses
        from app.services.brand_fields import get_field
        profile = {
            "foundation": {"what_you_do": "Coach"},
        }
        next_f = get_field("foundation.90_day_goal")
        responses = build_resume_responses(profile, next_f)
        assert len(responses) >= 1
        # Should have a resume message
        assert any(r["type"] == "message" for r in responses)

    def test_parse_wrapper_response(self):
        from app.services.brand_strategist import parse_strategist_response
        raw = json.dumps({
            "responses": [
                {"type": "save", "module": "foundation", "field": "what_you_do",
                 "value": "Coach", "message": "Saved."},
                {"type": "options", "module": "foundation", "field": "90_day_goal",
                 "message": "What is your 90-day goal?",
                 "options": [{"id": "A", "label": "Revenue", "text": "$10k"}],
                 "allow_custom": True, "allow_skip": True},
            ]
        })
        result = parse_strategist_response(raw)
        assert len(result) == 2
        assert result[0]["type"] == "save"
        assert result[1]["type"] == "options"

    def test_build_strategist_system_prompt(self):
        from app.services.brand_strategist import build_strategist_system_prompt
        from app.services.brand_fields import get_field
        prompt = build_strategist_system_prompt(
            profile_json={},
            next_field=get_field("foundation.what_you_do"),
        )
        assert "PositionedUp" in prompt
        assert "options" in prompt.lower()
        assert "foundation" in prompt.lower()
        assert "HUMAN WRITING" in prompt or "WRITING STYLE" in prompt or "human" in prompt.lower()

    def test_build_strategist_messages(self):
        from app.services.brand_strategist import build_strategist_messages
        from app.services.brand_fields import get_field
        messages = build_strategist_messages(
            profile_json={},
            conversation=[{"role": "user", "content": "Hi"}],
            next_field=get_field("foundation.what_you_do"),
        )
        assert len(messages) >= 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hi"

    def test_build_strategist_messages_with_document(self):
        from app.services.brand_strategist import build_strategist_messages
        messages = build_strategist_messages(
            profile_json={},
            conversation=[{"role": "user", "content": "Check this doc"}],
            document_context="Some extracted document text",
        )
        # Should have system + doc context user + doc ack assistant + user
        # Check that a user-role message contains the injected doc text
        doc_user_msgs = [
            m for m in messages
            if m.get("role") == "user"
            and "extracted document text" in m.get("content", "").lower()
        ]
        assert len(doc_user_msgs) == 1
        # There should also be an assistant ack message for the doc
        doc_ack_msgs = [
            m for m in messages
            if m.get("role") == "assistant" and "document" in m.get("content", "").lower()
        ]
        assert len(doc_ack_msgs) == 1

    def test_build_profile_context(self):
        from app.services.brand_strategist import _build_profile_context
        profile = {
            "foundation": {
                "what_you_do": "I help coaches build personal brands online",
                "90_day_goal": "Get 5 clients at $3000 each",
            },
        }
        summary = _build_profile_context(profile)
        assert "coaches" in summary
        assert "WHAT THE USER HAS TOLD YOU" in summary

    def test_build_profile_context_empty(self):
        from app.services.brand_strategist import _build_profile_context
        assert _build_profile_context({}) == ""

    def test_transform_history_for_llm_user_passthrough(self):
        from app.services.brand_strategist import transform_history_for_llm
        messages = [{"role": "user", "content": "I am a coach"}]
        result = transform_history_for_llm(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "I am a coach"

    def test_transform_history_for_llm_strips_metadata(self):
        from app.services.brand_strategist import transform_history_for_llm
        messages = [{"role": "user", "content": "[USER_ACTION: confirm]\n\nI am a coach"}]
        result = transform_history_for_llm(messages)
        assert result[0]["content"] == "I am a coach"

    def test_transform_history_for_llm_json_assistant(self):
        from app.services.brand_strategist import transform_history_for_llm
        json_content = json.dumps({
            "responses": [
                {"type": "save", "module": "foundation", "field": "what_you_do",
                 "value": "Coach", "message": "Good. That gives me something."},
                {"type": "options", "module": "foundation", "field": "90_day_goal",
                 "message": "What is your 90 day goal?",
                 "options": [{"id": "A", "label": "Revenue", "text": "Hit $10k MRR"}],
                 "allow_custom": True, "allow_skip": True},
            ]
        })
        messages = [{"role": "assistant", "content": json_content}]
        result = transform_history_for_llm(messages)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        # Should be natural text, not JSON
        assert "Good. That gives me something." in result[0]["content"]
        assert "90 day goal" in result[0]["content"]
        # Should NOT be raw JSON
        assert '"type"' not in result[0]["content"]

    def test_transform_history_for_llm_plain_text_assistant(self):
        from app.services.brand_strategist import transform_history_for_llm
        messages = [{"role": "assistant", "content": "Just a coaching message."}]
        result = transform_history_for_llm(messages)
        assert result[0]["content"] == "Just a coaching message."

    def test_parse_mixed_text_json(self):
        """Parser handles text before JSON block."""
        from app.services.brand_strategist import parse_strategist_response
        raw = 'Let me think...\n\n{"responses": [{"type": "message", "message": "Here is my take."}]}'
        result = parse_strategist_response(raw)
        assert len(result) == 1
        assert result[0]["type"] == "message"

    def test_pushback_templates_exist(self):
        from app.services.brand_strategist import PUSHBACK_TEMPLATES
        assert "vague_what_you_do" in PUSHBACK_TEMPLATES
        assert "vague_goal" in PUSHBACK_TEMPLATES
        assert len(PUSHBACK_TEMPLATES) >= 5


# ── Strategist Schemas ───────────────────────────────────────────


class TestStrategistSchemas:
    """Test Pydantic schemas for the strategist."""

    def test_option_card(self):
        from app.schemas.strategist import OptionCard
        card = OptionCard(id="A", label="Speed-focused", text="I get results fast")
        assert card.id == "A"

    def test_options_response(self):
        from app.schemas.strategist import OptionsResponse, OptionCard
        resp = OptionsResponse(
            module="foundation",
            field="what_you_do",
            message="What do you do?",
            options=[
                OptionCard(id="A", label="Coach", text="I coach people"),
                OptionCard(id="B", label="Consultant", text="I consult"),
            ],
        )
        assert resp.type == "options"
        assert len(resp.options) == 2
        assert resp.allow_custom is True
        assert resp.allow_skip is True

    def test_options_response_empty_options(self):
        """First question can have no options (zero context)."""
        from app.schemas.strategist import OptionsResponse
        resp = OptionsResponse(
            module="foundation",
            field="what_you_do",
            message="What do you do?",
            options=[],
        )
        assert len(resp.options) == 0

    def test_refinement_response(self):
        from app.schemas.strategist import RefinementResponse
        resp = RefinementResponse(
            module="foundation",
            field="what_you_do",
            message="Good pick. Here is a refined version.",
            refined_text="I help coaches build personal brands online",
        )
        assert resp.type == "refinement"
        assert "confirm" in resp.actions
        assert "edit" in resp.actions

    def test_save_response(self):
        from app.schemas.strategist import SaveResponse, CompletenessInfo
        resp = SaveResponse(
            module="foundation",
            field="what_you_do",
            value="Coach",
            message="Saved to Foundation.",
            completeness=CompletenessInfo(
                module_name="foundation",
                module_percent=20,
                overall_percent=5,
            ),
        )
        assert resp.type == "save"
        assert resp.completeness.overall_percent == 5

    def test_message_response(self):
        from app.schemas.strategist import MessageResponse
        resp = MessageResponse(message="Welcome to PositionedUp.")
        assert resp.type == "message"

    def test_content_response(self):
        from app.schemas.strategist import ContentResponse
        resp = ContentResponse(
            content_type="linkedin_post",
            platform="linkedin",
            hook="The reason your LinkedIn is failing...",
            body="Here is the body of the post",
            message="Here is your first LinkedIn post",
        )
        assert resp.type == "content"

    def test_strategist_chat_request(self):
        from app.schemas.strategist import StrategistChatRequest
        req = StrategistChatRequest(
            message="I am a business coach",
            brand_id="test-brand-id",
        )
        assert req.message == "I am a business coach"
        assert req.selected_option is None
        assert req.action is None

    def test_strategist_chat_request_with_option(self):
        from app.schemas.strategist import StrategistChatRequest
        req = StrategistChatRequest(
            message="I choose this one",
            brand_id="test-brand-id",
            selected_option="A",
            action="confirm",
            target_field="foundation.what_you_do",
        )
        assert req.selected_option == "A"
        assert req.action == "confirm"

    def test_field_completeness_response(self):
        from app.schemas.strategist import FieldCompletenessResponse
        resp = FieldCompletenessResponse(
            overall_percent=25,
            overall_filled=10,
            overall_total=43,
            modules={"foundation": {"label": "Foundation", "filled": 5, "total": 10, "percent": 50}},
            filled_fields=["foundation.what_you_do"],
            unfilled_fields=["authority.unfair_advantage"],
        )
        assert resp.overall_percent == 25

    def test_next_field_response_with_field(self):
        from app.schemas.strategist import NextFieldResponse
        resp = NextFieldResponse(
            module="foundation",
            field="what_you_do",
            label="What You Do",
            question="What do you do?",
        )
        assert resp.all_complete is False

    def test_next_field_response_complete(self):
        from app.schemas.strategist import NextFieldResponse
        resp = NextFieldResponse(all_complete=True)
        assert resp.all_complete is True
        assert resp.module is None


# ── Strategist Router ────────────────────────────────────────────


def _mock_supabase_table(mock_admin, data=None):
    """Set up mock that handles any chain of .select().eq().order().execute()."""
    if data is None:
        data = []
    mock_table = MagicMock()
    mock_admin.return_value.table.return_value = mock_table
    for method in [
        "select", "eq", "in_", "insert", "update", "delete",
        "order", "limit", "is_", "single", "gte", "lte",
    ]:
        getattr(mock_table, method).return_value = mock_table
    mock_table.execute.return_value.data = data
    return mock_table


class TestStrategistRouter:
    """Test strategist router endpoints using mock data."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked auth."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user, CurrentUser

        mock_user = CurrentUser(id="test-user-id", email="test@example.com")
        app.dependency_overrides[get_current_user] = lambda: mock_user
        yield TestClient(app)
        app.dependency_overrides.clear()

    @patch("app.routers.strategist.get_admin_client")
    def test_completeness_endpoint_404(self, mock_admin, client):
        """Test completeness endpoint returns 404 for unknown brand."""
        # Brand not found: empty data
        _mock_supabase_table(mock_admin, [])
        resp = client.get("/brand/strategist/completeness/nonexistent-brand-id")
        assert resp.status_code == 404

    @patch("app.routers.strategist.get_admin_client")
    def test_next_field_endpoint_404(self, mock_admin, client):
        """Test next-field endpoint returns 404 for unknown brand."""
        _mock_supabase_table(mock_admin, [])
        resp = client.get("/brand/strategist/next-field/nonexistent-brand-id")
        assert resp.status_code == 404

    @patch("app.routers.strategist.get_admin_client")
    def test_resume_endpoint_404(self, mock_admin, client):
        """Test resume endpoint returns 404 for unknown brand."""
        _mock_supabase_table(mock_admin, [])
        resp = client.post("/brand/strategist/chat/nonexistent-brand-id/resume")
        assert resp.status_code == 404

    @patch("app.routers.strategist.get_admin_client")
    def test_new_chat_endpoint_404(self, mock_admin, client):
        """Test new chat endpoint returns 404 for unknown brand."""
        _mock_supabase_table(mock_admin, [])
        resp = client.post("/brand/strategist/chat/nonexistent-brand-id/new")
        assert resp.status_code == 404

    def test_chat_endpoint_validation(self, client):
        """Test chat endpoint validates request body."""
        resp = client.post(
            "/brand/strategist/chat",
            json={"brand_id": "test", "message": ""},  # Empty message
        )
        assert resp.status_code == 422  # Validation error

    def test_chat_endpoint_requires_brand_id(self, client):
        """Test chat endpoint requires brand_id."""
        resp = client.post(
            "/brand/strategist/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 422

    @patch("app.routers.strategist.get_admin_client")
    def test_save_field_endpoint_validation(self, mock_admin, client):
        """Test save-field endpoint requires proper params."""
        # Brand not found
        _mock_supabase_table(mock_admin, [])
        resp = client.post(
            "/brand/strategist/save-field",
            params={
                "brand_id": "test-brand",
                "module": "foundation",
                "field": "what_you_do",
            },
            json={},  # Missing value
        )
        # Should return 400 (missing value) or 404 (brand not found)
        assert resp.status_code in (400, 404, 422)

    @patch("app.routers.strategist.get_admin_client")
    def test_completeness_endpoint_success(self, mock_admin, client):
        """Test completeness endpoint with a valid brand."""
        _mock_supabase_table(mock_admin, [{
            "id": "brand-123",
            "user_id": "test-user-id",
            "profile_json": {
                "foundation": {"what_you_do": "I help coaches grow"},
            },
            "name": "Test Brand",
        }])
        resp = client.get("/brand/strategist/completeness/brand-123")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_percent" in data
        assert "modules" in data
        assert data["overall_filled"] >= 1

    @patch("app.routers.strategist.get_admin_client")
    def test_next_field_endpoint_success(self, mock_admin, client):
        """Test next-field returns a field when profile is incomplete."""
        _mock_supabase_table(mock_admin, [{
            "id": "brand-123",
            "user_id": "test-user-id",
            "profile_json": {},
            "name": "Test Brand",
        }])
        resp = client.get("/brand/strategist/next-field/brand-123")
        assert resp.status_code == 200
        data = resp.json()
        # First field should be foundation.what_you_do
        assert data["module"] == "foundation"
        assert data["field"] == "what_you_do"
        assert data["all_complete"] is False

    def test_chat_history_endpoint(self, client):
        """Test chat history endpoint requires brand_id param."""
        resp = client.get("/brand/strategist/chat/history")
        assert resp.status_code == 422  # Missing brand_id query param


# ── Training System Tests ─────────────────────────────────────────


class TestAgentTrainingService:
    """Test the agent_training.py service functions."""

    def test_format_examples_for_prompt_empty(self):
        from app.services.agent_training import format_examples_for_prompt
        result = format_examples_for_prompt([])
        assert result == ""

    def test_format_examples_for_prompt_with_data(self):
        from app.services.agent_training import format_examples_for_prompt
        examples = [
            {
                "category": "good_response",
                "user_input": "What should I post about?",
                "ideal_response": "Based on your expertise in coaching...",
                "context_notes": "Shows specificity",
            },
        ]
        result = format_examples_for_prompt(examples)
        assert "TRAINING EXAMPLES" in result
        assert "What should I post about?" in result
        assert "coaching" in result
        assert "specificity" in result

    def test_format_examples_for_prompt_limits_to_max(self):
        from app.services.agent_training import format_examples_for_prompt
        examples = [
            {"category": "good_response", "user_input": f"Q{i}", "ideal_response": f"A{i}"}
            for i in range(10)
        ]
        result = format_examples_for_prompt(examples, max_examples=2)
        assert "Q0" in result
        assert "Q1" in result
        assert "Q2" not in result

    def test_format_feedback_for_prompt_no_feedback(self):
        from app.services.agent_training import format_feedback_for_prompt
        result = format_feedback_for_prompt({"has_feedback": False})
        assert result == ""

    def test_format_feedback_for_prompt_with_corrections(self):
        from app.services.agent_training import format_feedback_for_prompt
        result = format_feedback_for_prompt({
            "has_feedback": True,
            "thumbs_up": 5,
            "thumbs_down": 2,
            "corrections": ["Too formal", "Use simpler language"],
            "voice_issues": [],
        })
        assert "USER PREFERENCES" in result
        assert "Too formal" in result
        assert "simpler language" in result
        assert "71%" in result  # 5/7 = ~71%

    def test_format_feedback_for_prompt_with_voice_issues(self):
        from app.services.agent_training import format_feedback_for_prompt
        result = format_feedback_for_prompt({
            "has_feedback": True,
            "thumbs_up": 0,
            "thumbs_down": 0,
            "corrections": [],
            "voice_issues": ["Sounds too corporate"],
        })
        assert "Voice mismatch" in result
        assert "corporate" in result

    def test_format_instructions_for_prompt_none(self):
        from app.services.agent_training import format_instructions_for_prompt
        assert format_instructions_for_prompt(None) == ""

    def test_format_instructions_for_prompt_full(self):
        from app.services.agent_training import format_instructions_for_prompt
        result = format_instructions_for_prompt({
            "instructions": "Always use my trademark phrase: 'Level up or lose out'",
            "tone_preference": "bold and aggressive",
            "avoid_topics": ["politics", "religion"],
            "focus_areas": ["sales", "conversion"],
        })
        assert "CUSTOM INSTRUCTIONS" in result
        assert "Level up or lose out" in result
        assert "bold and aggressive" in result
        assert "politics" in result
        assert "sales" in result


class TestTrainingSchemas:
    """Test Pydantic schemas for the training system."""

    def test_prompt_config_out(self):
        from app.schemas.training import PromptConfigOut
        cfg = PromptConfigOut(
            id="test-id",
            config_type="identity",
            config_key="strategist_identity",
            content="You are a coach",
            version=1,
        )
        assert cfg.config_key == "strategist_identity"

    def test_training_example_create(self):
        from app.schemas.training import TrainingExampleCreate
        ex = TrainingExampleCreate(
            category="good_response",
            module="foundation",
            field="what_you_do",
            user_input="I help people",
            ideal_response="That's too vague...",
        )
        assert ex.category == "good_response"

    def test_feedback_create(self):
        from app.schemas.training import FeedbackCreate
        fb = FeedbackCreate(
            brand_id="brand-123",
            chat_id="chat-456",
            message_index=3,
            feedback_type="thumbs_down",
            feedback_text="Too generic",
            original_response="Here is what I suggest...",
        )
        assert fb.feedback_type == "thumbs_down"

    def test_custom_instructions_upsert(self):
        from app.schemas.training import CustomInstructionsUpsert
        inst = CustomInstructionsUpsert(
            instructions="Always reference my book",
            tone_preference="casual",
            avoid_topics=["politics"],
            focus_areas=["coaching", "branding"],
        )
        assert "coaching" in inst.focus_areas

    def test_feedback_summary(self):
        from app.schemas.training import FeedbackSummary
        s = FeedbackSummary(
            total_feedback=10,
            thumbs_up=7,
            thumbs_down=3,
        )
        assert s.total_feedback == 10

    def test_training_stats(self):
        from app.schemas.training import TrainingStats
        s = TrainingStats(
            total_configs=5,
            total_examples=20,
            total_feedback=100,
            feedback_by_type={"thumbs_up": 70, "thumbs_down": 30},
        )
        assert s.total_configs == 5


class TestTrainingRouter:
    """Test the training router endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.auth import get_current_user

        class FakeUser:
            id = "test-user-id"

        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        yield TestClient(app)
        app.dependency_overrides.clear()

    @patch("app.routers.training.get_admin_client")
    def test_list_prompt_configs(self, mock_admin, client):
        """Test listing prompt configs returns 200."""
        mock_sb = MagicMock()
        mock_admin.return_value = mock_sb
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "id": "cfg-1",
            "config_type": "identity",
            "config_key": "strategist_identity",
            "content": "Test identity",
            "version": 1,
            "is_active": True,
            "metadata": {},
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }])
        resp = client.get("/admin/training/config")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["config_key"] == "strategist_identity"

    @patch("app.routers.training.get_admin_client")
    def test_submit_feedback(self, mock_admin, client):
        """Test submitting user feedback."""
        mock_sb = MagicMock()
        mock_admin.return_value = mock_sb
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        mock_chain.insert.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[{
            "id": "fb-1",
            "user_id": "test-user-id",
            "brand_id": "brand-123",
            "chat_id": None,
            "message_index": None,
            "feedback_type": "thumbs_up",
            "feedback_text": "Great response",
            "original_response": "Test response",
            "response_metadata": {},
            "created_at": "2025-01-01T00:00:00Z",
        }])
        resp = client.post("/training/feedback", json={
            "brand_id": "brand-123",
            "feedback_type": "thumbs_up",
            "feedback_text": "Great response",
            "original_response": "Test response",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "thumbs_up"

    @patch("app.routers.training.get_admin_client")
    def test_feedback_summary(self, mock_admin, client):
        """Test feedback summary endpoint."""
        mock_sb = MagicMock()
        mock_admin.return_value = mock_sb
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[
            {
                "id": "fb-1", "user_id": "test-user-id", "brand_id": "b1",
                "chat_id": None, "message_index": None,
                "feedback_type": "thumbs_up", "feedback_text": "Good",
                "original_response": "", "response_metadata": {},
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "id": "fb-2", "user_id": "test-user-id", "brand_id": "b1",
                "chat_id": None, "message_index": None,
                "feedback_type": "thumbs_down", "feedback_text": "Bad",
                "original_response": "", "response_metadata": {},
                "created_at": "2025-01-01T00:00:00Z",
            },
        ])
        resp = client.get("/training/feedback/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_feedback"] == 2
        assert data["thumbs_up"] == 1
        assert data["thumbs_down"] == 1

    @patch("app.routers.training.get_admin_client")
    def test_get_custom_instructions_empty(self, mock_admin, client):
        """Test getting instructions when none exist."""
        mock_sb = MagicMock()
        mock_admin.return_value = mock_sb
        mock_chain = MagicMock()
        mock_sb.table.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock(data=[])
        resp = client.get("/training/instructions/brand-123")
        assert resp.status_code == 200
        # Returns null when no instructions
        assert resp.json() is None
