# Slice 94 — Pipeline Dashboard + Research Brief Live Feed

**Date:** 2026-03-03
**Status:** Complete
**Tests:** 8/8 pass | 0 TS errors

---

## Problem

1. Mission Control home felt "dead" — Agent Office animations + static Room Shortcuts with no live data.
2. Intelligence → Research tab was a hardcoded placeholder (no data from `research_briefs` table).
3. No way to see pipeline stage counts at a glance (CRM-style funnel view).
4. Pipeline ON/OFF toggle was a read-only label — could not be clicked.
5. Run Now errors were swallowed silently.

---

## What Was Built

### Pipeline Funnel (Mission Control home)

CRM-style row of 5 `StageCard` components showing live counts:

| Stage | Data source |
|---|---|
| 🔬 Research | `pipelineSettings.run_now ? 1 : 0` |
| ✍️ Writing | `board.draft.length` |
| ✅ QA | `deliverables` with `status=qa_review` |
| 👁 Your Review | `deliverables.length` (amber border if > 0) |
| 📅 Scheduled | `board.scheduled.length` |

### Latest Research Card (Mission Control home)

Between Approval section and Agent Office. Shows:
- `brief.content` (3-line clamp)
- `timeAgo(brief.created_at)` timestamp
- "View full brief →" link to `/intelligence`

### Research Brief Live Feed (Intelligence → Research tab)

- Fetches `researchBriefsApi.getLatest(currentBrand.id)` on tab change
- If brief: full content in scrollable `<pre>` + generation timestamp + topic count
- If no brief: "Run pipeline first" CTA pointing to Command Center Run Now
- If loading: skeleton pulse

### Pipeline Toggle

`StatusBar` component — the status dot + "Pipeline:" label is now a `<button onClick={onToggle}>`. Shows spinner while toggling. Calls `pipelineSettingsApi.update({ enabled: !current })`.

### Error Visibility

`handleRunNow()` now sets `runError` state on failure → red banner visible for 6 seconds at bottom of StatusBar.

---

## Files Changed

| File | Change |
|---|---|
| `apps/api/app/routers/research.py` | Added `GET /research/briefs/latest` (UUID guard + IDOR by user_id) |
| `apps/web/src/lib/api/research-briefs.ts` | NEW — API client |
| `apps/web/src/app/intelligence/page.tsx` | Research tab: real data fetch + empty CTA |
| `apps/web/src/app/mission-control/page.tsx` | Pipeline Funnel + Research card + toggle + error feedback |
| `apps/api/tests/test_slice94_pipeline_dashboard.py` | NEW — 8 tests |
| `docs/compound/project-log.md` | Slice 94 entry added |

---

## Security

| OWASP | Check | Implementation |
|---|---|---|
| A01 IDOR | Users only see own briefs | `.eq("user_id", user.id)` on `research_briefs` query |
| A03 Injection | UUID param validated | `_UUID_RE.match(brand_id)` → 400 if invalid |
| A07 Auth | Endpoint requires JWT | `Depends(get_current_user)` on `/research/briefs/latest` |

---

## E2E Verification

1. `pytest tests/test_slice94_pipeline_dashboard.py` → 8 pass ✅
2. `npx tsc --noEmit` → 0 errors ✅
3. Mission Control home → Content Pipeline row with 5 stage cards
4. Intelligence → Research tab → shows brief if pipeline has run, CTA otherwise
5. Pipeline ON/OFF toggle → click dot/label → toggles and reloads
6. Run Now failure → red banner appears for 6s

---

## Gap Identified (Next Actions)

- Sales room (4 tabs) is UI scaffolding only — no backend data. Priority next slice.
- Intelligence → YouTube Clips tab is placeholder.
- `research_briefs` rows only exist after pipeline runs at least once.
