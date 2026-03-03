# Slice 92c — Marketing Calendar + Competitor Embed
## Marketing Room: Fully Live

**Date:** March 2026
**Status:** Completed
**Tests:** 10 new (1378 total, +10 from 1368)
**TS Errors:** 0

---

## Agent Updates (Pre-Slice)

### ICP Research Mandate — `agents/trend-analyzer/SOUL.md`
Standing instruction added: 10-layer deep ICP research protocol:
1. Surface Demographics
2. Psychographics (where most research stops)
3. The Secret Life (what they do at 11pm, what rabbit holes they fall into)
4. Exact Language — verbatim quotes from forums, Reddit, comments
5. Two Pains — surface pain + deep fear
6. The Villain — who they blame
7. Dream Identity — who they want to BECOME
8. Objection Stack — why they haven't solved it yet
9. Where They Gather — specific subreddits, Slack groups, LinkedIn groups
10. Buying Triggers — what event makes them say yes right now

### ICP Briefing — `agents/jumbo/SOUL.md`
Jumbo's "BEFORE assigning research tasks" section updated to include standing ICP mandate briefing for Trend Analyzer on every audience-related task.

### Google Trends Keyword Scoring — `agents/trend-analyzer/SOUL.md`
Standing instruction added: Real-time keyword trend scoring before every research cycle.
- Pull keywords from brand profile content pillars
- Check Google Trends via Perplexity for each keyword
- Score 1–10: `(Volume × 0.4) + (Growth Rate × 0.4) + (Seasonality × 0.2)`
- BREAKOUT queries (>500% growth): flag for immediate content
- Output: "Keyword Trend Report" table with Direction / Score / Why / Recommended Action
- Top pick highlighted for Copywriter to use as this week's lead topic

---

## What Was Built

### 1. `apps/web/src/components/marketing-calendar.tsx` (NEW)

Month-view content calendar wired to `GET /schedule/calendar`.

**Features:**
- ← / → month navigation with auto-fetch on change
- 7×N grid (Monday-first, handles 4/5/6-week months correctly)
- Per-day cells: platform emoji badges (🔵🐦📸📺🎵) + overflow count
- "Today" cell highlighted with primary color ring
- Click a day → inline expansion panel with item title + status pill
- Status pills: `draft` (muted) / `scheduled` (blue) / `published` (green)
- Loading: 35-cell pulse skeleton
- Empty state: "No content scheduled for [Month]" + "Go to Kanban →" CTA
- "View Kanban →" link at top right

**Key pattern:**
```typescript
const loadItems = useCallback(async () => {
  const start = new Date(year, month, 1).toISOString();
  const end = new Date(year, month + 1, 0, 23, 59, 59).toISOString();
  const data = await scheduleApi.getCalendar(start, end, brandId);
  // Group by day-of-month
}, [brandId, year, month]);
```

### 2. `apps/web/src/components/competitor-intel-embed.tsx` (NEW)

Inline competitor intel summary card wired to `GET /competitors/intelligence` + `GET /competitors`.

**Features:**
- Stats row: Active count / Avg threat (with colour) / Open alerts (amber if >0)
- Top 3 threats sorted by `threat_level` descending, with name + platform + 5-bar threat meter + label
- Latest alert: amber card with competitor name + detail text + relative timestamp
- Last scan time: `formatRelativeTime(latest_analysis_date)`
- Loading: skeleton cards
- Empty state (no competitors): friendly "No competitors tracked yet" + "Add your first →" link
- "Full Dashboard →" links to `/mission-control/competitors`

**Reused patterns:**
- `THREAT_LEVELS` constant from `competitors.ts` for colour mapping
- `Promise.all` for parallel fetching of feed + list

### 3. `apps/web/src/app/marketing/page.tsx` (MODIFIED)

Two targeted changes only:
- Added imports: `MarketingCalendar` + `CompetitorIntelEmbed`
- Calendar tab: replaced placeholder with `<MarketingCalendar brandId={currentBrand.id} />`
- Competitors tab: replaced placeholder with `<CompetitorIntelEmbed brandId={currentBrand.id} />`
- Both tabs: graceful "No brand selected" fallback if `currentBrand` is null

### 4. Tests — `apps/api/tests/test_slice92c_marketing_calendar.py`

10 tests across 4 classes (all file-read, no live API calls):
- `TestMarketingCalendarComponent` (3): file exists, imports scheduleApi, calls getCalendar
- `TestCompetitorIntelComponent` (3): file exists, imports competitorsApi, has Full Dashboard link
- `TestMarketingPageUpdate` (2): placeholder text removed, components imported
- `TestBackendEndpointShapes` (2): /calendar + /intelligence endpoints verified in routers

---

## No Backend Changes

Both endpoints were already 100% production-ready:
- `GET /schedule/calendar?start=X&end=Y&brand_id=Z` (schedule.py, Slice 50+)
- `GET /competitors/intelligence?brand_id=Z` (competitors.py, Slice 77)

---

## Verification Checklist

- [x] `npx tsc --noEmit` → 0 errors
- [x] `pytest tests/test_slice92c_marketing_calendar.py` → 10/10 pass
- [x] Full `pytest tests/` → 1378 passed (27 pre-existing test_resources.py failures)
- [x] Marketing → Calendar tab renders month grid
- [x] Marketing → Competitors tab renders intel embed
- [x] ICP mandate saved to trend-analyzer SOUL.md
- [x] Google Trends keyword scoring saved to trend-analyzer SOUL.md
- [x] Jumbo ICP briefing instruction saved

## App URL & Manual Test Guide
**URL:** `https://web-tau-dun-23.vercel.app/marketing`

1. Click **Calendar** tab → month grid with day cells + platform badges
2. Click any cell with content → day expansion panel shows items
3. Use ← → to navigate months
4. Click **Competitors** tab → intel card with stats + threat list (or empty state if no competitors added)
5. If empty: click "Add your first competitor →" → `/mission-control/competitors`
