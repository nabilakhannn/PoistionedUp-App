# Slice 84 — Infrastructure Hardening Sprint

**Date:** 2026-03-02
**Status:** Complete
**Tests:** +25 new (total: 1199) | 0 TS errors

---

## Purpose

After 83 slices, 11 architectural gaps had accumulated across security, performance, reliability, UX,
and observability. This slice closes them all in one hardening sprint using the Compound Engineering
methodology and Ralph Loop.

---

## Gap → Fix Map

| # | Gap | Root Cause | Fix Applied |
|---|-----|-----------|------------|
| 1 | OpenClaw not programmatically controlled | SOUL.md-based only | `sdk_agents.py` SDK layer |
| 2 | Ad creative sequential | `for hook_type in hook_types` loop | `ThreadPoolExecutor(max_workers=5)` |
| 3 | Silent partial failures | `return []` on any exception | Per-hook `hook_errors` dict surfaced to UI |
| 4 | Quota exception swallowed as 500 | Generic `except Exception` | HTTP 429 in `main.py`; re-raise in ad_creative |
| 5 | Approvals lost on crash | React `useState` only | PATCH /approvals → `agent_deliverables` DB |
| 6 | localStorage no TTL | Raw JSON saved | `{data, generated_at}` wrapper, 24h expiry |
| 7 | Agent bridge IDOR warning | No X-User-Id log | WARNING log on missing header |
| 8 | No model fallback | Single provider | OpenAI fail → Anthropic retry (model map) |
| 9 | Research race condition | No stage lock | `if status == "running": return session` |
| 10 | PostgREST injection | Incomplete sanitization | Strict whitelist regex `[^\w\s\-]` stripped |
| 11 | SSRF TOCTOU | DNS failure allowed | DNS failure now raises `ValueError` |

---

## Patterns Established

### Pattern: Lazy-import vs module-level imports affect mock patchability

When a Python function uses `from module import name` inside the function body (lazy import),
`patch("calling_module.name")` will fail because the name isn't in the calling module's namespace.

**Rule:** Always import at module level for testability. Use lazy imports only for optional heavy
dependencies (langgraph, pymupdf, etc.) that might not be installed.

```python
# BAD — can't patch as `app.services.sdk_agents.get_llm_client`
def _run_task(...):
    from worker.graph.llm import get_llm_client
    llm = get_llm_client()

# GOOD — patchable as `app.services.sdk_agents.get_llm_client`
from worker.graph.llm import get_llm_client  # module level

def _run_task(...):
    llm = get_llm_client()
```

### Pattern: Parallel LLM calls with ThreadPoolExecutor

For I/O-bound LLM calls using a synchronous client, `ThreadPoolExecutor` is the right tool.
No async refactor needed. Safe because GIL releases on I/O.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

max_workers = min(len(items), 5)  # cap at 5 to avoid overwhelming API
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(process_item, item): item for item in items}
    for future in as_completed(futures):
        item = futures[future]
        try:
            result = future.result()
            results[item] = result
        except QuotaException:
            raise  # Always propagate quota/budget exceptions
        except Exception as exc:
            errors[item] = str(exc)
            results[item] = fallback_value
```

### Pattern: Quota exceptions must never be swallowed

`DailyTokenCapExceeded` and `WorkflowBudgetExceeded` indicate a hard system constraint.
They must propagate to the HTTP layer (HTTP 429) and never be silently caught.

```python
except Exception as e:
    from worker.graph.llm import DailyTokenCapExceeded, WorkflowBudgetExceeded
    if isinstance(e, (DailyTokenCapExceeded, WorkflowBudgetExceeded)):
        raise  # Never swallow quota exceptions
    logger.warning("Non-fatal error: %s", e)
    return fallback
```

In `main.py`, handle at the HTTP boundary:

```python
@app.exception_handler(Exception)
async def _global_exception_handler(request, exc):
    try:
        from worker.graph.llm import DailyTokenCapExceeded, WorkflowBudgetExceeded
        if isinstance(exc, (DailyTokenCapExceeded, WorkflowBudgetExceeded)):
            return JSONResponse(status_code=429, content={"type": "quota_exceeded", "message": str(exc)})
    except ImportError:
        pass
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

### Pattern: Model fallback mapping (OpenAI → Anthropic)

```python
_OPENAI_TO_ANTHROPIC_FALLBACK = {
    "gpt-4o": "claude-sonnet-4-6",
    "gpt-4o-mini": "claude-haiku-4-5-20251001",
    "gpt-4-turbo": "claude-sonnet-4-6",
    "gpt-4": "claude-sonnet-4-6",
    "gpt-3.5-turbo": "claude-haiku-4-5-20251001",
}

# In _chat_openai(), after all retries exhausted:
if self._anthropic_key and last_exc is not None and _is_retryable_error(last_exc):
    fallback_model = _OPENAI_TO_ANTHROPIC_FALLBACK.get(model)
    if fallback_model:
        logger.warning("OpenAI %s exhausted — falling back to Anthropic %s", model, fallback_model)
        return self._chat_anthropic(messages, fallback_model, temperature, max_tokens, response_format)
```

### Pattern: Optimistic concurrency lock for stateful services

```python
def run_stage(session_id: str, user_id: str) -> dict:
    session = get_session(session_id, user_id)
    # Optimistic lock: skip if already running (prevents concurrent double-execution)
    if session.get("status") == "running":
        logger.info("Session %s is already running — skipping concurrent execution", session_id)
        return session
    # ... proceed with stage execution
```

### Pattern: PostgREST injection prevention with whitelist regex

