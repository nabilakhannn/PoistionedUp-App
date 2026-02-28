"""Competitor Intelligence service.

Provides CRUD for competitor profiles, metric tracking, content monitoring,
comparison with user analytics, and LLM-powered analysis reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.analytics import track_event

logger = logging.getLogger(__name__)


# ── CRUD ────────────────────────────────────────────────────────


def create_competitor(
    user_id: str,
    data: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Insert a new competitor profile."""
    row = {
        "user_id": user_id,
        "name": data["name"],
        "platform": data.get("platform", "website"),
        "profile_url": data["profile_url"],
        "positioning": data.get("positioning"),
        "niche": data.get("niche"),
        "pricing_tier": data.get("pricing_tier"),
        "notes": data.get("notes"),
        "threat_level": data.get("threat_level", 3),
        "status": "active",
    }
    if data.get("brand_id"):
        row["brand_id"] = data["brand_id"]

    resp = sb.table("competitors").insert(row).execute()
    competitor = resp.data[0] if resp.data else row

    track_event(user_id, "competitor_created", {
        "competitor_name": data["name"],
        "platform": data.get("platform", "website"),
    })
    return competitor


def list_competitors(
    user_id: str,
    sb: Any,
    brand_id: Optional[str] = None,
    status: str = "active",
) -> List[Dict[str, Any]]:
    """Return filtered list of competitors with latest metrics joined."""
    query = (
        sb.table("competitors")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", status)
        .order("created_at", desc=True)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = query.execute()
    competitors = resp.data or []

    # Attach latest metrics snapshot per competitor
    for comp in competitors:
        metrics_resp = (
            sb.table("competitor_metrics")
            .select("*")
            .eq("competitor_id", comp["id"])
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        comp["latest_metrics"] = metrics_resp.data[0] if metrics_resp.data else None

    return competitors


def get_competitor(
    competitor_id: str,
    user_id: str,
    sb: Any,
) -> Optional[Dict[str, Any]]:
    """Get a single competitor with metrics history and recent content."""
    resp = (
        sb.table("competitors")
        .select("*")
        .eq("id", competitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        return None

    competitor = resp.data[0]

    # Latest metrics
    metrics_resp = (
        sb.table("competitor_metrics")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("recorded_at", desc=True)
        .limit(10)
        .execute()
    )
    competitor["metrics_history"] = metrics_resp.data or []
    competitor["latest_metrics"] = metrics_resp.data[0] if metrics_resp.data else None

    # Recent content
    content_resp = (
        sb.table("competitor_content")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("published_at", desc=True)
        .limit(20)
        .execute()
    )
    competitor["recent_content"] = content_resp.data or []

    return competitor


def update_competitor(
    competitor_id: str,
    user_id: str,
    updates: Dict[str, Any],
    sb: Any,
) -> Optional[Dict[str, Any]]:
    """PATCH a competitor profile. Only non-None fields are updated."""
    patch = {k: v for k, v in updates.items() if v is not None}
    if not patch:
        return get_competitor(competitor_id, user_id, sb)

    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    # If user explicitly sets threat_level, mark as manual override
    if "threat_level" in patch:
        patch["threat_level_override"] = True

    resp = (
        sb.table("competitors")
        .update(patch)
        .eq("id", competitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        return None
    return resp.data[0]


def delete_competitor(
    competitor_id: str,
    user_id: str,
    sb: Any,
) -> bool:
    """Soft-delete: set status to 'archived'."""
    resp = (
        sb.table("competitors")
        .update({"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", competitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(resp.data)


# ── Metrics ─────────────────────────────────────────────────────


def record_metrics(
    competitor_id: str,
    metrics: Dict[str, Any],
    sb: Any,
) -> Dict[str, Any]:
    """Insert a new metrics snapshot for a competitor."""
    row = {
        "competitor_id": competitor_id,
        "followers": metrics.get("followers"),
        "engagement_rate": metrics.get("engagement_rate"),
        "post_frequency_weekly": metrics.get("post_frequency_weekly"),
        "avg_post_engagement": metrics.get("avg_post_engagement"),
        "top_topic": metrics.get("top_topic"),
        "source": metrics.get("source", "manual"),
    }
    resp = sb.table("competitor_metrics").insert(row).execute()
    return resp.data[0] if resp.data else row


def get_metrics_history(
    competitor_id: str,
    sb: Any,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Return time-series metrics for charting."""
    resp = (
        sb.table("competitor_metrics")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("recorded_at", desc=True)
        .limit(days)
        .execute()
    )
    return resp.data or []


# ── Content Tracking ────────────────────────────────────────────


def record_content(
    competitor_id: str,
    content_items: List[Dict[str, Any]],
    sb: Any,
) -> int:
    """Batch-insert tracked content from a competitor. Returns count inserted."""
    if not content_items:
        return 0

    rows = []
    for item in content_items:
        rows.append({
            "competitor_id": competitor_id,
            "published_at": item.get("published_at"),
            "platform": item.get("platform"),
            "title": item.get("title"),
            "url": item.get("url"),
            "content_preview": item.get("content_preview"),
            "topics": item.get("topics", []),
            "engagement_count": item.get("engagement_count"),
            "engagement_rate": item.get("engagement_rate"),
            "format": item.get("format", "post"),
        })

    resp = sb.table("competitor_content").insert(rows).execute()
    return len(resp.data) if resp.data else 0


def get_recent_content(
    competitor_id: str,
    sb: Any,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Get recent tracked content for a competitor."""
    resp = (
        sb.table("competitor_content")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


# ── Comparison & Analysis ───────────────────────────────────────


def compare_with_user(
    user_id: str,
    competitor_id: str,
    sb: Any,
) -> Dict[str, Any]:
    """Side-by-side comparison of user analytics vs competitor metrics."""
    from app.services.performance_analytics import get_analytics

    # Competitor latest metrics
    comp_resp = (
        sb.table("competitors")
        .select("id, name")
        .eq("id", competitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not comp_resp.data:
        return {"error": "Competitor not found"}

    comp_name = comp_resp.data[0]["name"]

    metrics_resp = (
        sb.table("competitor_metrics")
        .select("*")
        .eq("competitor_id", competitor_id)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    comp_metrics = metrics_resp.data[0] if metrics_resp.data else {}

    # User analytics from scheduled_items
    items_resp = (
        sb.table("scheduled_items")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "published")
        .limit(100)
        .execute()
    )
    user_posts = items_resp.data or []
    user_analytics = get_analytics(user_posts) if user_posts else {}

    # Build comparison insights
    insights = _build_comparison_insights(user_analytics, comp_metrics)

    return {
        "competitor_id": competitor_id,
        "competitor_name": comp_name,
        "user_metrics": {
            "total_posts": user_analytics.get("total_posts", 0),
            "platforms": user_analytics.get("platforms", []),
            "top_topics": user_analytics.get("top_topics", []),
        },
        "competitor_metrics": {
            "followers": comp_metrics.get("followers"),
            "engagement_rate": comp_metrics.get("engagement_rate"),
            "post_frequency_weekly": comp_metrics.get("post_frequency_weekly"),
            "avg_post_engagement": comp_metrics.get("avg_post_engagement"),
            "top_topic": comp_metrics.get("top_topic"),
        },
        "insights": insights,
    }


def _build_comparison_insights(
    user_analytics: Dict[str, Any],
    comp_metrics: Dict[str, Any],
) -> List[str]:
    """Generate simple comparison insights between user and competitor."""
    insights: List[str] = []

    comp_engagement = comp_metrics.get("engagement_rate")
    if comp_engagement and user_analytics.get("platforms"):
        user_avg = sum(
            p.get("avg_engagement_rate", 0) for p in user_analytics["platforms"]
        ) / max(len(user_analytics["platforms"]), 1)
        if user_avg > comp_engagement:
            insights.append("Your engagement rate is higher than this competitor.")
        elif comp_engagement > user_avg:
            insights.append("This competitor has a higher engagement rate than you.")

    comp_freq = comp_metrics.get("post_frequency_weekly")
    user_total = user_analytics.get("total_posts", 0)
    if comp_freq and user_total:
        insights.append(
            f"Competitor posts ~{comp_freq:.1f}x/week. "
            f"You have {user_total} published posts total."
        )

    if not insights:
        insights.append("Add more metrics to unlock comparison insights.")

    return insights


def calculate_dynamic_threat(
    competitor_id: str,
    user_id: str,
    sb: Any,
) -> Dict[str, Any]:
    """Calculate dynamic threat score based on competitor metrics vs user metrics.

    Factors (each 0.0-1.0):
    - Engagement growth (30%): recent follower/engagement growth trajectory
    - Content overlap (25%): topic overlap between competitor and user
    - Post frequency (25%): competitor posting rate vs user
    - Follower ratio (20%): competitor size vs user

    Final score: 1.0 + weighted_sum * 4.0 → maps to 1.0-5.0.
    """
    comp_resp = (
        sb.table("competitors")
        .select("id, name, threat_level, threat_level_override")
        .eq("id", competitor_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not comp_resp.data:
        return {"error": "Competitor not found"}

    comp = comp_resp.data[0]
    old_level = comp.get("threat_level", 3)
    is_override = comp.get("threat_level_override", False)

    # ── Factor 1: Engagement growth (compare last 2 metric snapshots) ──
    metrics_resp = (
        sb.table("competitor_metrics")
        .select("followers, engagement_rate")
        .eq("competitor_id", competitor_id)
        .order("recorded_at", desc=True)
        .limit(2)
        .execute()
    )
    snapshots = metrics_resp.data or []
    engagement_growth = 0.0
    if len(snapshots) >= 2:
        latest_f = snapshots[0].get("followers") or 0
        prev_f = snapshots[1].get("followers") or 0
        if prev_f > 0 and latest_f > 0:
            growth_pct = ((latest_f - prev_f) / prev_f) * 100
            engagement_growth = min(abs(growth_pct) / 50.0, 1.0)

    # ── Factor 2: Content overlap ──
    # Competitor topics
    comp_content_resp = (
        sb.table("competitor_content")
        .select("topics")
        .eq("competitor_id", competitor_id)
        .limit(50)
        .execute()
    )
    comp_topics = set()
    for row in comp_content_resp.data or []:
        for t in row.get("topics", []):
            cleaned = t.lower().strip()
            if cleaned:
                comp_topics.add(cleaned)

    # User topics
    user_items_resp = (
        sb.table("scheduled_items")
        .select("topic_category")
        .eq("user_id", user_id)
        .limit(200)
        .execute()
    )
    user_topics = set()
    for row in user_items_resp.data or []:
        tc = (row.get("topic_category") or "").lower().strip()
        if tc:
            user_topics.add(tc)

    content_overlap = 0.0
    if comp_topics and user_topics:
        overlap = comp_topics & user_topics
        content_overlap = len(overlap) / max(len(user_topics), 1)

    # ── Factor 3: Post frequency comparison ──
    latest_metrics = snapshots[0] if snapshots else {}
    comp_freq = latest_metrics.get("post_frequency_weekly") if isinstance(latest_metrics, dict) else None

    # Estimate user post frequency from recent published items
    user_published_resp = (
        sb.table("scheduled_items")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "published")
        .limit(100)
        .execute()
    )
    user_post_count = len(user_published_resp.data or [])
    # Rough estimate: total published / ~4 weeks
    user_freq = user_post_count / max(4.0, 1.0) if user_post_count else 0.5

    frequency_factor = 0.0
    if comp_freq and comp_freq > 0:
        frequency_factor = min(comp_freq / max(user_freq, 0.5), 2.0) / 2.0

    # ── Factor 4: Follower ratio ──
    comp_followers = (snapshots[0].get("followers") or 0) if snapshots else 0
    # Use a baseline of 100 if user followers unknown
    follower_ratio = 0.0
    if comp_followers > 0:
        follower_ratio = min(comp_followers / max(100, 1), 10.0) / 10.0

    # ── Weighted score ──
    raw = (
        engagement_growth * 0.30
        + content_overlap * 0.25
        + frequency_factor * 0.25
        + follower_ratio * 0.20
    )
    calculated = round(1.0 + raw * 4.0, 1)
    new_level = max(1, min(5, round(calculated)))

    reasoning_parts = []
    if engagement_growth > 0.3:
        reasoning_parts.append(f"Strong growth ({engagement_growth:.0%})")
    if content_overlap > 0.3:
        reasoning_parts.append(f"High topic overlap ({content_overlap:.0%})")
    if frequency_factor > 0.5:
        reasoning_parts.append("Posts more frequently than you")
    if follower_ratio > 0.3:
        reasoning_parts.append("Significant follower base")
    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Low competitive pressure"

    result = {
        "competitor_id": competitor_id,
        "calculated_score": calculated,
        "new_level": new_level,
        "old_level": old_level,
        "changed": new_level != old_level and not is_override,
        "is_overridden": is_override,
        "engagement_growth_factor": round(engagement_growth, 3),
        "content_overlap_factor": round(content_overlap, 3),
        "frequency_factor": round(frequency_factor, 3),
        "follower_ratio_factor": round(follower_ratio, 3),
        "reasoning": reasoning,
    }

    # Update DB only if not manually overridden
    if not is_override and new_level != old_level:
        sb.table("competitors").update({
            "threat_level": new_level,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", competitor_id).eq("user_id", user_id).execute()

        track_event(user_id, "competitor_threat_updated", {
            "competitor_id": competitor_id,
            "old_level": old_level,
            "new_level": new_level,
        })

    return result


def get_content_gap_analysis(
    user_id: str,
    sb: Any,
    brand_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Identify topics competitors cover that the user doesn't, and vice versa."""
    # Gather competitor topics
    query = (
        sb.table("competitors")
        .select("id, name")
        .eq("user_id", user_id)
        .eq("status", "active")
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)
    comp_resp = query.execute()
    competitors = comp_resp.data or []

    competitor_topics: Dict[str, List[str]] = {}  # topic -> [competitor names]
    for comp in competitors:
        content_resp = (
            sb.table("competitor_content")
            .select("topics")
            .eq("competitor_id", comp["id"])
            .limit(50)
            .execute()
        )
        for row in content_resp.data or []:
            for topic in row.get("topics", []):
                t = topic.lower().strip()
                if t:
                    competitor_topics.setdefault(t, [])
                    if comp["name"] not in competitor_topics[t]:
                        competitor_topics[t].append(comp["name"])

    # Gather user topics from scheduled items
    items_resp = (
        sb.table("scheduled_items")
        .select("topic_category")
        .eq("user_id", user_id)
        .limit(200)
        .execute()
    )
    user_topics = set()
    for row in items_resp.data or []:
        tc = (row.get("topic_category") or "").lower().strip()
        if tc:
            user_topics.add(tc)

    # Build gap analysis
    gaps = []
    shared = []
    for topic, comp_names in competitor_topics.items():
        if topic not in user_topics:
            gaps.append({
                "topic": topic,
                "covered_by_competitors": comp_names,
                "your_coverage": False,
                "priority": "high" if len(comp_names) > 1 else "medium",
            })
        else:
            shared.append(topic)

    your_unique = [t for t in user_topics if t not in competitor_topics]

    return {
        "gaps": sorted(gaps, key=lambda g: len(g["covered_by_competitors"]), reverse=True),
        "your_unique_topics": sorted(your_unique),
        "shared_topics": sorted(shared),
    }


def generate_analysis_report(
    user_id: str,
    competitor_id: str,
    sb: Any,
) -> Dict[str, Any]:
    """LLM-powered competitive analysis using competitor content + user brand profile."""
    from worker.graph.llm import get_llm_client, get_model_for_step, parse_json_response

    # Fetch competitor data
    comp = get_competitor(competitor_id, user_id, sb)
    if not comp:
        return {"error": "Competitor not found"}

    # Fetch user brand profile for context
    brand_context = ""
    if comp.get("brand_id"):
        brand_resp = (
            sb.table("personal_brands")
            .select("profile_json")
            .eq("id", comp["brand_id"])
            .execute()
        )
        if brand_resp.data:
            profile = brand_resp.data[0].get("profile_json", {})
            brand_context = (
                f"User's brand: {profile.get('brand_name', 'N/A')}\n"
                f"Niche: {profile.get('niche', 'N/A')}\n"
                f"Target audience: {profile.get('target_audience', 'N/A')}"
            )

    # Build content summary for LLM
    content_summary = ""
    for item in comp.get("recent_content", [])[:10]:
        content_summary += (
            f"- {item.get('title', 'Untitled')} ({item.get('format', 'post')}) "
            f"engagement: {item.get('engagement_count', 'N/A')}\n"
        )

    metrics = comp.get("latest_metrics") or {}
    metrics_text = (
        f"Followers: {metrics.get('followers', 'N/A')}\n"
        f"Engagement rate: {metrics.get('engagement_rate', 'N/A')}%\n"
        f"Post frequency: {metrics.get('post_frequency_weekly', 'N/A')}/week\n"
        f"Top topic: {metrics.get('top_topic', 'N/A')}"
    )

    system_prompt = (
        "You are a competitive intelligence analyst. Analyze the competitor data "
        "and provide actionable insights. Return JSON with keys: summary, strengths, "
        "weaknesses, content_pillars, threat_assessment."
    )
    user_prompt = (
        f"Analyze this competitor:\n\n"
        f"Name: {comp['name']}\n"
        f"Platform: {comp['platform']}\n"
        f"Positioning: {comp.get('positioning', 'Unknown')}\n"
        f"Niche: {comp.get('niche', 'Unknown')}\n"
        f"\nMetrics:\n{metrics_text}\n"
        f"\nRecent Content:\n{content_summary or 'No content tracked yet.'}\n"
        f"\n{brand_context}"
    )

    try:
        llm = get_llm_client()
        model = get_model_for_step("script_generation")
        resp = llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        parsed = parse_json_response(resp["content"])

        track_event(user_id, "competitor_analysis_generated", {
            "competitor_id": competitor_id,
            "competitor_name": comp["name"],
        })

        return {
            "competitor_id": competitor_id,
            "summary": parsed.get("summary", ""),
            "strengths": parsed.get("strengths", []),
            "weaknesses": parsed.get("weaknesses", []),
            "content_pillars": parsed.get("content_pillars", []),
            "threat_assessment": parsed.get("threat_assessment", ""),
        }
    except Exception as e:
        logger.error("Analysis generation failed for competitor %s: %s", competitor_id, e)
        return {
            "competitor_id": competitor_id,
            "summary": f"Analysis failed: {e}",
            "strengths": [],
            "weaknesses": [],
            "content_pillars": [],
            "threat_assessment": "",
        }


# ── Scan / Refresh ──────────────────────────────────────────────


def scan_competitor_url(profile_url: str) -> Dict[str, Any]:
    """Use web search tools to gather fresh data from a competitor URL."""
    from app.services.web_search import analyze_competitor_url, search_web

    result: Dict[str, Any] = {"url": profile_url, "data": {}, "content_items": []}

    try:
        url_data = analyze_competitor_url(profile_url)
        result["data"]["raw_text"] = url_data.get("text", "")[:2000]
        result["data"]["source_type"] = url_data.get("source_type")
        result["data"]["metadata"] = url_data.get("metadata", {})
    except Exception as e:
        logger.warning("URL analysis failed for %s: %s", profile_url, e)
        result["data"]["error"] = str(e)

    # Search for recent activity
    try:
        search_results = search_web(f"site:{profile_url} recent posts", max_results=5)
        for sr in search_results:
            result["content_items"].append({
                "title": sr.get("title", ""),
                "url": sr.get("url", ""),
                "content_preview": sr.get("snippet", ""),
                "format": "post",
            })
    except Exception as e:
        logger.warning("Web search failed for %s: %s", profile_url, e)

    return result


def refresh_competitor_data(
    competitor_id: str,
    user_id: str,
    sb: Any,
) -> Dict[str, Any]:
    """Scan competitor URL and update metrics + content records."""
    comp = get_competitor(competitor_id, user_id, sb)
    if not comp:
        return {"error": "Competitor not found"}

    scan_result = scan_competitor_url(comp["profile_url"])

    # Record content items if any found
    content_count = 0
    if scan_result.get("content_items"):
        content_count = record_content(competitor_id, scan_result["content_items"], sb)

    # Update competitor updated_at
    sb.table("competitors").update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", competitor_id).eq("user_id", user_id).execute()

    # Run dynamic threat scoring after refresh
    threat_result = {}
    try:
        threat_result = calculate_dynamic_threat(competitor_id, user_id, sb)
    except Exception as e:
        logger.warning("Dynamic threat scoring failed for %s: %s", competitor_id, e)

    track_event(user_id, "competitor_refreshed", {
        "competitor_id": competitor_id,
        "content_items_found": content_count,
    })

    return {
        "competitor_id": competitor_id,
        "content_items_added": content_count,
        "scan_data": scan_result.get("data", {}),
        "threat_score": threat_result,
    }


# ── Intelligence Feed ──────────────────────────────────────────


def get_intelligence_feed(
    user_id: str,
    sb: Any,
    brand_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregate competitor intelligence data for the feed page."""
    # 1. Active competitors + avg threat level
    competitors = list_competitors(user_id, sb, brand_id=brand_id, status="active")
    active_count = len(competitors)
    avg_threat = 0.0
    if competitors:
        avg_threat = round(
            sum(c.get("threat_level", 3) for c in competitors) / active_count, 1
        )

    # 2. Recent analyses from agent_deliverables
    recent_analyses = []
    try:
        deliverables_resp = (
            sb.table("agent_deliverables")
            .select("id, title, content, created_at, metadata")
            .eq("user_id", user_id)
            .ilike("title", "%Competitor%")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for d in deliverables_resp.data or []:
            # Try to extract competitor_id from metadata
            meta = d.get("metadata") or {}
            comp_id = meta.get("competitor_id", "")
            comp_name = meta.get("competitor_name", "")
            if not comp_name:
                # Extract from title: "Competitor Analysis: CompName"
                title = d.get("title", "")
                if ":" in title:
                    comp_name = title.split(":", 1)[1].strip()

            recent_analyses.append({
                "item_type": "analysis",
                "competitor_id": comp_id,
                "competitor_name": comp_name,
                "summary": (d.get("content") or "")[:300],
                "date": d.get("created_at"),
            })
    except Exception as e:
        logger.warning("Failed to fetch recent analyses: %s", e)

    latest_analysis_date = None
    if recent_analyses:
        latest_analysis_date = recent_analyses[0].get("date")

    # 3. Recent alerts from agent_notifications
    recent_alerts = []
    try:
        notifs_resp = (
            sb.table("agent_notifications")
            .select("*")
            .eq("user_id", user_id)
            .ilike("action_url", "%/competitors%")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for n in notifs_resp.data or []:
            recent_alerts.append({
                "id": n.get("id"),
                "competitor_id": (n.get("metadata") or {}).get("competitor_id", ""),
                "competitor_name": (n.get("metadata") or {}).get("competitor_name", ""),
                "alert_type": (n.get("metadata") or {}).get("alert_type", "follower_surge"),
                "detail": n.get("body", ""),
                "severity": n.get("priority", "medium"),
                "created_at": n.get("created_at"),
            })
    except Exception as e:
        logger.warning("Failed to fetch competitor alerts: %s", e)

    # 4. Benchmarks: avg competitor metrics vs user
    comp_engagement_sum = 0.0
    comp_freq_sum = 0.0
    comp_followers_sum = 0
    counted = 0
    for comp in competitors:
        m = comp.get("latest_metrics")
        if m:
            counted += 1
            comp_engagement_sum += m.get("engagement_rate") or 0.0
            comp_freq_sum += m.get("post_frequency_weekly") or 0.0
            comp_followers_sum += m.get("followers") or 0

    benchmarks = {
        "competitor_avg_engagement": round(comp_engagement_sum / max(counted, 1), 2),
        "competitor_avg_frequency": round(comp_freq_sum / max(counted, 1), 1),
        "competitor_avg_followers": round(comp_followers_sum / max(counted, 1)),
        "competitors_counted": counted,
    }

    return {
        "active_competitors": active_count,
        "avg_threat_level": avg_threat,
        "latest_analysis_date": latest_analysis_date,
        "open_alerts": len(recent_alerts),
        "recent_analyses": recent_analyses,
        "recent_alerts": recent_alerts,
        "benchmarks": benchmarks,
    }
