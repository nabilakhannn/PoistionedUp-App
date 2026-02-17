# RC VALIDATE -- Pre-Build Checklists

**Purpose:** Verify these before writing any code. Check off during and after each slice.

---

## Security Checklist

- [x] RLS enabled on EVERY table (no exceptions) -- Slice 2: verified, 20/20 tests pass
- [x] RLS tests: User A cannot see User B's data (automated test in Slice 2) -- 20/20 PASS
- [x] Service role key used ONLY by backend worker -- never exposed to frontend -- Slice 3: backend uses service_role via deps.py, frontend uses anon_key only
- [x] `.env` is in `.gitignore` -- secrets never committed -- Slice 1: verified
- [x] `.env.example` has placeholder values only (no real keys) -- Slice 1: verified
- [x] OAuth tokens (Google/Notion) stored server-side only in `oauth_tokens` table with RLS -- Tier 1A/1B: tokens stored via admin client, never exposed to frontend. (Encryption at rest deferred to Supabase Vault.)
- [x] API endpoints require JWT authentication (no public write endpoints) -- Slice 3: all /workflows endpoints require Bearer JWT, 401 without
- [x] File uploads restricted: 50MB max, allowed MIME types only (PDF, DOCX, TXT, MD, CSV) -- Slice 2: storage bucket configured
- [x] Storage paths scoped by user_id (user can't access another user's files) -- Slice 2: storage RLS policies created
- [ ] Agent Zero runs in sandboxed Docker container with resource limits
- [x] No secrets in logs (API keys, tokens, passwords redacted) -- Tier 2C: `_redact_query()` masks code, token, access_token, refresh_token, state in logged paths. `_REDACT_HEADERS` strips authorization, cookie, x-api-key from logs.
- [x] CORS restricted to frontend origin only -- Slice 3: configured via CORS_ORIGINS env var, defaults to localhost:3000
- [x] Input validation on all API endpoints (Pydantic models) -- Slice 3: WorkflowCreate validates goal_text length (10-2000 chars), returns 422 on invalid
- [x] SQL injection prevented (Supabase client uses parameterized queries) -- Slice 3: all DB access via Supabase Python client (.eq(), .insert()), no raw SQL

## UX Baseline Checklist

- [x] Every status change visible in UI within 2 seconds (via Supabase Realtime) -- Slices 7-12: workflows table has Realtime enabled (008_realtime_workflows.sql), scheduled_items table too (009_schedule.sql). Workflow detail page and kanban board both subscribe to changes.
- [x] Loading states shown during all async operations -- Slices 7-12: Content dashboard, workflow detail, schedule page all show skeleton/spinner during fetch. Export and import buttons show "Loading..." state.
- [x] Error messages are human-readable (no raw stack traces shown to user) -- Slice 17/18: brand chat, research, performance all return user-friendly error messages (503 for quota, 502 for AI errors)
- [x] Workflow can be abandoned at any point without breaking anything -- Tier 1C: `POST /workflows/{id}/abandon` marks workflow as failed with audit trail. Works on queued, running, or awaiting_* statuses. Terminal statuses (approved, rejected, failed) return 409.
- [x] Topic selection UI shows scores, sources, and reasoning (not just titles) -- Slice 8: TopicSelection component renders score, evidence, and reasoning per topic
- [x] Hook selection UI shows hook type and score breakdown -- Slice 8: HookSelection component renders hook_type, score, and text
- [x] Reject flow allows free-text feedback + choice of "regenerate from" step -- Slice 10: ApprovalSection has reject form with feedback textarea and regen_from_step
- [x] Version history accessible for every workflow -- Week 8: Migration 010 adds version/is_latest columns. Backend endpoints for version list + restore. Frontend VersionHistoryPanel on workflow detail page.
- [x] Export works without page refresh (clipboard, Google Docs, Notion) -- Slice 11: ExportBar has "Copy to clipboard" and "Download .md" buttons, no page refresh
- [ ] Mobile-responsive is NOT required for MVP (desktop-first)
- [ ] Profile setup is simple -- no required fields block workflow creation

## Cost Governance Checklist

- [x] Per-step token ceiling enforced (MAX_TOKENS_PER_STEP) -- Slice 12: llm.py clamps max_tokens to settings.max_tokens_per_step, tested in test_usage.py
- [x] Per-workflow token ceiling enforced (MAX_TOKENS_PER_WORKFLOW) -- Tier 2A: `_check_workflow_budget()` in llm.py sums usage_costs for the workflow before every LLM call. Raises `WorkflowBudgetExceeded` at 200k tokens (configurable). Warns at 80%. Tested in test_oauth.py.
- [x] Per-user daily workflow cap enforced (MAX_WORKFLOWS_PER_USER_PER_DAY) -- Slice 12: check_daily_workflow_cap() in usage.py, returns 429 when exceeded, tested
- [x] usage_costs table populated for every LLM call -- Slice 12: llm.py auto-inserts to usage_costs via tracking context on every chat() call
- [x] Cost estimate visible per workflow in dashboard -- Slice 12: WorkflowSummary includes estimated_cost, shown as badge on content dashboard cards
- [x] Cheaper model used for editor/testing steps (GPT-4o-mini) -- Tier 2B: `get_model_for_step()` returns gpt-4o-mini for editor, testing, approval. Saves ~80% on those steps.
- [x] Full model used for research/scripts (GPT-4o) -- Tier 2B: `MODEL_FOR_STEP` dict maps signal_research, gap_analysis, topic_selection, hook_lab, script_generation to gpt-4o.
- [x] No runaway loops -- LangGraph pipeline has fixed node count (max 8 steps). Per-step token ceiling (32k) and per-workflow ceiling (200k) enforce hard stops.
- [x] Worker visibility timeout prevents duplicate processing (300s) -- Tier 1C: `_recover_stale_claims()` re-queues workflows stuck in 'running' past 300s. `claimed_at` timestamp tracks when a worker claimed the job.
- [x] Dead-letter queue catches jobs that fail 3+ times -- Tier 1C: `claim_next_job()` checks `retry_count >= MAX_RETRIES (3)` and moves to `status=failed` with audit event. User sees error in UI.

## Infrastructure Checklist

- [x] All services can run locally (web, API, worker, Supabase) -- Verified 2026-02-17: backend (port 8000) + frontend (port 3000) both start, 52/52 Playwright E2E pass, 578 backend tests pass
- [x] Supabase migrations are idempotent (can re-run without errors) -- Slice 2: verified via `supabase db push`
- [x] CI pipeline catches lint/type errors before merge -- Slice 1: `.github/workflows/ci.yml`
- [x] Health check endpoint exists for monitoring -- Slice 1: `GET /health`. Week 8: enhanced with DB connectivity check.
- [x] Environment variables documented in .env.example -- Slice 1: all vars with comments
- [x] No hardcoded URLs or keys in source code -- Tier 2C: Codebase audit confirmed. All secrets loaded from `.env` via `settings`. Google/Notion OAuth URLs are public endpoints (not secrets).
- [x] External API calls degrade gracefully on failure -- Slice 18: web search, YouTube, Reddit all wrap in try/except, return empty on failure, never crash the app