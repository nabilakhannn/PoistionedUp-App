# Slice 90 — Marketing & Sales Command Center

**Date:** 2026-03-03
**Tests:** 25/25 new | 1333/1333 total (pre-existing test_resources.py Supabase failures excluded)
**TS errors:** 0

---

## What This Slice Does

Complete UX overhaul: replaces the confusing 20-item sidebar with 5 purposeful rooms, adds a visual
Agent Office with CSS-animated desks, and connects Marketing intelligence to Sales agents.

**Before:** 20-item nav, users couldn't find anything. 7-day strip + briefing cluttered the Home page.

**After:** 5 rooms (Command Center / Marketing / Sales / Intelligence / Settings), each a focused
hub. Home shows Agent Office + Status Bar + Approval Inbox. Marketing has a Notion-style Kanban.
Sales reads from what Marketing researched. Intelligence has a working Experience Journal.

---

## Key Patterns Applied

### 1. 5-Room Navigation (Replace Feature Flag Nav with Purposeful Rooms)
```
Command Center → daily work, approvals, agent status
Marketing      → content pipeline, calendar, ads, competitors, analytics
Sales          → newsletter, leads, outreach, sequences
Intelligence   → research, brand profile, journal, youtube clips
Settings       → connectors, pipeline, knowledge base, team & system
```
**Why:** Users get lost in feature-flag-per-page nav. Group by mental model (job to be done).

### 2. Visual Agent Office
- 8 animated CSS desks in a 2×4 grid
- Green glow + 3-dot bounce = working; grey = idle; red = error
- Speech bubble shows `agent.status_reason`, disappears after 5s
- Polls `missionControlApi.listAgents()` every 15s
- Users feel the agents are real when they can see them "at their desks"

### 3. Notion-Style Editable Kanban
- Users define their own workflow stages (add/rename/drag/delete)
- Each stage toggles Auto (assign an agent) vs Manual (human reviews)
- Default stages auto-seeded for new brands via `_ensure_defaults()`
- `content_stages` table: `position` int for ordering, `stage_type` enum, `agent_id` FK

### 4. Two-Tier Knowledge Base
```
scope='system' — app owner sets platform SOPs; ALL users inherit automatically
scope='user'   — per-brand docs that layer on top of system SOPs
```
- System docs: platform writing rules (LinkedIn, Twitter, YouTube, email format)
- User docs: custom frameworks, cold email templates, case studies
- Agent injection: system SOPs first → user docs → then write
- Users cannot edit or delete system docs (enforced by `.eq("scope", "user")` on UPDATE/DELETE)

### 5. Experience Journal → Grounded Content
```
experience_journal(user_id, brand_id, source_type, raw_content, tags, insights)
source_type: call_recording | transcript | note | case_study
```
- Users paste call transcripts, notes, and case studies
- `get_relevant_experiences()` injects the 3 most recent entries into writing prompts
- Posts become: "I was on a call last week where a client told me X..."
- Future: semantic similarity search when `embedding vector(1536)` is populated

### 6. Marketing ↔ Sales Intelligence Bridge
```
Phase 1 Research → research_briefs table
                 ↓
Sales agents read get_marketing_insights() → newsletter + outreach
```
**Before:** Research output was in-memory, lost after Phase 2 write.
**After:** `save_research_brief()` persists every successful research run to DB.
Sales newsletter and outreach agents call `get_marketing_insights()` — they know what's
trending without re-running the expensive research phase.

### 7. Monthly AI Budget Gate
```
pipeline_settings.monthly_budget_usd (default $20)
                 ↓
check_monthly_budget(user_id) → estimates current month spend from sdk_agent_runs
                 ↓
HTTP 429 if over budget (never blocks on DB errors — silent fail pattern)
```

### 8. Memory Brand Isolation Bug Fix
**Bug:** `get_trend_memory()` was fetching WITHOUT user_id filter → all brands shared the same
trend memory pool → Brand A's research affected Brand B's topics.

