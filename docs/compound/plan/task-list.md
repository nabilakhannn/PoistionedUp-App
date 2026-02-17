# RC SEQUENCE -- Vertical Build Slices

**Source of truth:** Content_Orchestrator_MVP_PRD.md
**Architecture:** docs/compound/architecture.md
**Date:** 2026-02-12

Each slice is independently testable. Slices are ordered by dependency.

---

## Dependency Graph

```
Slice 1: Repo Scaffold
    |
    v
Slice 2: Schema + RLS
    |
    +-------> Slice 3: API (create + status)
    |             |
    |             +-------> Slice 4: Worker (queue + lifecycle)
    |             |             |
    |             |             +-------> Slice 6: LangGraph Pipeline
    |             |                         |
    |             |                         +-------> Slice 7: Topic UI
    |             |                         |             |
    |             |                         |             +-------> Slice 8: Hook UI
    |             |                         |                         |
    |             |                         |                         +-------> Slice 9: Script Pack
    |             |                         |                                     |
    |             |                         |                                     +-------> Slice 10: Editor+Test+Approval
    |             |                         |                                                 |
    |             |                         |                                                 +-------> Slice 11: Export
    |             |                         |
    |             |                         +-------> Slice 12: Observability (parallel with 7-11)
    |             |
    |             +-------> Slice 5: Resources CRUD (parallel with Slice 4)
```

**Parallelism:** Slices 4 & 5 can run in parallel. Slice 12 can run in parallel with 7-11.

---

## Milestone 1: "Workflow Skeleton Works" (Slices 1-4)

After completing slices 1-4, you can:
1. Click "Generate" (or call the API)
2. See a workflow row in Supabase with `status = queued`
3. Watch the worker pick it up and write snapshots
4. See status updates in the dashboard

No scripts yet -- just the async plumbing proving the architecture works.

---

## Slice 1: Repo Scaffold + Environment + CI

**What it delivers (plain English):**
An empty project with all folders, package managers configured, linting working, and a GitHub Actions CI pipeline. Nothing "runs" yet except a health check endpoint.

**Key files:**
- Root: `package.json` (pnpm workspace), `.gitignore`, `.env.example`, `docker-compose.yml`
- `apps/web/`: Next.js 14+ with App Router, Tailwind CSS, TypeScript
- `apps/api/`: FastAPI, `requirements.txt`, health check endpoint
- `packages/shared/schemas/`: Empty JSON schema placeholders
- `docs/compound/`: All subdirectories
- `.github/workflows/ci.yml`: Lint + type-check + format

**Definition of Done:**
- [ ] `pnpm install` succeeds in `apps/web/`
- [ ] `uv pip install -r requirements.txt` succeeds in `apps/api/`
- [ ] `pnpm lint` passes in `apps/web/`
- [ ] `ruff check apps/api/` passes
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `pnpm dev` in `apps/web/` shows default page at localhost:3000
- [ ] CI pipeline runs and passes on push
- [ ] `.env.example` has all required variables with comments
- [ ] All directories from PRD appendix exist

**Dependencies:** None

---

## Slice 2: Supabase Schema + RLS Verified

**What it delivers:**
All 9 database tables running locally via Supabase CLI, with row-level security policies active and verified by automated tests. No user can see another user's data.

**Key files:**
- `infra/supabase/migrations/001_init.sql`
- `infra/supabase/config.toml`
- `apps/api/tests/test_rls.py`
- `apps/api/scripts/seed.py`
- `docs/compound/patterns/rls.md`

**Definition of Done:**
- [ ] `supabase db reset` runs without errors
- [ ] All 9 tables visible in Supabase Studio
- [ ] RLS enabled on every table (verified programmatically)
- [ ] RLS test: User A cannot see User B's workflows
- [ ] RLS test: User A cannot see User B's resources
- [ ] RLS test: Unauthenticated request returns 0 rows
- [ ] Storage bucket `resource-uploads` exists with correct MIME type restrictions
- [ ] pgmq queues `workflow_jobs` and `workflow_jobs_dlq` exist
- [ ] Realtime enabled for `workflows` table
- [ ] `updated_at` trigger fires on UPDATE
- [ ] Seed script creates test data successfully

