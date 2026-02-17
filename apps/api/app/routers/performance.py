"""Performance Feedback endpoints: log posts, update metrics, analytics, AI analysis."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import CurrentUser, get_current_user
from app.deps import get_admin_client
from app.schemas.performance import (
    ContentPostCreate,
    ContentPostDetail,
    ContentPostSummary,
    ContentPostUpdateMetrics,
    PerformanceAnalytics,
    PostAnalysisResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content-posts", tags=["performance"])


# ── Helpers ──────────────────────────────────────────────

def _get_post_or_404(admin, post_id: str, user_id: str):
    """Fetch a content post row, 404 if not found or not owned."""
    resp = (
        admin.table("content_posts")
        .select("*")
        .eq("id", post_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content post not found",
        )
    return resp.data[0]


def _get_all_user_posts(admin, user_id: str) -> List[dict]:
    """Fetch all posts for a user (used for averages/tier calculation)."""
    resp = (
        admin.table("content_posts")
        .select("*")
        .eq("user_id", user_id)
        .order("published_at", desc=True)
        .execute()
    )
    return resp.data if resp.data else []


def _recalculate_post(admin, post_row: dict, all_posts: List[dict]):
    """Recalculate engagement_rate and performance_tier for a post."""
    from app.services.performance_analytics import (
        calculate_engagement_rate,
        calculate_performance_tier,
        get_user_averages,
    )

    engagement_rate = calculate_engagement_rate(
        views=post_row.get("views"),
        likes=post_row.get("likes"),
        comments=post_row.get("comments"),
        shares=post_row.get("shares"),
        saves=post_row.get("saves"),
    )

    # Calculate tier relative to user's averages on same platform
    avgs = get_user_averages(all_posts, platform=post_row.get("platform"))
    tier = calculate_performance_tier(
        engagement_rate=engagement_rate,
        avg_engagement=avgs["avg_engagement_rate"],
        total_user_posts=avgs["post_count"],
    )

    update_data = {}
    if engagement_rate is not None:
        update_data["engagement_rate"] = engagement_rate
    if tier is not None:
        update_data["performance_tier"] = tier

    if update_data:
        admin.table("content_posts").update(
            update_data
        ).eq("id", post_row["id"]).execute()

    return engagement_rate, tier


# ── CRUD ─────────────────────────────────────────────────


@router.post("", response_model=ContentPostSummary, status_code=status.HTTP_201_CREATED)
async def create_content_post(
    body: ContentPostCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Log a published piece of content."""
    admin = get_admin_client()

    insert_data = {
        "user_id": user.id,
        "title": body.title,
        "content_type": body.content_type,
        "platform": body.platform,
    }

    # Optional fields
    if body.hook_used is not None:
        insert_data["hook_used"] = body.hook_used
    if body.hook_type is not None:
        insert_data["hook_type"] = body.hook_type
    if body.topic is not None:
        insert_data["topic"] = body.topic
    if body.topic_category is not None:
        insert_data["topic_category"] = body.topic_category
    if body.content_body is not None:
        insert_data["content_body"] = body.content_body
    if body.workflow_id is not None:
        insert_data["workflow_id"] = body.workflow_id
    if body.collection_id is not None:
        insert_data["collection_id"] = body.collection_id
    if body.published_url is not None:
        insert_data["published_url"] = body.published_url
    if body.published_at is not None:
        insert_data["published_at"] = body.published_at
    if body.day_of_week is not None:
        insert_data["day_of_week"] = body.day_of_week
    if body.tags is not None:
        insert_data["tags"] = body.tags

    resp = admin.table("content_posts").insert(insert_data).execute()
    row = resp.data[0]

    return ContentPostSummary(
        id=row["id"],
        title=row["title"],
        content_type=row["content_type"],
        platform=row["platform"],
        hook_type=row.get("hook_type"),
        topic=row.get("topic"),
        topic_category=row.get("topic_category"),
        performance_tier=row.get("performance_tier"),
        engagement_rate=row.get("engagement_rate"),
        views=row.get("views"),
        likes=row.get("likes"),
        comments=row.get("comments"),
        published_at=row.get("published_at"),
        created_at=row["created_at"],
    )


