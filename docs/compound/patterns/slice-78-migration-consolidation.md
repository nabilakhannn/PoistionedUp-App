# Slice 78 — Migration Consolidation + Nav Fix

**Date:** 2026-02-27
**Status:** Complete
**Tests:** 1143 total (17 new) | 0 TS errors

---

## What Was Built

Pure correctness/infrastructure slice — no new features. Formalized 2 missing DB tables (`agent_notifications`, `agent_goals`) as migration files, added 3 missing autonomy columns to `openclaw_agents`, fixed Mission Control sidebar nav, added advisor rate limiting, fixed a column naming bug, and removed an orphaned directory.

## Files Changed

| Action | File | What |
|--------|------|------|
| CREATE | `infra/supabase/migrations/026_agent_notifications.sql` | Notifications table + RLS + 3 indexes |
| CREATE | `infra/supabase/migrations/027_agent_goals.sql` | Goals table + RLS + 2 indexes |
| CREATE | `infra/supabase/migrations/028_agent_autonomy_columns.sql` | 3 autonomy columns on openclaw_agents |
| CREATE | `apps/api/tests/test_migration_consolidation.py` | 17 new tests |
| MODIFY | `apps/web/src/app/nav-bar.tsx` | Added Competitors + QA to mcSubLinks |
| MODIFY | `apps/api/app/middleware/rate_limit.py` | Added /advisor/suggestions at TIER_LLM |
| MODIFY | `apps/api/app/routers/agent_bridge.py` | Fixed agent_id → from_agent_id (line 751) |
| DELETE | `agents/jarvis/SOUL.md` | Orphaned pre-Jumbo file |
| DELETE | `agents/jarvis/workflows/` | Orphaned directory |

## Key Issues Fixed

### 1. Missing Migration Files (Critical)
Two tables actively used by 15+ code sites had no CREATE TABLE migrations:
- `agent_notifications`: Used by notifications router, agent bridge /notify, orchestrator _create_notification(), competitor alert submissions
- `agent_goals`: Used by goals router (6 endpoints), orchestrator goal evaluation

Any fresh Supabase project or new deployment environment would silently fail when code tried to read/write these tables.

### 2. Missing Autonomy Columns
`openclaw_agents` was missing `autonomy_enabled`, `confidence_threshold`, `auto_execute` columns that `agent_orchestrator._get_agent_autonomy()` queries. Without these, the entire autonomy gating system silently returned `None`.

### 3. Nav-Bar Gap
Competitors (Slice 75) and QA (Slice 76) pages were built but never added to the sidebar nav. Users could only reach them via URL.

### 4. Advisor Rate Limit
`GET /advisor/suggestions` calls GPT-4o-mini on every request but defaulted to `TIER_READ` (200 req/min). Now at `TIER_LLM` (30 req/min).

### 5. Column Naming Bug
Competitor alert endpoint used `"agent_id"` as the insert key instead of `"from_agent_id"`, inconsistent with all other notification writes.

### 6. Orphaned Directory
`agents/jarvis/` contained the old pre-Jumbo orchestrator SOUL.md from before the rename in Slice 66.

## Security Checks

| Check | Status |
|-------|--------|
| RLS on agent_notifications | Enabled, user_id policy |
| RLS on agent_goals | Enabled, user_id policy |
| Rate limit: advisor | Now at TIER_LLM (30/min) |
| Column naming: from_agent_id | Fixed consistently |
| IF NOT EXISTS on all CREATE TABLE/ALTER | Idempotent migrations |
| Autonomy defaults | autonomy_enabled=false, auto_execute=false (safe) |
