"""QA Review router.

Endpoints:
  - POST /qa/review            -- Review content (LLM scoring)
  - GET  /qa/reviews           -- List recent reviews
  - GET  /qa/reviews/{id}      -- Get full review detail
  - GET  /qa/stats             -- Quality stats for dashboard
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.qa_review import (
    QAReviewRequest,
    QAReviewResult,
    QAReviewOut,
    QAStats,
    QAScoreBreakdown,
    QAIssue,
    QARiskFlag,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa"])


# ── POST /qa/review ──────────────────────────────────────────────

@router.post("/review", response_model=QAReviewResult)
async def review_content(
    body: QAReviewRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Review a piece of content and return a scored QA result.

    Runs two-phase scoring (rule-based + LLM) and returns:
    - Overall score (0-100)
    - 6-dimension breakdown
    - Verdict (pass/revise/fail)
    - Specific issues and risk flags
    - Auto-revision triggered if applicable
    """
    from app.services.qa_review import review_content as _review

    sb = get_admin_client()
    result = _review(user.id, body, sb)
    return result


# ── GET /qa/reviews ──────────────────────────────────────────────

@router.get("/reviews", response_model=List[QAReviewOut])
async def get_reviews(
    days: int = Query(30, ge=1, le=365),
    verdict: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    """List recent QA reviews with optional verdict filter."""
    from app.services.qa_review import list_reviews

    sb = get_admin_client()
    return list_reviews(user.id, days=days, verdict=verdict, limit=limit, sb=sb)


# ── GET /qa/reviews/{review_id} ──────────────────────────────────

@router.get("/reviews/{review_id}")
async def get_review_detail(
    review_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get full QA review detail including all scores and issues."""
    from app.services.qa_review import get_review

    sb = get_admin_client()
    review = get_review(review_id, user.id, sb)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


# ── GET /qa/stats ────────────────────────────────────────────────

@router.get("/stats", response_model=QAStats)
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
):
    """Get aggregated QA statistics for the dashboard."""
    from app.services.qa_review import get_qa_stats

    sb = get_admin_client()
    return get_qa_stats(user.id, days=days, sb=sb)
