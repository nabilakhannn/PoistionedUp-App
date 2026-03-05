#!/usr/bin/env python3
"""Jumbo Pipeline Runner — VPS orchestrator script (Slice 89 / 90-A).

Runs on the Hostinger VPS as `jumbo-pipeline.service` alongside OpenClaw.
Polls per-user pipeline settings from the API every 60s and runs the
3-phase pipeline for any user whose schedule is due (or who hit "Run Now").

  Phase 1: POST /orchestrator/pipeline/research  (< 60s on Vercel)
  Phase 2: POST /orchestrator/pipeline/write     (< 60s on Vercel)
  Phase 3: POST /orchestrator/pipeline/qa        (< 60s on Vercel)

Environment variables required (add to /root/.openclaw/.env):
  PIPELINE_VERCEL_URL   — https://api-iota-puce.vercel.app (no trailing slash)
  PIPELINE_SECRET_KEY   — Same secret set in Vercel env var PIPELINE_SECRET_KEY

Usage:
  systemctl start jumbo-pipeline   # Start on VPS
  systemctl status jumbo-pipeline  # Check status
  journalctl -u jumbo-pipeline -f  # Follow logs
"""

from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("Missing dependencies. Install: pip3 install httpx", file=sys.stderr)
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────

VERCEL_URL = os.environ.get("PIPELINE_VERCEL_URL", "").rstrip("/")
PIPELINE_KEY = os.environ.get("PIPELINE_SECRET_KEY", "")
POLL_INTERVAL_SECONDS = 60  # Check DB settings every 60 seconds

if not VERCEL_URL:
    print("ERROR: PIPELINE_VERCEL_URL not set in environment.", file=sys.stderr)
    sys.exit(1)

if not PIPELINE_KEY:
    print("ERROR: PIPELINE_SECRET_KEY not set in environment.", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "X-Pipeline-Key": PIPELINE_KEY,
    "Content-Type": "application/json",
}

# ── Logging ───────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [jumbo-pipeline] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline_runner")


# ── Settings polling ───────────────────────────────────────────────────────


