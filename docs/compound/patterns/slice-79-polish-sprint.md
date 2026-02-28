# Slice 79 — Polish Sprint: Notification Bell + MC Nav + Pipeline Status + Model Fix

**Date:** 2026-02-27
**Status:** Complete
**Tests:** 1151 total (8 new) | 0 TS errors

---

## What Was Built

UX polish slice — no new features. Promoted the NotificationBell from MC dashboard-only to the global sidebar nav, unified all 7 Mission Control sub-pages to use a shared 8-tab `MC_SUB_NAV` constant, added a pipeline status endpoint for agents, and fixed a model mismatch in DEFAULT_AGENTS.

## Files Changed

| Action | File | What |
|--------|------|------|
| MODIFY | `apps/web/src/app/nav-bar.tsx` | Import + render NotificationBell in sidebar bottom section |
| MODIFY | `apps/web/src/app/mission-control/constants.ts` | Added MC_SUB_NAV (8-item shared array) |
| MODIFY | `apps/web/src/app/mission-control/goals/page.tsx` | Replaced inline 6-item SUB_NAV with MC_SUB_NAV import |
| MODIFY | `apps/web/src/app/mission-control/competitors/page.tsx` | Replaced inline 8-item SUB_NAV with MC_SUB_NAV import |
| MODIFY | `apps/web/src/app/mission-control/qa/page.tsx` | Replaced inline 8-item SUB_NAV with MC_SUB_NAV import |
| MODIFY | `apps/web/src/app/mission-control/analytics/page.tsx` | Replaced inline 5-link hardcoded nav with MC_SUB_NAV loop |
| MODIFY | `apps/web/src/app/mission-control/orchestrator/page.tsx` | Replaced inline 5-link hardcoded nav with MC_SUB_NAV loop |
| MODIFY | `apps/web/src/app/mission-control/gateway/page.tsx` | Replaced inline 5-link hardcoded nav with MC_SUB_NAV loop |
| MODIFY | `apps/web/src/app/mission-control/chat/page.tsx` | Replaced inline 5-link hardcoded nav with MC_SUB_NAV loop |
| MODIFY | `apps/api/app/routers/agent_bridge.py` | Added GET /pipeline/{workflow_id} endpoint |
| MODIFY | `apps/api/app/routers/mission_control.py` | Fixed copywriter: anthropic/claude-sonnet -> openai/gpt-4o |
| CREATE | `apps/api/tests/test_polish_sprint.py` | 8 new tests |

## Key Improvements

### 1. Notification Bell in Global Nav
Previously only visible on MC dashboard (stats-bar.tsx). Now rendered in the sidebar bottom section alongside "Sign out" — visible on every page. Uses the existing self-contained `NotificationBell` component (polls `/notifications/unread-count` every 30s, renders bell + red badge + dropdown).

### 2. MC Sub-Nav Consistency
**Before:** 3 different states across 7 sub-pages:
- Competitors + QA: 8-item inline SUB_NAV (correct)
- Goals: 6-item inline SUB_NAV (missing Competitors + QA)
- Analytics, Orchestrator, Gateway, Chat: 5-item hardcoded Links (missing Goals + Competitors + QA)

**After:** All 7 pages import `MC_SUB_NAV` from `../constants` and render it via `.map()`. Single source of truth — adding a new MC page means updating one array.

### 3. Pipeline Status Endpoint
`GET /agent-api/pipeline/{workflow_id}` — agents can now check the status of a pipeline they triggered. Returns `id`, `status`, `current_step`, `error_message`, `updated_at`. Scoped to `caller.user_id` for security.

### 4. Copywriter Model Fix
DEFAULT_AGENTS showed `anthropic / claude-sonnet-4-20250514` for the copywriter, but `openclaw.json` (the runtime config) uses `openai / gpt-4o`. Fixed to match reality. Users viewing agent profiles in MC now see the correct model info.

## Security Checks

| Check | Status |
|-------|--------|
| Pipeline status: user scoping | `.eq("user_id", caller.user_id)` |
| Pipeline status: read-only | GET only, no mutations |
| NotificationBell: auth | Uses existing JWT-based notifications API |
| MC_SUB_NAV: no secrets | Static UI constant only |
