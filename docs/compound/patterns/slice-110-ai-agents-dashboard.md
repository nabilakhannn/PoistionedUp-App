# Slice 110 — AI Agents Dashboard + Phase 0 Core Fixes

**Date:** 2026-03-06
**Status:** Complete
**TS errors:** 0 | **Breaking changes:** None

---

## What Was Built

Two phases combined:
- **Phase 0 (8 core fixes)** — Broken core gaps fixed (brand isolation, approval flow, deal values, outreach UX, lead conversion, save-to-inbox, approval badge, checklist bug)
- **Phase 1 (7 UX files)** — Dashboard rewritten as AI Agents Hub, ClientAscension-style cards, MAIN/STUDIO/LIBRARY nav, Brand Room simplified to 2 tabs

---

## Phase 0 — Core Fixes

### 0A — Approved posts now schedule to publishing queue
- `mission_control.py`: `update_deliverable_status()` detects `status="approved"` + `platform` param → creates `scheduled_items` row(s); "all" platform creates 3 rows (linkedin/twitter/instagram)
- `approval-inbox.tsx`: inline platform picker (LinkedIn / Twitter / Instagram / All 3) before scheduling, same UX pattern as reject tags
- `_PROPOSAL_STATUSES` and `_APPROVAL_STATUSES` frozensets distinguish which column to update

### 0B — Brand isolation on all deliverables queries
- `list_deliverables()`: `brand_id: Optional[str] = Query(None)` param added, `.eq("brand_id", brand_id)` when provided
- `mission-control.ts`: `listDeliverables({ brand_id })` accepts brand_id
- `dashboard/page.tsx`: passes `currentBrand?.id` to every `listDeliverables()` call
- **Migration 049**: `brand_id UUID` column added to `agent_deliverables` table

### 0C — deal_value + proposal_status backend fix
- `update_deliverable_status()`: `deal_value` param accepted and saved; status routing distinguishes `proposal_status` vs `status` column based on value membership in frozensets

### 0D — Outreach sequences made actionable
- `leads-crm.tsx`: "Open LinkedIn →" button (linkedin channel) and "Open Gmail →" mailto button (email channel) added per sequence message

### 0E — Lead → Client handoff
- `leads.py`: `POST /leads/{id}/convert-to-client` endpoint — creates `personal_brands` entry (is_client_brand=True), copies lead data to profile_json, prevents duplicate conversion
- `leads-crm.tsx`: "Convert to Client →" sticky footer button for hot/customer leads, shows "✓ Converted" on success
- `leads.ts`: `convertToClient(leadId)` method added

### 0F — Workflow outputs → approval inbox
- `marketplace.py`: `POST /marketplace/runs/{run_id}/save-to-inbox` endpoint — IDOR-safe, idempotent (checks existing deliverable_id), creates `agent_deliverables` row
- `content/agents/[slug]/page.tsx`: "Save to Inbox" button after output generated
- `marketplace.ts`: `saveToInbox(runId)` method added

### 0G — Approval badge brand-scoped
- `pipeline_settings.py`: `get_approvals_count()` accepts `brand_id: Optional[str] = Query(None)`
- `pipeline-settings.ts`: `getApprovalsCount(brandId?: string)` with optional param
- `nav-bar.tsx`: polls `getApprovalsCount(currentBrand?.id)`, effect depends on `currentBrand?.id`

