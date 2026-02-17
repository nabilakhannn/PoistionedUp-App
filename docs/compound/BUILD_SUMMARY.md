# Content Orchestrator -- Build Summary

**Last updated:** 2026-02-12 (after Milestone 1 complete)
**Status:** Slices 1-4 done. Milestone 1 ("Workflow Skeleton Works") complete.

---

## What is this app?

An AI content creation assistant for YouTube creators. You tell it what kind of video you want to make, and it:

1. **Researches** what's working on YouTube right now (trends, outliers, gaps)
2. **Proposes 10 topics** with scores and evidence -- you pick one
3. **Generates 7 hooks** (opening lines) -- you pick one
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

---

## What have we built so far?

### The short version

We've built the **skeleton** -- the plumbing that makes the whole app work. No AI-generated scripts yet (that comes in Slices 6-9), but the entire flow from "click Generate" to "worker processes your request" is working end-to-end.

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

Steps 6-9 are stubs right now (they simulate work with 1-second delays instead of calling the AI). The real AI gets wired in at Slice 6.

### We verified this works live

We ran the full flow end-to-end:
- Created a workflow: *"Create a video about Python async programming"*
- Worker picked it up within 2 seconds
- Ran signal_research and gap_analysis (stub)
- Paused at topic_selection (status: `awaiting_topic`)
- 3 snapshots saved (one per step)

---

## What was built in each slice

### Slice 1: Project Setup (the empty house)

**What it is:** The folder structure, package managers, and basic configuration. Like building the foundation and framing of a house before adding rooms.

**What was created:**
- FastAPI backend with a health check endpoint (`/health` returns "ok")
- Next.js frontend with Tailwind CSS (placeholder page)
- CI pipeline that checks code quality on every push
- Environment configuration (API keys, database URLs)
- `.gitignore` to keep secrets out of version control

**Verification:** Health check works, linting passes, frontend builds.

---

### Slice 2: Database + Security (the vault)

**What it is:** All 10 database tables with security policies that ensure no user can ever see another user's data. Like building a bank vault where every customer has their own safe deposit box.

**Tables created:**

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

**Security (Row-Level Security):** Every table has policies that check "is this YOUR data?" before allowing access. Tested with 20 automated tests -- User A cannot see, edit, or delete User B's data. Period.

**Verification:** 20/20 RLS tests pass. Seed script creates sample data.

---

### Slice 3: API Endpoints (the front door)

**What it is:** The API that the frontend (and you) talk to. Three endpoints that let you create workflows and check their status.

**Endpoints:**

| Method | URL | What it does |
|--------|-----|-------------|
| `POST /workflows` | Creates a new workflow (queued for processing) |
| `GET /workflows` | Lists all YOUR workflows (newest first) |
| `GET /workflows/{id}` | Gets details of one specific workflow |

**Security:** Every request must include a valid login token (JWT). Without it, you get a 401 error. You can only see your own workflows.

**Bonus features:**
- Captures a snapshot of your profile at the moment you create a workflow (so if you change your profile later, old workflows still have the original settings)
- Logs an audit event every time a workflow is created

**Verification:** 13/13 endpoint tests pass. No regressions on RLS tests.

---

### Slice 4: Background Worker (the engine room)

**What it is:** A background process that watches for new workflows and processes them automatically. Like a kitchen where orders come in and the chef works through them one at a time.

