# Slice 72: Deployment-Ready Hardening

**Date:** 2026-02-26
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Fix critical deployment blockers, remove dead config, add error visibility, and make Mission Control sub-pages discoverable from the sidebar navigation.

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `openclaw.json` | Updated | Fixed port 3838 → 18789 (matches Docker/Caddy/env) |
| `deploy/env.example` | Rewritten | Added Section B with all backend vars (Supabase, OAuth, Tavily, cost governance) |
| `apps/api/app/config.py` | Updated | Removed dead Agent Zero config (3 unused fields) |
| `apps/api/app/routers/brand.py` | Updated | Added `logger.warning` to 2 silent exception blocks |
| `apps/api/app/routers/workflows.py` | Updated | Added `logger.warning` to 1 silent exception block |
| `apps/api/app/services/brand_strategist.py` | Updated | Added `logger.warning` to 1 silent exception block |
| `apps/api/app/services/ingestion.py` | Updated | Added `logger.debug` to 3 silent exception blocks |
| `apps/web/src/app/nav-bar.tsx` | Updated | Mission Control expandable sub-nav with 5 sub-pages |

## Critical Fix: Port Mismatch

**Before:** `openclaw.json` configured port 3838, but Docker/Caddy/env.example all used 18789.
**After:** All components consistently use port 18789.

```
openclaw.json → "port": 18789
Dockerfile    → CMD --port 18789
docker-compose → 127.0.0.1:18789:18789
Caddyfile     → reverse_proxy localhost:18789
```

## env.example Completeness

**Before:** 11 VPS-only vars, missing all backend API vars.
**After:** Two clearly labeled sections:

| Section | Vars | Purpose |
|---------|------|---------|
| **A: VPS** | 13 vars | OpenClaw gateway, LLM keys, Telegram, Agent Bridge, PostHog |
| **B: Backend** | 16 vars | Supabase, Tavily, gateway connection, OAuth, cost governance |

Every field in `config.py` now has a corresponding entry in `env.example`.

## Dead Config Removal

Removed from `config.py`:
- `agent_zero_enabled: bool = False`
- `agent_zero_docker_image: str = "agent0ai/agent-zero:latest"`
- `agent_zero_timeout_seconds: int = 120`

**Verified:** No code anywhere references these fields. `langgraph_db_uri` was kept — it IS used in `worker/graph/pipeline.py:47`.

## Silent Exception Logging

**Categorization:**
- **7 real error swallowers** → added `logger.warning` (with `exc_info=True` for stack traces) or `logger.debug` for expected failures
- **3 JSON parsing fallbacks** → left as `pass` (intentional control flow in strategy pattern)

| File | Line | Level | Context |
|------|------|-------|---------|
| `brand.py:622` | warning | Performance context fetch failed |
| `brand.py:630` | warning | Memory context fetch failed |
| `workflows.py:302` | warning | DB update to mark workflow as failed... also failed |
| `brand_strategist.py:238` | warning | Auto-context build failed |
| `ingestion.py:411` | debug | YouTube manual transcript not found (expected) |
| `ingestion.py:421` | debug | YouTube transcript iterator failed (expected) |
| `ingestion.py:882` | debug | Twitter oEmbed extraction failed (external API) |

## Mission Control Expandable Nav

**Before:** Single "Mission Control" link at `/mission-control` — sub-pages undiscoverable.
**After:** Expandable section with chevron toggle showing all 5 sub-pages:

```
▾ Mission Control
    Dashboard
    Analytics
    Orchestrator
    Gateway
    Agent Chat
```

- Auto-expands when user navigates to any MC page
- Parent button highlighted when on any MC page
- Sub-links show active state for exact match
- ChevronIcon reused from existing brand dropdown component

## Security Review

1. **env.example**: No real secrets — all values are clearly marked as placeholders
2. **Port fix**: Closes a deployment misconfiguration that would have caused gateway to be unreachable
3. **Error logging**: `exc_info=True` on warnings captures full stack traces server-side but never leaks to clients
4. **No new endpoints**: This slice only fixes existing code paths
5. **Dead config removal**: Eliminates confusion about Agent Zero capabilities

## Patterns

- **Config-as-documentation**: `env.example` should be the single source of truth for all required env vars, organized by deployment target
- **Port consistency check**: When multiple components reference the same port, verify they all agree (openclaw.json, Dockerfile CMD, docker-compose ports, Caddyfile proxy)
- **Logging triage**: Not all `except: pass` is bad — JSON parsing strategy patterns should stay silent; real operational errors need `logger.warning`
- **Expandable nav groups**: When a section has 3+ sub-pages, use a collapsible group instead of adding all to the flat nav list
