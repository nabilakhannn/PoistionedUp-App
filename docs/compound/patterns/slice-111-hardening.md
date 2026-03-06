# Slice 111 — Pipeline Hardening + Client Portal Expansion

**Date:** 2026-03-05
**Status:** Complete
**Tests:** 29/29 pass, 0 TS errors

## Problem
The autonomous pipeline had zero retry logic — any transient network error caused permanent failure with no indication. Content plans marked "done" even when 2/3 items failed. Context getters had no query timeouts (could hang indefinitely). No pipeline health monitoring existed. On the client portal side, deliverables had no lifecycle tracking and the clients dashboard lacked drill-down detail pages.

## Changes

### Part A: Pipeline Hardening

| Area | File | What |
|------|------|------|
| A1 Retry | `deploy/pipeline_runner.py` | `_retry_phase()` helper: 3 retries, 30s/120s/300s backoff, 5xx + timeout only |
| A2 Partial | `pipeline_runner.py` + `content_planning.py` | `"partial"` status, per-item results, zombie 30m, idempotency guard |
| A3 Timeout | `jumbo_pipeline.py` | `_with_timeout(5s)` decorator on 8 context getters via `threading.Thread` |
| A4 Health | `pipeline.py` + `pipeline-settings.ts` | `GET /pipeline/health` (JWT), 24h success/fail counts, `PipelineHealth` interface |
| A5 Budget | `jumbo_pipeline.py` + `pipeline.py` | `"budget_check_failed:..."` structured error, pipeline proceeds with warning |

### Part B: Client Portal Expansion

| Area | File | What |
|------|------|------|
| B1 Status | migration 047 + `client_deliverables.py` + `client-deliverables.ts` + `deliverables/page.tsx` | `proposal_status` column, PATCH status + POST regenerate endpoints, status dropdown + regenerate button |
| B2 Detail | `clients/[brandId]/page.tsx` + `clients/page.tsx` | Client detail page (sessions, action items, deliverables), client name links to detail |

## Key Decisions
- **Threading for timeouts** — Supabase Python client is sync/HTTP-based. `threading.Thread` + `.join(timeout)` is the simplest approach. Daemon threads complete harmlessly in background.
- **Structured budget error** — `"budget_check_failed:..."` prefix instead of silent `None`. Pipeline router detects prefix, logs warning, proceeds. Visible in logs.
- **Partial status** — `"partial"` in content plan lifecycle: not all items failed, not all succeeded. Per-item status merged into JSONB items array.
- **Idempotency guard** — Reject `executing` update if plan is not currently `approved`. Prevents double-execution.
- **30m zombie threshold** — Increased from 10m to 30m to account for retry delays (3 retries × 5m max backoff).

## Files Changed
| # | File | Action |
|---|------|--------|
| 1 | `infra/supabase/migrations/047_slice111_hardening.sql` | CREATE |
| 2 | `apps/api/app/services/jumbo_pipeline.py` | MODIFY |
| 3 | `apps/api/app/routers/pipeline.py` | MODIFY |
| 4 | `apps/api/app/routers/content_planning.py` | MODIFY |
| 5 | `apps/api/app/routers/client_deliverables.py` | MODIFY |
| 6 | `deploy/pipeline_runner.py` | MODIFY |
| 7 | `apps/web/src/lib/api/pipeline-settings.ts` | MODIFY |
| 8 | `apps/web/src/lib/api/client-deliverables.ts` | MODIFY |
| 9 | `apps/web/src/app/deliverables/page.tsx` | MODIFY |
| 10 | `apps/web/src/app/mission-control/clients/page.tsx` | MODIFY |
| 11 | `apps/web/src/app/mission-control/clients/[brandId]/page.tsx` | CREATE |
| 12 | `apps/api/tests/test_slice111_hardening.py` | CREATE |
| 13 | `apps/api/tests/test_slice90.py` | MODIFY (updated budget check test) |

## Verification
- `pytest tests/test_slice111_hardening.py -v` → 29/29 pass
- `npx tsc --noEmit` → 0 errors
- Full suite: 1696 passed, 39 failed (all pre-existing)
