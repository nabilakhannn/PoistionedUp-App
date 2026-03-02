"""Tests for Slice 83: Bulk Ad Creative Engine.

Validates:
  - Generate endpoint exists and is routed correctly
  - Stage endpoint exists and is routed correctly
  - 400 returned when session is not completed
  - Context builder extracts pain_points correctly
  - Context builder extracts tone_words from voice_positioning
  - hook_types defaults to all 5 when not specified
  - Staging N variation IDs creates N draft scheduled_items
  - agent_deliverables row is created with status=review on generate
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Endpoint existence ────────────────────────────────────────


class TestGenerateEndpointExists:
    """POST /brands/{brand_id}/ad-creative/generate must exist."""

    def test_generate_endpoint_exists(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        # 401 means route exists (auth failed); 404 means route missing
        resp = client.post("/brands/test-brand/ad-creative/generate", json={
            "session_id": "test-session",
        })
        assert resp.status_code != 404, (
            "POST /brands/{brand_id}/ad-creative/generate not found — "
            "register ad_creative.router in main.py"
        )


class TestStageEndpointExists:
    """POST /brands/{brand_id}/ad-creative/{deliverable_id}/stage must exist."""

    def test_stage_endpoint_exists(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post(
            "/brands/test-brand/ad-creative/test-deliverable/stage",
            json={"variation_ids": ["pain_1"]},
        )
        assert resp.status_code != 404, (
            "POST /brands/{brand_id}/ad-creative/{deliverable_id}/stage not found — "
            "register ad_creative.router in main.py"
        )


# ── Context builder ───────────────────────────────────────────


class TestBuildAdContextExtractsPainPoints:
    """_build_ad_context must pull pain_points from audience_research."""

    def test_build_ad_context_extracts_pain_points(self):
        from app.services.ad_creative import _build_ad_context

        brand = {"name": "TestBrand"}
        session = {
            "results": {
                "audience_research": {
                    "pain_points": [
                        {"pain_point": "no time"},
                        {"pain_point": "no leads"},
                        "plain string pain",
                    ],
                    "goals": [],
                    "objections": [],
                },
            }
        }
        ctx = _build_ad_context(brand, session)
        assert "no time" in ctx["pain_points"]
        assert "no leads" in ctx["pain_points"]
        assert "plain string pain" in ctx["pain_points"]
        assert len(ctx["pain_points"]) == 3

    def test_build_ad_context_extracts_voice(self):
        """_build_ad_context must extract tone_words from voice_positioning."""
        from app.services.ad_creative import _build_ad_context

        brand = {"name": "TestBrand"}
        session = {
            "results": {
                "voice_positioning": {
                    "positioning_statement": "The go-to coach for X",
                    "voice_options": [
                        {"tone_words": ["bold", "direct", "authoritative"]},
                    ],
                    "recommended_voice": "Bold Direct",
                },
            }
        }
        ctx = _build_ad_context(brand, session)
        assert ctx["positioning"] == "The go-to coach for X"
        assert "bold" in ctx["tone_words"]
        assert "direct" in ctx["tone_words"]
        assert ctx["recommended_voice"] == "Bold Direct"


# ── Hook type defaults ────────────────────────────────────────


class TestHookTypesDefaultAllFive:
    """generate_bulk_ads must default to all 5 hook types when not specified."""

    def test_hook_types_default_all_five(self):
        from app.services.ad_creative import ALL_HOOK_TYPES, generate_bulk_ads

        mock_brand = {"id": "b1", "name": "TestBrand", "user_id": "u1"}
        mock_session = {
            "id": "s1",
            "user_id": "u1",
            "brand_id": "b1",
            "status": "completed",
            "results": {},
        }

        called_hook_types: List[str] = []

        def mock_call_llm(hook_type, context, platforms, count):
            called_hook_types.append(hook_type)
            return [{"id": f"{hook_type}_1", "hook_type": hook_type, "headline": "Test", "primary_text": "Body", "cta": "Learn More", "platform": "facebook", "hook_angle": "angle"}]

        with patch("app.services.ad_creative.get_admin_client") as mock_admin, \
             patch("app.services.ad_creative._call_llm_for_hook", side_effect=mock_call_llm):
            mock_sb = MagicMock()
            mock_admin.return_value = mock_sb

            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = [
                MagicMock(data=[mock_brand]),
                MagicMock(data=[mock_session]),
            ]
            mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

            result = generate_bulk_ads(
                user_id="u1",
                brand_id="b1",
                session_id="s1",
                hook_types=None,  # Should default to all 5
            )

        assert set(called_hook_types) == set(ALL_HOOK_TYPES), (
            f"Expected all 5 hook types, got: {called_hook_types}"
        )
        assert len(called_hook_types) == 5


# ── Session must be completed ─────────────────────────────────


class TestRequiresCompletedSession:
    """generate_bulk_ads must raise ValueError if session status != completed."""

    def test_requires_completed_session(self):
        from app.services.ad_creative import generate_bulk_ads

        mock_brand = {"id": "b1", "name": "TestBrand", "user_id": "u1"}
        mock_session = {
            "id": "s1",
            "user_id": "u1",
            "brand_id": "b1",
            "status": "in_progress",  # NOT completed
            "results": {},
        }

        with patch("app.services.ad_creative.get_admin_client") as mock_admin:
            mock_sb = MagicMock()
            mock_admin.return_value = mock_sb
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = [
                MagicMock(data=[mock_brand]),
                MagicMock(data=[mock_session]),
            ]

            with pytest.raises(ValueError, match="not completed"):
                generate_bulk_ads(
                    user_id="u1",
                    brand_id="b1",
                    session_id="s1",
                )


# ── Deliverable created on generate ──────────────────────────


class TestDeliverableCreatedOnGenerate:
    """generate_bulk_ads must insert an agent_deliverables row with status=review."""

    def test_deliverable_created_on_generate(self):
        from app.services.ad_creative import generate_bulk_ads

        mock_brand = {"id": "b1", "name": "TestBrand", "user_id": "u1"}
        mock_session = {
            "id": "s1",
            "user_id": "u1",
            "brand_id": "b1",
            "status": "completed",
            "results": {
                "niche_analysis": {"recommended_niche": "coaches"},
            },
        }

        inserted_rows: List[Dict[str, Any]] = []

        def mock_insert(data):
            if isinstance(data, dict):
                inserted_rows.append(data)
            elif isinstance(data, list):
                inserted_rows.extend(data)
            mock_exec = MagicMock()
            mock_exec.execute.return_value = MagicMock(data=[{}])
            return mock_exec

        with patch("app.services.ad_creative.get_admin_client") as mock_admin, \
             patch("app.services.ad_creative._call_llm_for_hook") as mock_llm:
            mock_sb = MagicMock()
            mock_admin.return_value = mock_sb
            mock_llm.return_value = [
                {"id": "pain_1", "hook_type": "pain", "headline": "H", "primary_text": "P", "cta": "CTA", "platform": "facebook", "hook_angle": "a"},
            ]

            # Setup table chain for brands + sessions
            call_count = 0
            def table_side(*args, **kwargs):
                nonlocal call_count
                mock_t = MagicMock()
                mock_t.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[mock_brand if call_count == 0 else mock_session]
                )
                call_count += 1
                mock_t.insert = mock_insert
                return mock_t

            mock_sb.table.side_effect = table_side

            generate_bulk_ads(user_id="u1", brand_id="b1", session_id="s1")

        # Find the deliverable insert
        deliverable_inserts = [r for r in inserted_rows if r.get("deliverable_type") == "content"]
        assert len(deliverable_inserts) >= 1, "No agent_deliverables row was inserted"
        assert deliverable_inserts[0]["status"] == "review"
        assert deliverable_inserts[0]["created_by_agent_id"] == "copywriter"
        assert "Bulk Ad Pack" in deliverable_inserts[0]["title"]


# ── Staging creates scheduled_items ──────────────────────────


class TestStageCreatesScheduledItems:
    """stage_approved_ads must create N draft scheduled_items for N variation_ids."""

    def test_stage_creates_scheduled_items(self):
        import json
        from app.services.ad_creative import stage_approved_ads

        variations = [
            {"id": "pain_1", "hook_type": "pain", "headline": "Stop struggling", "primary_text": "Body 1", "cta": "Learn More", "platform": "facebook", "hook_angle": "time"},
            {"id": "outcome_1", "hook_type": "outcome", "headline": "Imagine this", "primary_text": "Body 2", "cta": "Book a Call", "platform": "linkedin", "hook_angle": "revenue"},
            {"id": "curiosity_1", "hook_type": "curiosity", "headline": "The secret", "primary_text": "Body 3", "cta": "Find Out", "platform": "instagram", "hook_angle": "secret"},
        ]
        mock_deliverable = {
            "id": "d1",
            "user_id": "u1",
            "content": json.dumps({"all_variations": variations}),
        }

        inserted_items: List[Dict[str, Any]] = []

        def mock_insert(data):
            if isinstance(data, list):
                inserted_items.extend(data)
            mock_exec = MagicMock()
            mock_exec.execute.return_value = MagicMock(data=data)
            return mock_exec

        with patch("app.services.ad_creative.get_admin_client") as mock_admin:
            mock_sb = MagicMock()
            mock_admin.return_value = mock_sb
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[mock_deliverable])
            mock_sb.table.return_value.insert = mock_insert

            result = stage_approved_ads(
                user_id="u1",
                brand_id="b1",
                deliverable_id="d1",
                variation_ids=["pain_1", "outcome_1", "curiosity_1"],
            )

        assert result["staged_count"] == 3
        assert len(result["scheduled_item_ids"]) == 3
        assert len(inserted_items) == 3
        # All items should be draft ad_copy
        for item in inserted_items:
            assert item["status"] == "draft"
            assert item["content_type"] == "ad_copy"
            assert item["brand_id"] == "b1"
            assert item["user_id"] == "u1"
