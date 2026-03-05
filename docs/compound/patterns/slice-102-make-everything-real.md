# Slice 102 — Make Everything Real

**Status:** Complete
**Date:** 2026-03-05
**Sprint:** Week 1 of V1 Sprint

---

## Goal

Fix all broken feedback loops so the app actually does what it claims.
Content was generic because deep brand intelligence was never reaching the copywriter.
Rejection feedback was silently failing. QA was regex-based. Activity/analytics showed fake data.

---

## What Was Built

### Fix A: Rich Brand Context Injection
- **`tool_use_agents.py` → `_exec_fetch_brand_profile()`**: Removed `is_client_brand` gate. ALL brands now receive the full 8-section dossier: `anxiety_list`, `benefit_list`, `power_words`, `industry_lingo`, `metaphors`, `emotional_journal_summary`, `transformation_zero/dream`. Previously only `is_client_brand=True` brands got this.
- **`jumbo_pipeline.py` → `build_writing_prompt()`**: Added `brand_context` parameter. Pre-injects brand intelligence directly into the system prompt — no extra tool-call round-trip. Removed `[:3000]` truncation on research brief.
- **`jumbo_pipeline.py` → `get_brand_context()`**: New public helper that fetches brand profile + latest 3 journal entries as a dict for prompt injection.
- **`routers/pipeline.py`**: Calls `get_brand_context()` before building writing prompt, passes it in.

### Fix B: Working Rejection Feedback Loop
- **`mission-control/page.tsx` → `handleReject()`**: Now passes actual `postText` (not just deliverable ID). Content saved includes excerpt: `voice_feedback | tag: {tag} | excerpt: "{first 300 chars}"` — so `get_rejection_history()` returns useful examples.
- Removed `.catch(() => {})` — rejection save failures now surface to user via `setRunError`.
- **`agent_bridge.py` → `submit_report`**: Switched from `get_agent_caller` to `get_user_or_agent_caller` (new dual-auth dependency) so frontend JWT calls succeed.

### Fix C: LLM-Based QA Scoring
- **`tool_use_agents.py` → `_exec_score_content_quality()`**: Hybrid approach — fast rule-based check (AI tells, em dashes) + gpt-4o-mini semantic scoring (6 dimensions: voice_authenticity, hook_strength, grounding, human_feel, virality, goal_alignment). Pass threshold = avg ≥ 7.0. Cost ~$0.001/call. Graceful fallback if LLM unavailable.

### Fix D: Real Agent Activity Feed
- **`agent_bridge.py` → `GET /agent-api/activity-feed`**: Reads from `agent_ledger` table, returns human-readable entries with emoji + status. Dual-auth (JWT or X-Agent-Key).
- **`intelligence/page.tsx` → AgentsTab**: Added live activity feed panel, polls every 15s. Shows what agents actually did most recently.
- **`agent-bridge.ts`**: Added `getActivityFeed()` method.

### Fix E: Real Analytics
- **`agent_bridge.py` → `GET /agent-api/analytics-summary`**: Real data from `agent_deliverables` (posts generated/approved/rejected, avg QA), `agent_ledger` (tasks completed/failed by agent), and `agent_memory` (rejection reason breakdown). Dual-auth.
- **`analytics/page.tsx`**: Added "Content Pipeline — Real Data" section at top with actual metrics. Existing fake stats cards still show below.
- **`agent-bridge.ts`**: Added `getAnalyticsSummary()` method.

### Fix F: Hook Library
- **`infra/supabase/migrations/040_hook_library.sql`**: New `hook_library` table with `hook_type`, `hook_text`, `times_used`, `engagement_score`, `source`. RLS enforced. `increment_hook_usage()` RPC function.
- **`routers/hooks.py`**: Full CRUD (`GET/POST/PATCH/DELETE /hooks`) + `GET /hooks/for-agent` (returns formatted prompt string). IDOR protection on all mutations. `VALID_HOOK_TYPES = {anxiety, benefit, story, competitor, belief, curiosity, custom}`.
- **`jumbo_pipeline.py` → `get_hooks_for_brand()`**: Fetches hooks and formats as prompt section "## Your Hook Library".
- **`build_writing_prompt()`**: Accepts `hooks_ctx` parameter, injects before writing rules.
- **`routers/pipeline.py`**: Calls `get_hooks_for_brand()` and passes to `build_writing_prompt()`.
- **`apps/web/src/app/studio/hooks/page.tsx`**: Full Hook Library UI — filter by type, grouped grid view, inline edit, delete, "Add Hook" form. Hook type badges with colors.
- **`lib/api/hooks.ts`**: `hooksApi` client with `list/create/update/delete/getForAgent` + `HOOK_TYPE_LABELS` constants.
- **Auto-populate**: Approving a post in `mission-control/page.tsx` → opening line auto-saved as `source: "pipeline_approved"` hook.

