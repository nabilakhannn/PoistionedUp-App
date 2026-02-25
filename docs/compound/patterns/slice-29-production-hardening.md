# Slice 29: Production Hardening + Research-to-Schedule Pipeline

**Date:** 2026-02-25
**Methodology:** Compound Engineering + Ralph Loop
**Scope:** P1 production blockers, P2 feature parity, security hardening

---

## Executive Summary

This slice closes the remaining gaps identified in the Slice 28 gap analysis. It delivers production-critical security middleware (rate limiting, input validation, token refresh fix), a 3-step onboarding wizard with auto-research kickoff, a research-to-schedule auto-scheduling pipeline, and error recovery for the brand research system. All builds verified clean (TypeScript 0 errors, Next.js production build, Python imports).

---

## A. WHAT WAS BUILT

### Priority 1 — Production Blockers

#### 1. Rate Limiting Middleware
**Files:**
- `apps/api/app/middleware/__init__.py` (NEW)
- `apps/api/app/middleware/rate_limit.py` (NEW)
- `apps/api/app/main.py` (MODIFIED — added middleware to stack)

**What it does:**
In-memory sliding window rate limiter with 5 tiered limits based on endpoint category. Prevents abuse and cost runaway from LLM-heavy endpoints.

| Tier | Limit | Endpoints |
|------|-------|-----------|
| `TIER_AUTH` | 10 req/min | `/auth/`, `/login`, `/signup` |
| `TIER_LLM` | 30 req/min | `/brand/chat`, `/brand/strategist`, `/workflows`, `/content-chat` |
| `TIER_WRITE` | 60 req/min | `/mission-control/` |
| `TIER_AGENT` | 120 req/min | `/agent-api/` |
| `TIER_READ` | 200 req/min | Everything else |

**Design decisions:**
- Thread-safe `_RateLimitStore` with periodic cleanup (every 5 min) to prevent memory growth
- Exempt paths: `/`, `/health`, `/docs`, `/openapi.json`, `/favicon.ico`
- Skips `OPTIONS` for CORS preflight
- Returns `429 Too Many Requests` with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers
- Rate key groups by IP + first path segment (not full path) to prevent path-enumeration bypass
- No external dependency (Redis-swappable later by replacing `_RateLimitStore`)

**Middleware stack order:**
```
RateLimitMiddleware → RequestLoggingMiddleware → CORSMiddleware
```

---

#### 2. Token Refresh Race Condition Fix
**File:** `apps/web/src/lib/api/client.ts` (REWRITTEN)

**Problem:** Multiple concurrent `apiFetch` calls receiving 401 could each trigger a separate `supabase.auth.refreshSession()`, causing race conditions and session corruption.

**Solution:** Promise-based refresh lock pattern:
```typescript
let _refreshPromise: Promise<string | null> | null = null;

async function _refreshToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;  // reuse in-flight refresh

  _refreshPromise = (async () => {
    try {
      const { data, error } = await supabase.auth.refreshSession();
      if (error) { /* sign out + redirect */ return null; }
      return data.session?.access_token ?? null;
    } finally {
      _refreshPromise = null;  // clear lock
    }
  })();
  return _refreshPromise;
}
```

Also added 429 rate limit handling in the client:
```typescript
if (res.status === 429) {
  const retryAfter = res.headers.get("Retry-After") || "60";
  throw new Error(`Too many requests. Please wait ${retryAfter} seconds.`);
}
```

---

#### 3. Input Length Validation
**Files:**
- `apps/api/app/schemas/mission_control.py` (MODIFIED)
- `apps/api/app/schemas/agent_bridge.py` (MODIFIED)

**What changed:**
Added Pydantic `Field` validators with `max_length` / `min_length` / `pattern` to all request schemas that accept free-text input:

