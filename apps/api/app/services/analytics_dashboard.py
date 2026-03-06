"""Analytics Dashboard Service — Slice 112.

Six pure aggregation functions. Each takes raw DB rows and returns
computed metrics. No database access — easy to unit test.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def compute_content_roi(
    deliverables: List[Dict[str, Any]],
    period_days: int,
) -> Dict[str, Any]:
    """Content generation ROI: velocity, approval rate, QA scores, daily trend."""
    total = len(deliverables)
    approved = sum(1 for d in deliverables if d.get("status") == "approved")
    rejected = sum(1 for d in deliverables if d.get("status") == "rejected")
    in_review = sum(1 for d in deliverables if d.get("status") == "review")

    qa_scores = [
        d["qa_score"]
        for d in deliverables
        if d.get("qa_score") and d["qa_score"] > 0
    ]
    avg_qa = round(sum(qa_scores) / len(qa_scores), 1) if qa_scores else 0.0

    # Daily breakdown
    by_day: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"generated": 0, "approved": 0, "rejected": 0, "qa_scores": []}
    )
    for d in deliverables:
        day = str(d.get("created_at", ""))[:10]
        if not day:
            continue
        by_day[day]["generated"] += 1
        if d.get("status") == "approved":
            by_day[day]["approved"] += 1
        elif d.get("status") == "rejected":
            by_day[day]["rejected"] += 1
        if d.get("qa_score") and d["qa_score"] > 0:
            by_day[day]["qa_scores"].append(d["qa_score"])

    daily_breakdown = sorted(
        [
            {
                "date": day,
                "generated": data["generated"],
                "approved": data["approved"],
                "rejected": data["rejected"],
                "avg_qa": round(sum(data["qa_scores"]) / len(data["qa_scores"]), 1)
                if data["qa_scores"]
                else 0.0,
            }
            for day, data in by_day.items()
        ],
        key=lambda x: x["date"],
    )

    return {
        "posts_per_day": round(total / max(period_days, 1), 2),
        "approval_rate": round(approved / total * 100, 1) if total else 0.0,
        "avg_qa_score": avg_qa,
        "total_generated": total,
        "approved": approved,
        "rejected": rejected,
        "in_review": in_review,
        "daily_breakdown": daily_breakdown,
    }


def compute_pipeline_performance(
    runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pipeline success rates, durations, phase breakdown, daily trend."""
    total = len(runs)
    completed = sum(1 for r in runs if r.get("status") == "completed")
    failed = sum(1 for r in runs if r.get("status") == "failed")

    durations = [r["duration_ms"] for r in runs if r.get("duration_ms") and r["duration_ms"] > 0]
    avg_duration = round(sum(durations) / len(durations)) if durations else 0

    # Phase breakdown
    phases: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "durations": [], "fail_count": 0}
    )
    for r in runs:
        tt = r.get("task_type", "unknown")
        phases[tt]["count"] += 1
        if r.get("duration_ms") and r["duration_ms"] > 0:
            phases[tt]["durations"].append(r["duration_ms"])
        if r.get("status") == "failed":
            phases[tt]["fail_count"] += 1

    phase_breakdown = {
        tt: {
            "count": data["count"],
            "avg_ms": round(sum(data["durations"]) / len(data["durations"]))
            if data["durations"]
            else 0,
            "fail_count": data["fail_count"],
        }
        for tt, data in phases.items()
    }

    # Daily runs
    by_day: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"completed": 0, "failed": 0}
    )
    for r in runs:
        day = str(r.get("created_at", ""))[:10]
        if not day:
            continue
        if r.get("status") == "completed":
            by_day[day]["completed"] += 1
        elif r.get("status") == "failed":
            by_day[day]["failed"] += 1

    daily_runs = sorted(
        [{"date": day, **data} for day, data in by_day.items()],
        key=lambda x: x["date"],
    )

    return {
        "total_runs": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round(completed / total * 100, 1) if total else 0.0,
        "avg_duration_ms": avg_duration,
        "phase_breakdown": phase_breakdown,
        "daily_runs": daily_runs,
    }


