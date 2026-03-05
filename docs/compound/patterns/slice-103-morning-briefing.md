# Slice 103 — Morning Briefing Home Screen

**Status:** Complete
**Date:** 2026-03-05
**Sprint:** Week 2 of V1 Sprint

---

## Goal

Transform the Mission Control home from a pipeline operations dashboard into a single "Morning Briefing" screen. User opens the app, sees one page that answers: what happened overnight, what needs me now, what's the #1 thing to do. No room-hopping required.

---

## What Was Built

### Redesign: `mission-control/page.tsx`
Complete rewrite of the home page. Same core handlers (handleApprove, handleReject, handleMarkRead, handleRunNow, handleToggle, StatusBar component) kept intact. Key changes:

**Removed from home:**
- Pipeline Funnel (5-stage StageCard row) — process view replaced by results
- AgentOffice component (8 animated desks) — stays on My Team page
- TranscriptDrop button section — accessible via Quick Capture modal

**Added new state:**
- `expandedIds: Set<string>` — tracks which approval cards have full text shown inline
- `overnight: ActivityItem[]` — from `agentBridgeApi.getActivityFeed(15)` in `loadAll()`
- `perf: AnalyticsSummary | null` — from `agentBridgeApi.getAnalyticsSummary(brandId)`, loaded on brand change
- `leadsPulse: LeadsPulse | null` — from `leadsApi.getLeadsPulse(brandId)`, loaded on brand change
- `priorities: Suggestion[]` — top 3 from `agentBridgeApi.getProactiveSuggestions(brandId)`, loaded on brand change

**New sections (order on page):**
1. **Header + StatusBar** — unchanged
2. **⚡ Needs Your Approval** — inline expand/collapse: click "▼ Show post" to expand full text in place; "▲ Collapse" to close. Approve/Reject buttons always visible.
3. **📋 Today's Priorities** — numbered list of top 3 proactive suggestions with priority dot, title, body excerpt, CTA link. Empty state: "Nothing urgent — agents are running."
4. **🤖 What Happened Overnight** — `getActivityFeed(15)` grouped by `agent_id`. Shows agent name, task count, success/fail counts, latest activity time and summary. Links to Intelligence page.
5. **📊 Leads Pulse + 📈 Performance** — side-by-side 2-column grid on wide screens (single column on mobile). Leads: new today / unreviewed / active sequences. Performance: approval rate / avg QA / top rejection reason.
6. **🔬 Latest Research** — unchanged from Slice 94.

### New Backend: `GET /leads/pulse`
**File:** `apps/api/app/routers/leads.py`

Lightweight endpoint for Morning Briefing home. Returns 3 counts:
```json
{ "new_leads": 5, "unreviewed": 3, "active_sequences": 2 }
```
- `new_leads` — leads with `created_at >= now() - 24h` for this brand
- `unreviewed` — leads with `status IN ('new', 'enriched')` (enriched but not yet actioned)
- `active_sequences` — outreach_sequences with `status = 'active'`

Security: UUID validation on `brand_id`, IDOR check (brand must belong to caller's `user_id`), `Depends(get_current_user)`.

### Frontend API: `leadsApi.getLeadsPulse(brandId)`
**File:** `apps/web/src/lib/api/leads.ts`

New method added to existing `leadsApi` object. Returns typed `{ new_leads, unreviewed, active_sequences }`.

### Nav Rename: `nav-bar.tsx`
3 `PRIMARY_NAV` label changes:
- "Home" → "Today"
- "Marketing" → "Create"
- "Sales" → "Grow"

Final nav: Today / Brand / Create / Grow / Studio / Settings

---

## Files Changed

### Backend
- `apps/api/app/routers/leads.py` — Added `GET /leads/pulse` + `datetime/timedelta` import
- `apps/api/tests/test_slice103_morning_briefing.py` — NEW: 8 tests (all passing)

### Frontend
- `apps/web/src/app/mission-control/page.tsx` — Complete rewrite as Morning Briefing
- `apps/web/src/lib/api/leads.ts` — Added `getLeadsPulse()` method
- `apps/web/src/app/nav-bar.tsx` — Renamed Home→Today, Marketing→Create, Sales→Grow

---

## Security (OWASP)
- **A01 IDOR:** `leads_pulse` verifies `personal_brands.user_id = auth user` before returning counts
- **A03 Injection:** UUID regex validation on `brand_id` before any DB query
- **A07 Auth:** `Depends(get_current_user)` on new endpoint; frontend uses authenticated `apiFetch`

---

## Tests

- **8 new pytest tests** — all passing
- **0 TypeScript errors** (npx tsc --noEmit)
- Covers: happy path, IDOR blocked (403), invalid UUID (400), zero counts, 24h cutoff logic, auth required, enriched status, active sequences filter