| Schema | Field | Validation |
|--------|-------|------------|
| `MessageCreate.message` | `max_length=10000` | Prevents oversized chat messages |
| `MessageCreate.message_type` | `pattern="^(chat\|delegation\|status\|deliverable\|escalation\|broadcast)$"` | Enum enforcement |
| `TaskBase.title` | `min_length=1, max_length=500` | Title bounds |
| `TaskBase.brief` | `max_length=5000` | Brief bounds |
| `TaskBase.priority` | `pattern="^(P0\|P1\|P2\|P3)$"` | Priority enum |
| `DeliverableCreate.title` | `min_length=1, max_length=500` | Title bounds |
| `DeliverableCreate.content` | `max_length=100000` | Deliverable content cap |
| `DeliverableCreate.deliverable_type` | `pattern="^(document\|image\|code\|report\|content)$"` | Type enum |
| `AgentReport.content` | `max_length=50000` | Agent report cap |
| `InspoSearchRequest.query` | `max_length=500` | Search query cap |

---

#### 4. Additional Security Fixes (from Slice 28)
- **Header redaction:** Added `x-agent-key` to `_REDACT_HEADERS` in `main.py`
- **SSRF hardening:** Added `ip.is_reserved`, `.localhost`/`.test` suffix blocking in `brand.py`
- **Search injection:** Sanitized PostgREST `.or_()` parameters in `agent_bridge.py`
- **Error disclosure:** Replaced raw LLM error messages with generic responses in `brand.py`
- **Health endpoint:** Removed `db_error` from health response body, replaced with `logger.warning()`

---

### Priority 2 — Feature Parity

#### 5. Onboarding Wizard (3-Step Brand Creation)
**File:** `apps/web/src/app/brands/new/page.tsx` (REWRITTEN)

**What it does:**
Transforms the simple brand creation form into a guided 3-step wizard:

| Step | Name | Fields | UX |
|------|------|--------|----|
| 1 | Basics | Brand name*, description | Enter key advances |
| 2 | Industry | Industry/niche*, target audience | 10 quick-suggestion chips, Skip option |
| 3 | Launch | Summary review, auto-research toggle | Green "Create Brand" CTA |

**Industry suggestions:** Personal branding for tech professionals, Health & wellness coaching, Business consulting, Creative freelancing, Real estate, Financial advisory, Education & online courses, SaaS/startup founder, Career coaching, Fitness & nutrition.

**On create:**
1. Creates brand via `personalBrandsApi.create()`
2. Selects brand in context + refreshes brand list
3. If auto-research enabled + industry provided: starts 7-stage research pipeline in background
4. Redirects to `/brands/{brand.id}`

**Progress indicator:** Step circles with completed (green check) / active (blue) / pending (gray) states connected by bars.

---

#### 6. Auto-Scheduling from Research Results
**Files:**
- `apps/api/app/routers/schedule.py` (MODIFIED — added `POST /from-research/{session_id}`)
- `apps/web/src/lib/api/schedule.ts` (MODIFIED — added `createFromResearch()`)
- `apps/web/src/app/brands/[brandId]/components/research-panel.tsx` (MODIFIED — added Auto-Schedule button)

**Backend endpoint:** `POST /schedule/from-research/{session_id}`

**Request body:**
```json
{ "schedule_dates": false }
```

**What it does:**
1. Fetches the research session, extracts `results.content_ideas`
2. Maps each idea's `format` → `content_type` and `platform` → schedule platform
3. Creates up to 20 scheduled items in `"draft"` status
4. Optionally distributes dates using `content_calendar_week_1` (starting next Monday, 9am UTC)

**Format mapping:**
```python
_FORMAT_MAP = {
    "video": "youtube_long",   "carousel": "linkedin_post",
    "post": "linkedin_post",   "thread": "twitter_post",
    "story": "short_form",     "reel": "short_form",
    "short": "youtube_short",
}
```

**Platform-aware refinement:**
- `video` + `tiktok` → `short_form` (not `youtube_long`)
- `video` + `youtube` → `youtube_long`
- `post` + `twitter` → `twitter_post` (not `linkedin_post`)

**Item metadata:**
- `color_label`: `"purple"` (visual indicator for auto-generated items)
- `content_json.source`: `"auto_research"` (traceability)
- `content_json.research_session_id`: session UUID (back-reference)
- `content_json.research_idea`: full original idea object
- `notes`: pillar name + engagement level

**Frontend:**
- "Auto-Schedule Ideas" button (blue) appears after research completes
- Success state shows count + "View schedule" link that navigates to `/schedule`

