#!/usr/bin/env python3
"""Jumbo Pipeline Runner — VPS orchestrator script (Slice 89).

Runs on the Hostinger VPS as `jumbo-pipeline.service` alongside OpenClaw.
Calls the Vercel API endpoints sequentially every 2 hours for each active brand:

  Phase 1: POST /orchestrator/pipeline/research  (< 60s on Vercel)
  Phase 2: POST /orchestrator/pipeline/write     (< 60s on Vercel)
  Phase 3: POST /orchestrator/pipeline/qa        (< 60s on Vercel)

Each phase runs within Vercel's 60-second limit. The VPS runner chains them
with no timeout constraints. This is why we run on VPS rather than Vercel cron:
the full chain takes 3-10 minutes total.

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
from datetime import datetime, timezone

try:
    import httpx
    import schedule
except ImportError:
    print("Missing dependencies. Install: pip3 install httpx schedule", file=sys.stderr)
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────

VERCEL_URL = os.environ.get("PIPELINE_VERCEL_URL", "").rstrip("/")
PIPELINE_KEY = os.environ.get("PIPELINE_SECRET_KEY", "")
PIPELINE_INTERVAL_HOURS = int(os.environ.get("PIPELINE_INTERVAL_HOURS", "2"))

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


def get_active_brands() -> list:
    """Fetch all active brands + user IDs from the pipeline brands endpoint.

    Returns list of {"user_id": str, "brand_id": str, "name": str}.
    Falls back to empty list on error.
    """
    try:
        resp = httpx.get(
            f"{VERCEL_URL}/orchestrator/pipeline/brands",
            headers=HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        brands = []
        for b in data.get("brands", []):
            if b.get("brand_id") and b.get("user_id"):
                brands.append({
                    "brand_id": b["brand_id"],
                    "user_id": b["user_id"],
                    "name": b.get("name", ""),
                })
        return brands

    except Exception as exc:
        logger.error("get_active_brands failed: %s", exc)
        return []


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


def run_all_brands() -> None:
    """Run the pipeline for every active brand. Called by APScheduler."""
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=== Pipeline run starting — %s ===", started_at)

    brands = get_active_brands()
    if not brands:
        logger.warning("No active brands found — nothing to process")
    else:
        logger.info("Processing %d brand(s)", len(brands))
        successes = 0
        failures = 0

        for b in brands:
            ok = run_pipeline_for_brand(
                user_id=b["user_id"],
                brand_id=b["brand_id"],
                brand_name=b.get("name", ""),
            )
            if ok:
                successes += 1
            else:
                failures += 1

        logger.info(
            "=== Pipeline run complete — %d success, %d failed ===",
            successes,
            failures,
        )

    # Always publish after pipeline (posts any approved scheduled content)
    run_publish()


# ── Main loop ─────────────────────────────────────────────────────────────


def main() -> None:
    logger.info(
        "Jumbo Pipeline Runner starting. Interval: every %dh. Target: %s",
        PIPELINE_INTERVAL_HOURS,
        VERCEL_URL,
    )

    # Run immediately on startup (don't wait for first scheduled trigger)
    run_all_brands()

    # Schedule recurring runs
    schedule.every(PIPELINE_INTERVAL_HOURS).hours.do(run_all_brands)

    logger.info("Scheduler active. Next run in %dh.", PIPELINE_INTERVAL_HOURS)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
