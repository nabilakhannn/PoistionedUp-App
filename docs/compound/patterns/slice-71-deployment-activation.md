# Slice 71: Deployment Activation — Mock Gateway + Runbook

**Date:** 2026-02-26
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Enable local development and demos without a running VPS by adding a mock gateway mode. Provide a deployment runbook so the system can be activated on Hostinger VPS.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      OPENCLAW_MOCK_MODE                         │
│                                                                 │
│  ┌──────────┐  mock=false  ┌──────────────┐   HTTP   ┌───────┐ │
│  │ Frontend  │ ──────────► │ gateway_client│ ───────► │  VPS  │ │
│  │ Dashboard │             │              │          │Gateway│ │
│  │ Chat      │  mock=true  │              │          └───────┘ │
│  └──────────┘  ──────────► │ gateway_mock │ (no HTTP calls)    │
│                            └──────────────┘                    │
│                                                                 │
│  Config:  settings.openclaw_mock_mode (bool, default False)    │
│  Toggle:  OPENCLAW_MOCK_MODE=true in .env                      │
│  Badge:   "DEMO MODE" shown on Gateway + Chat pages            │
└─────────────────────────────────────────────────────────────────┘
```

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/app/config.py` | Updated | Added `openclaw_mock_mode: bool = False` |
| `apps/api/app/services/gateway_mock.py` | Created | Mock implementations for all gateway functions |
| `apps/api/app/services/gateway_client.py` | Updated | Early-return delegation to mock when enabled |
| `apps/web/src/lib/api/gateway.ts` | Updated | Added `mock_mode` to TypeScript interfaces |
| `apps/web/src/app/mission-control/gateway/page.tsx` | Updated | DEMO MODE badge on gateway dashboard |
| `apps/web/src/app/mission-control/chat/page.tsx` | Updated | DEMO MODE badge on chat console |
| `apps/api/tests/test_gateway.py` | Updated | 10 new mock tests + fixed 8 existing tests |
| `deploy/DEPLOYMENT-RUNBOOK.md` | Created | One-page deployment guide |
| `deploy/env.example` | Updated | Added `OPENCLAW_MOCK_MODE` option |

## Mock Gateway Design

### Delegation Pattern
Each public function in `gateway_client.py` starts with:
```python
if settings.openclaw_mock_mode:
    from app.services.gateway_mock import mock_check_health
    return await mock_check_health()
```

This keeps mock logic fully separated from real gateway code. The import is deferred to avoid loading mock data when not needed.

### Mock Data
- **6 agents** with correct IDs, models, channels, and status (matches `openclaw.json`)
- **2 mock sessions** (Jumbo active, Trend Analyzer idle)
- **Per-agent response personas**: Each agent has contextually relevant demo responses
- **Realistic health**: `connected=True`, `mock_mode=True`, random latency 1-5ms
- **Session continuity**: Preserves passed `session_id`, generates UUID for new sessions

### Frontend Indicators
Both Gateway Dashboard and Chat Console show a `DEMO MODE` badge:
```tsx
{isMockMode && (
  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border
    bg-violet-500/15 text-violet-400 border-violet-500/20">
    DEMO MODE
  </span>
)}
```

## Deployment Runbook

Created `deploy/DEPLOYMENT-RUNBOOK.md` covering:
1. **5-step quick start** for VPS activation
2. **Local dev with mock mode** (one env var toggle)
3. **HTTPS setup** with Caddy
4. **Troubleshooting table** for common issues
5. **Architecture diagram** showing component connections

## Security Review

1. **Mock mode cannot be triggered accidentally**: Defaults to `False`, requires explicit `OPENCLAW_MOCK_MODE=true` in env
2. **Mock responses clearly labeled**: `mock_mode: True` flag in all health responses, `version: "1.0.0-mock"`
3. **No secrets in mock data**: Mock responses contain only demo text, no real tokens/keys
4. **Gateway URL shown as `mock://localhost (demo mode)`**: Cannot be confused with real connection
5. **No bypass of auth**: Mock mode only affects gateway client internals; JWT auth still required on all endpoints
6. **Message cap still enforced**: `message[:10000]` limit applies even in mock mode (via client layer)
7. **Existing test isolation**: All tests that patch settings now explicitly set `openclaw_mock_mode = False` to prevent MagicMock truthy leak

## Tests

- **10 new tests** in `TestMockGateway` class:
  - Direct mock function tests (health, agents, sessions, messages)
  - Integration tests via gateway_client with mock_mode=True
  - Full status flag propagation
- **8 existing tests fixed**: Added `openclaw_mock_mode = False` to prevent MagicMock attribute leak
- **866/866 Python tests passing** (up from 856)
- **0 TypeScript errors**

## Patterns

- **Feature toggle delegation**: Single boolean config toggle routes all calls to mock at function entry point
- **Deferred import**: Mock module imported only when needed (`from ... import` inside if-block)
- **MagicMock attribute defense**: When patching settings in tests, always explicitly set new boolean attributes to prevent truthy-by-default leak
- **DEMO MODE badge**: Visual indicator on all pages that use gateway data when mock mode active
- **Runbook-driven deployment**: One-page guide reduces deployment from exploration to checklist execution
