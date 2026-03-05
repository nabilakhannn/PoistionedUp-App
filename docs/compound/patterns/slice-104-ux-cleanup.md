# Slice 104 — UX Cleanup Sprint

**Status:** Complete
**Date:** 2026-03-05
**Sprint:** Week 2 of V1 Sprint

---

## Goal

Fix 6 concrete UX issues found in a full-app audit. The app felt "too jumbled" — these fixes remove fake data, add missing guards, and align labels so every screen feels intentional.

---

## Issues Fixed

### 1. Monthly budget hardcoded to $20
**Files:** `apps/api/app/routers/pipeline_settings.py`, `apps/web/src/lib/api/pipeline-settings.ts`, `apps/web/src/app/mission-control/page.tsx`

- Backend: Added `monthly_budget_usd: float = 20.0` to `PipelineSettingsResponse`. Reads from `pipeline_settings.monthly_budget_usd` DB column (defaults to 20.0 if NULL).
- Frontend type: Added `monthly_budget_usd: number` to `PipelineSettings` interface.
- StatusBar: Replaced `const monthlyBudget = 20` with `const monthlyBudget = pipelineSettings?.monthly_budget_usd ?? 20`.

### 2. Marketing Strategy — hardcoded content pillars
**File:** `apps/web/src/app/marketing/page.tsx`

- Added `agentBridgeApi` import + `useEffect` import.
- Added state: `pillars: string[]`, `pillarsLoading: boolean`.
- On `activeSection === "strategy"` + brand change: calls `agentBridgeApi.getContext(brandId)` to get `content_pillars: string[]` (same source agents use).
- Renders: loading skeleton → real pillars from brand → empty state with "Run brand research →" CTA.

### 3. Hook Library — no brand guard
**File:** `apps/web/src/app/studio/hooks/page.tsx`

- Added early return: if `!currentBrand`, shows a centered "No brand selected" card with link to `/brands`.
- Previously: silently loaded hooks with `brand_id: undefined`, showing stale/wrong data.

### 4. Hook card Edit/Del buttons invisible on mobile
**File:** `apps/web/src/app/studio/hooks/page.tsx`

- Changed `opacity-0 group-hover:opacity-100` → `opacity-40 group-hover:opacity-100`.
- Buttons now always visible at 40% opacity (tappable on touch), full opacity on hover.

### 5. MC_SUB_NAV "Home" label inconsistency
**File:** `apps/web/src/app/mission-control/constants.ts`

- Changed `label: "Home"` → `label: "Today"` in `MC_SUB_NAV`.
- Now consistent with the Slice 103 nav rename (Today / Brand / Create / Grow / Studio / Settings).

### 6. Marketing room h1 mismatch
**File:** `apps/web/src/app/marketing/page.tsx`

- Renamed `📣 Marketing` → `📣 Create` to match the Slice 103 nav rename.

---

## Files Changed

### Backend
- `apps/api/app/routers/pipeline_settings.py` — Added `monthly_budget_usd` to `PipelineSettingsResponse` + all 3 return sites

### Frontend
- `apps/web/src/lib/api/pipeline-settings.ts` — Added `monthly_budget_usd: number` to `PipelineSettings` interface
- `apps/web/src/app/mission-control/page.tsx` — StatusBar uses API budget instead of hardcoded 20
- `apps/web/src/app/marketing/page.tsx` — Real content pillars + h1 rename
- `apps/web/src/app/studio/hooks/page.tsx` — Brand guard + Edit/Del mobile visibility
- `apps/web/src/app/mission-control/constants.ts` — MC_SUB_NAV "Home" → "Today"

---

## Security (OWASP)
- No new endpoints — no new attack surface.
- Brand context endpoint (`/agent-api/context/{brandId}`) already has IDOR protection from Slice 85.

---

## Tests
- **0 TypeScript errors** (npx tsc --noEmit)
- **30/30 pytest** passing (Slices 102 + 103 test suites)
- No new backend tests needed — all changes are either type additions or frontend-only