**Dependencies:** Slice 1

---

## Slice 3: API -- Create Workflow + Status

**What it delivers:**
Two working API endpoints: create a workflow and get its status. Establishes the FastAPI project structure, Supabase client integration, JWT auth middleware, and request/response schemas.

**Key files:**
- `apps/api/app/main.py`: FastAPI app with CORS, lifespan
- `apps/api/app/deps.py`: Dependency injection (Supabase client, auth)
- `apps/api/app/auth.py`: JWT verification via Supabase Auth
- `apps/api/app/routers/workflows.py`: POST + GET endpoints
- `apps/api/app/schemas/workflow.py`: Pydantic models
- `apps/api/tests/test_workflows.py`
- `docs/compound/patterns/fastapi-auth.md`

**Definition of Done:**
- [ ] `POST /workflows` with valid JWT creates a workflow (status=queued)
- [ ] `POST /workflows` without JWT returns 401
- [ ] `GET /workflows` returns only the authenticated user's workflows
- [ ] `GET /workflows/{id}` returns workflow detail (status, goal, created_at)
- [ ] `GET /workflows/{id}` for another user's workflow returns 404
- [ ] Profile snapshot captured at creation time
- [ ] `audit_events` row inserted on creation
- [ ] Swagger docs at `/docs` show correct schemas

**Dependencies:** Slice 2

---

## Slice 4: Worker -- Queue + Run Lifecycle

**What it delivers:**
A worker process that dequeues jobs from pgmq, transitions workflow status through its lifecycle, and handles failures. Uses a **stub pipeline** (no LangGraph yet) that simulates step progression.

**Key files:**
- `apps/api/worker/main.py`: Entry point with async loop + signal handling
- `apps/api/worker/executor.py`: Stub executor (simulates steps)
- `apps/api/worker/lifecycle.py`: Status transitions, error handling, dead-letter
- `apps/api/app/routers/workflows.py`: Add pgmq enqueue to POST
- `apps/api/tests/test_worker.py`
- `docs/compound/patterns/async-worker.md`

**Definition of Done:**
- [ ] Worker starts and polls pgmq without errors
- [ ] Creating a workflow via API enqueues a job
- [ ] Worker picks up job within 5 seconds
- [ ] Worker updates status: `queued` -> `running`
- [ ] Worker stub runs simulated steps, updates `current_step`
- [ ] Worker sets `status = awaiting_topic` at interrupt point
- [ ] Worker handles exceptions: sets `status = failed`, writes `error_message`
- [ ] After 3 failed attempts, message goes to `workflow_jobs_dlq`
- [ ] Worker shuts down gracefully on SIGTERM
- [ ] `workflow_snapshots` rows created for each step

**Dependencies:** Slice 3

---

## Slice 5: Resources CRUD + Ingestion

**What it delivers:**
Full resource management: upload files to Supabase Storage, add links/notes/transcripts, tag them, mark as gold, delete. Text extraction and chunking for uploaded files.

**Key files:**
- `apps/api/app/routers/resources.py`: POST, GET, PATCH, DELETE endpoints
- `apps/api/app/schemas/resource.py`: Pydantic models
- `apps/api/app/services/ingestion.py`: Text extraction + chunking
- `apps/api/app/services/storage.py`: Supabase Storage helpers
- `apps/web/app/resources/page.tsx`: Resources list page
- `apps/web/app/resources/components/`: ResourceList, AddResourceDialog, ResourceCard
- `apps/api/tests/test_resources.py`
- `docs/compound/patterns/resource-ingestion.md`

