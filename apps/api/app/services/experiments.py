"""Experiment service — proposes, tracks, and concludes A/B experiments.

The agent deliberately tests new content approaches. For example:
  "Do story hooks or question hooks work better on YouTube?"
It proposes experiments, the user approves, posts get assigned to
variants, and when enough data is collected the winner is determined
and a memory is created.

Key functions:
  - propose_experiment() — agent suggests an experiment
  - approve_experiment() / cancel_experiment() — user lifecycle control
  - assign_post_to_experiment() — tag a post with a variant
  - check_and_conclude() — evaluate results when enough posts collected
  - get_active_experiment_context() — format for pipeline injection
  - auto_propose_experiments() — LLM analyzes data and suggests experiments
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("app.services.experiments")

# Minimum posts per variant before we can conclude
MIN_POSTS_PER_VARIANT = 2
# How much better variant must be to declare a winner (30%)
WINNER_THRESHOLD = 0.30


# ── Experiment CRUD ───────────────────────────────────────

def create_experiment(
    user_id: str,
    hypothesis: str,
    variable: str,
    variant_a: str,
    variant_b: str,
    platform: str,
    target_posts: int = 4,
    status: str = "proposed",
    brand_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new experiment."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    insert_data = {
        "user_id": user_id,
        "hypothesis": hypothesis,
        "variable": variable,
        "variant_a": variant_a,
        "variant_b": variant_b,
        "platform": platform,
        "target_posts": target_posts,
        "status": status,
    }
    if brand_id:
        insert_data["brand_id"] = brand_id

    resp = admin.table("agent_experiments").insert(insert_data).execute()
    if not resp.data:
        raise RuntimeError("Failed to create experiment")

    logger.info(
        "Experiment created: %s (variable=%s, %s vs %s)",
        hypothesis[:50], variable, variant_a, variant_b,
    )
    return resp.data[0]


def get_experiment_by_id(user_id: str, experiment_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single experiment by ID."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("agent_experiments")
        .select("*")
        .eq("id", experiment_id)
        .eq("user_id", user_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def list_experiments(
    user_id: str,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    brand_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List experiments with optional filters."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    query = (
        admin.table("agent_experiments")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)
    if status:
        query = query.eq("status", status)
    if platform:
        query = query.eq("platform", platform)

    resp = query.execute()
    return resp.data if resp.data else []


def update_experiment(
    user_id: str,
    experiment_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Update experiment fields."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("agent_experiments")
        .update(updates)
        .eq("id", experiment_id)
        .eq("user_id", user_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def delete_experiment(user_id: str, experiment_id: str) -> bool:
    """Delete an experiment."""
    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("agent_experiments")
        .delete()
        .eq("id", experiment_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(resp.data)


# ── Lifecycle Actions ─────────────────────────────────────

def approve_experiment(user_id: str, experiment_id: str) -> Dict[str, Any]:
    """Approve a proposed experiment to start collecting data."""
    exp = get_experiment_by_id(user_id, experiment_id)
    if not exp:
        raise ValueError("Experiment not found")
    if exp["status"] != "proposed":
        raise ValueError(f"Cannot approve experiment in '{exp['status']}' status")

    result = update_experiment(user_id, experiment_id, {"status": "approved"})
    if not result:
        raise RuntimeError("Failed to approve experiment")

    logger.info("Experiment approved: %s", experiment_id)
    return result


def cancel_experiment(user_id: str, experiment_id: str) -> Dict[str, Any]:
    """Cancel an experiment."""
    exp = get_experiment_by_id(user_id, experiment_id)
    if not exp:
        raise ValueError("Experiment not found")
    if exp["status"] in ("completed", "cancelled"):
        raise ValueError(f"Cannot cancel experiment in '{exp['status']}' status")

    result = update_experiment(user_id, experiment_id, {"status": "cancelled"})
    if not result:
        raise RuntimeError("Failed to cancel experiment")

    logger.info("Experiment cancelled: %s", experiment_id)
    return result


def assign_post_to_experiment(
    user_id: str,
    experiment_id: str,
    post_id: str,
    variant: str,
) -> Dict[str, Any]:
    """Assign a published post to an experiment variant.

    variant must be 'variant_a' or 'variant_b'.
    Moves experiment to 'running' if not already.
    """
    if variant not in ("variant_a", "variant_b"):
        raise ValueError("variant must be 'variant_a' or 'variant_b'")

    exp = get_experiment_by_id(user_id, experiment_id)
    if not exp:
        raise ValueError("Experiment not found")
    if exp["status"] not in ("approved", "running"):
        raise ValueError(f"Cannot assign posts to experiment in '{exp['status']}' status")

    # Add post ID to the correct variant array
    post_list_key = f"{variant}_posts"
    current_posts = exp.get(post_list_key, []) or []
    if post_id in current_posts:
        raise ValueError(f"Post {post_id} already assigned to {variant}")

    updated_posts = current_posts + [post_id]
    updates = {
        post_list_key: updated_posts,
        "status": "running",  # Auto-move to running when first post assigned
    }

    result = update_experiment(user_id, experiment_id, updates)
    if not result:
        raise RuntimeError("Failed to assign post to experiment")

    logger.info(
        "Post %s assigned to experiment %s %s (total: %d)",
        post_id, experiment_id, variant, len(updated_posts),
    )
    return result


# ── Conclusion Logic ──────────────────────────────────────

def calculate_variant_engagement(
    user_id: str,
    post_ids: List[str],
) -> Optional[float]:
    """Calculate average engagement rate for a list of post IDs."""
    if not post_ids:
        return None

    from app.deps import get_admin_client
    admin = get_admin_client()

    resp = (
        admin.table("content_posts")
        .select("engagement_rate")
        .eq("user_id", user_id)
        .in_("id", post_ids)
        .execute()
    )
    if not resp.data:
        return None

    rates = [r["engagement_rate"] for r in resp.data if r.get("engagement_rate") is not None]
    if not rates:
        return None

    return round(sum(rates) / len(rates), 6)


def check_and_conclude(user_id: str, experiment_id: str) -> Dict[str, Any]:
    """Check if experiment has enough data and determine the winner.

    Returns the updated experiment with results.
    Auto-creates an agent_memory lesson from the conclusion.
    """
    exp = get_experiment_by_id(user_id, experiment_id)
    if not exp:
        raise ValueError("Experiment not found")
    if exp["status"] == "completed":
        return exp

    a_posts = exp.get("variant_a_posts", []) or []
    b_posts = exp.get("variant_b_posts", []) or []

    # Check if we have minimum posts per variant
    if len(a_posts) < MIN_POSTS_PER_VARIANT or len(b_posts) < MIN_POSTS_PER_VARIANT:
        return {
            **exp,
            "message": (
                f"Not enough data yet. Need {MIN_POSTS_PER_VARIANT} posts per variant. "
                f"Variant A: {len(a_posts)}, Variant B: {len(b_posts)}."
            ),
        }

    # Calculate engagements
    a_avg = calculate_variant_engagement(user_id, a_posts)
    b_avg = calculate_variant_engagement(user_id, b_posts)

    if a_avg is None or b_avg is None:
        return {
            **exp,
            "message": "Cannot conclude — posts are missing engagement data.",
        }

    # Determine winner
    if a_avg == 0 and b_avg == 0:
        winner = "inconclusive"
        conclusion = (
            f"Both variants had 0% engagement. "
            f"Cannot determine a winner for '{exp['hypothesis']}'."
        )
    else:
        # Calculate relative difference
        max_avg = max(a_avg, b_avg)
        diff = abs(a_avg - b_avg) / max_avg if max_avg > 0 else 0

        if diff < WINNER_THRESHOLD:
            winner = "inconclusive"
            conclusion = (
                f"Results are too close to call. "
                f"'{exp['variant_a']}' ({a_avg:.4%}) vs '{exp['variant_b']}' ({b_avg:.4%}). "
                f"Difference: {diff:.1%}. Need > {WINNER_THRESHOLD:.0%} to declare winner."
            )
        elif a_avg > b_avg:
            winner = "variant_a"
            conclusion = (
                f"'{exp['variant_a']}' outperformed '{exp['variant_b']}' "
                f"({a_avg:.4%} vs {b_avg:.4%}, +{diff:.1%}) "
                f"for {exp['variable']} on {exp['platform']}."
            )
        else:
            winner = "variant_b"
            conclusion = (
                f"'{exp['variant_b']}' outperformed '{exp['variant_a']}' "
                f"({b_avg:.4%} vs {a_avg:.4%}, +{diff:.1%}) "
                f"for {exp['variable']} on {exp['platform']}."
            )

    # Update experiment with results
    updates = {
        "variant_a_avg_engagement": a_avg,
        "variant_b_avg_engagement": b_avg,
        "winner": winner,
        "conclusion": conclusion,
        "status": "completed",
        "completed_at": "now()",
    }

    # Create a memory from the conclusion (if we have a clear winner)
    resulting_memory_id = None
    if winner != "inconclusive":
        try:
            from app.services.agent_memory import create_memory
            memory = create_memory(
                user_id=user_id,
                memory_type="lesson",
                content=conclusion,
                confidence=0.7,
                platform=exp["platform"],
                category=exp["variable"],
                source="experiment",
                status="pending_approval",
                brand_id=exp.get("brand_id"),
            )
            resulting_memory_id = memory.get("id")
            updates["resulting_memory_id"] = resulting_memory_id
            logger.info("Created memory from experiment conclusion: %s", resulting_memory_id)
        except Exception as e:
            logger.warning("Failed to create memory from experiment: %s", e)

    result = update_experiment(user_id, experiment_id, updates)
    if not result:
        raise RuntimeError("Failed to conclude experiment")

    logger.info(
        "Experiment concluded: %s — winner=%s",
        experiment_id, winner,
    )
    return result


# ── Pipeline Integration ──────────────────────────────────

def get_active_experiment_context(
    user_id: str,
    platform: Optional[str] = None,
    brand_id: Optional[str] = None,
) -> str:
    """Get formatted experiment context for pipeline prompt injection.

    Returns a string describing any active/running experiments the agent
    should be aware of when generating content.
    """
    experiments = list_experiments(user_id, brand_id=brand_id)

    # Filter to approved/running experiments for this platform
    active = [
        e for e in experiments
        if e["status"] in ("approved", "running")
        and (not platform or e["platform"] == platform)
    ]

    if not active:
        return ""

    lines = ["--- ACTIVE EXPERIMENTS ---"]
    lines.append("The user is currently running these content experiments:")
    lines.append("")

    for exp in active:
        a_count = len(exp.get("variant_a_posts", []) or [])
        b_count = len(exp.get("variant_b_posts", []) or [])
        target = exp.get("target_posts", 4)

        lines.append(f"EXPERIMENT: {exp['hypothesis']}")
        lines.append(f"  Testing: {exp['variable']}")
        lines.append(f"  Variant A: '{exp['variant_a']}' ({a_count}/{target} posts)")
        lines.append(f"  Variant B: '{exp['variant_b']}' ({b_count}/{target} posts)")

        # Suggest which variant needs more posts
        if a_count < b_count:
            lines.append(f"  >> Next post should use: {exp['variant_a']} (variant A needs more data)")
        elif b_count < a_count:
            lines.append(f"  >> Next post should use: {exp['variant_b']} (variant B needs more data)")
        else:
            lines.append(f"  >> Either variant is fine for the next post")
        lines.append("")

    lines.append("Consider these experiments when generating content suggestions.")
    return "\n".join(lines)


# ── Completed Experiment Summary ──────────────────────────

def get_completed_experiments_summary(
    user_id: str,
    platform: Optional[str] = None,
    limit: int = 5,
    brand_id: Optional[str] = None,
) -> str:
    """Get summary of completed experiments for context injection."""
    experiments = list_experiments(user_id, status="completed", brand_id=brand_id)

    if platform:
        experiments = [e for e in experiments if e["platform"] == platform]

    experiments = experiments[:limit]
    if not experiments:
        return ""

    lines = ["--- COMPLETED EXPERIMENTS ---"]
    for exp in experiments:
        if exp.get("conclusion"):
            lines.append(f"- {exp['conclusion']}")

    return "\n".join(lines)


# ── Auto-Proposal ─────────────────────────────────────────

def auto_propose_experiments(user_id: str, brand_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Use LLM to analyze performance data and propose experiments.

    Looks at the user's content_posts, finds variables with variance,
    and suggests experiments to test.
    """
    from app.deps import get_admin_client
    admin = get_admin_client()

    # Get user's posts with engagement data
    query = (
        admin.table("content_posts")
        .select("hook_type, topic_category, platform, engagement_rate, performance_tier")
        .eq("user_id", user_id)
    )
    if brand_id:
        query = query.eq("brand_id", brand_id)

    resp = (
        query
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    posts = resp.data if resp.data else []

    if len(posts) < 5:
        logger.info("Not enough posts (%d) for auto-proposals", len(posts))
        return []

    # Get existing experiments to avoid duplicates
    existing = list_experiments(user_id, brand_id=brand_id)
    existing_vars = set()
    for e in existing:
        if e["status"] not in ("cancelled", "completed"):
            existing_vars.add((e["variable"], e["variant_a"], e["variant_b"], e["platform"]))

    # Build summary for LLM
    from collections import defaultdict

    # Group by platform → variable → value
    data_summary = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for post in posts:
        platform = post.get("platform", "unknown")
        for var_key in ["hook_type", "topic_category"]:
            val = post.get(var_key)
            if val and post.get("engagement_rate") is not None:
                data_summary[platform][var_key][val].append(post["engagement_rate"])

    # Build proposals from data patterns
    proposals = []
    for platform, variables in data_summary.items():
        for var_name, values in variables.items():
            # Need at least 2 different values with enough data
            if len(values) < 2:
                continue

            # Sort values by average engagement
            ranked = sorted(
                [(v, sum(rates) / len(rates), len(rates)) for v, rates in values.items() if len(rates) >= 2],
                key=lambda x: x[1],
                reverse=True,
            )

            if len(ranked) < 2:
                continue

            top_val, top_avg, top_count = ranked[0]
            second_val, second_avg, second_count = ranked[1]

            # Skip if already being tested
            if (var_name, top_val, second_val, platform) in existing_vars:
                continue
            if (var_name, second_val, top_val, platform) in existing_vars:
                continue

            # Only propose if there's meaningful variance
            if top_avg > 0 and (top_avg - second_avg) / top_avg > 0.15:
                hypothesis = (
                    f"'{top_val}' {var_name} outperforms '{second_val}' on {platform} "
                    f"(current data: {top_avg:.4%} vs {second_avg:.4%})"
                )
                proposals.append({
                    "hypothesis": hypothesis,
                    "variable": var_name,
                    "variant_a": top_val,
                    "variant_b": second_val,
                    "platform": platform,
                    "target_posts": 4,
                })

    # Create proposed experiments
    created = []
    for p in proposals[:3]:  # Max 3 proposals at a time
        try:
            exp = create_experiment(
                user_id=user_id,
                hypothesis=p["hypothesis"],
                variable=p["variable"],
                variant_a=p["variant_a"],
                variant_b=p["variant_b"],
                platform=p["platform"],
                target_posts=p["target_posts"],
                status="proposed",
                brand_id=brand_id,
            )
            created.append(exp)
        except Exception as e:
            logger.warning("Failed to create experiment proposal: %s", e)

    logger.info("Auto-proposed %d experiments for user %s", len(created), user_id)
    return created
