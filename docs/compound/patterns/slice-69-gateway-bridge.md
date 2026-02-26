# Slice 69: OpenClaw Gateway Bridge + Deployment Health Dashboard

**Date:** 2026-02-26
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Connect the Vercel-hosted PositionedUp API to the Hostinger VPS-hosted OpenClaw agent runtime. Provide a deployment health dashboard in Mission Control so the owner can verify gateway connectivity, agent status, and deployment readiness at a glance.

## Architecture

```
┌──────────────┐   HTTPS   ┌───────────────────┐   HTTP   ┌──────────────┐
│  Next.js UI  │ ───────── │  FastAPI (Vercel)  │ ──────── │  OpenClaw VPS │
│  /gateway    │  JWT auth  │  /gateway/*        │  Bearer   │  :18789       │
└──────────────┘           └───────────────────┘          └──────────────┘
```

- **Direction:** PositionedUp API → OpenClaw gateway (outbound proxy)
- **Complement:** Agent Bridge (`/agent-api/*`) handles the reverse direction (agents → API)
- **Auth:** JWT required on all frontend-facing endpoints; Bearer token for gateway-to-VPS

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/app/config.py` | Updated | Added `openclaw_gateway_url` and `openclaw_gateway_token` settings |
| `apps/api/app/services/gateway_client.py` | Created | HTTP client: health check, agent listing, sessions, message relay, full status aggregation |
| `apps/api/app/routers/gateway.py` | Created | 5 proxy endpoints: `/gateway/{health,status,agents,sessions,message}` |
| `apps/api/app/main.py` | Updated | Registered gateway router |
| `apps/api/app/middleware/rate_limit.py` | Updated | Added gateway rate limit tiers (LLM for message, WRITE for reads) |
| `apps/web/src/lib/api/gateway.ts` | Created | TypeScript API client with full type definitions |
| `apps/web/src/lib/api/index.ts` | Updated | Re-export gateway module |
| `apps/web/src/app/mission-control/gateway/page.tsx` | Created | Deployment dashboard: health, checklist, agents, sessions |
| `apps/web/src/app/mission-control/page.tsx` | Updated | Added Gateway sub-nav link |
| `apps/web/src/app/mission-control/analytics/page.tsx` | Updated | Added Gateway sub-nav link |
| `apps/web/src/app/mission-control/orchestrator/page.tsx` | Updated | Added Gateway sub-nav link |
| `deploy/env.example` | Updated | Added gateway connection env vars |
| `apps/api/tests/test_gateway.py` | Created | 30 tests covering all gateway functionality |

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/gateway/health` | Check gateway connectivity + latency |
| GET | `/gateway/status` | Full status: health + agents + sessions + checklist |
| GET | `/gateway/agents` | List agents from gateway (fallback to config) |
| GET | `/gateway/sessions` | List active gateway sessions |
| POST | `/gateway/message` | Send message to agent via gateway |

## Security

1. **JWT auth** on all 5 endpoints (Depends(get_current_user))
2. **Input validation** — agent_id regex `^[a-zA-Z0-9_-]+$`, message max 10k chars
3. **Response sanitization** — `_sanitize_agent()`, `_sanitize_session()`, `_sanitize_message_response()` strip internal fields
4. **URL masking** — `_mask_url()` strips credentials from gateway URLs before returning to frontend
5. **Rate limiting** — `/gateway/message` at LLM tier (30/min), reads at WRITE tier (60/min)
6. **Timeout protection** — 5s connect, 30s read for health/agents, 60s read for messages
7. **Generic error messages** — raw gateway errors logged server-side, generic messages returned to client

## Dashboard Features

- **Connection status** — 4 stat cards (status, latency, agents loaded, active sessions)
- **Deployment checklist** — 7 items with pass/fail/warn/skip indicators
- **Agent roster** — live list from gateway with model, channels, default flag
- **Sessions panel** — active sessions with agent, status, message count
- **Quick deploy guide** — shown when gateway is offline, links to deployment docs
- **Auto-refresh** — polls every 30 seconds

## Patterns

- **Gateway proxy pattern:** API acts as secure proxy between frontend and agent runtime — frontend never talks directly to VPS
- **Graceful degradation:** When gateway is unreachable, agent list falls back to `openclaw.json` config, dashboard shows deploy guide
- **Deployment checklist pattern:** Dynamic verification list built from runtime health + config state, drives dashboard UI
- **Sanitize all external responses:** Never pass raw third-party JSON to frontend — extract only known-safe fields

## Tests

- 30 new tests in `test_gateway.py`
- 856/856 total Python tests passing
- 0 TypeScript errors
- Test classes: HealthCheck(5), Agents(2), Checklist(3), URLMasking(3), Sanitization(2), FullStatus(1), Router(5), MessageValidation(6), ConfigFallback(3)