**Definition of Done:**
- [ ] `POST /resources` (type=note) creates resource + generates chunks
- [ ] `POST /resources` (type=file) uploads to Storage, extracts text, generates chunks
- [ ] File upload respects 50MB limit and allowed MIME types
- [ ] `GET /resources` returns user's resources with tags and gold flag
- [ ] `GET /resources?tag=hooks` filters by tag
- [ ] `PATCH /resources/{id}` toggles `is_gold`
- [ ] `DELETE /resources/{id}` deletes resource + chunks + storage file
- [ ] Chunking produces ~500-token chunks (tested with sample PDF)
- [ ] Resources page renders in dashboard with Add, Search, Gold toggle, Delete
- [ ] Storage RLS: User A cannot access User B's files

**Dependencies:** Slice 2, Slice 3 (for auth patterns). Can run **parallel with Slice 4**.

---

## Slice 6: LangGraph Pipeline + Checkpoint + Interrupts

**What it delivers:**
The real LangGraph state machine with all 8 nodes, Postgres checkpointing, and working `interrupt()` at 3 points. Resume from interrupt verified end-to-end.

**Key files:**
- `apps/api/worker/graph/state.py`: TypedDict for graph state
- `apps/api/worker/graph/nodes/`: 8 node files (signal_research, gap_analysis, topic_selection, hook_lab, script_generation, editor, testing, approval)
- `apps/api/worker/graph/pipeline.py`: Graph compilation + AsyncPostgresSaver
- `apps/api/worker/graph/prompts/`: Prompt templates per node
- `apps/api/worker/executor.py`: Replace stub with real LangGraph
- `apps/api/app/routers/workflows.py`: Add POST /topic and POST /hook endpoints
- `packages/shared/schemas/`: JSON schemas for outputs
- `apps/api/tests/test_pipeline.py`
- `docs/compound/patterns/langgraph-interrupts.md`

**Definition of Done:**
- [x] Graph compiles with PostgresSaver connected to Postgres
- [x] `checkpointer.setup()` creates checkpoint tables
- [x] Full pipeline runs end-to-end with mocked LLM (30 tests passing)
- [x] `interrupt()` at topic_selection pauses and saves checkpoint
- [x] `POST /workflows/{id}/topic` resumes correctly
- [x] Pipeline continues to hook_lab and pauses again
- [x] `POST /workflows/{id}/hook` resumes to script_generation
- [x] Pipeline runs editor, testing, and pauses at approval
- [x] `POST /workflows/{id}/approve` resumes to completion
- [x] `workflow_snapshots` written after each interrupt
- [x] `content_assets` created with correct types and versions
- [ ] `usage_costs` recorded per node (deferred — Slice 12)
- [ ] `workflow_resources_used` records created (deferred — needs gold resources)
- [ ] Retry: 2 retries per node, then fail (deferred — Slice 12)

**Status: DONE** (2026-02-14). Core pipeline complete. Cost tracking and retries deferred to Slice 12 (Observability).

**Dependencies:** Slice 4, Slice 5

---

## Slice 7: Topic Candidates UI + Selection

**What it delivers:**
Dashboard shows 10 scored topic candidates when workflow is in `awaiting_topic`. User picks a topic, optionally tweaks angle/audience/tone, submits. Workflow resumes.

**Key files:**
- `apps/web/app/workflows/[id]/page.tsx`: Status-based rendering
- `apps/web/app/workflows/[id]/components/TopicCandidatesPanel.tsx`
- `apps/web/app/workflows/[id]/components/TopicCard.tsx`
- `apps/web/app/workflows/[id]/components/TopicSelectionDialog.tsx`
- `apps/web/lib/api.ts`: Typed API client
- `apps/web/lib/realtime.ts`: Supabase Realtime hook
- `apps/web/app/workflows/page.tsx`: Workflow list