**How it works:**
1. Worker polls every 2 seconds: "Any new workflows?"
2. Finds the oldest `status = queued` workflow
3. Claims it (using a lock so two workers can't grab the same one)
4. Runs the pipeline step by step
5. At decision points (topic selection, hook selection, approval), pauses and waits for user input
6. If anything goes wrong, marks the workflow as "failed" with an error message

**The 8-step pipeline:**

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

Right now, steps 1-8 are stubs (simulated). The real AI gets connected in Slice 6.

**Safety features:**
- Graceful shutdown: if you stop the worker, it finishes its current job first
- Failure handling: errors are caught, logged, and the workflow is marked failed (never crashes the whole system)
- Status validation: the system prevents impossible status changes (e.g., a "queued" workflow can't jump directly to "approved")

**Verification:** 15/15 worker tests pass. No regressions.

---

## How compound engineering works

Every slice follows the same 4-step loop:

```
PLAN     Check existing patterns. Design what we'll build.
   |
WORK     Write the code. Run tests. Fix bugs. (max 5 fix attempts)
   |
REVIEW   Show what changed in plain English. Get approval.
   |
COMPOUND Save reusable patterns for future slices.
```

### Why this matters to you

Each slice **builds on what came before** and **leaves knowledge behind** for future slices. We never solve the same problem twice. When a future slice needs authentication, it uses the pattern from Slice 3. When it needs database access, it uses the pattern from Slice 2.

### Patterns saved so far

| Pattern | What it teaches future slices |
|---------|------------------------------|
| [methodology.md](patterns/methodology.md) | The full build process (RC + Compound + Ralph) |
| [repo-scaffold.md](patterns/repo-scaffold.md) | How this project is structured |
| [rls.md](patterns/rls.md) | How to secure database tables + test them |
| [fastapi-auth.md](patterns/fastapi-auth.md) | How to protect API endpoints with login tokens |
| [async-worker.md](patterns/async-worker.md) | How the background worker claims and processes jobs |

### Decisions logged

| # | Decision | Why |
|---|----------|-----|
| 1 | Export-only MVP (no YouTube publishing) | Saves 3-4 weeks, validates core idea first |
| 2 | Google Docs + Notion export | Your preference |
| 3 | Brain + Poppy UI deferred to v1.1 | Pipeline must work first |
| 4 | Postgres-native queue (not Redis) | No extra infrastructure |
| 5 | LangGraph for pipeline | Checkpoints + interrupts built-in |
| 6 | Agent Zero optional in MVP | Reduces complexity |
| 7 | Configurable research sources | You want control over where it looks |
| 8 | Outlier detection in research | Better signal than "most viewed" |
| 9 | Two-phase build (factory then brain) | Lower risk |
| 10 | WebSocket for live status updates | Instant, no polling |
| 11 | `gen_random_uuid()` for Supabase cloud | Compatibility fix |
| 12 | Table-based polling for MVP (not pgmq) | Supabase REST API limitation |

---

## Everything that exists right now

### By the numbers

| Category | Count |
|----------|-------|
| Source code files | 25 |
| Test files | 3 (48 tests total) |
| Documentation files | 13 |
| Database tables | 10 |
| API endpoints | 4 (health + 3 workflow) |
| Compound patterns | 5 |
| Decisions logged | 12 |
| Total files | ~45 |

### Test results

| Test suite | Tests | Result |
|------------|-------|--------|
| RLS security tests | 20 | All pass |
| Workflow API tests | 13 | All pass |
| Worker tests | 15 | All pass |
| **Total** | **48** | **All pass** |

### All files

```
Project Root
|
+-- .env.example                    # Environment variable template
+-- .gitignore                      # Keeps secrets out of git
+-- Content_Orchestrator_MVP_PRD.md # The original product requirements
|
+-- .github/
|   +-- workflows/ci.yml           # CI pipeline (lint + type-check)
|
+-- apps/
|   +-- api/                        # Python backend
|   |   +-- app/
|   |   |   +-- main.py            # FastAPI app entry point
|   |   |   +-- config.py          # Settings (reads .env)
|   |   |   +-- auth.py            # JWT authentication
|   |   |   +-- deps.py            # Supabase client factory
|   |   |   +-- routers/
|   |   |   |   +-- workflows.py   # POST/GET workflow endpoints
|   |   |   +-- schemas/
|   |   |   |   +-- workflow.py    # Request/response models
|   |   |   +-- services/          # (empty, used in future slices)
|   |   |
|   |   +-- worker/
|   |   |   +-- main.py            # Worker entry point (poll loop)
|   |   |   +-- queue.py           # Job claiming (optimistic lock)
|   |   |   +-- lifecycle.py       # Status transitions + snapshots
|   |   |   +-- executor.py        # Stub pipeline (8 steps)
|   |   |   +-- graph/             # (empty, LangGraph in Slice 6)
|   |   |
|   |   +-- tests/
|   |   |   +-- conftest.py        # Shared test fixtures
|   |   |   +-- test_rls.py        # 20 security tests
|   |   |   +-- test_workflows.py  # 13 API tests
|   |   |   +-- test_worker.py     # 15 worker tests
|   |   |
|   |   +-- scripts/
|   |       +-- seed.py            # Creates sample test data
|   |
|   +-- web/                        # Next.js frontend
|       +-- src/app/
|       |   +-- layout.tsx         # Root layout
|       |   +-- page.tsx           # Home page (placeholder)
|       +-- package.json
|       +-- tailwind.config.ts
|       +-- tsconfig.json
|
+-- packages/
|   +-- shared/schemas/
|       +-- content_pack.schema.json   # Content Pack structure
|       +-- workflow_plan.schema.json  # Workflow plan structure
|
+-- infra/
|   +-- supabase/migrations/
|       +-- 001_init.sql               # Database schema (reference)
|
+-- supabase/
|   +-- migrations/
|   |   +-- 20260212000000_init.sql    # Database schema (deployed)
|   |   +-- 20260212000001_queue_helpers.sql # pgmq wrappers (future use)
|   +-- config.toml                    # Supabase CLI config
|
+-- docs/
    +-- compound/
        +-- BUILD_SUMMARY.md           # This file
        +-- project-log.md             # Full engineering log
        +-- architecture.md            # System architecture
        +-- validate-checklists.md     # Pre-build verification
        +-- full-build-process.md      # Process reference
        +-- plan/
        |   +-- task-list.md           # 12 build slices with DoD
        +-- decisions/
        |   +-- 01-mvp-mode.md         # Export-only decision
        |   +-- 02-brain-v1.1.md       # Brain + Poppy UI roadmap
        +-- patterns/
        |   +-- methodology.md         # Build process
        |   +-- repo-scaffold.md       # Project structure
        |   +-- rls.md                 # Database security
        |   +-- fastapi-auth.md        # API authentication
        |   +-- async-worker.md        # Background worker
        +-- runbooks/
            +-- local-dev.md           # How to run locally
```

---

## What's next

### Remaining slices (8 of 12)

| # | Slice | What it adds | Status |
|---|-------|-------------|--------|
| 5 | Resources CRUD + Ingestion | Upload files/links, tag, search, gold | Next up |
| 6 | LangGraph Pipeline | Real AI pipeline (replace stubs) | Needs Slice 4+5 |
| 7 | Topic Candidates UI | Dashboard shows 10 topics to pick from | Needs Slice 6 |
| 8 | Hook Lab UI | Dashboard shows 7 hooks to pick from | Needs Slice 7 |
| 9 | Script Pack Generation | AI writes the full Content Pack | Needs Slice 8 |
| 10 | Editor + Testing + Approval | Quality gates + approve/reject flow | Needs Slice 9 |
| 11 | Export | One-click to Google Docs or Notion | Needs Slice 10 |
| 12 | Observability + Cost Caps | Usage tracking, spending limits | Parallel with 7-11 |

### Milestones

| Milestone | Slices | What it proves | Status |
|-----------|--------|---------------|--------|
| 1. Workflow Skeleton Works | 1-4 | The plumbing works end-to-end | **COMPLETE** |
| 2. AI Pipeline Works | 5-6 | Real AI generates content | Next |
| 3. User Can Interact | 7-8 | Pick topics and hooks in the UI | After M2 |
| 4. Full Content Pack | 9-10 | Complete scripts with quality checks | After M3 |
| 5. Ship It | 11-12 | Export + observability | After M4 |

---

## Monthly costs (estimated)

| Service | Cost |
|---------|------|
| Supabase Pro | $25/mo |
| Hosting (Vercel + Railway) | ~$20-40/mo |
| Domain | ~$12/year |
| **Fixed total** | **~$50-70/mo** |

| Per workflow (AI costs) | ~$0.40-0.60 |
|------------------------|-------------|
| Signal research (GPT-4o) | ~$0.06 |
| Topic candidates (GPT-4o) | ~$0.12 |
| Hook lab (GPT-4o) | ~$0.06 |
| Script generation (GPT-4o) | ~$0.18 |
| Editor pass (GPT-4o-mini) | ~$0.01 |
| Testing pass (GPT-4o-mini) | ~$0.005 |

---

*This document is auto-updated after each slice as part of compound engineering.*
