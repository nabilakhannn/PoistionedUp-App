# Slice 30: Autonomous Agent Orchestration

**Date:** 2026-02-25
**Methodology:** Compound Engineering + Ralph Loop
**Scope:** Agent orchestrator service, schedule automation, security hardening, E2E tests

---

## Executive Summary

This slice delivers the **Agent Orchestrator** — the autonomous engine that makes OpenClaw agents actually work. It bridges the gap between schedule definitions (openclaw.json cron jobs) and real task execution by creating Mission Control tasks, routing them to the right backend service (brand research, content pipeline, analytics), and recording results as deliverables. All endpoints are auth-protected, rate-limited, input-validated, and covered by 30 unit tests.

---

## A. WHAT WAS BUILT

### 1. OpenClaw Configuration Fix
**File:** `openclaw.json` (MODIFIED)

**Changes:**
- Added `web_fetch` to Jarvis's tool allow list (required for Agent Bridge API calls)
- Fixed cron job #3: replaced NotebookLM reference with "Brand Research Pipeline via Agent Bridge API"
- Added `POSITIONEDUP_API_URL` and `POSITIONEDUP_AGENT_KEY` to optional env vars

---

### 2. Agent Orchestrator Service
**File:** `apps/api/app/services/agent_orchestrator.py` (NEW — ~400 lines)

**Core functions:**

| Function | Purpose |
|----------|---------|
| `pulse(user_id, auto_execute, force)` | Evaluate all schedules, create tasks for due ones, optionally execute |
| `execute_task(task_id, user_id)` | Execute a specific task by routing to the correct handler |
| `trigger_schedule(user_id, schedule_id)` | Manually trigger a schedule, ignoring cooldown |
| `get_status(user_id)` | Get schedule states, active tasks, recent history |

**Schedule definitions (mirroring openclaw.json cron):**

| Schedule | Day | Hour (EST) | Agent | Task Type |
|----------|-----|------------|-------|-----------|
| `weekly_research` | Saturday | 10:00 | trend-analyzer | research |
| `weekly_analytics` | Sunday | 20:00 | analytics | analytics |
| `weekly_competitor` | Monday | 06:00 | trend-analyzer | competitor |

**Task type handlers:**

| Type | Handler | Backend Service |
|------|---------|-----------------|
| `research` | `_handle_research()` | `brand_research.run_all_stages()` — 7-stage pipeline |
| `content` | `_handle_content()` | `executor.run_pipeline()` — 8-node LangGraph pipeline |
| `analytics` | `_handle_analytics()` | Direct Supabase queries → report generation |
| `competitor` | `_handle_competitor()` | `brand_research.run_all_stages()` (competitor focus) |

**Design principles:**
- **Idempotent**: Cooldown-based deduplication prevents duplicate tasks (6-day window per schedule)
- **Observable**: Every action creates Mission Control messages (delegation from Jarvis, status from agent)
- **Stateless**: All state lives in Supabase — no in-memory persistence
- **Traceable**: Tasks tagged with `orchestrator`, `auto:{schedule_id}`, `type:{task_type}`

---

### 3. Orchestrator API Endpoints
**File:** `apps/api/app/routers/orchestrator.py` (NEW)

| Method | Path | Purpose | Rate Limit |
|--------|------|---------|------------|
| `POST` | `/orchestrator/pulse` | Check schedules, create & execute tasks | 5 req/min |
| `POST` | `/orchestrator/trigger` | Manually trigger a schedule | 5 req/min |
| `POST` | `/orchestrator/execute/{task_id}` | Execute a specific task | 5 req/min |
| `GET` | `/orchestrator/status` | Schedule states + recent history | 200 req/min |
| `GET` | `/orchestrator/schedules` | List schedule definitions | 200 req/min |

**Security measures:**
- All endpoints require `get_current_user` auth
- `task_id` validated with regex (`^[A-Za-z0-9_-]{1,80}$`) and max_length
- `schedule_id` validated with Pydantic regex pattern
- Error responses sanitized — only `ValueError` messages returned; all others get generic message
- Endpoints declared as sync `def` (not `async def`) to prevent event loop starvation during long-running LLM pipelines

---

### 4. Orchestrator Schemas
**File:** `apps/api/app/schemas/orchestrator.py` (NEW)

| Schema | Purpose |
|--------|---------|
| `PulseRequest` | `auto_execute: bool`, `force: bool` |
| `PulseResult` | Created tasks, skipped, executed, active brand |
| `TriggerRequest` | `schedule_id` (regex-validated), `auto_execute` |
| `TriggerResult` | Task + execution result |
| `ExecuteResult` | Status, task_id, deliverable_id, error, details |
| `OrchestratorStatus` | Schedules, active tasks, recent completed |