@router.get("", response_model=List[ContentPostSummary])
async def list_content_posts(
    platform: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """List content posts, optionally filtered by platform or tier."""
    admin = get_admin_client()

    query = (
        admin.table("content_posts")
        .select("*")
        .eq("user_id", user.id)
    )
    if platform:
        query = query.eq("platform", platform)
    if tier:
        query = query.eq("performance_tier", tier)

    resp = query.order("created_at", desc=True).execute()

    if not resp.data:
        return []

    return [
        ContentPostSummary(
            id=r["id"],
            title=r["title"],
            content_type=r["content_type"],
            platform=r["platform"],
            hook_type=r.get("hook_type"),
            topic=r.get("topic"),
            topic_category=r.get("topic_category"),
            performance_tier=r.get("performance_tier"),
            engagement_rate=r.get("engagement_rate"),
            views=r.get("views"),
            likes=r.get("likes"),
            comments=r.get("comments"),
            published_at=r.get("published_at"),
            created_at=r["created_at"],
        )
        for r in resp.data
    ]


@router.get("/analytics", response_model=PerformanceAnalytics)
async def get_analytics(
    platform: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Get aggregated performance analytics."""
    admin = get_admin_client()
    all_posts = _get_all_user_posts(admin, user.id)

    from app.services.performance_analytics import get_analytics as compute_analytics
    analytics = compute_analytics(all_posts)

    return PerformanceAnalytics(**analytics)


@router.get("/{post_id}", response_model=ContentPostDetail)
async def get_content_post(
    post_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get full detail for a content post."""
    admin = get_admin_client()
    row = _get_post_or_404(admin, post_id, user.id)

    return ContentPostDetail(
        id=row["id"],
        title=row["title"],
        content_type=row["content_type"],
        platform=row["platform"],
        hook_used=row.get("hook_used"),
        hook_type=row.get("hook_type"),
        topic=row.get("topic"),
        topic_category=row.get("topic_category"),
        content_body=row.get("content_body"),
        workflow_id=row.get("workflow_id"),
        collection_id=row.get("collection_id"),
        published_url=row.get("published_url"),
        published_at=row.get("published_at"),
        day_of_week=row.get("day_of_week"),
        views=row.get("views"),
        likes=row.get("likes"),
        comments=row.get("comments"),
        shares=row.get("shares"),
        saves=row.get("saves"),
        watch_time_seconds=row.get("watch_time_seconds"),
        click_through_rate=row.get("click_through_rate"),
        impressions=row.get("impressions"),
        reach=row.get("reach"),
        subscribers_gained=row.get("subscribers_gained"),
        engagement_rate=row.get("engagement_rate"),
        performance_tier=row.get("performance_tier"),
        agent_analysis=row.get("agent_analysis", {}),
        tags=row.get("tags", []),
        metadata=row.get("metadata", {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/{post_id}", response_model=ContentPostDetail)
async def update_post_metrics(
    post_id: str,
    body: ContentPostUpdateMetrics,
    user: CurrentUser = Depends(get_current_user),
):
    """Update metrics for a content post (views, likes, etc.).

    Also auto-recalculates engagement_rate and performance_tier.
    """
    admin = get_admin_client()
    row = _get_post_or_404(admin, post_id, user.id)

    # Build update dict from non-None fields
    update_data = {}
    for field in [
        "views", "likes", "comments", "shares", "saves",
        "watch_time_seconds", "click_through_rate", "impressions",
        "reach", "subscribers_gained",
    ]:
        value = getattr(body, field, None)
        if value is not None:
            update_data[field] = value

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No metrics to update",
        )

    # Update metrics
    resp = (
        admin.table("content_posts")
        .update(update_data)
        .eq("id", post_id)
        .eq("user_id", user.id)
        .execute()
    )
    updated_row = resp.data[0]

    # Recalculate engagement rate and performance tier
    all_posts = _get_all_user_posts(admin, user.id)
    engagement_rate, tier = _recalculate_post(admin, updated_row, all_posts)

    # Re-fetch to get calculated fields
    final_row = _get_post_or_404(admin, post_id, user.id)

    return ContentPostDetail(
        id=final_row["id"],
        title=final_row["title"],
        content_type=final_row["content_type"],
        platform=final_row["platform"],
        hook_used=final_row.get("hook_used"),
        hook_type=final_row.get("hook_type"),
        topic=final_row.get("topic"),
        topic_category=final_row.get("topic_category"),
        content_body=final_row.get("content_body"),
        workflow_id=final_row.get("workflow_id"),
        collection_id=final_row.get("collection_id"),
        published_url=final_row.get("published_url"),
        published_at=final_row.get("published_at"),
        day_of_week=final_row.get("day_of_week"),
        views=final_row.get("views"),
        likes=final_row.get("likes"),
        comments=final_row.get("comments"),
        shares=final_row.get("shares"),
        saves=final_row.get("saves"),
        watch_time_seconds=final_row.get("watch_time_seconds"),
        click_through_rate=final_row.get("click_through_rate"),
        impressions=final_row.get("impressions"),
        reach=final_row.get("reach"),
        subscribers_gained=final_row.get("subscribers_gained"),
        engagement_rate=final_row.get("engagement_rate"),
        performance_tier=final_row.get("performance_tier"),
        agent_analysis=final_row.get("agent_analysis", {}),
        tags=final_row.get("tags", []),
        metadata=final_row.get("metadata", {}),
        created_at=final_row["created_at"],
        updated_at=final_row["updated_at"],
    )


@router.post("/{post_id}/analyze", response_model=PostAnalysisResponse)
async def analyze_post(
    post_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Trigger AI analysis of why a post performed well or poorly."""
    admin = get_admin_client()
    row = _get_post_or_404(admin, post_id, user.id)

    try:
        from app.services.performance_analytics import analyze_post_performance
        analysis = analyze_post_performance(row)
    except Exception as e:
        error_msg = str(e)
        logger.error("Post analysis failed for %s: %s", post_id, e)
        if "429" in error_msg or "quota" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/billing",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI analysis failed: {error_msg[:200]}",
        )

    # Store analysis in the post
    admin.table("content_posts").update({
        "agent_analysis": analysis,
    }).eq("id", post_id).execute()

    return PostAnalysisResponse(
        post_id=post_id,
        performance_tier=row.get("performance_tier"),
        analysis=analysis,
        message="Post analysis complete.",
    )