---

#### 7. Research Error Recovery (Retry + Skip)
**Files:**
- `apps/api/app/services/brand_research.py` (MODIFIED — retry on failed + new `skip_stage()` function)
- `apps/api/app/routers/brands.py` (MODIFIED — added `POST /{brand_id}/research/{session_id}/skip`)
- `apps/web/src/lib/api/brand.ts` (MODIFIED — added `skipResearchStage()`)
- `apps/web/src/app/brands/[brandId]/components/research-panel.tsx` (MODIFIED — retry/skip UI)

**Backend changes:**

*Retry:* Modified `run_stage()` to allow retrying failed sessions. When session status is `"failed"`, it resets to `"running"` (clears error) and re-runs the failed stage instead of raising an error.

*Skip:* New `skip_stage()` function:
1. Identifies the current (failed/pending) stage
2. Marks it as completed with `{"_skipped": true}` result
3. Advances `current_stage` to the next stage
4. Clears the error
5. If it was the last stage, marks session as `"completed"`

**Frontend UI states:**

| Session Status | Buttons Shown |
|---------------|---------------|
| `running` / `pending` | "Run Next: {stage}" + "Run All" |
| `failed` | Error box + "Retry Failed Stage" + "Skip & Continue" (amber) |
| `completed` | "Apply Research to Brand Profile" + "Auto-Schedule Ideas" |
| Any terminal | "New Research" (resets to start form) |

**Error display:** Failed state shows a styled red box with the error message from the session, separate from transient UI errors.

---

## B. FILES CHANGED

### New Files
| File | Lines | Purpose |
|------|-------|---------|
| `apps/api/app/middleware/__init__.py` | 3 | Barrel export for middleware |
| `apps/api/app/middleware/rate_limit.py` | 201 | Rate limiting middleware |
| `infra/supabase/migrations/022_brand_research.sql` | ~30 | Research sessions table + RLS |
| `apps/api/app/services/brand_research.py` | ~600 | 7-stage research pipeline service |
| `apps/web/src/app/brands/[brandId]/components/research-panel.tsx` | ~510 | Research pipeline UI component |
| `docs/compound/patterns/slice-28-gap-analysis.md` | ~300 | Gap analysis document |
| `docs/compound/patterns/slice-29-production-hardening.md` | THIS | Session documentation |

### Modified Files
| File | Changes |
|------|---------|
| `apps/api/app/main.py` | Added rate limit middleware, header redaction, health fix |
| `apps/api/app/routers/schedule.py` | Added `POST /from-research/{session_id}` auto-schedule endpoint |
| `apps/api/app/routers/brands.py` | Added 6 research endpoints + skip endpoint |
| `apps/api/app/routers/brand.py` | SSRF hardening, error disclosure fix |
| `apps/api/app/routers/agent_bridge.py` | Search injection sanitization, schema validation |
| `apps/api/app/schemas/mission_control.py` | Field validators (max_length, pattern) |
| `apps/api/app/schemas/agent_bridge.py` | max_length on content + query fields |
| `apps/web/src/lib/api/client.ts` | Token refresh lock, 429 handling |
| `apps/web/src/lib/api/schedule.ts` | Added `createFromResearch()` |
| `apps/web/src/lib/api/brand.ts` | Added research + skip API methods |
| `apps/web/src/app/brands/new/page.tsx` | 3-step onboarding wizard |
| `apps/web/src/app/brands/[brandId]/page.tsx` | Research panel integration |

---

