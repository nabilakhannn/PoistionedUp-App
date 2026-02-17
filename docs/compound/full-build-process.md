# Full Build Process -- Content Orchestrator

**What this document is:** A complete record of how this project was built from a blank repo to working software, using the RC Method + Compound Engineering + Ralph Loop methodology.

**Who it's for:** Anyone who wants to understand exactly what was done, why, and in what order -- or replicate this process on another project.

**Last updated:** 2026-02-12 after Slice 3 completion

---

## Table of Contents

1. [The Starting Point](#1-the-starting-point)
2. [Methodology Overview](#2-methodology-overview)
3. [Phase 1: ILLUMINATE + DEFINE](#3-phase-1-illuminate--define)
4. [Phase 2: ARCHITECT](#4-phase-2-architect)
5. [Phase 3: SEQUENCE](#5-phase-3-sequence)
6. [Phase 4: VALIDATE](#6-phase-4-validate)
7. [Phase 5: FORGE -- Slice 1 (Repo Scaffold)](#7-phase-5-forge----slice-1-repo-scaffold)
8. [Phase 5: FORGE -- Slice 2 (Database + Security)](#8-phase-5-forge----slice-2-database--security)
9. [Phase 5: FORGE -- Slice 3 (API Endpoints)](#9-phase-5-forge----slice-3-api-endpoints)
10. [Current State + What's Next](#10-current-state--whats-next)
11. [All Files Created](#11-all-files-created)
12. [All Decisions Made](#12-all-decisions-made)
13. [Lessons Learned (Ralph Loop Failures)](#13-lessons-learned-ralph-loop-failures)
14. [Cost Summary](#14-cost-summary)

---

## 1. The Starting Point

### What existed
- A 728-line Product Requirements Document (`Content_Orchestrator_MVP_PRD.md`)
- Two reference ZIP files (compound engineering plugin + RC method agent)
- A Supabase cloud project with API keys in `.env`
- **Zero code. Zero infrastructure. Zero database tables.**

### What we're building
An AI content creation agent for YouTube creators that:
- Researches trending topics across YouTube, Reddit, newsletters, and news
- Proposes 10 scored topic candidates (user picks one)
- Generates 7 hook options (user picks one)
- Produces a complete Content Pack: long script + 3 shorts + titles + description + tags + pinned comment + thumbnail brief
- Tests quality automatically (structure, repetition, claims, length)
- Lets the user approve, reject with feedback, or regenerate from any step
- Exports to Google Docs, Notion, or clipboard
- Remembers what works and improves over time (v1.1)

### Tech stack chosen
| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 15 + Tailwind CSS | Fast, modern, SSR for SEO if needed |
| Backend | FastAPI (Python) | Async, fast, great for AI/ML work |
| Database | Supabase Postgres + RLS | Managed Postgres with auth, storage, realtime built in |
| Pipeline | LangGraph | Checkpoints + interrupts for pause/resume built in |
| Queue | pgmq | Postgres-native, no Redis to manage |
| Planner | Agent Zero | Sandboxed Docker container (optional in MVP) |
| Real-time | Supabase Realtime | WebSocket push for live status updates |
| Export | Google Docs API + Notion API | One-click export to where creators already work |

---

## 2. Methodology Overview

Three interlocking systems govern how the project is built:

### The RC Method (Phase Gates)

Every phase produces documents/artifacts. The product owner must approve before moving on.

```
ILLUMINATE  → Read the PRD, understand the problem
DEFINE      → Lock scope, lock schemas
ARCHITECT   → Design components, database, infrastructure (no code yet)
SEQUENCE    → Break into small build slices with acceptance criteria
VALIDATE    → Security, UX, and cost checklists (before writing code)
FORGE       → Build each slice one by one (this is where code lives)
CONNECT     → Integration testing, end-to-end verification
COMPOUND    → Extract learnings, save patterns for next time
```

### The Compound Loop (Every Slice)

Every build slice (a unit of work) follows this cycle:

```
PLAN     → Check existing patterns. Write what we'll build and why.
WORK     → Write the code. Run the Ralph loop.
REVIEW   → Show what changed in plain English + tests + how to verify.
COMPOUND → Save reusable patterns to docs/compound/patterns/.
           Update project-log.md.
           Update validate-checklists.md.
```

### The Ralph Loop (Inside WORK Only)

When running code, if something fails:

```
1. RUN    → Execute the code or run tests
2. READ   → Read the error message carefully
3. PATCH  → Fix the specific issue
4. RERUN  → Run again
5. After 5 failures → STOP and ask the product owner
```

### Gate Approval Format

Before every approval, the product owner sees:

1. **What we did** (1-2 sentences, no jargon)
2. **What files changed** (table)
3. **What changed in behavior** (plain English)
4. **Tests run + results** (pass/fail)
5. **How to verify manually** (3 steps)
6. **Risks + mitigations**

---

## 3. Phase 1: ILLUMINATE + DEFINE

### What happened
Read the full 728-line PRD. Extracted:
- MVP scope (what's in, what's out)
- Data model (10 tables)
- Workflow pipeline (8 nodes, 3 human interrupts)
- API surface (13 endpoints)
- Non-negotiable architecture decisions

### Key scope decisions
**In for MVP:**
- Auth + per-user workspace
- Profile (voice, audience, guardrails)
- Resources library (upload, tag, search, gold-star)
- Full 8-node pipeline with 3 pause points
- Export to Google Docs + Notion + clipboard
- Observability + cost governance

**Out for MVP (deferred):**
- YouTube API publishing (export-only instead)
- Multi-seat roles/permissions
- Canvas/board UI (Poppy-style, moved to v1.1)
- Fine-tuning a model
- Instagram/TikTok posting

### Output
Scope locked. Ready for architecture.

---

## 4. Phase 2: ARCHITECT

### What happened
Designed the full system architecture without writing any code. Produced 4 documents:

### Artifact 1: `docs/compound/architecture.md`
- **Component diagram** showing how all pieces connect: Browser -> Next.js -> FastAPI -> Worker -> LangGraph -> Supabase
- **Async worker design:** When user clicks "Generate," the API drops a message into pgmq (Postgres-native queue). A worker process picks it up and runs the 8-step pipeline. No blocking.
- **LangGraph checkpoint strategy:** After every pipeline step, a checkpoint is saved to Postgres. At 3 points (topic, hook, approval), the pipeline pauses and waits for user input. It resumes from exactly where it left off.
- **Agent Zero sandbox:** Runs in Docker with CPU/memory limits, no database access, no host filesystem. Used only for the planning step. Optional in MVP.
- **Real-time updates:** Supabase Realtime pushes status changes to the browser over WebSocket. No polling.
- **Error handling:** 2 retries per LLM call, graceful failure with checkpoint preserved, dead-letter queue after 3 failures.

### Artifact 2: `infra/supabase/migrations/001_init.sql`
- **10 tables:** profiles, resources, resource_chunks, workflows, workflow_snapshots, content_assets, workflow_resources_used, audit_events, usage_costs, oauth_tokens
- **Row-Level Security:** Every table locked down. User A can never see User B's data. Worker uses service-role key (never exposed to frontend).
- **Indexes** for fast queries (by user, by status, by date, by tags)
- **pgmq queues** for job dispatch (workflow_jobs + dead-letter queue)
- **Storage bucket** for file uploads (50MB limit, PDF/DOCX/TXT/MD/CSV only)
- **Realtime enabled** on workflows table for live status updates

### Artifact 3: `docs/compound/runbooks/local-dev.md`
- Prerequisites: Node 20, Python 3.11+, Docker, Supabase CLI
- How to start all 4 services (web, API, worker, optional Agent Zero)
- All environment variables needed
- How to seed test data
- How to run tests
- Troubleshooting table

### Artifact 4: `docs/compound/decisions/01-mvp-mode.md`
- **Decision:** MVP is export-only (no YouTube API publishing)
- **Why:** Publishing adds 3-4 weeks and doesn't help validate the core hypothesis
- **What we build instead:** Google Docs export, Notion export, clipboard copy
- **Reversibility:** Adding publishing later is purely additive, zero refactoring

### Gate result: APPROVED

---

## 5. Phase 3: SEQUENCE

### What happened
Broke the entire build into 12 vertical slices. Each slice delivers something testable.

### The 12 slices

| # | Slice | What It Delivers | Definition of Done |
|---|-------|-----------------|-------------------|
| 1 | Repo scaffold + env + CI | Empty project with folders, linting, CI | `pnpm install` works, health check returns OK |
| 2 | Supabase schema + RLS | All 10 tables with security policies | 20/20 RLS tests pass |
| 3 | API: create workflow + status | Two endpoints: create and view workflows | POST creates row, GET returns only your data |
| 4 | Worker: queue + run lifecycle | Background worker picks up jobs | Worker dequeues in 5s, transitions status |
| 5 | Resources CRUD + ingestion | Upload files, tag, search, gold-star | Upload PDF -> text extracted -> chunks stored |
| 6 | LangGraph pipeline + checkpoints | Real 8-node pipeline with pause/resume | Full pipeline runs end-to-end with mocked LLM |
| 7 | Topic candidates UI | Dashboard shows 10 scored topics | Select topic -> workflow resumes via Realtime |
| 8 | Hook lab UI | Dashboard shows 7 scored hooks | Select hook -> pipeline continues |
| 9 | Script pack generation | Full Content Pack generated | Long + 3 shorts + all metadata created |
| 10 | Editor + testing + approval | Quality gate with approve/reject | Test report PASS/FAIL, reject with feedback |
| 11 | Export pack | Google Docs + Notion + clipboard | One-click export creates formatted doc/page |
| 12 | Observability + cost caps | Logging, cost tracking, rate limits | Usage dashboard, per-user daily caps |

### Dependency order
```
1 -> 2 -> 3 -> 4 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11
               \-> 5 (parallel with 4)
          6 -> 12 (parallel with 7-11)
```

### Milestone 1: "Workflow Skeleton Works" (Slices 1-4)
After these 4 slices: click Generate -> workflow row appears -> worker picks it up -> status updates live. No fancy scripts yet -- just the pipeline plumbing.

### Gate result: APPROVED

---

## 6. Phase 4: VALIDATE

### What happened
Created 4 checklists with concrete items to verify during and after each slice. These are living documents -- items get checked off as slices prove them.

### Security Checklist (14 items)
Covers: RLS on every table, service role key isolation, .env in .gitignore, OAuth token security, JWT auth on all endpoints, file upload restrictions, storage path scoping, Agent Zero sandboxing, no secrets in logs, CORS restrictions, input validation, SQL injection prevention.

### UX Baseline Checklist (11 items)
Covers: Real-time status updates <2s, loading states, human-readable errors, workflow abandonment safety, topic/hook UI quality, reject flow, version history, export, desktop-first.

### Cost Governance Checklist (10 items)
Covers: Per-step token ceiling, per-workflow ceiling, per-user daily cap, usage tracking, cost visibility, model selection, no runaway loops, visibility timeout, dead-letter queue.

### Infrastructure Checklist (6 items)
Covers: Local development, idempotent migrations, CI pipeline, health check, env documentation, no hardcoded secrets.

### Output: `docs/compound/validate-checklists.md`

---

## 7. Phase 5: FORGE -- Slice 1 (Repo Scaffold)

### Compound Loop: PLAN
Reviewed the task-list Definition of Done. No existing patterns to check (first slice).

### Compound Loop: WORK

**What was built:**
- FastAPI app with health check (`apps/api/app/main.py`)
- Settings from environment (`apps/api/app/config.py`)
- Next.js 15 + Tailwind CSS scaffold (`apps/web/`)
- Python dependencies (`apps/api/requirements.txt`)
- Node dependencies (`apps/web/package.json`)
- JSON schemas for workflow plan + content pack (`packages/shared/schemas/`)
- GitHub Actions CI pipeline (`.github/workflows/ci.yml`)
- `.gitignore` (excludes .env, node_modules, __pycache__, .venv)
- `.env.example` (all required variables with comments)

**Ralph loop: 2 iterations**
1. Missing `autoprefixer` dependency -> added to package.json

### Compound Loop: REVIEW

**Verification:**
- `ruff check` PASSED
- `GET /health` returns `{"status":"ok"}` VERIFIED
- `next build` PASSED
- `.gitignore` includes `.env` VERIFIED

**Validate checklist items checked off (4):**
- .env in .gitignore
- .env.example has placeholder values only
- CI pipeline catches errors
- Health check endpoint exists

### Compound Loop: COMPOUND

**Pattern saved:** `docs/compound/patterns/repo-scaffold.md`
- Project structure (monorepo with apps/web, apps/api, packages/shared)
- Package managers (pnpm for Node, uv for Python)
- Folder layout conventions

---

## 8. Phase 5: FORGE -- Slice 2 (Database + Security)

### Compound Loop: PLAN
Reviewed repo-scaffold pattern. Goal: deploy the full database schema to Supabase cloud and prove that Row-Level Security works.

### Compound Loop: WORK

**What was built:**
- Supabase CLI installed (v2.75.0) and linked to cloud project
- Migration pushed to cloud: 10 tables + RLS policies + pgmq queues + storage bucket + Realtime publication
- 20 RLS verification tests (`apps/api/tests/test_rls.py`)
- Seed script (`apps/api/scripts/seed.py`) -- creates test user with full sample data
- Test fixtures (`apps/api/tests/conftest.py`) -- shared Supabase client setup

**Ralph loop: 2 iterations**
1. `uuid_generate_v4()` not available in Supabase cloud -> switched to `gen_random_uuid()` (built into Postgres 13+)

### Compound Loop: REVIEW

**Test results:**
- `pytest tests/test_rls.py` **20/20 PASSED** (5.15s)
- Tests create two users and verify that User A cannot see User B's data across profiles, resources, resource_chunks, workflows, workflow_snapshots, content_assets, audit_events, and usage_costs
- Unauthenticated requests return 0 rows

**Verification:**
- `supabase db push` PASSED
- All 10 tables visible in Supabase Studio
- RLS enabled on every table
- Storage bucket `resource-uploads` exists with correct MIME restrictions
- pgmq queues exist
- Seed script creates test data successfully

**Validate checklist items checked off (4 new, 8 total):**
- RLS enabled on every table
- RLS tests pass (User A can't see User B)
- File uploads restricted (50MB, allowed MIME types)
- Storage paths scoped by user_id
- Migrations are idempotent
- Environment variables documented

### Compound Loop: COMPOUND

**Pattern saved:** `docs/compound/patterns/rls.md`
- How to write RLS policies for Supabase
- The `gen_random_uuid()` vs `uuid_generate_v4()` gotcha
- How to test RLS with two test users
- Junction table RLS (access via parent ownership)

---

## 9. Phase 5: FORGE -- Slice 3 (API Endpoints)

### Compound Loop: PLAN
Reviewed repo-scaffold and rls patterns. Goal: build JWT-authenticated endpoints to create and view workflows. Establish the FastAPI project structure (routers, dependencies, auth middleware, Pydantic schemas).

### Compound Loop: WORK

**What was built:**

| File | Purpose |
|------|---------|
| `apps/api/app/auth.py` | JWT authentication -- extracts user from `Authorization: Bearer <token>` header, validates via Supabase `auth.get_user(token)` |
| `apps/api/app/deps.py` | Dependency injection -- factory for Supabase admin client (service-role key, bypasses RLS) |
| `apps/api/app/routers/workflows.py` | Three endpoints: POST /workflows (create), GET /workflows (list yours), GET /workflows/{id} (detail) |
| `apps/api/app/schemas/workflow.py` | Pydantic models: WorkflowCreate (request), WorkflowSummary (list response), WorkflowDetail (detail response), WorkflowCreated (creation response) |
| `apps/api/app/main.py` | Modified to register the workflow router |
| `apps/api/app/config.py` | Modified to fix .env path resolution, allow extra env vars, Python 3.9 compatibility |
| `apps/api/tests/test_workflows.py` | 13 tests covering all endpoints and edge cases |

**How the auth flow works:**
1. Frontend signs in via Supabase Auth SDK -> gets a JWT (access_token)
2. Frontend sends `Authorization: Bearer <token>` on every API request
3. FastAPI `get_current_user` dependency extracts the token
4. Calls `admin.auth.get_user(token)` which verifies the JWT signature
5. Returns `CurrentUser(id=..., email=...)` for downstream use
6. All database queries filter by `user_id` for data isolation

**How POST /workflows works:**
1. Validate JWT -> get user_id
2. Fetch user's profile from `profiles` table -> capture as `profile_snapshot`
3. Insert new workflow row (status=queued, goal_text, settings, profile_snapshot)
4. Insert audit_events row (event_type=workflow_created)
5. Return `{id, status, message}`

**Ralph loop: 4 iterations**
1. `str | None` syntax fails on Python 3.9 -> switched to `Optional[str]` from typing
2. `.env` not found because pydantic-settings looks in CWD, not project root -> fixed with explicit path resolution using `Path(__file__).resolve().parent.parent.parent.parent / ".env"`
3. Pydantic rejects `NEXT_PUBLIC_*` vars from `.env` as "extra inputs not permitted" -> added `"extra": "ignore"` to `model_config`
4. `maybe_single()` in supabase-py returns `None` (not an object with `.data = None`) -> switched to `.execute()` and checking `resp.data` as a list

### Compound Loop: REVIEW

**Test results:**
- `pytest tests/test_workflows.py` **13/13 PASSED** (6.55s)
- `pytest tests/test_rls.py` **20/20 PASSED** (3.94s) -- no regressions
- **Total: 33/33 PASSED**

**Test coverage:**

| Test | What it proves |
|------|---------------|
| `test_create_workflow_success` | POST with valid JWT creates workflow with status=queued |
| `test_create_workflow_no_auth` | POST without token returns 401 |
| `test_create_workflow_invalid_token` | POST with garbage token returns 401 |
| `test_create_workflow_goal_too_short` | POST with goal < 10 chars returns 422 (validation error) |
| `test_create_workflow_captures_profile_snapshot` | Profile data captured at creation time (verified in DB) |
| `test_create_workflow_logs_audit_event` | audit_events row inserted (verified in DB) |
| `test_list_workflows_returns_own` | GET returns user's workflows |
| `test_list_workflows_no_auth` | GET without token returns 401 |
| `test_list_workflows_user_isolation` | User B cannot see User A's workflows in list |
| `test_get_workflow_detail` | GET by ID returns full workflow data |
| `test_get_workflow_not_found` | GET with fake UUID returns 404 |
| `test_get_workflow_other_user_returns_404` | User B cannot access User A's workflow by ID |
| `test_get_workflow_no_auth` | GET by ID without token returns 401 |

**Manual verification steps:**
1. Start API: `cd apps/api && .venv/bin/uvicorn app.main:app --port 8000`
2. Open `http://localhost:8000/docs` -- see 3 workflow endpoints listed
3. Try POST /workflows without token -- get 401 error

**Validate checklist items checked off (5 new, 13 total):**
- Service role key used only by backend
- API endpoints require JWT authentication
- CORS restricted to frontend origin
- Input validation on all endpoints (Pydantic models)
- SQL injection prevented (Supabase client, no raw SQL)

### Compound Loop: COMPOUND

**Pattern saved:** `docs/compound/patterns/fastapi-auth.md`
- JWT auth flow with Supabase
- `maybe_single()` gotcha (returns None, not object)
- `.env` path resolution for monorepos
- Pydantic `extra=ignore` for shared .env files
- Python 3.9 `Optional[str]` instead of `str | None`
- Test pattern: create users, sign in for JWT, httpx requests

---

## 10. Current State + What's Next

### Phase completion

| Phase | Status |
|-------|--------|
| ILLUMINATE + DEFINE | Done |
| ARCHITECT | Done + Approved |
| SEQUENCE | Done + Approved |
| VALIDATE | Done (checklists are living documents) |
| FORGE Slice 1 (Repo scaffold) | Done |
| FORGE Slice 2 (Schema + RLS) | Done |
| FORGE Slice 3 (API endpoints) | Done |
| FORGE Slice 4 (Worker) | **Next up** |
| FORGE Slices 5-12 | Planned |

### Milestone 1 progress (3 of 4 slices done)

- [x] Slice 1: Repo scaffold + env + CI
- [x] Slice 2: Supabase schema + RLS verified (20/20 tests)
- [x] Slice 3: API: create workflow + status (13/13 tests)
- [ ] Slice 4: Worker: queue + run lifecycle

### What Milestone 1 completion looks like
After Slice 4, you can:
1. Call `POST /workflows` with a goal
2. See a workflow row appear in Supabase with `status = queued`
3. Watch the worker pick it up within 5 seconds
4. See `workflow_snapshots` written as the worker simulates pipeline steps
5. See status transition: `queued -> running -> awaiting_topic`

No scripts yet -- just the async plumbing proving the architecture works end-to-end.

### After Milestone 1 (Slices 5-12)

| Slice | What it adds |
|-------|-------------|
| 5 | Upload resources (PDF, links, notes). Tag, search, gold-star. Text extraction + chunking. |
| 6 | Real LangGraph pipeline (8 nodes). Checkpoints to Postgres. interrupt() at 3 points. Resume with user's choice. |
| 7 | Dashboard shows 10 topic candidates with scores. User picks one. Workflow resumes via WebSocket. |
| 8 | Dashboard shows 7 hook options with scores. User picks one. |
| 9 | Pipeline generates full Content Pack (long script + 3 shorts + titles + description + tags + pinned comment + thumbnail brief). |
| 10 | Editor refines for voice. Testing produces PASS/FAIL report. Approve, reject with feedback, or regenerate from any step. |
| 11 | One-click export to Google Docs or Notion. Copy any asset to clipboard. |
| 12 | Structured logging, cost tracking per workflow, per-user daily caps, usage dashboard. |

### After MVP (v1.1)
- Video link ingestion (paste YouTube/TikTok/Instagram URL -> auto-transcribe)
- Canvas/board UI (Poppy-style drag-and-drop)
- Agent personality + self-measurement
- Proactive advisor mode ("here are 3 video ideas for this week")
- Learning loop (approval/rejection patterns -> better future generations)

---

## 11. All Files Created

### Architecture + Planning (8 files)
| # | File | Purpose |
|---|------|---------|
| 1 | `docs/compound/architecture.md` | System architecture + component diagram |
| 2 | `docs/compound/decisions/01-mvp-mode.md` | Export-only decision (no YouTube API) |
| 3 | `docs/compound/decisions/02-brain-v1.1.md` | Brain + Poppy UI roadmap |
| 4 | `docs/compound/runbooks/local-dev.md` | How to run everything locally |
| 5 | `docs/compound/plan/task-list.md` | 12 build slices with Definitions of Done |
| 6 | `docs/compound/validate-checklists.md` | Security, UX, cost, infra checklists |
| 7 | `docs/compound/patterns/methodology.md` | Full RC + Compound process reference |
| 8 | `docs/compound/project-log.md` | Living project history |

### Compound Patterns (4 files)
| # | File | Source Slice |
|---|------|-------------|
| 9 | `docs/compound/patterns/repo-scaffold.md` | Slice 1 |
| 10 | `docs/compound/patterns/rls.md` | Slice 2 |
| 11 | `docs/compound/patterns/fastapi-auth.md` | Slice 3 |
| 12 | `docs/compound/full-build-process.md` | This file |

### Infrastructure (3 files)
| # | File | Purpose |
|---|------|---------|
| 13 | `infra/supabase/migrations/001_init.sql` | Database schema (original) |
| 14 | `supabase/migrations/20260212000000_init.sql` | Database schema (CLI format) |
| 15 | `supabase/config.toml` | Supabase CLI config |

### Configuration (4 files)
| # | File | Purpose |
|---|------|---------|
| 16 | `.env.example` | All environment variables with comments |
| 17 | `.env` | Real keys (NOT committed to git) |
| 18 | `.gitignore` | Security exclusions |
| 19 | `.github/workflows/ci.yml` | CI pipeline (lint + type-check) |

### Source Code -- Slice 1 (7 files)
| # | File | Purpose |
|---|------|---------|
| 20 | `apps/api/app/main.py` | FastAPI app entry point |
| 21 | `apps/api/app/config.py` | Settings from environment |
| 22 | `apps/api/requirements.txt` | Python dependencies |
| 23 | `apps/web/package.json` | Node dependencies |
| 24 | `apps/web/src/app/layout.tsx` | Root layout |
| 25 | `apps/web/src/app/page.tsx` | Home page |
| 26 | `packages/shared/schemas/*.json` | JSON schemas (2 files) |

### Source Code -- Slice 2 (3 files)
| # | File | Purpose |
|---|------|---------|
| 27 | `apps/api/tests/conftest.py` | Shared test fixtures |
| 28 | `apps/api/tests/test_rls.py` | 20 RLS verification tests |
| 29 | `apps/api/scripts/seed.py` | Development seed data |

### Source Code -- Slice 3 (6 files)
| # | File | Purpose |
|---|------|---------|
| 30 | `apps/api/app/auth.py` | JWT auth middleware |
| 31 | `apps/api/app/deps.py` | Supabase client factory |
| 32 | `apps/api/app/routers/workflows.py` | Workflow CRUD endpoints |
| 33 | `apps/api/app/schemas/workflow.py` | Pydantic request/response models |
| 34 | `apps/api/tests/test_workflows.py` | 13 endpoint tests |
| 35 | `apps/api/app/routers/__init__.py` | Package init |

**Total: 35+ files across planning, infrastructure, configuration, source code, tests, and patterns.**

---

## 12. All Decisions Made

| # | Decision | Why | Document |
|---|----------|-----|----------|
| 1 | Export-only MVP (no YouTube publishing) | Saves 3-4 weeks, validates core hypothesis first | `decisions/01-mvp-mode.md` |
| 2 | Google Docs + Notion export (not .zip) | Product owner preference -- export to where creators work | `decisions/01-mvp-mode.md` |
| 3 | Brain + Poppy UI deferred to v1.1 | Pipeline must produce good scripts before adding personality | `decisions/02-brain-v1.1.md` |
| 4 | pgmq for job queue (not Redis) | Postgres-native, no extra infrastructure to deploy | `architecture.md` |
| 5 | LangGraph for pipeline (not custom) | Checkpoints + interrupts for pause/resume built in | `architecture.md` |
| 6 | Agent Zero optional in MVP | Reduces complexity, pipeline makes direct LLM calls instead | `architecture.md` |
| 7 | Configurable research sources | Product owner wants control over where the agent researches | `architecture.md` |
| 8 | Outlier detection in research | Better signal than "most viewed" -- finds videos that overperformed | `architecture.md` |
| 9 | Two-phase build (factory then brain) | Lower risk, faster to a working product | `decisions/02-brain-v1.1.md` |
| 10 | Supabase Realtime for status updates | No polling needed, instant via WebSocket | `architecture.md` |
| 11 | `gen_random_uuid()` not `uuid_generate_v4()` | Supabase cloud compatibility (no extension needed) | `patterns/rls.md` |
| 12 | Service-role key for backend DB access | Backend validates JWT then uses service-role for all queries. RLS as safety net. | `patterns/fastapi-auth.md` |

---

## 13. Lessons Learned (Ralph Loop Failures)

Every time a test failed, we learned something. These are documented in compound patterns so we don't repeat them.

### Slice 1 (2 Ralph iterations)
| Error | Root Cause | Fix |
|-------|-----------|-----|
| `next build` fails, missing autoprefixer | Next.js + Tailwind requires autoprefixer as peer dep | Added `autoprefixer` to package.json |

### Slice 2 (2 Ralph iterations)
| Error | Root Cause | Fix |
|-------|-----------|-----|
| `uuid_generate_v4()` not found | Function requires `uuid-ossp` extension, not enabled in Supabase cloud | Switched to `gen_random_uuid()` (built into Postgres 13+) |

### Slice 3 (4 Ralph iterations)
| Error | Root Cause | Fix |
|-------|-----------|-----|
| `TypeError: unsupported operand type(s) for \|: 'type' and 'NoneType'` | Python 3.9 doesn't support `str \| None` syntax (needs 3.10+) | Use `Optional[str]` from `typing` module |
| Settings loads empty strings for all Supabase keys | Pydantic-settings looks for `.env` relative to CWD, which is `apps/api/`, not project root | Explicit path: `Path(__file__).resolve().parent.parent.parent.parent / ".env"` |
| `ValidationError: extra inputs not permitted` for `next_public_supabase_url` | `.env` contains `NEXT_PUBLIC_*` vars not in Settings model | Added `"extra": "ignore"` to `model_config` |
| `AttributeError: 'NoneType' object has no attribute 'data'` | `maybe_single()` in supabase-py returns `None` when no rows found, not an object | Use `.execute()` and check `resp.data` as a list instead |

---

## 14. Cost Summary

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