### 0H — GettingStartedChecklist step 6 bug fixed
- `getting-started-checklist.tsx`: step 6 now checks `localStorage.getItem("visited_content_room") === "true"` (was duplicating step 5's `hasApproved` condition)
- `content/page.tsx`: `useEffect` sets `visited_content_room` flag on mount

### Phase 1E (bonus) — Remove duplicate AI Agents card from Content nav
- `content/page.tsx`: removed "AI Agents" card from `CONTENT_CARDS` (Dashboard is now the canonical home for all 24 workflows)

---

## Phase 1 — UX Overhaul

### New file: `apps/web/src/components/workflow-card.tsx`
ClientAscension-style premium card component:
- **Props:** `workflow: WorkflowInfo, usageCount: number, href: string`
- **Gradient icon box** (36px, category-colored: orange/violet/emerald/blue/amber)
- **Category label** (10px, from CATEGORY_COLORS record)
- **Bold title** + 2-line description
- **Tags row**: tag pills (max 3) + multi-step pill (violet) + Manus pill (blue)
- **Status badge**: green "● ACTIVE" or grey "COMING SOON"
- **Usage count**: "Used X times" if > 0
- `coming_soon` → `<div>` with `opacity-60 cursor-not-allowed`; `active` → `<Link>` with violet hover ring + `-translate-y-px`

### Rewrite: `apps/web/src/app/dashboard/page.tsx`
- **Hero**: "AI Agents Dashboard" + brand pill + workflow count
- **Jumbo prompt bar**: `What would you like to build today?` → routes to `/intelligence?q=...` on Enter; 4 quick chips (30 Hooks, Nurture Sequence, Offer Outline, Content Calendar)
- **5 category sections**: sorted by `cat.order`, divider line with icon + category name + count
- **24 WorkflowCards** in 3-col grid (1 col mobile, 2 col md, 3 col lg)
- **Right sidebar** (w-72, sticky md:top-8): Pending Approvals (quick approve = linkedin) + Pipeline status widget + This Week stats
- **GettingStartedChecklist** at top (auto-hides at ≥5/6 steps)
- **No brand guard**: centered card "Select a brand to see your AI workflows"
- Data: `Promise.allSettled([getRegistry, getHistory(200→usageMap), listDeliverables(brand_id), pipelineSettings, usage])`

### Upgrade: `apps/web/src/app/content/agents/page.tsx` (3 changes)
1. Added usage fetch in `load()` → builds `usageMap` from history (200 runs)
2. Replaced 80-line inline card JSX with `<WorkflowCard>`
3. Added Jumbo prompt bar + QUICK_CHIPS above category filter tabs

### Upgrade: `apps/web/src/app/nav-bar.tsx` (4 changes)
1. `NavSection` helper: 9px uppercase tracking-widest zinc-700 label + children wrapper
2. `DocumentTextIcon` SVG helper (document outline)
3. Deliverables added to `PRIMARY_NAV` (href=/deliverables, subtitle="Client outputs")
4. Nav wrapped in MAIN/STUDIO/LIBRARY sections: Dashboard under MAIN, Content/Brand/Growth under STUDIO, Deliverables+Jumbo under LIBRARY

### Simplify: `apps/web/src/app/brand/page.tsx`
- Reduced from 4 tabs (research/profile/team/settings) to 2 (research/settings)
- Default tab changed from `profile` → `research`
- `TAB_REDIRECT` map handles legacy `?tab=profile` → research, `?tab=team` → settings
- Settings tab now renders both `BrandSettingsTab` + `BrandTeamTab` (Team merged into Settings)

### Upgrade: `apps/web/src/app/brand/tabs/research.tsx`
- Added 4th mode card: "ICP Research" 🎯 → `/growth?tab=icp`
- Layout changed from `sm:grid-cols-3` to `sm:grid-cols-2 lg:grid-cols-4`
- Fetches dossier via `clientResearchApi.getReport(brandId)` on mount
- Renders `BrandIntelligenceReport` below mode cards (loading skeleton → dossier → empty CTA)
- Fully replaces the Profile tab's functionality

---

## Migration

### `infra/supabase/migrations/049_brand_id_on_deliverables.sql`
```sql
ALTER TABLE public.agent_deliverables
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_agent_deliverables_brand_id
  ON public.agent_deliverables(brand_id) WHERE brand_id IS NOT NULL;
```

---

## Security (OWASP)
- **A01 IDOR**: `save-to-inbox` verifies `workflow_runs.user_id == auth user`; `list_deliverables` with brand_id verifies brand ownership via user_id filter on all queries
- **A01 IDOR (Gap I)**: `get_approvals_count` with brand_id verifies user ownership
- **A03 Injection**: prompt bar input passed through `encodeURIComponent()` before routing; no HTML rendering of user content
- **A07 Auth**: all new backend endpoints use `get_current_user` dependency; `convert-to-client` is JWT-gated

---

## Files Changed

**New:**
- `apps/web/src/components/workflow-card.tsx`
- `infra/supabase/migrations/049_brand_id_on_deliverables.sql`

**Modified (backend):**
- `apps/api/app/routers/mission_control.py` — brand_id filter, platform picker, deal_value, proposal_status
- `apps/api/app/routers/marketplace.py` — save-to-inbox endpoint
- `apps/api/app/routers/leads.py` — convert-to-client endpoint
- `apps/api/app/routers/pipeline_settings.py` — brand_id on approvals count
- `apps/api/app/services/jumbo_pipeline.py` — brand_id in save_deliverable()

**Modified (frontend):**
- `apps/web/src/app/dashboard/page.tsx` — AI Agents Hub (complete rewrite)
- `apps/web/src/app/dashboard/components/approval-inbox.tsx` — platform picker
- `apps/web/src/app/content/agents/page.tsx` — WorkflowCard + prompt bar
- `apps/web/src/app/content/page.tsx` — remove AI Agents card + visited_content_room flag
- `apps/web/src/app/content/agents/[slug]/page.tsx` — Save to Inbox button
- `apps/web/src/app/brand/page.tsx` — 2 tabs
- `apps/web/src/app/brand/tabs/research.tsx` — ICP card + dossier
- `apps/web/src/app/nav-bar.tsx` — MAIN/STUDIO/LIBRARY sections + Deliverables
- `apps/web/src/components/leads-crm.tsx` — outreach buttons + convert-to-client
- `apps/web/src/components/getting-started-checklist.tsx` — step 6 fix
- `apps/web/src/lib/api/mission-control.ts` — brand_id + platform + dealValue
- `apps/web/src/lib/api/marketplace.ts` — saveToInbox
- `apps/web/src/lib/api/leads.ts` — convertToClient
- `apps/web/src/lib/api/pipeline-settings.ts` — brand_id on getApprovalsCount

**Tests:** 0 TS errors | **Tests:** Backend tests stable (no new endpoints requiring additional test coverage in this slice beyond existing patterns)