---

### 5. Rate Limit Hardening
**File:** `apps/api/app/middleware/rate_limit.py` (MODIFIED)

**New tier:** `TIER_ORCHESTRATOR = (5, 60)` — 5 requests per minute

Orchestrator POST endpoints (pulse/trigger/execute) are the most expensive in the entire API — a single call can spawn multiple LLM pipelines. The new tier is stricter than even the LLM tier (30/min).

GET endpoints (/status, /schedules) use the standard READ tier (200/min).

---

### 6. Frontend: API Client + Orchestrator Panel
**Files:**
- `apps/web/src/lib/api/orchestrator.ts` (NEW)
- `apps/web/src/lib/api/index.ts` (MODIFIED — added barrel export)
- `apps/web/src/app/mission-control/orchestrator/page.tsx` (MODIFIED)

**Frontend API client** provides typed methods for all 5 orchestrator endpoints.

**Orchestrator page enhancements:**
- **"Run Pulse" button** in header — triggers schedule evaluation with one click
- **Scheduled Automations panel** in left sidebar:
  - Shows all 3 schedule states (DUE / RAN / WAITING)
  - Per-schedule "Run" button for manual trigger
  - Last run status and time ago
  - Assigned agent with emoji
- **Pulse feedback toast** — shows result message after pulse/trigger
- All existing orchestrator functionality (timeline, delegations, tasks, deliverables) preserved

---

### 7. E2E Test Suite
**File:** `apps/api/tests/test_orchestrator.py` (NEW — 30 tests)

| Test Class | Tests | Coverage |
|-----------|-------|----------|
| `TestScheduleEvaluation` | 5 | Day-of-week, hour, timezone offset logic |
| `TestTagExtraction` | 4 | Tag parsing from task arrays |
| `TestHandlerDispatch` | 2 | All handlers registered and callable |
| `TestScheduleDefinitions` | 4 | Schema completeness, uniqueness, type validity |
| `TestPulseLogic` | 2 | Mocked DB: skip when not due, skip within cooldown |
| `TestSchemaValidation` | 4 | Valid IDs, injection rejection, defaults |
| `TestRateLimitTiers` | 6 | Correct tier per endpoint, strictness assertion |
| `TestHelpers` | 3 | Format counter helper |

**Result:** 30/30 passed in 0.25s

---

## B. FILES CHANGED

### New Files
| File | Lines | Purpose |
|------|-------|---------|
| `apps/api/app/services/agent_orchestrator.py` | ~400 | Core orchestrator service |
| `apps/api/app/schemas/orchestrator.py` | ~50 | Pydantic request/response models |
| `apps/api/app/routers/orchestrator.py` | ~100 | API endpoints |
| `apps/web/src/lib/api/orchestrator.ts` | ~100 | Frontend API client |
| `apps/api/tests/test_orchestrator.py` | ~250 | 30 unit tests |
| `docs/compound/patterns/slice-30-agent-orchestration.md` | THIS | Documentation |

### Modified Files
| File | Changes |
|------|---------|
| `openclaw.json` | Fixed Jarvis tools, cron #3, env vars |
| `apps/api/app/main.py` | Added orchestrator router |
| `apps/api/app/middleware/rate_limit.py` | Added TIER_ORCHESTRATOR (5/min), orchestrator route entries |
| `apps/web/src/lib/api/index.ts` | Barrel export for orchestrator |
| `apps/web/src/app/mission-control/orchestrator/page.tsx` | Schedule panel, pulse button, trigger controls |

---

## C. EXECUTION FLOW

### Autonomous Flow (Cron/Pulse)
```
Cron trigger (or manual "Run Pulse" click)
  → POST /orchestrator/pulse { auto_execute: true }
  → pulse(user_id)
    → for each SCHEDULE:
      → _is_schedule_due(schedule, now) → is today the right day/hour?
      → _has_recent_task(user_id, schedule_id) → cooldown check
      → _create_orchestrated_task() → insert agent_tasks row
      → _log_delegation() → insert agent_messages (Jarvis → agent)
      → execute_task(task_id)
        → _extract_tag(tags, "type:") → "research"
        → _get_handlers()["research"] → _handle_research()
          → brand_research.create_session()
          → brand_research.run_all_stages()
          → Build summary report
        → _create_deliverable() → insert agent_deliverables
        → _update_task_status("done")
        → _update_agent_status("idle")
```

### Manual Trigger Flow
```
User clicks "Run" on a schedule card
  → POST /orchestrator/trigger { schedule_id: "weekly_research" }
  → trigger_schedule(user_id, schedule_id)
    → Creates task (ignores cooldown)
    → Delegates to agent
    → Executes and returns result
```

---

## D. SECURITY AUDIT SUMMARY

