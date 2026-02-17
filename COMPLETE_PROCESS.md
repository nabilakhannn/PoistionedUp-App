# Content Orchestrator -- Complete Process Record

**What this is:** A single document covering everything that has been planned, decided, built, and tested from day one through Milestone 1 completion (Slices 1-4).

**Who it's for:** A non-technical product owner who wants to understand exactly what happened, what exists, what works, and what's next.

**Date:** 2026-02-12
**Status:** Milestone 1 COMPLETE. Next up: Slice 5 (Resources CRUD + Ingestion).

---

## Table of Contents

1. [What We're Building](#1-what-were-building)
2. [How We Build It (Methodology)](#2-how-we-build-it-methodology)
3. [Tech Stack](#3-tech-stack)
4. [Phase 1: ILLUMINATE + DEFINE (Understand the Problem)](#4-phase-1-illuminate--define)
5. [Phase 2: ARCHITECT (Design Everything, Build Nothing)](#5-phase-2-architect)
6. [Phase 3: SEQUENCE (Break Into Slices)](#6-phase-3-sequence)
7. [Phase 4: VALIDATE (Safety Checklists)](#7-phase-4-validate)
8. [Phase 5: FORGE -- Slice 1 (Empty House)](#8-phase-5-forge--slice-1)
9. [Phase 5: FORGE -- Slice 2 (The Vault)](#9-phase-5-forge--slice-2)
10. [Phase 5: FORGE -- Slice 3 (The Front Door)](#10-phase-5-forge--slice-3)
11. [Phase 5: FORGE -- Slice 4 (The Engine Room)](#11-phase-5-forge--slice-4)
12. [Milestone 1: What Works Today](#12-milestone-1-what-works-today)
13. [Architecture Overview](#13-architecture-overview)
14. [Database Design](#14-database-design)
15. [All 12 Decisions Made](#15-all-12-decisions-made)
16. [All Compound Patterns Saved](#16-all-compound-patterns-saved)
17. [All Bugs Hit and Fixed (Ralph Loop Log)](#17-all-bugs-hit-and-fixed)
18. [Test Results Summary](#18-test-results-summary)
19. [Security Checklist Progress](#19-security-checklist-progress)
20. [Complete File Inventory](#20-complete-file-inventory)
21. [What's Next (Slices 5-12)](#21-whats-next)
22. [v1.1 Roadmap (Brain + Poppy UI)](#22-v11-roadmap)
23. [Cost Estimates](#23-cost-estimates)
24. [How to Run Everything Locally](#24-how-to-run-everything-locally)

---

## 1. What We're Building

An AI content creation agent for YouTube creators. You tell it what kind of video you want to make, and it:

1. **Researches** what's working on YouTube right now (trends, outliers, gaps) -- across YouTube, Reddit, newsletters, news, and more
2. **Proposes 10 topics** with scores and evidence -- you pick one
3. **Generates 7 hooks** (opening lines) with scores -- you pick one
4. **Writes a complete Content Pack:**
   - Full long-form script (with story arc, case studies, timestamps)
   - 3 short-form scripts (for Shorts/Reels/TikTok)
   - 10 title options
   - Description, tags, pinned comment
   - Thumbnail brief (3 visual concepts)
5. **Edits** the scripts for voice and clarity
6. **Tests** the quality (structure, repetition, risk flags) -- PASS/FAIL report
7. **Asks for your approval** -- you approve, reject with feedback, or regenerate
8. **Exports** to Google Docs or Notion with one click

It saves everything you approve, learns from your rejections, and gets better over time.

### What makes it different

- **Not a chat tool.** It's a deterministic pipeline with save points. Every step produces a real artifact.
- **Not one-shot.** If you reject something, it regenerates from the exact step you choose -- no re-running the whole thing.
- **Quality gates.** Automated testing before you ever see the output.
- **Memory.** It remembers what you approved and rejected, and adjusts future output.
- **Your resources.** You upload your own research, notes, and reference material. The pipeline uses them.

---

## 2. How We Build It (Methodology)

Three interlocking systems:

### The RC Method (Phase Gates)

Every phase produces documents. You approve before we move on. No skipping.

```
ILLUMINATE  --> Understand the problem (read PRD, ask questions)
DEFINE      --> Lock scope and schemas
ARCHITECT   --> Design components, database, infrastructure (NO code yet)
SEQUENCE    --> Break into small build slices with acceptance criteria
VALIDATE    --> Security, UX, and cost checklists (BEFORE writing code)
FORGE       --> Build each slice one by one (this is where code lives)
CONNECT     --> Integration testing, end-to-end verification
COMPOUND    --> Extract learnings, save patterns for next time
```

### The Compound Loop (Every Slice)

Every build slice follows this cycle:

```
PLAN     --> Check existing patterns. Write what we'll build and why.
WORK     --> Write the code. Run tests. Fix bugs.
REVIEW   --> Show what changed in plain English + tests + how to verify.
COMPOUND --> Save reusable patterns to docs/compound/patterns/.
```

### The Ralph Loop (Inside WORK Only, Max 5 Tries)

When tests fail:

```
1. RUN    --> Execute the code or run tests
2. READ   --> Read the error message carefully
3. PATCH  --> Fix the specific issue
4. RERUN  --> Run again
5. After 5 failures --> STOP and ask the product owner
```

### Gate Approval Format (What You See Before Every Approval)

1. **What we did** (1-2 sentences, no jargon)
2. **What files changed** (table)
3. **What changed in behavior** (plain English)
4. **Tests run + results** (pass/fail)
5. **How to verify manually** (3 steps)
6. **Risks + mitigations**

---

## 3. Tech Stack

| Layer | Technology | Why We Chose It |
|-------|-----------|----------------|
| Frontend | Next.js 15 + Tailwind CSS | Fast, modern, server-side rendering |
| Backend | FastAPI (Python) | Async, fast, great for AI/ML work |
| Database | Supabase Postgres + RLS | Managed Postgres with auth, storage, realtime built in |
| Pipeline | LangGraph | Checkpoints + interrupts for pause/resume built in |
| Queue | Table-based polling (pgmq available for upgrade) | Postgres-native, no Redis to manage |
| Planner | Agent Zero | Sandboxed Docker container (optional in MVP) |
| Real-time | Supabase Realtime | WebSocket push for live status updates, no polling |
| Export | Google Docs API + Notion API + Clipboard | One-click export to where creators already work |

---

## 4. Phase 1: ILLUMINATE + DEFINE

### What happened
Read the full 728-line PRD. Extracted scope, data model, pipeline design, and API surface.

### What's IN for MVP
- Auth + per-user workspace
- Profile (voice, audience, guardrails)
- Resources library (upload files/links/notes, tag, search, gold-star)
- Full 8-node pipeline with 3 pause points (topic, hook, approval)
- Export to Google Docs + Notion + clipboard
- Observability + cost governance

### What's OUT for MVP (deferred)
- YouTube API publishing (export-only instead)
- Multi-seat roles/permissions
- Canvas/board UI (Poppy-style -- moved to v1.1)
- Fine-tuning a model
- Instagram/TikTok posting
- Video link ingestion (moved to v1.1)

### Result: Scope locked. Ready for architecture.

---

## 5. Phase 2: ARCHITECT

### What happened
Designed the full system architecture without writing any code. Produced 4 documents.

### Document 1: Architecture (`docs/compound/architecture.md`)

**Component diagram (how everything connects):**

```
Browser (you)
    |
    v
Next.js Dashboard (apps/web/)
    |
    | REST API calls with your login token
    v
FastAPI Server (apps/api/)
    |
    | Creates workflow row + queues job
    v
Worker Process (apps/api/worker/)
    |
    | Picks up job, runs pipeline step-by-step
    v
LangGraph Engine (8-node state machine)
    |
    | Saves checkpoint after every step
    | Pauses at 3 points for your input
    v
Supabase Postgres (all data + real-time)
    |
    | Pushes status changes to your browser instantly
    v
Back to your browser (you see "Pick a topic")
```

**Key design decisions in architecture:**
- **Async jobs:** When you click "Generate," the API creates a workflow and returns immediately. A worker picks it up in the background. No waiting.
- **Checkpoints:** LangGraph saves state to Postgres after every step. If anything crashes, it resumes from exactly where it left off.
- **Interrupts:** At 3 points (topic selection, hook selection, final approval), the pipeline pauses and waits for your input. When you submit, it continues from that exact point.
- **Agent Zero sandbox:** Runs in a Docker container with CPU/memory limits, no database access, no filesystem access. Used only for the planning step. Optional in MVP.
- **Real-time:** Supabase pushes status changes to your browser via WebSocket. No polling needed.
- **Configurable research:** You control which sources the agent searches (YouTube, Reddit, Twitter/X, TikTok, newsletters, news, competitor channels, your own resources).

### Document 2: Database Schema (`infra/supabase/migrations/001_init.sql`)
- 10 tables with full security (see Section 14)
- Row-Level Security on every table
- Indexes for fast queries
- pgmq queues for job dispatch
- Storage bucket for file uploads
- Realtime enabled for live updates

### Document 3: Local Dev Runbook (`docs/compound/runbooks/local-dev.md`)
- Prerequisites, how to start 4 services, environment variables, seed data, testing, troubleshooting

### Document 4: Export-Only Decision (`docs/compound/decisions/01-mvp-mode.md`)
- MVP is export-only (no YouTube publishing)
- Publishing adds 3-4 weeks that don't help validate the core idea
- Adding publishing later is purely additive -- zero refactoring needed

### Gate result: APPROVED

---

## 6. Phase 3: SEQUENCE

### What happened
Broke the entire build into 12 vertical slices. Each slice delivers something testable and independently valuable.

### The 12 Slices

| # | Slice | What It Delivers (Plain English) | Definition of Done |
|---|-------|----------------------------------|-------------------|
| 1 | Repo scaffold + env + CI | Empty project with folders, linting, CI | `pnpm install` works, health check OK, CI passes |
| 2 | Supabase schema + RLS | All 10 tables with security policies | 20/20 RLS tests pass |
| 3 | API: create workflow + status | Two endpoints: create and view workflows | POST creates row, GET returns only your data |
| 4 | Worker: queue + run lifecycle | Background worker picks up and processes jobs | Worker dequeues in 5s, handles crashes |
| 5 | Resources CRUD + ingestion | Upload files/links/notes, tag, search, gold | Upload PDF -> text extracted -> chunks stored |
| 6 | LangGraph pipeline + checkpoints | Real 8-node pipeline with pause/resume | Full pipeline runs with mocked LLM |
| 7 | Topic candidates UI | Dashboard shows 10 scored topics to pick | Select topic -> workflow resumes via Realtime |
| 8 | Hook lab UI | Dashboard shows 7 scored hooks to pick | Select hook -> pipeline continues |
| 9 | Script pack generation | Full Content Pack generated by AI | Long + 3 shorts + titles + all metadata |
| 10 | Editor + testing + approval | Quality gate with approve/reject/regenerate | Test report, reject with feedback, versions |
| 11 | Export (Google Docs + Notion) | One-click export | Formatted doc/page, clipboard copy |
| 12 | Observability + cost caps | Logging, cost tracking, spending limits | Usage dashboard, per-user daily caps |

### Dependency Order
```
1 --> 2 --> 3 --> 4 --> 6 --> 7 --> 8 --> 9 --> 10 --> 11
                  \--> 5 (parallel with 4)
             6 --> 12 (parallel with 7-11)
```

### Milestones

| Milestone | Slices | What It Proves | Status |
|-----------|--------|---------------|--------|
| 1. Workflow Skeleton Works | 1-4 | The plumbing works end-to-end | **COMPLETE** |
| 2. AI Pipeline Works | 5-6 | Real AI generates content | Next |
| 3. User Can Interact | 7-8 | Pick topics and hooks in the UI | After M2 |
| 4. Full Content Pack | 9-10 | Complete scripts with quality checks | After M3 |
| 5. Ship It | 11-12 | Export + observability | After M4 |

### Gate result: APPROVED

---

## 7. Phase 4: VALIDATE

### What happened
Created 4 safety checklists with concrete items to verify during and after each slice. These are living documents that get checked off as slices prove them.

### Security Checklist (14 items, 11 checked off)
- [x] RLS enabled on every table
- [x] RLS tests pass (User A can't see User B's data)
- [x] Service role key used only by backend (never exposed to frontend)
- [x] `.env` in `.gitignore` (secrets never committed)
- [x] `.env.example` has placeholder values only
- [ ] OAuth tokens encrypted, server-side only
- [x] API endpoints require JWT authentication
- [x] File uploads restricted (50MB max, allowed MIME types only)
- [x] Storage paths scoped by user_id
- [ ] Agent Zero sandboxed with resource limits
- [ ] No secrets in logs
- [x] CORS restricted to frontend origin
- [x] Input validation on all endpoints
- [x] SQL injection prevented (parameterized queries)

### UX Baseline Checklist (11 items -- all pending, verified in UI slices 7-11)
### Cost Governance Checklist (10 items -- all pending, verified in slice 12)
### Infrastructure Checklist (6 items, 4 checked off)

Full details in `docs/compound/validate-checklists.md`.

---

## 8. Phase 5: FORGE -- Slice 1 (The Empty House)

### What we did
Built the project skeleton -- folder structure, package managers, linting, CI pipeline, health check endpoint. Like building the foundation and framing of a house before adding rooms.

### What was created

| File | Purpose |
|------|---------|
| `apps/api/app/main.py` | FastAPI app with health check (`/health` returns OK) |
| `apps/api/app/config.py` | Settings (reads from .env) |
| `apps/api/requirements.txt` | Python dependencies |
| `apps/web/package.json` | Node dependencies |
| `apps/web/src/app/layout.tsx` | Root layout with Tailwind |
| `apps/web/src/app/page.tsx` | Home page (placeholder) |
| `packages/shared/schemas/*.json` | JSON schemas for Content Pack + Workflow Plan |
| `.github/workflows/ci.yml` | CI pipeline (lint + type-check on every push) |
| `.env.example` | All environment variables with comments |
| `.gitignore` | Keeps secrets and build artifacts out of git |

### Verification
- `ruff check` PASSED (Python linting)
- `GET /health` returns `{"status": "ok"}`
- `next build` PASSED (frontend builds)
- `.gitignore` includes `.env` -- VERIFIED

### Ralph loop: 2 iterations
1. Missing `autoprefixer` dependency --> added to package.json

### Compound pattern saved: `docs/compound/patterns/repo-scaffold.md`

---

## 9. Phase 5: FORGE -- Slice 2 (The Vault)

### What we did
Deployed the complete database with security policies that ensure no user can ever see another user's data. Like building a bank vault where every customer has their own safe deposit box.

### Tables created

| Table | What it stores |
|-------|---------------|
| `profiles` | Your channel name, voice style, audience, guardrails |
| `resources` | Your uploaded links, files, notes, transcripts |
| `resource_chunks` | Searchable text pieces from your resources |
| `workflows` | Each "Generate" run (status, goal, settings) |
| `workflow_snapshots` | Saved state after each pipeline step |
| `content_assets` | Generated scripts, titles, descriptions, etc. |
| `workflow_resources_used` | Which resources the AI referenced |
| `audit_events` | Log of every action (created, approved, failed) |
| `usage_costs` | Token usage and cost per step |
| `oauth_tokens` | Google/Notion connection tokens |

### What was created

| File | Purpose |
|------|---------|
| `supabase/migrations/20260212000000_init.sql` | Database schema (deployed to cloud) |
| `supabase/config.toml` | Supabase CLI config |
| `apps/api/tests/conftest.py` | Shared test fixtures |
| `apps/api/tests/test_rls.py` | 20 security tests |
| `apps/api/scripts/seed.py` | Creates sample test data |
| `docs/compound/patterns/rls.md` | Reusable security pattern |

### Verification
- `supabase db push` PASSED
- All 10 tables visible in Supabase Studio
- RLS enabled on every table
- **`pytest tests/test_rls.py` -- 20/20 PASSED** (5.15s)
- Storage bucket `resource-uploads` exists with correct MIME restrictions
- Seed script creates test data successfully

### How RLS works (plain English)
Every table has policies that check "is this YOUR data?" before allowing access:
- When you SELECT: you only see rows where `user_id` matches your login
- When you INSERT: you can only create rows that belong to you
- When you UPDATE: you can only change your own rows
- When you DELETE: you can only delete your own rows
- The worker uses a special "service-role" key that bypasses all this (so it can update any workflow). This key is NEVER exposed to the frontend.

### Ralph loop: 2 iterations
1. `uuid_generate_v4()` not available in Supabase cloud --> switched to `gen_random_uuid()` (built into Postgres 13+)

### Compound pattern saved: `docs/compound/patterns/rls.md`

---

## 10. Phase 5: FORGE -- Slice 3 (The Front Door)

### What we did
Built the API endpoints that the frontend talks to. Three endpoints let you create workflows and check their status. Every request requires a valid login token.

### Endpoints

| Method | URL | What it does |
|--------|-----|-------------|
| `POST /workflows` | Creates a new workflow (queued for processing) |
| `GET /workflows` | Lists all YOUR workflows (newest first) |
| `GET /workflows/{id}` | Gets details of one specific workflow |

### What was created

| File | Purpose |
|------|---------|
| `apps/api/app/auth.py` | JWT authentication middleware |
| `apps/api/app/deps.py` | Supabase client factory |
| `apps/api/app/routers/workflows.py` | POST + GET workflow endpoints |
| `apps/api/app/schemas/workflow.py` | Request/response validation models |
| `apps/api/tests/test_workflows.py` | 13 endpoint tests |
| `docs/compound/patterns/fastapi-auth.md` | Reusable auth pattern |

### How the auth flow works
1. Frontend signs in via Supabase Auth --> gets a login token (JWT)
2. Frontend sends `Authorization: Bearer <token>` on every API call
3. FastAPI extracts the token and asks Supabase: "Is this token valid? Who does it belong to?"
4. Supabase verifies the signature and returns the user
5. All database queries filter by that user's ID for data isolation

### How POST /workflows works
1. Validate your login token --> get your user ID
2. Fetch your profile --> capture as a "profile snapshot" (so old workflows keep their original settings)
3. Create a new workflow row (status = queued)
4. Log an audit event ("workflow created")
5. Return the new workflow ID

### Verification
- **`pytest tests/test_workflows.py` -- 13/13 PASSED** (6.55s)
- **`pytest tests/test_rls.py` -- 20/20 PASSED** (3.94s) -- no regressions
- POST without token: 401 VERIFIED
- POST with bad token: 401 VERIFIED
- GET returns only your data: VERIFIED
- GET someone else's workflow: 404 VERIFIED
- Profile snapshot captured: VERIFIED
- Audit event logged: VERIFIED
- Swagger docs at /docs: all 3 endpoints visible

### What the 13 tests prove

| Test | What it proves |
|------|---------------|
| `test_create_workflow_success` | POST with valid token creates workflow (status=queued) |
| `test_create_workflow_no_auth` | POST without token returns 401 |
| `test_create_workflow_invalid_token` | POST with garbage token returns 401 |
| `test_create_workflow_goal_too_short` | POST with goal < 10 chars returns 422 (validation) |
| `test_create_workflow_captures_profile_snapshot` | Profile data saved at creation time |
| `test_create_workflow_logs_audit_event` | Audit event row inserted |
| `test_list_workflows_returns_own` | GET returns your workflows |
| `test_list_workflows_no_auth` | GET without token returns 401 |
| `test_list_workflows_user_isolation` | User B cannot see User A's workflows |
| `test_get_workflow_detail` | GET by ID returns full workflow data |
| `test_get_workflow_not_found` | GET with fake ID returns 404 |
| `test_get_workflow_other_user_returns_404` | User B cannot access User A's workflow |
| `test_get_workflow_no_auth` | GET by ID without token returns 401 |

### Ralph loop: 4 iterations
1. Python 3.9 `str | None` syntax not supported --> switched to `Optional[str]`
2. `.env` not found (CWD mismatch) --> explicit path resolution
3. Pydantic rejects `NEXT_PUBLIC_*` vars --> `extra="ignore"` in config
4. `maybe_single()` returns None, not object --> use `.execute()` and check `.data`

### Compound pattern saved: `docs/compound/patterns/fastapi-auth.md`

---

## 11. Phase 5: FORGE -- Slice 4 (The Engine Room)

### What we did
Built the background worker that watches for new workflows and processes them automatically. Like a kitchen where orders come in and the chef works through them one at a time.

### How it works
1. Worker polls every 2 seconds: "Any new workflows?"
2. Finds the oldest `status = queued` workflow
3. Claims it using a lock (so two workers can't grab the same one)
4. Runs the pipeline step by step
5. At decision points (topic, hook, approval), pauses and waits for your input
6. If anything goes wrong, marks the workflow as "failed" with an error message

### The 8-step pipeline (currently stubs)

| Step | Name | What it will do | Pauses? |
|------|------|----------------|---------|
| 1 | Signal Research | Find what's trending | No |
| 2 | Gap Analysis | Score topic candidates | No |
| 3 | Topic Selection | **YOU pick a topic** | Yes |
| 4 | Hook Lab | Generate 7 opening hooks | Yes |
| 5 | Script Generation | Write the full Content Pack | No |
| 6 | Editor | Polish for voice and clarity | No |
| 7 | Testing | Quality check (PASS/FAIL) | No |
| 8 | Approval | **YOU approve or reject** | Yes |

Steps 1-8 are stubs right now (they simulate work with 1-second delays instead of calling the AI). The real AI gets connected in Slice 6.

### Design decision: Table-based polling (not pgmq)

pgmq is set up in the database but its functions aren't accessible via the Supabase REST API (they live in a separate schema). For MVP, we use the workflow `status` column as the queue:
- `status = 'queued'` IS the queue
- Worker polls every 2 seconds
- Atomically claims via optimistic locking (only one worker can grab a job)
- No separate enqueue step needed

**Upgrade path:** When a direct Postgres connection is configured, swap to pgmq for exactly-once delivery.

### What was created

| File | Purpose |
|------|---------|
| `apps/api/worker/queue.py` | Job claiming with optimistic locking |
| `apps/api/worker/lifecycle.py` | Status transitions + snapshot creation |
| `apps/api/worker/executor.py` | Stub pipeline (8 steps, 3 interrupt points) |
| `apps/api/worker/main.py` | Worker entry point + graceful shutdown |
| `supabase/migrations/20260212000001_queue_helpers.sql` | pgmq wrappers (for future use) |
| `apps/api/tests/test_worker.py` | 15 worker tests |
| `docs/compound/patterns/async-worker.md` | Reusable worker pattern |

### Safety features
- **Graceful shutdown:** If you stop the worker, it finishes its current job first
- **Failure handling:** Errors are caught, logged, and the workflow is marked failed (never crashes the whole system)
- **Status validation:** Prevents impossible status changes (e.g., "queued" can't jump to "approved")

### Verification
- **`pytest tests/test_worker.py` -- 15/15 PASSED** (22.95s)
- **`pytest tests/test_rls.py` -- 20/20 PASSED** (3.97s) -- no regressions
- Worker claims oldest queued workflow: VERIFIED
- Optimistic locking prevents double-claim: VERIFIED
- Invalid status transition raises error: VERIFIED
- Stub pipeline interrupts at topic_selection: VERIFIED
- Resume after interrupt continues to hook_lab: VERIFIED
- Full resume chain reaches awaiting_approval: VERIFIED
- 3 snapshots created for initial run: VERIFIED
- `mark_failed` sets status + error + audit event: VERIFIED
- SIGTERM sets shutdown flag: VERIFIED

### Ralph loop: 2 iterations
1. Stale queued workflows from previous tests --> drain queue before ordering test

### Compound pattern saved: `docs/compound/patterns/async-worker.md`

---

## 12. Milestone 1: What Works Today

### MILESTONE 1 COMPLETE: "Workflow Skeleton Works"

All 4 slices done:
- [x] Slice 1: Repo scaffold + env + CI
- [x] Slice 2: Supabase schema + RLS verified
- [x] Slice 3: API: create workflow + status
- [x] Slice 4: Worker: queue + run lifecycle

### What happens when you click Generate (today)

```
You (or the API)                    The System
     |                                   |
     | "Create a video about X"          |
     |---------------------------------->|
     |                                   | 1. Creates a workflow (status: queued)
     |                                   | 2. Saves your profile snapshot
     |                                   | 3. Logs an audit event
     |                                   |
     |                                   | [Worker polls every 2 seconds]
     |                                   |
     |                                   | 4. Worker picks up your workflow
     |                                   | 5. Changes status to "running"
     |                                   | 6. Runs Step 1: Signal Research (stub)
     |                                   | 7. Saves snapshot of Step 1 results
     |                                   | 8. Runs Step 2: Gap Analysis (stub)
     |                                   | 9. Saves snapshot of Step 2 results
     |                                   | 10. Reaches Step 3: Topic Selection
     |                                   | 11. PAUSES -- waiting for you to pick
     |                                   | 12. Status: "awaiting_topic"
     |                                   |
     | [You can see the status change]   |
     |<----------------------------------|
```

Steps 6-9 are stubs (simulated). The real AI gets wired in at Slice 6.

### We verified this works live
- Created a workflow: *"Create a video about Python async programming"*
- Worker picked it up within 2 seconds
- Ran signal_research and gap_analysis (stub)
- Paused at topic_selection (status: `awaiting_topic`)
- 3 snapshots saved (one per step)

---

## 13. Architecture Overview

### Component Diagram

```
+---------------------+
|   Browser (User)    |
+----------+----------+
           |
           | HTTPS (JWT via Supabase Auth)
           v
+----------+----------+     Supabase Realtime (WebSocket)
|  Web (Next.js)      |<-----------------------------------------+
|  apps/web/           |                                          |
|  - Dashboard         |                                          |
|  - Workflows         |                                          |
|  - Resources         |                                          |
|  - Approvals/Export  |                                          |
+----------+----------+                                          |
           |                                                      |
           | REST (Bearer JWT)                                    |
           v                                                      |
+----------+----------+                                          |
|  API (FastAPI)       |                                          |
|  apps/api/           |                                          |
|  - /workflows CRUD   |                                          |
|  - /resources CRUD   |                                          |
|  - /approve,reject   |                                          |
|  - Auth middleware    |                                          |
+----------+----------+                                          |
           |                                                      |
           v                                                      |
+----------+----------+                                          |
|  Worker Process      |                                          |
|  apps/api/worker/    |                                          |
|  - Polls every 2s    |                                          |
|  - Claims + runs     |                                          |
+----------+----------+                                          |
           |                                                      |
           v                                                      |
+----------+-----------+                                         |
| LangGraph Engine     |                                         |
| - 8 pipeline nodes   |                                         |
| - Checkpoint/resume  |                                         |
| - interrupt() x3     |                                         |
+----------+-----------+                                         |
           |                                                      |
           v                                                      |
+----------+-------------------------------------------+          |
|          Supabase Postgres (+ RLS)                   |----------+
|  profiles, resources, workflows, content_assets      | status changes
|  workflow_snapshots, audit_events, usage_costs       | trigger Realtime
+------------------------------------------------------+
```

### The 8-Node Pipeline

```
signal_research  (searches YouTube, Reddit, newsletters, news, etc.)
      |
gap_analysis_topic_candidates  (scores and ranks 10 topics)
      |
topic_selection  <-- INTERRUPT (waits for you to pick a topic)
      |
hook_lab         <-- INTERRUPT (waits for you to pick a hook)
      |
script_generation  (writes long script + 3 shorts + all metadata)
      |
editor  (refines for voice and clarity)
      |
testing  (automated quality check -- PASS/FAIL)
      |
approval  <-- INTERRUPT (waits for you to approve/reject)
```

### Data Flow for a Complete Workflow Run

| Step | Who | What happens |
|------|-----|-------------|
| 1 | You | Click "Generate" with a goal |
| 2 | API | Creates workflow (status=queued), logs audit event |
| 3 | Worker | Picks up job, sets status=running |
| 4 | Pipeline | Runs signal_research (searches configured sources) |
| 5 | Pipeline | Runs gap_analysis (generates 10 scored topic candidates) |
| 6 | Pipeline | Pauses at topic_selection |
| 7 | Worker | Sets status=awaiting_topic |
| 8 | Realtime | Pushes status to your browser instantly |
| 9 | You | Pick a topic, click Submit |
| 10 | API | Sends resume message with your choice |
| 11 | Worker | Loads checkpoint, resumes pipeline |
| 12 | Pipeline | Runs hook_lab (generates 7 scored hooks) |
| 13 | Pipeline | Pauses at hook_lab |
| 14 | You | Pick a hook, click Submit |
| 15 | Worker | Resumes, runs script_generation |
| 16 | Pipeline | Runs editor (refines for voice/clarity) |
| 17 | Pipeline | Runs testing (quality checks) |
| 18 | Pipeline | Pauses at approval |
| 19 | You | Review pack, click Approve (or Reject with feedback) |
| 20 | API | Updates assets to approved, workflow done |

### Error Handling
- **Per-node retry:** Each LLM call retries up to 2 times (exponential backoff)
- **Workflow failure:** Worker catches errors, marks workflow as "failed" with error message, preserves last checkpoint
- **Queue recovery:** If worker crashes, the job reappears after 300 seconds
- **Dead-letter queue:** After 3 failures, job moves to dead-letter queue for inspection
- **Schema validation:** Every LLM output validated against JSON schema, one auto-repair attempt on failure
- **Cost circuit breakers:** Per-step and per-workflow token ceilings prevent runaway costs

---

## 14. Database Design

### 10 Tables

| Table | Columns (key ones) | Purpose |
|-------|-------------------|---------|
| `profiles` | user_id, channel_name, voice_style, audience, guardrails | Your channel personality and rules |
| `resources` | user_id, type, title, tags, is_gold, source_url | Your uploaded research materials |
| `resource_chunks` | resource_id, chunk_text, chunk_index, token_count | Searchable text pieces from resources |
| `workflows` | user_id, status, goal_text, settings, current_step, profile_snapshot | Each "Generate" run |
| `workflow_snapshots` | workflow_id, step_name, snapshot_data | Saved state after each pipeline step |
| `content_assets` | workflow_id, asset_type, content, version, status | Generated scripts, titles, descriptions |
| `workflow_resources_used` | workflow_id, resource_id, chunk_ids, relevance_score | What resources the AI referenced |
| `audit_events` | user_id, workflow_id, event_type, details | Log of every action |
| `usage_costs` | workflow_id, step_name, model, tokens_in, tokens_out, cost_usd | Token usage and cost per step |
| `oauth_tokens` | user_id, provider, access_token, refresh_token, expires_at | Google/Notion connection tokens |

### Row-Level Security (RLS)

Every table has policies enforcing: **you can only see, create, edit, and delete YOUR data.**

- Direct ownership: `auth.uid() = user_id`
- Indirect ownership (child tables): checks through parent table (e.g., workflow_snapshots checks that the workflow belongs to you)
- Worker bypass: uses service-role key (never exposed to frontend)

### Verified by 20 automated tests
- User A cannot see User B's profiles, resources, workflows, snapshots, assets, audit events, or costs
- Unauthenticated requests return 0 rows

---

## 15. All 12 Decisions Made

| # | Decision | Why | Document |
|---|----------|-----|----------|
| 1 | Export-only MVP (no YouTube publishing) | Saves 3-4 weeks, validates core hypothesis first | `decisions/01-mvp-mode.md` |
| 2 | Google Docs + Notion export (not .zip) | Export to where creators already work | `decisions/01-mvp-mode.md` |
| 3 | Brain + Poppy UI deferred to v1.1 | Pipeline must produce good scripts before adding personality | `decisions/02-brain-v1.1.md` |
| 4 | pgmq for job queue (not Redis) | Postgres-native, no extra infrastructure | `architecture.md` |
| 5 | LangGraph for pipeline (not custom) | Checkpoints + interrupts built in | `architecture.md` |
| 6 | Agent Zero optional in MVP | Reduces complexity | `architecture.md` |
| 7 | Configurable research sources | You want control over where the agent looks | `architecture.md` |
| 8 | Outlier detection in research | Better signal than "most viewed" | `architecture.md` |
| 9 | Two-phase build (factory then brain) | Lower risk, faster to working product | `decisions/02-brain-v1.1.md` |
| 10 | Supabase Realtime for status updates | Instant via WebSocket, no polling | `architecture.md` |
| 11 | `gen_random_uuid()` for Supabase cloud | Compatibility fix (no extension needed) | `patterns/rls.md` |
| 12 | Table-based polling for MVP (not pgmq) | pgmq schema not exposed via REST API | `patterns/async-worker.md` |

---

## 16. All Compound Patterns Saved

Compound Engineering means every slice leaves behind reusable knowledge. Here's what we've captured:

| Pattern | File | Source Slice | What Future Slices Learn |
|---------|------|-------------|-------------------------|
| Methodology | `patterns/methodology.md` | Pre-build | Full RC + Compound + Ralph process |
| Repo Scaffold | `patterns/repo-scaffold.md` | Slice 1 | Project structure, package managers, folder layout |
| Row-Level Security | `patterns/rls.md` | Slice 2 | How to secure tables + test them + uuid gotcha |
| FastAPI Auth | `patterns/fastapi-auth.md` | Slice 3 | JWT auth, .env paths, Pydantic config, supabase-py gotchas |
| Async Worker | `patterns/async-worker.md` | Slice 4 | Table-based polling, optimistic locking, stub pipeline |

### Why this matters
Each slice builds on what came before and leaves knowledge behind. We never solve the same problem twice. When Slice 5 needs authentication, it uses the FastAPI Auth pattern. When Slice 6 needs database access, it uses the RLS pattern. This is what makes compound engineering work.

---

## 17. All Bugs Hit and Fixed (Ralph Loop Log)

Every test failure was tracked, fixed, and documented so we don't repeat them.

### Slice 1 (2 Ralph iterations)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `next build` fails | Missing autoprefixer peer dependency | Added `autoprefixer` to package.json |

### Slice 2 (2 Ralph iterations)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `uuid_generate_v4()` not found | Function needs `uuid-ossp` extension, not enabled on Supabase cloud | Switched to `gen_random_uuid()` (built into Postgres 13+) |

### Slice 3 (4 Ralph iterations)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `TypeError: unsupported operand type(s) for \|` | Python 3.9 doesn't support `str \| None` syntax | Use `Optional[str]` from typing module |
| All Supabase keys are empty strings | Pydantic-settings looks for `.env` in CWD (apps/api/), not project root | Explicit path resolution |
| `ValidationError: extra inputs not permitted` | `.env` has `NEXT_PUBLIC_*` vars not in Settings model | `extra="ignore"` in model_config |
| `AttributeError: 'NoneType' has no attribute 'data'` | `maybe_single()` returns None, not an object | Use `.execute()` and check `.data` list |

### Slice 4 (2 Ralph iterations)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| Test picks up stale workflow | Previous tests left workflows in queued status | Drain queue before ordering test |

**Total: 10 Ralph iterations across 4 slices. All resolved within the 5-iteration limit.**

---

## 18. Test Results Summary

| Test Suite | File | Tests | Result | Time |
|-----------|------|-------|--------|------|
| RLS Security | `tests/test_rls.py` | 20 | All pass | 3.97s |
| Workflow API | `tests/test_workflows.py` | 13 | All pass | 6.55s |
| Worker | `tests/test_worker.py` | 15 | All pass | 22.95s |
| **Total** | | **48** | **All pass** | **~33s** |

### What the tests prove
- **RLS (20 tests):** No user can see another user's data. Period. Tested across all tables.
- **API (13 tests):** Endpoints work correctly, require authentication, validate input, isolate data per user, capture profile snapshots, and log audit events.
- **Worker (15 tests):** Claims jobs correctly, prevents double-claiming, validates status transitions, runs stub pipeline with interrupts, creates snapshots, handles failures gracefully, shuts down cleanly.

---

## 19. Security Checklist Progress

| # | Item | Status | Verified In |
|---|------|--------|------------|
| 1 | RLS on every table | Done | Slice 2 |
| 2 | RLS tests pass | Done | Slice 2 |
| 3 | Service role key backend-only | Done | Slice 3 |
| 4 | .env in .gitignore | Done | Slice 1 |
| 5 | .env.example placeholder values only | Done | Slice 1 |
| 6 | OAuth tokens encrypted | Pending | Slice 11 |
| 7 | JWT auth on all endpoints | Done | Slice 3 |
| 8 | File upload restrictions | Done | Slice 2 |
| 9 | Storage paths scoped by user_id | Done | Slice 2 |
| 10 | Agent Zero sandboxed | Pending | Slice 6 |
| 11 | No secrets in logs | Pending | Slice 12 |
| 12 | CORS restricted | Done | Slice 3 |
| 13 | Input validation (Pydantic) | Done | Slice 3 |
| 14 | SQL injection prevented | Done | Slice 3 |

**11 of 14 items verified. Remaining 3 will be covered in Slices 6, 11, and 12.**

---

## 20. Complete File Inventory

### Architecture + Planning (9 files)

| File | Purpose |
|------|---------|
| `docs/compound/architecture.md` | System architecture + component diagram |
| `docs/compound/decisions/01-mvp-mode.md` | Export-only decision |
| `docs/compound/decisions/02-brain-v1.1.md` | Brain + Poppy UI roadmap |
| `docs/compound/runbooks/local-dev.md` | How to run everything locally |
| `docs/compound/plan/task-list.md` | 12 build slices with Definitions of Done |
| `docs/compound/validate-checklists.md` | Security, UX, cost, infra checklists |
| `docs/compound/patterns/methodology.md` | Full build methodology |
| `docs/compound/project-log.md` | Full engineering log |
| `docs/compound/BUILD_SUMMARY.md` | Plain-English build summary |

### Compound Patterns (5 files)

| File | Source |
|------|--------|
| `docs/compound/patterns/repo-scaffold.md` | Slice 1 |
| `docs/compound/patterns/rls.md` | Slice 2 |
| `docs/compound/patterns/fastapi-auth.md` | Slice 3 |
| `docs/compound/patterns/async-worker.md` | Slice 4 |
| `docs/compound/full-build-process.md` | Slice 3 |

### Infrastructure (3 files)

| File | Purpose |
|------|---------|
| `infra/supabase/migrations/001_init.sql` | Database schema (original reference) |
| `supabase/migrations/20260212000000_init.sql` | Database schema (deployed) |
| `supabase/migrations/20260212000001_queue_helpers.sql` | pgmq wrappers (future use) |

### Configuration (4 files)

| File | Purpose |
|------|---------|
| `.env.example` | All environment variables with comments |
| `.gitignore` | Keeps secrets out of git |
| `.github/workflows/ci.yml` | CI pipeline (lint + type-check) |
| `supabase/config.toml` | Supabase CLI config |

### Source Code -- API (10 files)

| File | Purpose |
|------|---------|
| `apps/api/app/main.py` | FastAPI app entry point + health check |
| `apps/api/app/config.py` | Settings from .env |
| `apps/api/app/auth.py` | JWT authentication middleware |
| `apps/api/app/deps.py` | Supabase client factory |
| `apps/api/app/routers/workflows.py` | POST + GET workflow endpoints |
| `apps/api/app/schemas/workflow.py` | Pydantic request/response models |
| `apps/api/worker/queue.py` | Job claiming (optimistic lock) |
| `apps/api/worker/lifecycle.py` | Status transitions + snapshots |
| `apps/api/worker/executor.py` | Stub pipeline (8 steps, 3 interrupts) |
| `apps/api/worker/main.py` | Worker entry point + signal handling |

### Source Code -- Web (3 files)

| File | Purpose |
|------|---------|
| `apps/web/src/app/layout.tsx` | Root layout with Tailwind |
| `apps/web/src/app/page.tsx` | Home page (placeholder) |
| `apps/web/package.json` | Node dependencies |

### Shared Schemas (2 files)

| File | Purpose |
|------|---------|
| `packages/shared/schemas/content_pack.schema.json` | Content Pack structure |
| `packages/shared/schemas/workflow_plan.schema.json` | Workflow plan structure |

### Tests + Scripts (4 files)

| File | Tests |
|------|-------|
| `apps/api/tests/conftest.py` | Shared test fixtures |
| `apps/api/tests/test_rls.py` | 20 security tests |
| `apps/api/tests/test_workflows.py` | 13 API tests |
| `apps/api/tests/test_worker.py` | 15 worker tests |
| `apps/api/scripts/seed.py` | Development seed data |

### Dependencies

| File | Purpose |
|------|---------|
| `apps/api/requirements.txt` | Python dependencies |
| `apps/web/tailwind.config.ts` | Tailwind configuration |
| `apps/web/tsconfig.json` | TypeScript configuration |

**Total: ~45 files across planning, infrastructure, source code, tests, and patterns.**

---

## 21. What's Next (Slices 5-12)

| # | Slice | What It Adds | Status |
|---|-------|-------------|--------|
| **5** | **Resources CRUD + Ingestion** | Upload files/links/notes, tag, search, gold-star, text extraction + chunking | **Next up** |
| 6 | LangGraph Pipeline | Replace stubs with real AI pipeline. Checkpoint to Postgres. 3 working interrupts. | Needs 4+5 |
| 7 | Topic Candidates UI | Dashboard shows 10 scored topics. Pick one. Live status updates. | Needs 6 |
| 8 | Hook Lab UI | Dashboard shows 7 scored hooks. Pick one. | Needs 7 |
| 9 | Script Pack Generation | AI writes full Content Pack (long + shorts + all metadata). | Needs 8 |
| 10 | Editor + Testing + Approval | Quality gate. Approve/reject/regenerate with feedback. Version history. | Needs 9 |
| 11 | Export | One-click to Google Docs or Notion. Clipboard copy for any asset. | Needs 10 |
| 12 | Observability + Cost Caps | Structured logging, cost tracking, usage dashboard, daily limits. | Parallel with 7-11 |

### Remaining Milestones

| Milestone | Slices | What It Proves |
|-----------|--------|---------------|
| 2. AI Pipeline Works | 5-6 | Real AI generates content with checkpoints |
| 3. User Can Interact | 7-8 | Pick topics and hooks in the UI |
| 4. Full Content Pack | 9-10 | Complete scripts with quality checks |
| 5. Ship It | 11-12 | Export + observability |

---

## 22. v1.1 Roadmap (Brain + Poppy UI)

After MVP ships, the app evolves from a "content factory" to a "content brain":

### What v1.1 adds:
1. **Video link ingestion** -- Paste YouTube/TikTok/Instagram URLs, auto-extract transcripts
2. **YouTube channel bulk import** -- Drop a channel URL, import all videos as resources
3. **Canvas/board UI** -- Poppy-style drag-and-drop workspace (not flat lists)
4. **Agent personality** -- Custom persona with opinions and visible reasoning
5. **Self-measurement** -- Tracks approval rates, preferred hook types, best-performing topics
6. **Learning loop** -- Approval/rejection patterns improve future output
7. **Proactive advisor** -- "Based on trends + your style, here are 3 video ideas for this week"

### Why after MVP (not now):
- The pipeline must produce good scripts before personality helps
- Video ingestion needs the resource system working (Slice 5)
- Learning needs data (user must approve/reject several workflows first)
- Canvas UI is a major frontend rewrite

**MVP proves:** "Can the pipeline produce scripts worth approving?"
**v1.1 proves:** "Can the agent become a trusted content strategist?"

Full details in `docs/compound/decisions/02-brain-v1.1.md`.

---

## 23. Cost Estimates

### Infrastructure (monthly)

| Service | Cost |
|---------|------|
| Supabase Pro | $25/mo |
| Hosting (Vercel + Railway) | ~$20-40/mo |
| Domain | ~$12/year |
| **Total fixed** | **~$50-70/mo** |

### Per workflow (~$0.40-0.60)

| Pipeline Step | Model | Est. Cost |
|--------------|-------|-----------|
| Signal research | GPT-4o | ~$0.06 |
| Topic candidates | GPT-4o | ~$0.12 |
| Hook lab | GPT-4o | ~$0.06 |
| Script generation | GPT-4o | ~$0.18 |
| Editor pass | GPT-4o-mini | ~$0.01 |
| Testing pass | GPT-4o-mini | ~$0.005 |

### At scale
- 10 workflows/day = ~$5-6/day in LLM costs
- 100 workflows/day = ~$50-60/day
- Per-user daily caps prevent runaway costs
- Per-step and per-workflow token ceilings as circuit breakers

---

## 24. How to Run Everything Locally

### Prerequisites
- Node.js 20.x, pnpm 9.x, Python 3.11+, Docker Desktop, Supabase CLI

### Quick Start (4 terminals)

**Terminal 1 -- Supabase:**
```bash
supabase start        # Starts local Supabase
supabase db reset     # Applies all migrations
```

**Terminal 2 -- Next.js Dashboard:**
```bash
cd apps/web && pnpm dev       # http://localhost:3000
```

**Terminal 3 -- FastAPI Server:**
```bash
cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# http://localhost:8000 (Swagger docs at /docs)
```

**Terminal 4 -- Worker:**
```bash
cd apps/api && source .venv/bin/activate && python -m worker.main
```

### Seed test data:
```bash
cd apps/api && python -m scripts.seed
```
Creates a test user (test@example.com / password123) with sample data.

### Run all tests:
```bash
cd apps/api && pytest tests/ -v
# Expected: 48/48 PASSED
```

### Environment variables
Copy `.env.example` to `.env` and fill in your Supabase keys (from `supabase start` output) and OpenAI API key.

Full details in `docs/compound/runbooks/local-dev.md`.

---

*This document was generated on 2026-02-12 after Milestone 1 completion (Slices 1-4). It will be updated as slices 5-12 are completed.*
