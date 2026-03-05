# Slice 105 — Nav Clarity Sprint

**Status:** Complete
**Date:** 2026-03-05
**Sprint:** Week 2 of V1 Sprint

---

## Goal

The nav had 6 unlabelled rooms that felt like an admin control panel. Users couldn't tell what "Studio" or "Today" meant without clicking. This slice adds one-line purpose descriptions to every nav item, moves Settings out of the primary nav, and adds a live Approvals badge on Today so users know the moment agents have work waiting for them.

---

## Gap Analysis (run before build)

Three gaps found in the original proposal and corrected:

1. **"Write a post" CTA contradicts value prop** — the app's value is agents write for you. A "Write a post" button says you still write manually. Replaced with Approvals (N) badge on Today, which reinforces "agents wrote, you approve."

2. **Studio must stay visible** — Hook Library + Agent Training + Playbooks are active agent management tools, not settings. Hiding Studio in a gear dropdown would make the feedback loop invisible and unused.

3. **Settings removal from primary nav** — Settings moved to the bottom section (with Journal, Notifications, Sign Out). Freed one visual slot. Settings is admin-mode, not a daily room.

---

## Changes

### 1. Backend — `GET /pipeline/approvals/count`
**File:** `apps/api/app/routers/pipeline_settings.py`

New JWT-authenticated endpoint. Returns `{ count: number }` — the count of `agent_deliverables` rows where `user_id = caller.id` AND `status = 'review'`.

- No new table — reads from existing `agent_deliverables`
- Silent fallback: exception → `{"count": 0}` (badge just doesn't show)
- IDOR protected: filtered by `user_id` from JWT (no brand_id parameter needed)

### 2. Frontend API client
**File:** `apps/web/src/lib/api/pipeline-settings.ts`

Added `getApprovalsCount()` method to existing `pipelineSettingsApi` object.

### 3. NavBar redesign
**File:** `apps/web/src/app/nav-bar.tsx`

**PRIMARY_NAV changes:**
- Removed Settings from PRIMARY_NAV (moved to bottom)
- Added `subtitle` field to each item:
  - Today → "Approvals & briefing"
  - Brand → "Brand intelligence"
  - Create → "Content & campaigns"
  - Grow → "Leads & outreach"
  - Studio → "Agents & tools"

**Nav item render:**
- Each item now has a two-line layout: label (bold, 14px) + subtitle (10px, muted)
- Today item gets an orange badge showing `approvalCount` when > 0

**Approval count polling:**
- `useEffect` on mount: calls `getApprovalsCount()` immediately + every 60s
- Silent on error — badge just holds last value

**Bottom section:**
- Added Settings link (gear icon) above Journal
- Settings active state highlights correctly when on `/mission-control/settings`
- Journal, Notifications, Sign Out unchanged

---

## Files Changed

### Backend
- `apps/api/app/routers/pipeline_settings.py` — `GET /pipeline/approvals/count` endpoint

### Frontend
- `apps/web/src/lib/api/pipeline-settings.ts` — `getApprovalsCount()` method
- `apps/web/src/app/nav-bar.tsx` — Subtitles, Settings to bottom, Approvals badge

---

## Security (OWASP)
- **A01 IDOR:** `approvals/count` filters by `user.id` from JWT — no user can see another user's count
- **A07 Auth:** `Depends(get_current_user)` on endpoint; badge silently shows 0 if unauthenticated (safe)
- No new input parameters — no injection surface

---

## Tests
- **0 TypeScript errors** (npx tsc --noEmit)
- **30/30 pytest** passing (Slices 102 + 103 test suites)
- No new backend tests needed — endpoint is a simple count query with no business logic branch