## C. NEW API ENDPOINTS

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/brands/{brand_id}/research` | Start research session |
| `GET` | `/brands/{brand_id}/research` | List sessions |
| `GET` | `/brands/{brand_id}/research/{session_id}` | Get session |
| `POST` | `/brands/{brand_id}/research/{session_id}/run` | Run stage(s) |
| `POST` | `/brands/{brand_id}/research/{session_id}/skip` | Skip failed stage |
| `POST` | `/brands/{brand_id}/research/{session_id}/apply` | Apply to profile |
| `POST` | `/schedule/from-research/{session_id}` | Auto-schedule from research |

---

## D. BEHAVIOR CHANGES

1. **Every API request** now goes through rate limiting. Exceeding the limit returns 429 with a `Retry-After` header. The frontend client handles this gracefully.
2. **Token refresh** is now atomic — concurrent 401s share a single refresh call instead of racing.
3. **Creating a new brand** walks through a guided wizard instead of a single form. Auto-research starts in the background if enabled.
4. **Completed research** can now be converted to schedule items with one click. Items appear as purple-labeled drafts in the kanban board.
5. **Failed research stages** can be retried or skipped. Skipped stages produce empty results but don't block the pipeline.
6. **All free-text inputs** to Mission Control and Agent Bridge are now length-validated at the Pydantic layer.

---

## E. TESTS + VERIFICATION

### Build Verification
| Check | Result |
|-------|--------|
| TypeScript (`tsc --noEmit`) | 0 errors |
| Next.js production build | Clean |
| Python module imports (7 modules) | All pass |

### Manual Verification Steps

**Rate limiting:**
1. Hit any API endpoint 31 times in 60 seconds
2. Verify 429 response with `Retry-After: 60` header
3. Verify `X-RateLimit-Remaining` decrements on each call

**Onboarding wizard:**
1. Navigate to `/brands/new`
2. Step through: name → industry (try a quick suggestion chip) → launch
3. Toggle auto-research ON, click "Create Brand & Start Research"
4. Verify redirect to brand page + research starts running

**Auto-scheduling:**
1. Complete a research pipeline (all 7 stages)
2. Click "Auto-Schedule Ideas"
3. Navigate to `/schedule` — verify purple-labeled draft items appear
4. Verify each item has research context in notes

**Error recovery:**
1. Start research, simulate a stage failure (or wait for one)
2. Verify "Retry Failed Stage" and "Skip & Continue" buttons appear
3. Click "Skip & Continue" — verify pipeline advances to next stage
4. Click "Retry Failed Stage" on a different failure — verify it re-runs

---

## F. RISKS + MITIGATIONS

| Risk | Mitigation |
|------|------------|
| Rate limiter is in-memory (resets on restart) | Acceptable for current scale. Redis swap documented in code. |
| Auto-schedule could create duplicates if clicked twice | Items have `research_session_id` in `content_json` for dedup. UI hides button after first success. |
| Skipped stages produce empty results | Downstream stages handle missing data gracefully (use defaults from seed input). |
| LLM format/platform mapping is lossy | Explicit `_FORMAT_MAP` + `_PLATFORM_MAP` with platform-aware refinement. Unmapped values fall back to `"note"` / `"other"`. |
| Rate limit bypass via X-Forwarded-For spoofing | Acceptable for current deployment. Production should configure trusted proxy headers. |

---

## G. ARCHITECTURE PATTERNS ESTABLISHED

### Pattern: Tiered Rate Limiting
```
Request → _get_tier(path, method) → (max_requests, window_seconds)
        → _store.is_allowed(key, max, window) → (allowed, remaining)
        → 429 or pass-through with headers
```
Key insight: Group rate key by `{IP}:{first_path_segment}` not full path, so `/brands/abc/research` and `/brands/def/research` share the same bucket per IP.

### Pattern: Research → Schedule Pipeline
```
Research Session (completed)
  → results.content_ideas.content_ideas[]
  → _FORMAT_MAP + _PLATFORM_MAP transform
  → ScheduledItem[] (draft, purple-labeled)
  → Batch insert → Kanban board
```

### Pattern: Stage Pipeline Error Recovery
```
Failed session → Retry: reset status + re-run same stage
              → Skip: mark stage completed with {_skipped: true} + advance
              → New Research: reset UI to start form
```

---

## H. WHAT'S NEXT (Remaining from Gap Analysis)

### Not yet addressed
- [ ] SSRF: Allowlist for web search URLs (currently only IP-based blocking)
- [ ] Agent bridge authentication: Move from static API key to JWT-based
- [ ] brand_chat.py refactor: Extract god object into smaller services
- [ ] Redis-backed rate limiting for multi-instance deployment
- [ ] Content pipeline integration tests
- [ ] PostHog analytics for research funnel tracking