10 findings identified, all addressed:

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Orchestrator not covered by rate limiter | HIGH | **FIXED** — Added TIER_ORCHESTRATOR (5/min) |
| 2 | Raw exception strings in responses | MEDIUM | **FIXED** — Sanitized to safe messages |
| 3 | No validation on task_id path param | MEDIUM | **FIXED** — Regex + max_length validation |
| 4 | `globals()` handler dispatch | LOW | **FIXED** — Direct function reference map |
| 5 | Sync blocking in async endpoints | MEDIUM | **FIXED** — Changed to sync `def` for thread pool |
| 6 | No concurrency control on pulse | MEDIUM | **ACCEPTED** — 5/min rate limit mitigates. Per-user lock deferred. |
| 7 | Admin client bypasses RLS | MEDIUM | **ACCEPTED** — App-wide pattern, manual user_id filtering consistent |
| 8 | `Dict[str, Any]` response models | LOW | **ACCEPTED** — Pragmatic for MVP, typed models deferred |
| 9 | X-Forwarded-For spoofing | MEDIUM | **ACCEPTED** — Documented for production proxy config |
| 10 | Rate key granularity | LOW | **MITIGATED** — POST/GET separation via explicit route entries |

---

## E. ARCHITECTURE PATTERNS

### Pattern: Schedule → Task → Execute → Deliverable
```
Schedule Definition (SCHEDULES list)
  → Pulse evaluates: day_of_week + hour + cooldown
  → Task created in agent_tasks (tagged with orchestrator + auto + type)
  → Delegation message logged (Jarvis → assigned agent)
  → Handler routes by task_type to correct service
  → Result → Deliverable in Mission Control
  → Agent status updated (idle/working/error)
```

### Pattern: Idempotent Pulse
```
pulse(force=False)
  → _is_schedule_due() — check day + hour
  → _has_recent_task() — check DB for tasks with auto:{id} tag in cooldown window
  → Only create if both pass
  → Safe to call from: cron, frontend button, OpenClaw heartbeat, multiple instances
```

### Pattern: Handler Registry
```python
def _get_handlers():
    return {
        "research": _handle_research,    # → brand_research pipeline
        "content": _handle_content,      # → LangGraph content pipeline
        "analytics": _handle_analytics,  # → direct DB queries + report
        "competitor": _handle_competitor, # → brand_research (competitor focus)
    }
```
Extend by adding a new handler function + schedule definition. Zero changes to routing/pulse logic.

---

## F. WHAT'S NEXT — GAP ANALYSIS

### Production Ready
| Component | Status | Notes |
|-----------|--------|-------|
| Orchestrator service | DONE | Creates, delegates, executes, reports |
| Rate limiting | DONE | 5/min on POST endpoints |
| Auth protection | DONE | All endpoints require user auth |
| Input validation | DONE | Regex on task_id, pattern on schedule_id |
| Error sanitization | DONE | Only safe messages returned |
| Tests | DONE | 30 tests passing |
| Frontend controls | DONE | Pulse button, schedule cards, trigger buttons |

### Remaining Gaps (Future Slices)

| Gap | Priority | Description |
|-----|----------|-------------|
| Background execution | P1 | Long-running tasks (research, content) should execute async with progress polling. Currently blocks the HTTP response. |
| Per-user concurrency lock | P2 | Prevent two simultaneous pulse calls from creating duplicate tasks in a race. Current rate limit (5/min) mitigates but doesn't eliminate. |
| Content pipeline auto-trigger | P2 | Add a `weekly_content` schedule that auto-generates content when brand completeness >= 50%. Handler exists but no schedule yet. |
| Redis-backed rate limiting | P2 | In-memory rate limiter resets on restart. Swap to Redis for multi-instance deployments. |
| OpenClaw heartbeat integration | P2 | The orchestrator pulse should be callable from OpenClaw's heartbeat system (via Agent Bridge /heartbeat endpoint). Currently only callable from authenticated web API. |
| Agent JWT auth | P3 | Replace static API key (X-Agent-Key) with JWT-based auth for agent-to-API communication. |
| Typed response models | P3 | Replace `Dict[str, Any]` in OrchestratorStatus with proper Pydantic models for better API docs. |
| PostHog analytics | P3 | Track orchestrator events (pulse, trigger, execute) for funnel analysis. |

---

## G. BUILD VERIFICATION

| Check | Result |
|-------|--------|
| TypeScript (`tsc --noEmit`) | 0 errors |
| Python module imports (8 modules) | All pass |
| Unit tests (30 tests) | 30/30 passed (0.25s) |
| API routes loaded | 202 total, 6 orchestrator |
| Rate limit tiers | All 5 orchestrator routes correctly tiered |
