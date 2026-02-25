# Pattern: PostHog Analytics Integration

**Created:** Slice 27
**Status:** Active

## What

Full-stack PostHog analytics integration covering user identification, custom event tracking, LLM usage monitoring, and pipeline lifecycle events.

## Architecture

### Frontend (Next.js)

```
posthog-js SDK
  -> lib/posthog.ts          (init, identify, trackEvent, trackPageView)
  -> app/posthog-provider.tsx (auto pageview on route change, wraps children with PHJSProvider)
  -> app/layout.tsx           (PostHogProvider wraps BrandProvider + children)
  -> individual pages         (usePostHog() hook for event capture)
```

### Backend (FastAPI)

```
posthog Python SDK
  -> app/services/analytics.py  (lazy singleton, identify_user, track_event, track_llm_event, track_pipeline_event, flush)
  -> app/routers/*.py            (track_event calls in endpoint handlers)
  -> worker/executor.py          (track_pipeline_event for lifecycle events)
```

## Key Patterns

### 1. Graceful No-Op

Both frontend and backend treat PostHog as optional. If the API key is missing, all calls become silent no-ops. This means the app works identically in dev (no key) and prod (key set).

Frontend:
```typescript
export function initPostHog() {
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) {
    console.warn("[PostHog] No NEXT_PUBLIC_POSTHOG_KEY set, analytics disabled");
    return;
  }
  // ...
}
```

Backend:
```python
def _get_client():
    api_key = getattr(settings, "posthog_api_key", "")
    if not api_key:
        logger.info("PostHog API key not set, server-side analytics disabled")
        return None
```

### 2. Never Crash on Analytics

All backend analytics calls wrap in try/except and log at debug level. Frontend uses optional chaining. Analytics should never break user flows.

```python
def track_event(user_id, event_name, properties=None):
    client = _get_client()
    if not client:
        return
    try:
        client.capture(distinct_id=user_id, event=event_name, properties=properties or {})
    except Exception as e:
        logger.debug("PostHog capture failed: %s", e)
```

### 3. Lazy Initialization with Singleton

Backend uses module-level globals with a `_initialized` flag to avoid re-running setup logic on every call. Frontend checks `initialized` boolean.

### 4. User Identification on Auth Events

Frontend identifies users immediately after Supabase auth succeeds (login/signup). This links all subsequent events to the user.

```typescript
if (data.session) {
  identifyUser(data.session.user.id, { email: data.session.user.email });
  trackEvent("user_logged_in", { method: "email" });
}
```

### 5. Manual Pageview Tracking

PostHog's automatic `capture_pageview` is disabled because Next.js App Router uses client-side navigation. Instead, `PostHogProvider` listens to `usePathname()` and `useSearchParams()` changes and fires `$pageview` manually.

### 6. Frontend Event Tracking via usePostHog Hook

Pages use `usePostHog()` from `posthog-js/react` to capture events inline:

```typescript
const posthog = usePostHog();
// In handler:
posthog.capture("inspo_board_created", { brand_id: brandId || "" });
```

### 7. Structured LLM Events

`track_llm_event` captures model, step, token counts, latency, and success/error status. This enables cost analysis and reliability dashboards in PostHog.

### 8. Pipeline Lifecycle Events

`track_pipeline_event` captures workflow lifecycle with event_type (started, completed, failed, interrupted) and optional step context.

## Event Naming Convention

| Category | Pattern | Examples |
|----------|---------|----------|
| Auth | `user_{action}` | `user_logged_in`, `user_signed_up` |
| Brand | `brand_{action}` | `brand_created`, `brand_chat_message_sent` |
| Content | `content_{action}` | `content_workflow_started`, `content_exported` |
| Inspo | `inspo_{entity}_{action}` | `inspo_board_created`, `inspo_item_starred` |
| Schedule | `schedule_item_{action}` | `schedule_item_created`, `schedule_item_moved` |
| Performance | `performance_{action}` | `performance_post_logged`, `performance_post_analyzed` |
| Knowledge | `resource_{action}` | `resource_created`, `resource_uploaded` |
| Pipeline | `pipeline_{event_type}` | `pipeline_started`, `pipeline_completed` |
| LLM | `llm_api_call` | Always `llm_api_call` with model/step in properties |
| Page | `$pageview` | Standard PostHog pageview |

## Files

| File | Role |
|------|------|
| `apps/web/src/lib/posthog.ts` | Client init, convenience wrappers |
| `apps/web/src/app/posthog-provider.tsx` | Route-change pageview tracker, PHJSProvider wrapper |
| `apps/web/src/app/layout.tsx` | Mounts PostHogProvider around app |
| `apps/api/app/services/analytics.py` | Server-side analytics service |
| `apps/api/app/config.py` | `posthog_api_key` + `posthog_host` settings |
| `apps/api/tests/test_analytics.py` | 21 tests for analytics service |

## Config

| Variable | Where | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_POSTHOG_KEY` | `.env` / Vercel env | Frontend PostHog project API key |
| `NEXT_PUBLIC_POSTHOG_HOST` | `.env` / Vercel env | PostHog API host (default: `https://us.i.posthog.com`) |
| `POSTHOG_API_KEY` | `.env` / backend env | Backend PostHog project API key |
| `POSTHOG_HOST` | `.env` / backend env | Backend PostHog API host |

## Gotchas

1. `posthog-js` must only initialize in the browser (`typeof window !== "undefined"`).
2. `capture_pageview: false` is required for Next.js App Router because the SDK cannot detect client-side navigations.
3. Backend `_get_client()` imports `settings` inside the function body to avoid circular imports at module load time.
4. Always pass `brand_id` in event properties to enable per-brand analytics filtering.
