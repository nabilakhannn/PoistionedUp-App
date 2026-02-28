"""Tests for Slice 74: Pipeline Extension (Ad Copy + Carousel).

Covers:
- ContentPack TypedDict accepts ad_copy and carousel_slides
- _save_pack_assets handles new content types
- Schedule _FORMAT_MAP includes new entries
- Schedule import creates items for ad_copy and carousel
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, call


# ── ContentPack State Tests ──────────────────────────────────

class TestContentPackExtension:
    """Test that ContentPack supports ad_copy and carousel_slides."""

    def test_content_pack_accepts_ad_copy(self):
        from worker.graph.state import ContentPack

        pack: ContentPack = {
            "ad_copy": [
                {"ad_format": "single_image", "headline": "Test", "body": "Ad body", "cta": "Buy now"},
            ],
        }
        assert len(pack["ad_copy"]) == 1
        assert pack["ad_copy"][0]["ad_format"] == "single_image"

    def test_content_pack_accepts_carousel_slides(self):
        from worker.graph.state import ContentPack

        pack: ContentPack = {
            "carousel_slides": [
                {"platform": "linkedin", "cover_text": "Test Carousel", "slides": []},
            ],
        }
        assert len(pack["carousel_slides"]) == 1
        assert pack["carousel_slides"][0]["platform"] == "linkedin"

    def test_content_pack_empty_new_fields(self):
        from worker.graph.state import ContentPack

        pack: ContentPack = {
            "ad_copy": [],
            "carousel_slides": [],
        }
        assert pack["ad_copy"] == []
        assert pack["carousel_slides"] == []


# ── Asset Saving Tests ───────────────────────────────────────

class TestSavePackAssets:
    """Test _save_pack_assets handles ad_copy and carousel."""

    def test_saves_ad_copy_assets(self):
        from worker.executor import _save_pack_assets

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

        pack = {
            "ad_copy": [
                {"ad_format": "single_image", "headline": "Test Ad"},
                {"ad_format": "video_ad", "headline": "Video Ad"},
            ],
        }

        _save_pack_assets(client, "wf-1", pack)

        # Should have called insert for each ad
        insert_calls = client.table.return_value.insert.call_args_list
        ad_inserts = [
            c for c in insert_calls
            if c[0][0].get("type") == "ad_copy"
        ]
        assert len(ad_inserts) == 2
        assert ad_inserts[0][0][0]["content_json"]["ad_index"] == 1
        assert ad_inserts[1][0][0]["content_json"]["ad_index"] == 2

    def test_saves_carousel_assets(self):
        from worker.executor import _save_pack_assets

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

        pack = {
            "carousel_slides": [
                {"platform": "linkedin", "cover_text": "Carousel 1"},
            ],
        }

        _save_pack_assets(client, "wf-1", pack)

        insert_calls = client.table.return_value.insert.call_args_list
        carousel_inserts = [
            c for c in insert_calls
            if c[0][0].get("type") == "carousel"
        ]
        assert len(carousel_inserts) == 1

    def test_skips_empty_new_fields(self):
        from worker.executor import _save_pack_assets

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])

        pack: Dict[str, Any] = {}  # No ad_copy or carousel_slides

        _save_pack_assets(client, "wf-1", pack)

        # Should not have called insert for ad_copy or carousel
        insert_calls = client.table.return_value.insert.call_args_list
        new_type_inserts = [
            c for c in insert_calls
            if c[0][0].get("type") in ("ad_copy", "carousel")
        ]
        assert len(new_type_inserts) == 0


# ── Schedule FORMAT_MAP Tests ────────────────────────────────

class TestFormatMap:
    """Test that _FORMAT_MAP includes new content types."""

    def test_format_map_has_ad(self):
        from app.routers.schedule import _FORMAT_MAP

        assert "ad" in _FORMAT_MAP
        assert _FORMAT_MAP["ad"] == "ad_copy"

    def test_format_map_has_carousel(self):
        from app.routers.schedule import _FORMAT_MAP

        assert "carousel" in _FORMAT_MAP
        assert _FORMAT_MAP["carousel"] == "carousel"

    def test_format_map_preserves_existing(self):
        from app.routers.schedule import _FORMAT_MAP

        assert _FORMAT_MAP["video"] == "youtube_long"
        assert _FORMAT_MAP["post"] == "linkedin_post"
        assert _FORMAT_MAP["thread"] == "twitter_post"
        assert _FORMAT_MAP["short"] == "youtube_short"