**Definition of Done:**
- [ ] Workflow list page shows all workflows with status badges
- [ ] Workflow detail page renders different UI per status
- [ ] `awaiting_topic` shows TopicCandidatesPanel with all 10 candidates
- [ ] Each card shows: title, audience pain, why now, score (0-100), breakdown, sources, risks
- [ ] Click "Select" opens dialog with tweak fields (angle, audience, tone, length)
- [ ] Submit calls POST /topic, shows loading state
- [ ] After submit, status updates to `running` via Realtime
- [ ] Error handling: API errors show clear message

**Dependencies:** Slice 6

---

## Slice 8: Hook Lab UI + Selection

**What it delivers:**
When workflow reaches `awaiting_hook`, dashboard shows 7 hook options with scores. User picks a hook, workflow resumes.

**Key files:**
- `apps/web/app/workflows/[id]/components/HookLabPanel.tsx`
- `apps/web/app/workflows/[id]/components/HookCard.tsx`
- `apps/web/app/workflows/[id]/components/HookSelectionDialog.tsx`

**Definition of Done:**
- [ ] `awaiting_hook` shows HookLabPanel with 7 hooks
- [ ] Each card shows: hook text, type (curiosity/contrarian/story/data/challenge/myth-bust/learned), score breakdown (clarity, curiosity gap, specificity, credibility)
- [ ] Click "Select" submits choice
- [ ] Status changes to `running` via Realtime
- [ ] "Regenerate hooks" button calls POST /regenerate with regen_from_step=hook_lab
- [ ] Selected topic brief visible above hooks for context

**Dependencies:** Slice 7

---

## Slice 9: Script Pack Generation

**What it delivers:**
Pipeline generates full Content Pack: long script + 3 shorts + 10 titles + description + tags + pinned comment + thumbnail brief. Dashboard displays everything.

**Key files:**
- `apps/api/worker/graph/nodes/script_generation.py`: Real LLM prompts
- `apps/api/worker/graph/prompts/long_script.py`
- `apps/api/worker/graph/prompts/shorts.py`
- `apps/api/worker/graph/prompts/metadata.py`
- `packages/shared/schemas/`: JSON schemas per asset type
- `apps/web/app/workflows/[id]/components/ScriptPackPanel.tsx`
- `apps/web/app/workflows/[id]/components/LongScriptView.tsx`
- `apps/web/app/workflows/[id]/components/ShortScriptView.tsx`
- `apps/web/app/workflows/[id]/components/MetadataView.tsx`

**Definition of Done:**
- [ ] Long script has: hook, promise/stakes, story arc, 2-3 case studies, new tech, summary, CTA, timestamps
- [ ] 3 shorts each have: hook, script, punchline, CTA, on-screen text
- [ ] 10 titles generated
- [ ] Description, tags, pinned comment, thumbnail brief (3 concepts) generated
- [ ] All assets validated against JSON schemas (1 auto-repair attempt on failure)
- [ ] All assets stored in `content_assets` with correct type + version
- [ ] Dashboard renders full pack with tabs/accordion
- [ ] Profile voice constraints applied
- [ ] `workflow_resources_used` tracks which resources were referenced

**Dependencies:** Slice 8

---

## Slice 10: Editor + Testing + Approval

**What it delivers:**
Editor refines scripts for voice/clarity. Testing produces quality report (PASS/FAIL per asset). Approval interrupt lets user approve, reject with feedback, or regenerate from any step. Version history visible.

**Key files:**
- `apps/api/worker/graph/nodes/editor.py`: Editing prompts
- `apps/api/worker/graph/nodes/testing.py`: Quality checks
- `apps/api/app/routers/workflows.py`: POST /approve, /reject, /regenerate
- `apps/web/app/workflows/[id]/components/TestReportPanel.tsx`
- `apps/web/app/workflows/[id]/components/ApprovalPanel.tsx`
- `apps/web/app/workflows/[id]/components/VersionHistory.tsx`
- `apps/web/app/workflows/[id]/components/RejectDialog.tsx`

