# Slice 112 — Analytics & ROI Dashboard

**Date:** 2026-03-05
**Status:** Complete
**Tests:** 33/33 pass, 0 TS errors

## Problem

Analytics data scattered across 5 tables (agent_deliverables, sdk_agent_runs, content_posts, leads, pipeline_settings). The existing `/mission-control/analytics` page showed mock agent-performance tables from Slice 72 era — no charts, no trends, no revenue tracking. No `deal_value` column existed for revenue attribution.

## Solution

### Part 1: Migration (`048_analytics_roi.sql`)
- Added `deal_value DECIMAL(12,2)` column to `agent_deliverables`
- Created partial index `idx_deliverables_revenue` for revenue queries

### Part 2: Backend Service (`analytics_dashboard.py` service)
6 pure aggregation functions — no DB access, easy to unit test:

| Function | Output |
|----------|--------|
| `compute_content_roi(deliverables, period_days)` | posts/day, approval rate, QA scores, daily breakdown |
| `compute_pipeline_performance(runs)` | success rate, duration, phase breakdown, daily runs |
| `compute_revenue_attribution(deliverables)` | closed_won total, proposal funnel, win rate |
| `compute_engagement_trends(posts)` | hook/topic/day performance, top posts, tier dist |
| `compute_lead_funnel(leads, period_start)` | status/BANT distribution, conversion rate |
| `compute_cost_tracking(runs, budget, total_posts)` | token costs, budget utilization, daily spend |

### Part 3: Backend Router (`analytics_dashboard.py` router)
- `GET /analytics/dashboard?brand_id=...&period=30d`
- JWT auth, UUID validation, period validation (7d/30d/90d)
- 5 parallel Supabase queries via `ThreadPoolExecutor(max_workers=5)`
- Response: `AnalyticsDashboardResponse` with 6 Pydantic sub-models

### Part 4: Deal Value Extension
- Extended `DeliverableStatusBody` with `deal_value: Optional[float]`
- Updated `PATCH /deliverables/{id}/status` to persist deal_value
- Updated `client-deliverables.ts` `updateStatus()` to accept `dealValue`
- Added deal_value input UI to deliverables page (appears on `closed_won`)

### Part 5: Frontend (`analytics/page.tsx` rewrite)
- Full Recharts ROI dashboard (first charts in the platform)
- 4 sections: Content ROI (AreaChart), Pipeline+Cost (BarChart + budget bar), Engagement (horizontal BarChart + top posts), Revenue+Leads (funnel bars)
- Period selector (7d/30d/90d), loading skeleton, error retry
- Glass Modern design system

## Architecture Decisions

- **Pure functions** — service layer has zero DB access. All 6 functions take raw data and return dicts. This makes unit testing trivial (no mocking).
- **ThreadPoolExecutor** — 5 parallel DB queries. Each thread creates its own Supabase client via `get_admin_client()`. Thread-safe (already used in `ad_creative.py` and `repurpose.py`).
- **Recharts** — React-native charting library (~45KB gzipped), tree-shakeable, dark-theme compatible. "use client" page avoids SSR issues.
- **Full page rewrite** — justified because existing analytics page used mock data from `missionControlApi`. No real data was lost.

## Gap Analysis (Pre-Build)

| Gap | Severity | Resolution |
|-----|----------|------------|
| No endpoint to SET deal_value | HIGH | Extended PATCH handler + UI |
| content_posts.brand_id missing? | FALSE POSITIVE | Migration 012 adds it |
| agent_deliverables.qa_score missing? | FALSE POSITIVE | Exists in live DB |
| ThreadPoolExecutor thread safety | LOW | Each thread gets own client |
| Analytics page loses existing data | MEDIUM | Existing data was mock |

## Files

| File | Action | Lines |
|------|--------|-------|
| `infra/supabase/migrations/048_analytics_roi.sql` | CREATE | 10 |
| `apps/api/app/services/analytics_dashboard.py` | CREATE | 371 |
| `apps/api/app/routers/analytics_dashboard.py` | CREATE | 263 |
| `apps/api/app/main.py` | MODIFY | +2 |
| `apps/api/app/routers/client_deliverables.py` | MODIFY | +5 |
| `apps/web/src/lib/api/analytics-dashboard.ts` | CREATE | 124 |
| `apps/web/src/lib/api/client-deliverables.ts` | MODIFY | +4 |
| `apps/web/src/app/mission-control/analytics/page.tsx` | REWRITE | ~340 |
| `apps/web/src/app/deliverables/page.tsx` | MODIFY | +25 |
| `apps/api/tests/test_slice112_analytics_dashboard.py` | CREATE | ~230 |

## Security (OWASP)

- **A01 IDOR:** All queries filter by `user_id` from JWT
- **A03 Injection:** UUID regex validation on `brand_id`
- **A07 Auth:** JWT required via `get_current_user` dependency
- **A09 Logging:** Warning logs on fetch failures
