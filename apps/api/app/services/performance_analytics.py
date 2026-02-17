"""Performance analytics service — calculates tiers, aggregates insights,
and formats performance context for LLM prompt injection.

This is the brain of the feedback loop. It answers the question:
"What kind of content works best for YOUR specific audience?"
"""

import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Minimum posts before tier calculation is meaningful
MIN_POSTS_FOR_TIERS = 5

# Tier thresholds relative to user's own average engagement
TIER_THRESHOLDS = {
    "viral": 3.0,           # 3x+ your average
    "above_average": 1.5,   # 1.5x - 3x your average
    "average_high": 0.7,    # 0.7x - 1.5x your average
    "below_average": 0.3,   # 0.3x - 0.7x your average
    # Below 0.3x = "flop"
}


# ── Core Calculations ───────────────────────────────────────

def calculate_engagement_rate(
    views: Optional[int],
    likes: Optional[int] = None,
    comments: Optional[int] = None,
    shares: Optional[int] = None,
    saves: Optional[int] = None,
) -> Optional[float]:
    """Calculate engagement rate: (likes + comments + shares + saves) / views.

    Returns None if views is missing or zero.
    """
    if not views or views <= 0:
        return None

    engagements = sum(
        v for v in [likes, comments, shares, saves]
        if v is not None
    )
    return round(engagements / views, 6)


def calculate_performance_tier(
    engagement_rate: Optional[float],
    avg_engagement: Optional[float],
    total_user_posts: int,
) -> Optional[str]:
    """Calculate performance tier relative to the user's own average.

    Returns None if not enough data to calculate.
    """
    if total_user_posts < MIN_POSTS_FOR_TIERS:
        return None
    if engagement_rate is None or avg_engagement is None:
        return None
    if avg_engagement <= 0:
        return None

    ratio = engagement_rate / avg_engagement

    if ratio >= TIER_THRESHOLDS["viral"]:
        return "viral"
    elif ratio >= TIER_THRESHOLDS["above_average"]:
        return "above_average"
    elif ratio >= TIER_THRESHOLDS["average_high"]:
        return "average"
    elif ratio >= TIER_THRESHOLDS["below_average"]:
        return "below_average"
    else:
        return "flop"


def get_user_averages(posts: List[Dict[str, Any]], platform: Optional[str] = None) -> Dict[str, Optional[float]]:
    """Calculate average engagement rate and views for a user's posts.

    If platform is specified, filter to that platform only.
    """
    filtered = posts
    if platform:
        filtered = [p for p in posts if p.get("platform") == platform]

    if not filtered:
        return {"avg_engagement_rate": None, "avg_views": None, "post_count": 0}

    engagement_rates = [
        p["engagement_rate"] for p in filtered
        if p.get("engagement_rate") is not None
    ]
    view_counts = [
        p["views"] for p in filtered
        if p.get("views") is not None
    ]

    return {
        "avg_engagement_rate": (
            round(sum(engagement_rates) / len(engagement_rates), 6)
            if engagement_rates else None
        ),
        "avg_views": (
            round(sum(view_counts) / len(view_counts), 1)
            if view_counts else None
        ),
        "post_count": len(filtered),
    }


# ── Analytics Aggregation ───────────────────────────────────