**Definition of Done:**
- [ ] Editor produces refined versions (diff summary in metadata)
- [ ] Prior versions preserved when editor creates new version
- [ ] Test report: schema validity, required sections, repetition, risk flags, resource usage, length
- [ ] Dashboard shows test report with PASS/FAIL per asset
- [ ] `awaiting_approval` shows ApprovalPanel with 3 actions
- [ ] "Approve" sets all assets to approved, workflow to approved
- [ ] "Reject" opens dialog with feedback + tags + regen_from_step selector
- [ ] "Regenerate" creates new version, resumes from selected step
- [ ] Version history shows all versions with timestamps
- [ ] FAIL test report blocks approval unless user explicitly overrides (override logged)
- [ ] Audit events recorded for approve, reject, regenerate

**Dependencies:** Slice 9

---

## Slice 11: Export (Google Docs + Notion + Clipboard)

**What it delivers:**
Export Content Pack to Google Docs or Notion with one click. Copy any asset to clipboard. Requires lightweight OAuth for Google and Notion.

**Key files:**
- `apps/api/app/routers/exports.py`: POST /export/google-docs, POST /export/notion
- `apps/api/app/routers/oauth.py`: OAuth connect/callback routes for Google + Notion
- `apps/api/app/services/google_docs.py`: Google Docs API client
- `apps/api/app/services/notion_export.py`: Notion API client
- `apps/web/app/workflows/[id]/components/ExportPanel.tsx`
- `apps/web/app/settings/integrations/page.tsx`: Connect Google + Notion accounts
- `infra/supabase/migrations/002_oauth_tokens.sql`: OAuth tokens table

**Definition of Done:**
- [ ] User can connect Google account (OAuth, docs scope only)
- [ ] User can connect Notion account (OAuth integration)
- [ ] "Send to Google Docs" creates a formatted doc with full Content Pack
- [ ] Google Doc has organized headings: Long Script, Shorts 1-3, Titles, etc.
- [ ] "Send to Notion" creates a formatted page in user's workspace
- [ ] Notion page has organized sections matching the Content Pack
- [ ] "Copy" button copies any individual asset to clipboard (no OAuth needed)
- [ ] Export works for drafts and approved packs
- [ ] OAuth tokens stored securely (encrypted, server-side only)
- [ ] `audit_events` logged on export
- [ ] Disconnecting Google/Notion revokes tokens

**Dependencies:** Slice 10

---

## Slice 12: Observability + Cost Caps

**What it delivers:**
Structured logging with workflow_id correlation, cost tracking, per-user daily caps, per-step token ceilings, usage dashboard.

**Key files:**
- `apps/api/app/middleware/logging.py`: Request/response logging
- `apps/api/worker/observability.py`: Structured log helpers
- `apps/api/worker/cost_tracker.py`: Token counting + ceiling enforcement
- `apps/api/app/routers/usage.py`: GET /usage endpoints
- `apps/web/app/usage/page.tsx`: Usage dashboard
- `apps/api/app/middleware/rate_limit.py`: Per-user daily cap
- `docs/compound/patterns/observability.md`

**Definition of Done:**
- [ ] Every log line includes `workflow_id` and `user_id` when applicable
- [ ] Logs are structured JSON
- [ ] Secrets never appear in logs (verified by grep)
- [ ] `usage_costs` populated for every LLM call
- [ ] Per-step ceiling: step fails if it exceeds MAX_TOKENS_PER_STEP
- [ ] Per-workflow ceiling: workflow fails with `cost_limit_exceeded`
- [ ] Per-user daily cap: POST /workflows returns 429 at limit
- [ ] Usage dashboard shows: total cost (today/week/all), per-workflow, per-step
- [ ] Failed workflows listed with error_message and step
- [ ] Health check includes queue depth + recent failure count

**Dependencies:** Slice 6. Can run **parallel with Slices 7-11**.
