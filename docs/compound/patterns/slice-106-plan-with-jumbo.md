# Slice 106 — Plan with Jumbo (Content Planning Conversation)

**Status:** Complete
**Date:** 2026-03-05
**Sprint:** Week 3 of V1 Sprint

---

## Goal

The autonomous pipeline decides what to write without asking the user. Users feel like passengers. This slice adds a collaborative planning conversation: Jumbo surfaces trending opportunities, the user decides what they want, approves a plan, and Jumbo executes exactly that.

---

## User Flow

```
1. User opens Today → sees "Plan Content" section
2. Clicks "Chat with Jumbo →"
3. ContentPlanChat component loads Jumbo's opening brainstorm message
4. User responds — picks topics, specifies how many, sets angles
5. Jumbo confirms with a PLAN: section
6. Frontend parsePlan() extracts structured items → approval cards shown
7. User clicks "Approve & Create N Posts"
8. Today shows "Jumbo is writing 3 posts..." (polls status/15s)
9. Posts appear in Needs Approval when done
```

---

## Gap Analysis (run before build)

7 gaps closed before implementation:

1. **`build_writing_prompt()` with empty research_brief** → made Research Brief section conditional (only injected when non-empty — prevents hallucination when content plan skips Phase 1)
2. **VPS runner endpoints** → explicitly designed `GET /plan/approved-for-runner` with pipeline-key auth (not JWT)
3. **PLAN: format deviations** → manual fallback always available (expander with topic entry form)
4. **Empty trend_memory** → brainstorm endpoint falls back to `content_pillars` from brand context for new users
5. **Zombie plan prevention** → `last_updated_at` column + zombie detection in status endpoint (>10 min executing → treated as failed)
6. **Post-approval UX** → Today polls `plan status` every 15s, shows "Jumbo is writing…" banner until done
7. **Source tagging** → `source: 'planned'` column added to `agent_deliverables` so approval queue can distinguish plan-generated posts

---

## What Changed

### DB — `infra/supabase/migrations/041_content_plans.sql` (NEW)
- `content_plans` table: `id, user_id, brand_id, items (JSONB), status, approved_at, last_updated_at`
- Status lifecycle: `draft → approved → executing → done | failed`
- RLS: `auth.uid() = user_id`
- Indexes: by `(brand_id, status, created_at)` and `(user_id, status, approved_at)` WHERE `status='approved'`
- `ALTER TABLE agent_deliverables ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'autonomous'`

### Backend — `apps/api/app/services/jumbo_pipeline.py`
- `build_writing_prompt()` — added `topic_focus: Optional[str] = None` parameter
- When `topic_focus` is set: prepends `## PRIORITY TOPIC` section
- Research Brief section now conditional: only added when `research_brief.strip()` is non-empty

### Backend — `apps/api/app/routers/pipeline.py`
- `WriteRequest` schema: added `topic_focus: Optional[str] = None` and `source: str = "autonomous"`
- Write handler: threads `safe_topic` (capped 500 chars) through `get_relevant_experiences()` and `build_writing_prompt()`

### Backend — `apps/api/app/routers/content_planning.py` (NEW)
6 endpoints:
- `POST /plan/brainstorm` (JWT) — loads brand context + trends → Jumbo opening message
- `POST /plan/chat` (JWT) — multi-turn conversation continuation
- `POST /plan/approve` (JWT) — saves items to `content_plans` (capped at 10, topic≤300, angle≤200)
- `GET /plan/status/{plan_id}` (JWT) — polls status with zombie detection
- `GET /plan/approved-for-runner` (pipeline-key) — VPS fetches approved plans
- `PATCH /plan/{plan_id}/status` (pipeline-key) — VPS updates plan status

Security:
- IDOR: `_verify_brand_ownership()` on all user endpoints
- UUID: `_UUID_RE` validates all IDs
- Injection: text fields capped at schema level
- Pipeline key: `hmac.compare_digest`

### Backend — `apps/api/app/main.py`
- Imported and registered `content_planning.router`

### Frontend — `apps/web/src/lib/api/content-planning.ts` (NEW)
- `contentPlanningApi.brainstorm(brandId)` — opens the conversation
- `contentPlanningApi.chat(brandId, messages)` — continues the conversation
- `contentPlanningApi.approve(brandId, items)` — saves approved plan
- `contentPlanningApi.status(planId)` — polls execution status

### Frontend — `apps/web/src/components/content-plan-chat.tsx` (NEW)
Key behaviours:
- On mount: calls `brainstorm()` → shows Jumbo's opening message
- `parsePlan()`: lenient regex for `PLAN:` section, splits on `| – — -`
- When plan detected: renders approval cards + "Approve & Create N Posts" button
- Manual fallback: expandable topic entry form always available
- On approve: calls `contentPlanningApi.approve()` → calls `onApproved(planId, itemCount)`

### Frontend — `apps/web/src/app/mission-control/page.tsx`
- Added `planningOpen` + `activePlan` state
- Added 15s polling useEffect for active plan status
- Added "Plan Content" section between StatusBar and "Needs Your Approval":
  - "Chat with Jumbo →" button when idle
  - `ContentPlanChat` component when open
  - Amber "Jumbo is writing N posts..." banner when plan is executing

### VPS — `deploy/pipeline_runner.py`
- Added `run_plan_item(user_id, brand_id, item)` — executes one topic through Write + QA (skips Phase 1)
- Added `run_approved_plans()` — fetches all approved plans, marks `executing`, runs items in parallel (max 3 workers), marks `done`/`failed`
- Updated main loop: calls `run_approved_plans()` BEFORE autonomous pipeline check

---

## Files Changed

### DB
- `infra/supabase/migrations/041_content_plans.sql` — NEW

### Backend
- `apps/api/app/services/jumbo_pipeline.py` — `topic_focus` + conditional research_brief
- `apps/api/app/routers/pipeline.py` — WriteRequest schema
- `apps/api/app/routers/content_planning.py` — NEW (6 endpoints)
- `apps/api/app/main.py` — register content_planning.router

### Frontend
- `apps/web/src/lib/api/content-planning.ts` — NEW
- `apps/web/src/components/content-plan-chat.tsx` — NEW
- `apps/web/src/app/mission-control/page.tsx` — Plan Content section

### VPS
- `deploy/pipeline_runner.py` — `run_plan_item()`, `run_approved_plans()`, ThreadPoolExecutor

### Tests
- `apps/api/tests/test_slice106_content_planning.py` — NEW: 25 tests

---

## Security (OWASP)
- **A01 IDOR:** all user endpoints call `_verify_brand_ownership()` before any DB access; plan status verifies `user_id` on plan row
- **A03 Injection:** brand_id and plan_id validated as strict UUIDs; topic (≤300), angle (≤200), items (≤10) capped
- **A07 Auth:** user endpoints use `Depends(get_current_user)`; VPS endpoints use `_require_pipeline_key` + `hmac.compare_digest`

---

## Tests
- **25/25 pytest** (test_slice106_content_planning.py)
- **0 TypeScript errors** (npx tsc --noEmit)

---

## Verification
1. `python3 -m pytest tests/test_slice106_content_planning.py -v` → 25/25 pass
2. `npx tsc --noEmit` → 0 errors
3. Manual: Today → "Chat with Jumbo" → Jumbo sends brainstorm → reply with topics → plan cards → Approve → banner → posts in Needs Approval