def get_analytics(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build full analytics dashboard from a user's posts.

    Returns platform breakdowns, top topics, top hook types,
    best day, detected patterns, top hooks, and anti-hooks.
    """
    if not posts:
        return {
            "total_posts": 0,
            "platforms": [],
            "top_topics": [],
            "top_hook_types": [],
            "best_day_of_week": None,
            "patterns": [],
            "top_hooks": [],
            "anti_hooks": [],
        }

    # Platform breakdown
    by_platform = defaultdict(list)
    for p in posts:
        by_platform[p.get("platform", "unknown")].append(p)

    platforms = []
    for plat, plat_posts in by_platform.items():
        er_values = [
            p["engagement_rate"] for p in plat_posts
            if p.get("engagement_rate") is not None
        ]
        view_values = [
            p["views"] for p in plat_posts
            if p.get("views") is not None
        ]
        top_tier = sum(
            1 for p in plat_posts
            if p.get("performance_tier") in ("viral", "above_average")
        )
        platforms.append({
            "platform": plat,
            "post_count": len(plat_posts),
            "avg_engagement_rate": (
                round(sum(er_values) / len(er_values), 6) if er_values else None
            ),
            "avg_views": (
                round(sum(view_values) / len(view_values), 1) if view_values else None
            ),
            "top_tier_count": top_tier,
        })

    # Topic breakdown (top 10 by avg engagement)
    by_topic = defaultdict(list)
    for p in posts:
        tc = p.get("topic_category")
        if tc:
            by_topic[tc].append(p)

    top_topics = []
    for topic, topic_posts in by_topic.items():
        er_values = [
            p["engagement_rate"] for p in topic_posts
            if p.get("engagement_rate") is not None
        ]
        view_values = [
            p["views"] for p in topic_posts
            if p.get("views") is not None
        ]
        top_topics.append({
            "topic_category": topic,
            "post_count": len(topic_posts),
            "avg_engagement_rate": (
                round(sum(er_values) / len(er_values), 6) if er_values else None
            ),
            "avg_views": (
                round(sum(view_values) / len(view_values), 1) if view_values else None
            ),
        })
    top_topics.sort(key=lambda x: x.get("avg_engagement_rate") or 0, reverse=True)
    top_topics = top_topics[:10]

    # Hook type breakdown
    by_hook = defaultdict(list)
    for p in posts:
        ht = p.get("hook_type")
        if ht:
            by_hook[ht].append(p)

    top_hook_types = []
    for hook_type, hook_posts in by_hook.items():
        er_values = [
            p["engagement_rate"] for p in hook_posts
            if p.get("engagement_rate") is not None
        ]
        example_hooks = [
            p["hook_used"] for p in hook_posts
            if p.get("hook_used") and p.get("performance_tier") in ("viral", "above_average")
        ][:3]
        top_hook_types.append({
            "hook_type": hook_type,
            "post_count": len(hook_posts),
            "avg_engagement_rate": (
                round(sum(er_values) / len(er_values), 6) if er_values else None
            ),
            "example_hooks": example_hooks,
        })
    top_hook_types.sort(key=lambda x: x.get("avg_engagement_rate") or 0, reverse=True)

    # Best day of week
    by_day = defaultdict(list)
    for p in posts:
        dow = p.get("day_of_week")
        if dow:
            by_day[dow].append(p)

    best_day = None
    best_day_er = 0
    for day, day_posts in by_day.items():
        er_values = [
            p["engagement_rate"] for p in day_posts
            if p.get("engagement_rate") is not None
        ]
        if er_values:
            avg = sum(er_values) / len(er_values)
            if avg > best_day_er:
                best_day_er = avg
                best_day = day

    # Top hooks (actual hook text from best performers)
    sorted_by_er = sorted(
        [p for p in posts if p.get("engagement_rate") is not None and p.get("hook_used")],
        key=lambda p: p["engagement_rate"],
        reverse=True,
    )
    top_hooks = [p["hook_used"] for p in sorted_by_er[:10]]
    anti_hooks = [p["hook_used"] for p in reversed(sorted_by_er) if p.get("hook_used")][:5]

    # Detect patterns
    patterns = detect_patterns(posts, by_hook, by_topic, by_day)

    return {
        "total_posts": len(posts),
        "platforms": platforms,
        "top_topics": top_topics,
        "top_hook_types": top_hook_types,
        "best_day_of_week": best_day,
        "patterns": patterns,
        "top_hooks": top_hooks,
        "anti_hooks": anti_hooks,
    }


def detect_patterns(
    posts: List[Dict[str, Any]],
    by_hook: Optional[Dict[str, List]] = None,
    by_topic: Optional[Dict[str, List]] = None,
    by_day: Optional[Dict[str, List]] = None,
) -> List[Dict[str, Any]]:
    """Auto-detect performance patterns from content data.

    Returns patterns like "story hooks outperform question hooks by 2.3x".
    """
    patterns = []

    if len(posts) < MIN_POSTS_FOR_TIERS:
        return patterns

    # Build groupings if not provided
    if by_hook is None:
        by_hook = defaultdict(list)
        for p in posts:
            ht = p.get("hook_type")
            if ht:
                by_hook[ht].append(p)

    if by_topic is None:
        by_topic = defaultdict(list)
        for p in posts:
            tc = p.get("topic_category")
            if tc:
                by_topic[tc].append(p)

    if by_day is None:
        by_day = defaultdict(list)
        for p in posts:
            dow = p.get("day_of_week")
            if dow:
                by_day[dow].append(p)

    # Pattern: hook type comparison
    hook_avgs = {}
    for ht, hp in by_hook.items():
        ers = [p["engagement_rate"] for p in hp if p.get("engagement_rate") is not None]
        if len(ers) >= 2:
            hook_avgs[ht] = sum(ers) / len(ers)

    if len(hook_avgs) >= 2:
        sorted_hooks = sorted(hook_avgs.items(), key=lambda x: x[1], reverse=True)
        best_hook = sorted_hooks[0]
        worst_hook = sorted_hooks[-1]
        if worst_hook[1] > 0:
            ratio = round(best_hook[1] / worst_hook[1], 1)
            if ratio >= 1.5:
                patterns.append({
                    "pattern": f"{best_hook[0]} hooks outperform {worst_hook[0]} hooks by {ratio}x",
                    "evidence": f"Avg engagement: {best_hook[0]}={round(best_hook[1]*100, 2)}% vs {worst_hook[0]}={round(worst_hook[1]*100, 2)}%",
                    "confidence": min(0.9, 0.5 + len(posts) * 0.02),
                })

    # Pattern: topic comparison
    topic_avgs = {}
    for tc, tp in by_topic.items():
        ers = [p["engagement_rate"] for p in tp if p.get("engagement_rate") is not None]
        if len(ers) >= 2:
            topic_avgs[tc] = sum(ers) / len(ers)

    if len(topic_avgs) >= 2:
        sorted_topics = sorted(topic_avgs.items(), key=lambda x: x[1], reverse=True)
        best_topic = sorted_topics[0]
        patterns.append({
            "pattern": f"Your audience engages most with {best_topic[0]} content",
            "evidence": f"Avg engagement rate: {round(best_topic[1]*100, 2)}% across {len(by_topic[best_topic[0]])} posts",
            "confidence": min(0.9, 0.5 + len(by_topic[best_topic[0]]) * 0.05),
        })

    # Pattern: day of week
    day_avgs = {}
    for d, dp in by_day.items():
        ers = [p["engagement_rate"] for p in dp if p.get("engagement_rate") is not None]
        if len(ers) >= 2:
            day_avgs[d] = sum(ers) / len(ers)

    if len(day_avgs) >= 2:
        sorted_days = sorted(day_avgs.items(), key=lambda x: x[1], reverse=True)
        best_day_info = sorted_days[0]
        worst_day_info = sorted_days[-1]
        if worst_day_info[1] > 0:
            ratio = round(best_day_info[1] / worst_day_info[1], 1)
            if ratio >= 1.3:
                patterns.append({
                    "pattern": f"Posts on {best_day_info[0]} outperform {worst_day_info[0]} by {ratio}x",
                    "evidence": f"{best_day_info[0]} avg: {round(best_day_info[1]*100, 2)}%, {worst_day_info[0]} avg: {round(worst_day_info[1]*100, 2)}%",
                    "confidence": min(0.8, 0.4 + len(posts) * 0.02),
                })

    return patterns


# ── Top Hooks / Anti-Hooks ──────────────────────────────────

def get_top_hooks(posts: List[Dict[str, Any]], platform: Optional[str] = None, limit: int = 5) -> List[str]:
    """Get top-performing hooks for a user, optionally filtered by platform."""
    filtered = posts
    if platform:
        filtered = [p for p in posts if p.get("platform") == platform]

    sorted_posts = sorted(
        [p for p in filtered if p.get("engagement_rate") is not None and p.get("hook_used")],
        key=lambda p: p["engagement_rate"],
        reverse=True,
    )
    return [p["hook_used"] for p in sorted_posts[:limit]]


def get_anti_hooks(posts: List[Dict[str, Any]], platform: Optional[str] = None, limit: int = 3) -> List[str]:
    """Get worst-performing hooks to avoid."""
    filtered = posts
    if platform:
        filtered = [p for p in posts if p.get("platform") == platform]

    sorted_posts = sorted(
        [p for p in filtered if p.get("engagement_rate") is not None and p.get("hook_used")],
        key=lambda p: p["engagement_rate"],
    )
    return [p["hook_used"] for p in sorted_posts[:limit]]


# ── LLM Post Analysis ──────────────────────────────────────

from worker.graph.prompts.writing_style import HUMAN_WRITING_RULES

POST_ANALYSIS_SYSTEM = """You are a content performance analyst. Analyze why a piece of content performed the way it did.

Consider the hook, topic, content structure, timing, and any patterns visible.

Return a JSON object with:
{
  "why_it_worked_or_failed": "2-3 sentences explaining the likely reason",
  "hook_assessment": "Was the hook strong? Why or why not?",
  "topic_relevance": "How relevant was this topic to the audience?",
  "improvement_suggestions": ["List of 2-3 specific suggestions for improvement"],
  "key_takeaway": "One sentence summary lesson from this post"
}""" + HUMAN_WRITING_RULES


def analyze_post_performance(post: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to analyze why a post performed well or poorly.

    Returns analysis dict. Raises on LLM errors.
    """
    from worker.graph.llm import get_llm_client, parse_json_response

    tier = post.get("performance_tier", "unknown")
    user_prompt = (
        f"Analyze this content post's performance:\n\n"
        f"Title: {post.get('title', 'N/A')}\n"
        f"Platform: {post.get('platform', 'N/A')}\n"
        f"Hook: {post.get('hook_used', 'N/A')}\n"
        f"Hook Type: {post.get('hook_type', 'N/A')}\n"
        f"Topic: {post.get('topic', 'N/A')}\n"
        f"Topic Category: {post.get('topic_category', 'N/A')}\n"
        f"Day Published: {post.get('day_of_week', 'N/A')}\n"
        f"Performance Tier: {tier}\n"
        f"Views: {post.get('views', 'N/A')}\n"
        f"Engagement Rate: {post.get('engagement_rate', 'N/A')}\n"
        f"Likes: {post.get('likes', 'N/A')}\n"
        f"Comments: {post.get('comments', 'N/A')}\n"
        f"Shares: {post.get('shares', 'N/A')}\n"
    )

    body = post.get("content_body")
    if body:
        user_prompt += f"\nContent (first 500 chars):\n{body[:500]}\n"

    llm = get_llm_client()
    response = llm.chat(
        messages=[
            {"role": "system", "content": POST_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model="gpt-4o",
        temperature=0.5,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    return parse_json_response(response["content"])


# ── Performance Context for Pipeline Injection ──────────────

def get_performance_context(
    posts: List[Dict[str, Any]],
    platform: Optional[str] = None,
) -> str:
    """Format performance data as a context block for LLM prompt injection.

    This is the key function that connects performance data to content generation.
    Injected into pipeline node system prompts alongside brand/resource context.
    """
    if not posts:
        return "No performance data available yet."

    filtered = posts
    if platform:
        filtered = [p for p in posts if p.get("platform") == platform]
    if not filtered:
        filtered = posts  # Fall back to all posts if no platform match

    parts = ["--- YOUR CONTENT PERFORMANCE DATA ---"]
    parts.append(f"Based on {len(filtered)} published posts:")

    # Averages
    avgs = get_user_averages(filtered)
    if avgs["avg_engagement_rate"] is not None:
        parts.append(f"Average engagement rate: {round(avgs['avg_engagement_rate'] * 100, 2)}%")
    if avgs["avg_views"] is not None:
        parts.append(f"Average views: {int(avgs['avg_views'])}")

    # Top hooks
    hooks = get_top_hooks(filtered, limit=5)
    if hooks:
        parts.append("\nTOP PERFORMING HOOKS (use these as inspiration):")
        for h in hooks:
            parts.append(f"  - {h}")

    # Anti-hooks
    bad_hooks = get_anti_hooks(filtered, limit=3)
    if bad_hooks:
        parts.append("\nHOOKS THAT FLOPPED (avoid these patterns):")
        for h in bad_hooks:
            parts.append(f"  - {h}")

    # Best topics
    analytics = get_analytics(filtered)
    if analytics["top_topics"]:
        parts.append("\nBEST PERFORMING TOPICS:")
        for t in analytics["top_topics"][:5]:
            er_str = f"{round(t['avg_engagement_rate'] * 100, 2)}%" if t.get("avg_engagement_rate") else "N/A"
            parts.append(f"  - {t['topic_category']} ({t['post_count']} posts, avg engagement: {er_str})")

    # Patterns
    if analytics["patterns"]:
        parts.append("\nDETECTED PATTERNS:")
        for pat in analytics["patterns"]:
            parts.append(f"  - {pat['pattern']}")

    # Best day
    if analytics["best_day_of_week"]:
        parts.append(f"\nBest posting day: {analytics['best_day_of_week']}")

    parts.append("\nUse these insights to optimize the content you're generating.")

    return "\n".join(parts)