def compute_revenue_attribution(
    deliverables: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Proposal funnel and revenue from closed deals."""
    client_deliverables = [
        d for d in deliverables if d.get("client_brand")
    ]

    funnel: Dict[str, int] = {
        "draft": 0,
        "sent": 0,
        "accepted": 0,
        "rejected": 0,
        "closed_won": 0,
        "closed_lost": 0,
    }
    total_closed_won = 0.0

    for d in client_deliverables:
        status = d.get("proposal_status", "draft")
        if status in funnel:
            funnel[status] += 1
        if status == "closed_won" and d.get("deal_value"):
            total_closed_won += float(d["deal_value"])

    won = funnel["closed_won"]
    lost = funnel["closed_lost"]
    win_rate = round(won / (won + lost) * 100, 1) if (won + lost) > 0 else 0.0

    return {
        "total_closed_won": round(total_closed_won, 2),
        "total_proposals_sent": sum(
            funnel[s] for s in ["sent", "accepted", "rejected", "closed_won", "closed_lost"]
        ),
        "proposal_funnel": funnel,
        "win_rate": win_rate,
    }


def compute_engagement_trends(
    posts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Engagement metrics from published content."""
    total_views = sum(p.get("views", 0) or 0 for p in posts)
    total_likes = sum(p.get("likes", 0) or 0 for p in posts)
    total_comments = sum(p.get("comments", 0) or 0 for p in posts)

    rates = [p["engagement_rate"] for p in posts if p.get("engagement_rate") and p["engagement_rate"] > 0]
    avg_engagement = round(sum(rates) / len(rates), 4) if rates else 0.0

    # Tier distribution
    tiers: Dict[str, int] = defaultdict(int)
    for p in posts:
        tier = p.get("performance_tier")
        if tier:
            tiers[tier] += 1

    # Top 5 posts by engagement
    sorted_posts = sorted(
        [p for p in posts if p.get("engagement_rate")],
        key=lambda x: x.get("engagement_rate", 0),
        reverse=True,
    )[:5]
    top_posts = [
        {
            "title": p.get("title", "Untitled"),
            "engagement_rate": p.get("engagement_rate", 0),
            "platform": p.get("platform", ""),
            "hook_type": p.get("hook_type", ""),
            "published_at": p.get("published_at", ""),
        }
        for p in sorted_posts
    ]

    # Hook type performance
    hook_groups: Dict[str, List[float]] = defaultdict(list)
    for p in posts:
        ht = p.get("hook_type")
        er = p.get("engagement_rate")
        if ht and er and er > 0:
            hook_groups[ht].append(er)

    hook_type_performance = sorted(
        [
            {
                "hook_type": ht,
                "avg_engagement": round(sum(rates) / len(rates), 4),
                "count": len(rates),
            }
            for ht, rates in hook_groups.items()
        ],
        key=lambda x: x["avg_engagement"],
        reverse=True,
    )

    # Topic performance
    topic_groups: Dict[str, List[float]] = defaultdict(list)
    for p in posts:
        tc = p.get("topic_category")
        er = p.get("engagement_rate")
        if tc and er and er > 0:
            topic_groups[tc].append(er)

    topic_performance = sorted(
        [
            {
                "topic_category": tc,
                "avg_engagement": round(sum(rates) / len(rates), 4),
                "count": len(rates),
            }
            for tc, rates in topic_groups.items()
        ],
        key=lambda x: x["avg_engagement"],
        reverse=True,
    )

    # Best posting days
    day_groups: Dict[str, List[float]] = defaultdict(list)
    for p in posts:
        dow = p.get("day_of_week")
        er = p.get("engagement_rate")
        if dow and er and er > 0:
            day_groups[dow].append(er)

    best_posting_days = sorted(
        [
            {
                "day_of_week": dow,
                "avg_engagement": round(sum(rates) / len(rates), 4),
                "count": len(rates),
            }
            for dow, rates in day_groups.items()
        ],
        key=lambda x: x["avg_engagement"],
        reverse=True,
    )

    return {
        "avg_engagement_rate": avg_engagement,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "tier_distribution": dict(tiers),
        "top_posts": top_posts,
        "hook_type_performance": hook_type_performance,
        "topic_performance": topic_performance,
        "best_posting_days": best_posting_days,
    }


def compute_lead_funnel(
    leads: List[Dict[str, Any]],
    period_start: str = "",
) -> Dict[str, Any]:
    """Lead status distribution, BANT scores, conversion rate."""
    total = len(leads)

    status_dist: Dict[str, int] = defaultdict(int)
    bant_dist: Dict[int, int] = defaultdict(int)

    for lead in leads:
        status = lead.get("status", "cold")
        status_dist[status] += 1
        bant = lead.get("bant_score")
        if bant is not None:
            bant_dist[int(bant)] += 1

    customers = status_dist.get("customer", 0)
    disqualified = status_dist.get("disqualified", 0)
    eligible = total - disqualified
    conversion_rate = round(customers / eligible * 100, 1) if eligible > 0 else 0.0

    new_leads = 0
    if period_start:
        new_leads = sum(
            1 for lead in leads
            if str(lead.get("created_at", "")) >= period_start
        )

    return {
        "total_leads": total,
        "status_distribution": dict(status_dist),
        "bant_distribution": {str(k): v for k, v in sorted(bant_dist.items())},
        "conversion_rate": conversion_rate,
        "new_leads_period": new_leads,
    }


def compute_cost_tracking(
    runs: List[Dict[str, Any]],
    monthly_budget: float,
    total_posts: int,
) -> Dict[str, Any]:
    """Token usage, estimated cost, budget utilization."""
    total_tokens = sum(r.get("total_tokens", 0) or 0 for r in runs)
    estimated_cost = round(total_tokens / 1000 * 0.003, 2)
    budget_utilization = (
        round(estimated_cost / monthly_budget * 100, 1)
        if monthly_budget > 0
        else 0.0
    )
    cost_per_content = (
        round(estimated_cost / total_posts, 3)
        if total_posts > 0
        else 0.0
    )

    # Daily spend
    by_day: Dict[str, int] = defaultdict(int)
    for r in runs:
        day = str(r.get("created_at", ""))[:10]
        if day and r.get("total_tokens"):
            by_day[day] += r["total_tokens"]

    daily_spend = sorted(
        [
            {
                "date": day,
                "tokens": tokens,
                "cost": round(tokens / 1000 * 0.003, 3),
            }
            for day, tokens in by_day.items()
        ],
        key=lambda x: x["date"],
    )

    return {
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
        "monthly_budget": monthly_budget,
        "budget_utilization": budget_utilization,
        "cost_per_content": cost_per_content,
        "daily_spend": daily_spend,
    }