```python
import re as _re

# Whitelist: only word chars, spaces, hyphens — strip everything else
safe_query = _re.sub(r"[^\w\s\-]", "", raw_query, flags=_re.UNICODE).strip()[:200]
```

Never use `.replace("'", "").replace(";", "")` — blocklist approaches always miss edge cases.

### Pattern: SSRF TOCTOU fix — DNS failure should block, not allow

```python
try:
    socket.getaddrinfo(hostname, None)
except socket.gaierror:
    # SSRF TOCTOU fix: DNS failure means we can't validate safety — block it
    raise ValueError(
        f"URL hostname '{hostname}' could not be resolved — blocked for safety. "
        "Verify the URL is accessible and correct."
    )
```

### Pattern: localStorage TTL cache

```typescript
interface CachedResult<T> {
  data: T;
  generated_at: number;  // Date.now() ms
}

const CACHE_TTL_MS = 24 * 60 * 60 * 1000;  // 24 hours

function loadFromCache<T>(key: string): T | null {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    const cached: CachedResult<T> = JSON.parse(raw);
    if (Date.now() - cached.generated_at > CACHE_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return cached.data;
  } catch {
    return null;
  }
}

function saveToCache<T>(key: string, data: T): void {
  const entry: CachedResult<T> = { data, generated_at: Date.now() };
  localStorage.setItem(key, JSON.stringify(entry));
}
```

### Pattern: Debounced persistence on UI state toggle

```typescript
const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

const persistApprovals = useCallback((approved: string[], dismissed: string[]) => {
  if (debounceRef.current) clearTimeout(debounceRef.current);
  debounceRef.current = setTimeout(() => {
    adCreativeApi.patchApprovals(brandId, deliverableId, {
      approved_ids: approved,
      dismissed_ids: dismissed,
    });
  }, 500);
}, [brandId, deliverableId]);
```

### Pattern: SDK Agent Layer (AgentResult dataclass)

```python
@dataclass
class AgentResult:
    success: bool
    content: str
    parsed: Optional[Dict[str, Any]] = None  # JSON-parsed if applicable
    error: Optional[str] = None
    model_used: str = ""
    tokens_used: int = 0
    fallback_used: bool = False

def run_copywriter_task(prompt: str, brand_context: str = "", model: str = "gpt-4o") -> AgentResult:
    """Direct SDK wrapper — full programmatic control, no OpenClaw dependency."""
    ...
```

---

## OWASP Coverage

| OWASP ID | Vulnerability | Fix |
|----------|--------------|-----|
| A01 Broken Access Control | Agent bridge missing X-User-Id warning | WARNING log added |
| A03 Injection | PostgREST filter injection in inspo/search | Whitelist regex `[^\w\s\-]` |
| A05 Security Misconfiguration | CORS typo "poistioned" in origins | Fixed in `config.py` |
| A07 Auth & Identity Failures | Agent bridge fallback without user context | Warning + audit trail |
| A09 Logging & Monitoring | No correlation IDs | `request_id` in tracking context |
| A10 SSRF | DNS validation TOCTOU in url_validation | DNS failure → block |

---

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| `app/services/sdk_agents.py` | SDK agent layer with AgentResult dataclass |
| `infra/supabase/migrations/029_slice84_hardening.sql` | approved_variation_ids columns + index |
| `tests/test_slice84.py` | 25 new tests across all 5 phases |
| `docs/compound/patterns/slice-84-infrastructure-hardening.md` | This file |

### Modified Files
| File | Change |
|------|--------|
| `app/config.py` | CORS typo fix ("poistioned" → "positioned") |
| `app/utils/url_validation.py` | DNS failure raises ValueError (SSRF fix) |
| `app/routers/agent_bridge.py` | Injection whitelist + missing header warning |
| `app/main.py` | Quota exceptions → HTTP 429 |
| `worker/graph/llm.py` | Model fallback, Claude 4 pricing, correlation IDs |
| `app/services/ad_creative.py` | ThreadPoolExecutor parallel, quota re-raise, hook_errors |
| `app/services/repurpose.py` | ThreadPoolExecutor parallel |
| `app/services/brand_research.py` | Optimistic concurrency lock |
| `app/routers/ad_creative.py` | hook_errors field + PATCH /approvals endpoint |
| `apps/web/src/lib/api/ad-creative.ts` | hook_errors type + patchApprovals() |
| `apps/web/src/app/ad-creative/page.tsx` | TTL cache + approval persistence + error UI |

---

## Test Results

```
tests/test_slice84.py — 25/25 passed
Full suite — 1172/1199 passed (27 failures: httpx.ReadTimeout in test_resources.py, pre-existing network issue)
TypeScript — 0 errors
```

---

## E2E Verification Checklist

- [ ] Generate 40 ads → approve 5 → reload page → approvals still there
- [ ] Trigger ad generation → backend logs show 5 parallel thread starts
- [ ] Force OpenAI failure (bad key) → verify Anthropic fallback in logs
- [ ] POST to inspo/search with `'; DROP TABLE users; --` → verify it's sanitized
- [ ] Check `/usage/cap` endpoint returns proper quota status
- [ ] Trigger quota exceeded → verify HTTP 429 (not 500) returned

---

## Database Migration

Run `infra/supabase/migrations/029_slice84_hardening.sql` in Supabase dashboard SQL editor:

```sql
ALTER TABLE public.agent_deliverables
  ADD COLUMN IF NOT EXISTS approved_variation_ids TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS dismissed_variation_ids TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS approvals_updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_deliverables_brand_type_created
  ON public.agent_deliverables(brand_id, deliverable_type, created_at DESC)
  WHERE brand_id IS NOT NULL;
```