def get_pipeline_controls() -> list:
    """Fetch per-user pipeline settings from the API.

    Returns list of {user_id, enabled, run_now, interval_hours, next_run_at}.
    """
    try:
        resp = httpx.get(
            f"{VERCEL_URL}/orchestrator/pipeline/control",
            headers=HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("controls", [])
    except Exception as exc:
        logger.error("get_pipeline_controls failed: %s", exc)
        return []


def ack_run(user_id: str, interval_hours: int) -> None:
    """Tell the API a run completed so it can update last/next run times."""
    try:
        httpx.post(
            f"{VERCEL_URL}/orchestrator/pipeline/control/ack",
            json={"user_id": user_id, "interval_hours": interval_hours},
            headers=HEADERS,
            timeout=10.0,
        )
    except Exception as exc:
        logger.warning("ack_run failed for user=%s: %s", user_id, exc)


def is_due(control: dict) -> bool:
    """Return True if this user's pipeline should run now."""
    if not control.get("enabled", True):
        return False
    if control.get("run_now", False):
        return True
    next_run_at = control.get("next_run_at")
    if not next_run_at:
        return True  # Never run before — run now
    try:
        next_dt = datetime.fromisoformat(next_run_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= next_dt
    except Exception:
        return False


# ── Brand fetching ────────────────────────────────────────────────────────


def get_brands_for_user(user_id: str) -> list:
    """Fetch active brands for a specific user."""
    try:
        resp = httpx.get(
            f"{VERCEL_URL}/orchestrator/pipeline/brands",
            headers=HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()
        all_brands = resp.json().get("brands", [])
        return [b for b in all_brands if b.get("user_id") == user_id]
    except Exception as exc:
        logger.error("get_brands_for_user failed user=%s: %s", user_id, exc)
        return []


# ── Core pipeline ─────────────────────────────────────────────────────────


def run_pipeline_for_brand(user_id: str, brand_id: str, brand_name: str = "") -> bool:
    """Execute the 3-phase pipeline for one brand.

    Returns True on success, False on any phase failure.
    Each HTTP call has a 58-second timeout (just under Vercel's 60s limit).
    """
    label = brand_name or brand_id[:8]
    base = f"{VERCEL_URL}/orchestrator/pipeline"
    payload_base = {"brand_id": brand_id, "user_id": user_id}

    logger.info("Pipeline start — brand=%s", label)

    try:
        # ── Phase 1: Research ─────────────────────────────────────────────
        logger.info("  Phase 1: Research — brand=%s", label)
        r1 = httpx.post(
            f"{base}/research",
            json=payload_base,
            headers=HEADERS,
            timeout=58.0,
        )
        r1.raise_for_status()
        research_brief = r1.json().get("research_brief", "")

        if not research_brief:
            logger.warning("  Phase 1 returned empty brief — skipping brand=%s", label)
            return False

        logger.info(
            "  Phase 1 done — %d chars, %d tokens",
            len(research_brief),
            r1.json().get("tokens", 0),
        )

        # ── Phase 2: Write ────────────────────────────────────────────────
        logger.info("  Phase 2: Write — brand=%s", label)
        r2 = httpx.post(
            f"{base}/write",
            json={**payload_base, "research_brief": research_brief},
            headers=HEADERS,
            timeout=58.0,
        )
        r2.raise_for_status()
        draft = r2.json().get("draft", "")

        if not draft:
            logger.warning("  Phase 2 returned empty draft — skipping brand=%s", label)
            return False

        logger.info(
            "  Phase 2 done — %d chars, self_qa=%s",
            len(draft),
            r2.json().get("self_qa_passed"),
        )

        # ── Phase 3: QA ───────────────────────────────────────────────────
        logger.info("  Phase 3: QA — brand=%s", label)
        r3 = httpx.post(
            f"{base}/qa",
            json={**payload_base, "draft": draft},
            headers=HEADERS,
            timeout=58.0,
        )
        r3.raise_for_status()
        qa_data = r3.json()

        qa_score = qa_data.get("qa_score", 0)
        verdict = qa_data.get("verdict", "FAIL")
        deliverable_id = qa_data.get("deliverable_id")

        logger.info(
            "  Phase 3 done — score=%d verdict=%s deliverable=%s brand=%s",
            qa_score,
            verdict,
            deliverable_id,
            label,
        )

        if verdict == "PASS":
            logger.info("Pipeline SUCCESS — post queued for approval. brand=%s", label)
        else:
            logger.info(
                "Pipeline complete — post failed QA (score=%d). brand=%s",
                qa_score,
                label,
            )

        return True

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Pipeline HTTP error %d on %s for brand=%s",
            exc.response.status_code,
            exc.request.url,
            label,
        )
        return False

    except httpx.TimeoutException:
        logger.error("Pipeline timeout — brand=%s (Vercel >58s)", label)
        return False

    except Exception as exc:
        logger.error("Pipeline unexpected error brand=%s: %s", label, exc)
        return False


# ── Content plan execution ────────────────────────────────────────────────


def _update_plan_status(plan_id: str, status: str) -> None:
    """PATCH /plan/{plan_id}/status — mark plan status during/after execution."""
    try:
        httpx.patch(
            f"{VERCEL_URL}/plan/{plan_id}/status",
            json={"status": status},
            headers=HEADERS,
            timeout=10.0,
        )
    except Exception as exc:
        logger.warning("_update_plan_status failed plan=%s status=%s: %s", plan_id, status, exc)


def run_plan_item(user_id: str, brand_id: str, item: dict) -> bool:
    """Execute one planned content item through write + QA (skips Phase 1 research).

    The topic_focus is already user-approved — no research needed.
    """
    topic = item.get("topic", "")
    angle = item.get("angle", "")
    fmt = item.get("format", "post")
    label = topic[:60] if topic else "(no topic)"

    base = f"{VERCEL_URL}/orchestrator/pipeline"
    payload_base = {"brand_id": brand_id, "user_id": user_id}

    logger.info("  [PLAN] Item start — %s", label)

    try:
        # Phase 2: Write (topic_focus skips research brief; source='planned' for display)
        topic_focus = f"{topic} — {angle}".strip(" —") if angle else topic
        r2 = httpx.post(
            f"{base}/write",
            json={
                **payload_base,
                "research_brief": "",         # empty — topic_focus overrides
                "topic_focus": topic_focus[:500],
                "source": "planned",
                "format": fmt,
            },
            headers=HEADERS,
            timeout=58.0,
        )
        r2.raise_for_status()
        draft = r2.json().get("draft", "")

        if not draft:
            logger.warning("  [PLAN] Write returned empty draft — %s", label)
            return False

        # Phase 3: QA (thread source so deliverable is tagged correctly)
        r3 = httpx.post(
            f"{base}/qa",
            json={**payload_base, "draft": draft, "source": "planned"},
            headers=HEADERS,
            timeout=58.0,
        )
        r3.raise_for_status()
        qa_data = r3.json()

        logger.info(
            "  [PLAN] Item done — score=%d verdict=%s topic=%s",
            qa_data.get("qa_score", 0),
            qa_data.get("verdict", "?"),
            label,
        )
        return True

    except httpx.HTTPStatusError as exc:
        body = ""
        try:
            body = exc.response.text[:500]
        except Exception:
            pass
        logger.error("[PLAN] HTTP error %d for topic=%s body=%s", exc.response.status_code, label, body)
        return False
    except httpx.TimeoutException:
        logger.error("[PLAN] Timeout writing topic=%s", label)
        return False
    except Exception as exc:
        logger.error("[PLAN] Unexpected error topic=%s: %s", label, exc)
        return False


def run_approved_plans() -> None:
    """Fetch and execute all user-approved content plans.

    Called at the start of each poll cycle — user-planned content takes priority
    over the autonomous pipeline. Plans are executed with up to 3 parallel workers
    (one per item), so a 3-post plan completes in ~1 minute instead of ~3.
    """
    try:
        resp = httpx.get(
            f"{VERCEL_URL}/plan/approved-for-runner",
            headers=HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()
        plans = resp.json().get("plans", [])
    except Exception as exc:
        logger.error("run_approved_plans: fetch failed: %s", exc)
        return

    if not plans:
        return

    logger.info("[PLAN] %d approved plan(s) to execute", len(plans))

    for plan in plans:
        plan_id = plan.get("id", "")
        user_id = plan.get("user_id", "")
        brand_id = plan.get("brand_id", "")
        items = plan.get("items", [])

        if not (plan_id and user_id and brand_id and items):
            logger.warning("[PLAN] Skipping malformed plan=%s", plan_id)
            continue

        logger.info("[PLAN] Executing plan=%s items=%d", plan_id[:8], len(items))
        _update_plan_status(plan_id, "executing")

        try:
            with ThreadPoolExecutor(max_workers=3) as ex:
                futures = {
                    ex.submit(run_plan_item, user_id, brand_id, item): item
                    for item in items
                }
                failed = 0
                for future in as_completed(futures):
                    item = futures[future]
                    if not future.result():
                        failed += 1
                        logger.warning("[PLAN] Item failed — topic: %s", item.get("topic", "unknown"))

            final_status = "failed" if failed == len(items) else "done"
            _update_plan_status(plan_id, final_status)
            logger.info(
                "[PLAN] plan=%s %s (%d/%d succeeded)",
                plan_id[:8],
                final_status,
                len(items) - failed,
                len(items),
            )
        except Exception as exc:
            logger.error("[PLAN] plan=%s executor failed: %s", plan_id[:8], exc)
            _update_plan_status(plan_id, "failed")


def run_publish() -> None:
    """Call /cron/publish to post any approved scheduled content."""
    try:
        resp = httpx.post(
            f"{VERCEL_URL}/cron/publish",
            headers=HEADERS,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(
            "Publish run — published=%d errors=%d users=%d",
            data.get("published", 0),
            data.get("errors", 0),
            data.get("users_processed", 0),
        )
    except Exception as exc:
        logger.error("run_publish failed: %s", exc)


def run_for_user(control: dict) -> None:
    """Run the full pipeline for one user and acknowledge completion."""
    user_id = control["user_id"]
    interval_hours = control.get("interval_hours", 24)
    run_now = control.get("run_now", False)

    trigger = "run_now" if run_now else "scheduled"
    logger.info("=== User %s pipeline starting (trigger=%s) ===", user_id[:8], trigger)

    brands = get_brands_for_user(user_id)
    if not brands:
        logger.warning("No active brands for user=%s — skipping", user_id[:8])
    else:
        logger.info("Processing %d brand(s) for user=%s", len(brands), user_id[:8])
        for b in brands:
            run_pipeline_for_brand(
                user_id=b["user_id"],
                brand_id=b["brand_id"],
                brand_name=b.get("name", ""),
            )

    ack_run(user_id, interval_hours)
    logger.info("=== User %s pipeline complete ===", user_id[:8])


# ── Main poll loop ─────────────────────────────────────────────────────────


def main() -> None:
    logger.info(
        "Jumbo Pipeline Runner starting. Poll interval: %ds. Target: %s",
        POLL_INTERVAL_SECONDS,
        VERCEL_URL,
    )

    while True:
        # 1. User-planned content first (priority over autonomous pipeline)
        run_approved_plans()

        # 2. Autonomous pipeline for scheduled users
        controls = get_pipeline_controls()
        due = [c for c in controls if is_due(c)]
        if due:
            logger.info("%d user(s) due for pipeline run", len(due))
            for control in due:
                run_for_user(control)
            run_publish()
        else:
            logger.debug("No users due — sleeping %ds", POLL_INTERVAL_SECONDS)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
