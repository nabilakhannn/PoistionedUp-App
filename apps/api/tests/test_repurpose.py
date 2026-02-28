"""Tests for Slice 74: Content Repurposing Engine.

Covers:
- RepurposeRequest schema validation (platforms, text limits)
- RepurposeResponse schema validation
- Repurpose router registration (prefix, tags, endpoints)
- Rate limit tier assignment
- Platform constraints
- Security: input size, platform enum validation
"""

from __future__ import annotations

import pytest


# ── Schema Validation Tests ─────────────────────────────────

class TestRepurposeSchemas:
    """Test Pydantic schemas for repurposing."""

    def test_request_valid(self):
        from app.schemas.repurpose import RepurposeRequest

        req = RepurposeRequest(
            source_text="This is my YouTube script about marketing.",
            source_platform="youtube",
            target_platforms=["linkedin", "twitter"],
        )
        assert req.source_platform == "youtube"
        assert len(req.target_platforms) == 2

    def test_request_all_source_platforms_valid(self):
        from app.schemas.repurpose import RepurposeRequest, VALID_SOURCE_PLATFORMS

        for platform in VALID_SOURCE_PLATFORMS:
            req = RepurposeRequest(
                source_text="Test content",
                source_platform=platform,
                target_platforms=["linkedin"],
            )
            assert req.source_platform == platform

    def test_request_all_target_platforms_valid(self):
        from app.schemas.repurpose import RepurposeRequest, VALID_TARGET_PLATFORMS

        for platform in VALID_TARGET_PLATFORMS:
            req = RepurposeRequest(
                source_text="Test content",
                source_platform="youtube",
                target_platforms=[platform],
            )
            assert platform in req.target_platforms

    def test_request_rejects_invalid_source_platform(self):
        from app.schemas.repurpose import RepurposeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RepurposeRequest(
                source_text="Test",
                source_platform="invalid_platform",
                target_platforms=["linkedin"],
            )

    def test_request_rejects_invalid_target_platform(self):
        from app.schemas.repurpose import RepurposeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RepurposeRequest(
                source_text="Test",
                source_platform="youtube",
                target_platforms=["nonexistent"],
            )

    def test_request_requires_at_least_one_target(self):
        from app.schemas.repurpose import RepurposeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RepurposeRequest(
                source_text="Test",
                source_platform="youtube",
                target_platforms=[],
            )

    def test_request_defaults(self):
        from app.schemas.repurpose import RepurposeRequest

        req = RepurposeRequest(
            source_text="Test",
            source_platform="youtube",
            target_platforms=["linkedin"],
        )
        assert req.auto_schedule is False
        assert req.brand_id is None
        assert req.source_id is None

    def test_response_model(self):
        from app.schemas.repurpose import RepurposeResponse, RepurposedItem

        resp = RepurposeResponse(
            source_platform="youtube",
            repurposed=[
                RepurposedItem(
                    platform="linkedin",
                    content_type="linkedin_post",
                    title="Test",
                    body="Repurposed content",
                )
            ],
            scheduled_items_created=0,
        )
        assert resp.source_platform == "youtube"
        assert len(resp.repurposed) == 1

    def test_platform_info_model(self):
        from app.schemas.repurpose import PlatformInfo

        info = PlatformInfo(
            platform="linkedin",
            content_type="linkedin_post",
            char_limit=3000,
            description="Professional platform",
        )
        assert info.char_limit == 3000


# ── Route Registration Tests ────────────────────────────────

class TestRepurposeRouteRegistration:
    """Test that repurpose routes are registered."""

    def test_router_has_prefix(self):
        from app.routers.repurpose import router

        assert router.prefix == "/repurpose"

    def test_router_has_tag(self):
        from app.routers.repurpose import router

        assert "repurpose" in router.tags

    def test_has_repurpose_endpoint(self):
        from app.routers.repurpose import router

        routes = [r.path for r in router.routes]
        assert "/repurpose" in routes

    def test_has_platforms_endpoint(self):
        from app.routers.repurpose import router

        routes = [r.path for r in router.routes]
        assert "/repurpose/platforms" in routes

    def test_repurpose_is_post(self):
        from app.routers.repurpose import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/repurpose":
                assert "POST" in route.methods
                break

    def test_platforms_is_get(self):
        from app.routers.repurpose import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/repurpose/platforms":
                assert "GET" in route.methods
                break


# ── Rate Limit Tier Tests ───────────────────────────────────

class TestRepurposeRateLimits:
    """Test rate limit tier for repurpose endpoints."""

    def test_repurpose_uses_llm_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_LLM

        tier = _get_tier("/repurpose", "POST")
        assert tier == TIER_LLM


# ── Platform Constraints Tests ───────────────────────────────

class TestPlatformConstraints:
    """Test that platform constraints are well-defined."""

    def test_all_target_platforms_have_constraints(self):
        from app.schemas.repurpose import VALID_TARGET_PLATFORMS
        from worker.graph.prompts.repurpose import PLATFORM_CONSTRAINTS

        for platform in VALID_TARGET_PLATFORMS:
            assert platform in PLATFORM_CONSTRAINTS, (
                f"Missing constraint for platform: {platform}"
            )

    def test_constraints_have_required_keys(self):
        from worker.graph.prompts.repurpose import PLATFORM_CONSTRAINTS

        for name, constraint in PLATFORM_CONSTRAINTS.items():
            assert "content_type" in constraint, f"{name} missing content_type"
            assert "rules" in constraint, f"{name} missing rules"
            assert isinstance(constraint["rules"], str), f"{name} rules not a string"
            assert len(constraint["rules"]) > 20, f"{name} rules too short"