### Fix G: Proactive Jumbo Triggers
- **`services/proactive_triggers.py`**: 7 trigger conditions checked in `get_suggestions(user_id, brand_id)`:
  1. No approved post in 48h
  2. No journal entry in 3 days
  3. Last 3 posts same hook type (question hook)
  4. Competitor threat score > 70
  5. Stale approvals > 48h old
  6. New ICP leads ≥ 3 unreviewed
  7. Avg QA score < 75 this week
  Returns max 5 suggestions sorted by priority (urgent → high → normal).
- **`agent_bridge.py` → `GET /agent-api/suggestions`**: Exposes suggestions endpoint. Dual-auth.
- **`components/jumbo-suggestions.tsx`**: Floating suggestion bubble (bottom right). Shows most urgent suggestion collapsed. Click → expanded list with dismiss per-suggestion. Polls every 5 min.
- **`app/layout.tsx`**: `<JumboSuggestions />` added inside `BrandProvider` (every page).
- **`agent-bridge.ts`**: Added `getProactiveSuggestions()` method.

### Dual Auth Dependency
- **`agent_bridge.py` → `get_user_or_agent_caller()`**: New dependency. Accepts either `X-Agent-Key` header (agents) OR `Authorization: Bearer {jwt}` (frontend). Used for: `submit_report`, `activity-feed`, `analytics-summary`, `suggestions`.

---

## Files Changed

### Backend
- `apps/api/app/services/tool_use_agents.py` — Fix A (brand profile), Fix C (QA)
- `apps/api/app/services/jumbo_pipeline.py` — Fix A (`build_writing_prompt`, `get_brand_context`, `get_hooks_for_brand`)
- `apps/api/app/routers/pipeline.py` — Fix A (pass brand_ctx, hooks_ctx)
- `apps/api/app/routers/agent_bridge.py` — Fix B (dual auth on submit_report), Fix D (activity-feed), Fix E (analytics-summary), Fix G (suggestions), new `get_user_or_agent_caller`
- `apps/api/app/routers/hooks.py` — NEW: Hook Library CRUD
- `apps/api/app/services/proactive_triggers.py` — NEW: 7 trigger conditions
- `apps/api/app/main.py` — Register hooks router
- `infra/supabase/migrations/040_hook_library.sql` — NEW

### Frontend
- `apps/web/src/app/mission-control/page.tsx` — Fix B (rejection with content, auto-save hook on approve)
- `apps/web/src/app/intelligence/page.tsx` — Fix D (activity feed panel)
- `apps/web/src/app/mission-control/analytics/page.tsx` — Fix E (real analytics section)
- `apps/web/src/app/studio/hooks/page.tsx` — NEW: Hook Library UI
- `apps/web/src/app/layout.tsx` — Fix G (add JumboSuggestions)
- `apps/web/src/components/jumbo-suggestions.tsx` — NEW: floating suggestions
- `apps/web/src/lib/api/agent-bridge.ts` — Add getActivityFeed, getAnalyticsSummary, getProactiveSuggestions
- `apps/web/src/lib/api/hooks.ts` — NEW: hooksApi client

### Tests
- `apps/api/tests/test_slice102_make_real.py` — NEW: 22 tests (all passing)

---

## Security (OWASP)

- **A01 IDOR**: All Hook Library mutations check `user_id` match. Analytics/activity enforce caller's user_id. `get_hooks_for_agent` verifies brand belongs to user.
- **A03 Injection**: `brand_id` validated with UUID regex before all DB queries. Hook text sanitized (stripped, max 1000 chars). `VALID_HOOK_TYPES` whitelist enforced.
- **A07 Auth**: `get_user_or_agent_caller` — either API key (timing-safe `hmac.compare_digest`) or validated JWT. No anonymous access to any data.

---

## Tests

- **22 new pytest tests** — all passing
- **0 TypeScript errors** (npx tsc --noEmit)
- Covers: brand profile deep intel, writing prompt injection, QA hybrid scoring, activity feed, analytics summary, hook CRUD (create/delete IDOR/list/for-agent), proactive triggers (returns list, max 5, sorted), dual auth rejection