**Fix:** Added `_get_user_for_brand(brand_id, sb)` lookup and filter by `user_id`.

```python
# Before (BROKEN):
sb.table("agent_deliverables").select("content").eq("created_by_agent_id", "trend-analyzer").limit(1)

# After (FIXED):
user_id = _get_user_for_brand(brand_id, sb)
sb.table("agent_deliverables").eq("created_by_agent_id", "trend-analyzer").eq("user_id", user_id)
```

---

## Files Changed

| File | Change |
|------|--------|
| `infra/supabase/migrations/033_slice90.sql` | NEW — 4 tables + embedding + budget columns |
| `apps/api/app/routers/stages.py` | NEW — Kanban pipeline stage CRUD |
| `apps/api/app/routers/knowledge_docs.py` | NEW — Two-tier knowledge base CRUD |
| `apps/api/app/routers/journal.py` | NEW — Experience journal CRUD |
| `apps/api/app/services/jumbo_pipeline.py` | Bug fix + 5 new context helpers |
| `apps/api/app/routers/pipeline.py` | Budget gate + research brief save |
| `apps/api/app/main.py` | Register 3 new routers |
| `apps/api/vercel.json` | Re-added hourly cron for /cron/publish (was lost) |
| `apps/web/src/lib/api/stages.ts` | NEW — stagesApi client |
| `apps/web/src/lib/api/knowledge-docs.ts` | NEW — knowledgeDocsApi client |
| `apps/web/src/lib/api/journal.ts` | NEW — journalApi client |
| `apps/web/src/lib/api/mission-control.ts` | Added `qa_score?: number` to Deliverable type |
| `apps/web/src/components/agent-office.tsx` | NEW — CSS animated 8-agent office |
| `apps/web/src/components/content-kanban.tsx` | NEW — Notion-style Kanban |
| `apps/web/src/app/nav-bar.tsx` | Rewrite: 20 items → 5 PRIMARY_NAV rooms |
| `apps/web/src/app/page.tsx` | Root redirect → /mission-control |
| `apps/web/src/app/mission-control/page.tsx` | AgentOffice + StatusBar + Rooms grid |
| `apps/web/src/app/marketing/page.tsx` | NEW — 5-tab Marketing hub |
| `apps/web/src/app/sales/page.tsx` | NEW — 4-tab Sales hub |
| `apps/web/src/app/intelligence/page.tsx` | NEW — 4-tab Intelligence hub (Journal working) |
| `apps/web/src/app/mission-control/settings/page.tsx` | 4 tabs: Connectors/Pipeline/KB/Team |
| `apps/api/tests/test_slice90.py` | NEW — 25 tests |
| `apps/api/tests/test_slice88.py` | Updated 3 tests for Slice 90 intentional changes |

---

## Verification Results

```
npx tsc --noEmit  → 0 errors
pytest test_slice90.py → 25/25
pytest (all, excl. test_resources.py) → 1333/1333 passed
```

---

## What's Next (Slice 91)

- Nightly CEO Agent (Jumbo reviews signals, decides ONE action, executes overnight)
- UGC Video Ads (Sora/HeyGen/Runway → Meta Ads → daily monitor)
- Newsletter Engine (400-600 words → approve → Resend sends)
- Cold Email Outreach (personalized per lead → Resend → unsubscribe auto-appended)
- YouTube Research Tool (fetch_youtube_transcript → title + channel + timestamp + segment)
- Real CRM (contacts table: Cold/Warm/Hot/Customer Kanban)
- Zero-Setup Onboarding (LinkedIn URL → 60s → brand profile from YOUR real posts)
- Weekly Memory Consolidation (Jumbo condenses week → never bloated)
- Content Repurposing surfaced ([Repurpose →] on any post → 5 formats)
- Role-based access (agency: clients see only their brand)
