"""Tests for Slice 80: Composer → QA Gate.

Covers:
- QA review endpoint contract (~2 tests)
- Score dimensions have correct count and weights (~2 tests)
- Verdict thresholds are correct (~2 tests)
- Composer API has no publish() yet (~1 test)
- ScoreBadge component exists (~1 test)
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# ── QA Review Endpoint Contract ────────────────────────────────

class TestQAReviewEndpointContract:
    """Test that POST /qa/review exists and has expected structure."""

    def test_qa_review_route_exists(self):
        from app.routers import qa

        source = inspect.getsource(qa)
        assert '"/review"' in source or "'/review'" in source

    def test_qa_review_is_post(self):
        from app.routers import qa

        source = inspect.getsource(qa)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "review" in line and "router." in line:
                assert "router.post" in line, (
                    f"Expected @router.post for /review, got: {line}"
                )
                return
        pytest.fail("Could not find /review route decorator")


# ── Score Dimensions ──────────────────────────────────────────

class TestQAScoreDimensions:
    """Test that all 6 score dimensions exist with correct weights."""

    def test_six_score_dimensions(self):
        from app.schemas.qa_review import SCORE_WEIGHTS

        assert len(SCORE_WEIGHTS) == 6, (
            f"Expected 6 score dimensions, got {len(SCORE_WEIGHTS)}"
        )

    def test_weights_sum_to_one(self):
        from app.schemas.qa_review import SCORE_WEIGHTS

        total = sum(SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, (
            f"Score weights sum to {total}, expected 1.0"
        )


# ── Verdict Thresholds ────────────────────────────────────────

class TestQAVerdictThresholds:
    """Test that pass/revise thresholds are correctly configured."""

    def test_pass_threshold_is_80(self):
        from app.schemas.qa_review import QA_PASS_THRESHOLD

        assert QA_PASS_THRESHOLD == 80

    def test_revise_threshold_is_50(self):
        from app.schemas.qa_review import QA_REVISE_THRESHOLD

        assert QA_REVISE_THRESHOLD == 50


# ── Composer API Gap ──────────────────────────────────────────

COMPOSER_TS = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "apps"
    / "web"
    / "src"
    / "lib"
    / "api"
    / "composer.ts"
)


class TestComposerAPIHasNoPublish:
    """Document that composer.ts has no publish() method yet."""

    def test_no_publish_method(self):
        assert COMPOSER_TS.exists(), f"composer.ts not found at {COMPOSER_TS}"
        content = COMPOSER_TS.read_text()
        assert "publish:" not in content and "publish(" not in content, (
            "composer.ts now has a publish method — update this test!"
        )


# ── ScoreBadge Component ──────────────────────────────────────

SCORE_BADGE_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "apps"
    / "web"
    / "src"
    / "app"
    / "mission-control"
    / "qa"
    / "components"
    / "score-badge.tsx"
)


class TestScoreBadgeComponentExists:
    """Test that the reusable ScoreBadge component exists."""

    def test_score_badge_file_exists(self):
        assert SCORE_BADGE_FILE.exists(), (
            f"score-badge.tsx not found at {SCORE_BADGE_FILE}"
        )
        content = SCORE_BADGE_FILE.read_text()
        assert "ScoreBadge" in content
        assert "score" in content
