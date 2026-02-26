# Slice 66: OpenClaw Agent Squad — Rename Jarvis → Jumbo + Dynamic Agent Creation + NotebookLM MCP

**Date:** 2026-02-25
**Methodology:** Compound Engineering + Ralph Loop
**Scope:** Full rename across 20+ files, dynamic agent creation capability, NotebookLM MCP wiring, deployment updates

---

## Executive Summary

This slice transforms the agent system from a placeholder-named orchestrator ("Jarvis") into the production-ready **Jumbo** orchestrator, adds the ability for Jumbo to dynamically create new specialist agents at runtime, and wires NotebookLM MCP integration for zero-hallucination research. All 30 existing tests continue to pass with zero regressions.

---

## A. WHAT WAS BUILT

### 1. Jarvis → Jumbo Rename (20+ files, 60+ references)

**Why:** "Jarvis" was a placeholder name. The human chose "Jumbo" as the orchestrator's permanent identity.

**Scope of changes:**

| Category | Files Changed | Reference Count |
|----------|--------------|-----------------|
| Agent configs | `openclaw.json`, `agents/jumbo/SOUL.md` (renamed from `agents/jarvis/`) | ~15 |
| Root docs | `SOUL.md`, `AGENTS.md` (read-only), `HEARTBEAT.md`, `task_board.md` | ~10 |
| Playbooks | `AGENT_BRIDGE_PLAYBOOK.md`, `OPENCLAW_NOTEBOOKLM_PLAYBOOK.md` | ~12 |
| Specialist agents | 5x `agents/{name}/SOUL.md` | ~10 |
| Backend Python | `services/agent_orchestrator.py`, `routers/mission_control.py` | ~8 |
| Frontend TSX | `mission-control/orchestrator/page.tsx` | ~6 |
| Analytics | `analytics/__init__.py`, `tracker.py`, `cli.py`, `client.py` | ~5 |
| Deploy | `Dockerfile`, `env.example`, `DEPLOYMENT.md` | ~4 |

**Key code changes:**

```python
# apps/api/app/services/agent_orchestrator.py
"from_agent_id": "jumbo",   # was "jarvis"
"to_agent_id": "jumbo",     # was "jarvis"

# apps/api/app/routers/mission_control.py
DEFAULT_AGENTS = [
    {
        "id": "jumbo",              # was "jarvis"
        "name": "Jumbo",            # was "Jarvis"
        "role": "Orchestrator",
        "skills": ["coordination", "decomposition", "delegation",
                   "monitoring", "reporting", "agent-creation"],  # added agent-creation
        "workspace_path": "./agents/jumbo",   # was "./agents/jarvis"
    },
    ...
]
```

```typescript
// apps/web/src/app/mission-control/orchestrator/page.tsx
const jumbo = agents.find((a) => a.id === "jumbo");  // was "jarvis"
{jumbo?.name || "Jumbo"}                              // was "Jarvis"
```

---

### 2. Dynamic Agent Creation Capability

**Added to:** `agents/jumbo/SOUL.md`

Jumbo can now create new specialist agents at runtime when the human requests a capability the current squad doesn't cover.

**How it works:**

1. Jumbo writes a new `agents/{agent-id}/SOUL.md` using the specialist template
2. Spawns the agent via `sessions_spawn` with the new `agentId`
3. Registers the agent in `task_board.md`
4. Notifies the human via Telegram

**Rules enforced:**
- Maximum 8 total agents in the squad
- New agents inherit ALL rules from root `SOUL.md`
- New agents NEVER get direct Brain API access (only Jumbo has that)
- New agents default to `gpt-4o-mini` (cost savings)
- Human confirmation required before creating permanent roles

**Config change in `openclaw.json`:**
```json
"allowAgents": ["trend-analyzer", "copywriter", "visual-designer",
                "distributor", "analytics", "*"]
```
The `"*"` wildcard allows Jumbo to spawn dynamically-named agents.

**Specialist SOUL Template** (embedded in Jumbo's SOUL.md):
```markdown
# {AGENT_NAME} — {ROLE}
> {One-line purpose}

## IDENTITY
## CAPABILITIES (3-5 items)
## BOUNDARIES
## SECURITY RULES (inherits root SOUL.md)
## TOOLS
## USING THE POSITIONEDUP BRAIN (via Jumbo)
## OUTPUT FORMAT
## DELIVERABLE SUBMISSION
```

---

### 3. NotebookLM MCP Integration

**What:** Wired the NotebookLM MCP server into OpenClaw for zero-hallucination research synthesis.

**Changes:**

| File | Change |
|------|--------|
| `openclaw.json` | Added `mcp.servers.notebooklm` config block |
| `deploy/Dockerfile` | Added `notebooklm-mcp@latest` to npm global install |
| `deploy/Dockerfile` | Added `COPY` for `OPENCLAW_NOTEBOOKLM_PLAYBOOK.md` |
| `deploy/env.example` | Added `GOOGLE_ACCESS_TOKEN` optional section |

```json
// openclaw.json
"mcp": {
  "servers": {
    "notebooklm": {
      "command": "npx",
      "args": ["notebooklm-mcp@latest"],
      "env": {
        "GOOGLE_ACCESS_TOKEN": "${GOOGLE_ACCESS_TOKEN}"
      }
    }
  }
}
```

---

## B. ALL FILES CHANGED

### Renamed
| Old Path | New Path |
|----------|----------|
| `agents/jarvis/SOUL.md` | `agents/jumbo/SOUL.md` |

### Modified
| File | Changes |
|------|---------|
| `openclaw.json` | id/name/workspace → "jumbo", 3 cron agentIds → "jumbo", added MCP config, `"*"` in allowAgents, `GOOGLE_ACCESS_TOKEN` in optional env |
| `SOUL.md` | All "Jarvis" → "Jumbo" in hierarchy, brain connection, agent paths |
| `HEARTBEAT.md` | "Jarvis (Orchestrator)" → "Jumbo (Orchestrator)" |
| `task_board.md` | Brain injection note + backlog instruction → "Jumbo" |
| `AGENT_BRIDGE_PLAYBOOK.md` | All Jarvis/JARVIS → Jumbo/JUMBO (architecture diagram, workflows, security, setup) |
| `OPENCLAW_NOTEBOOKLM_PLAYBOOK.md` | agentId + file paths → "jumbo" |
| `agents/jumbo/SOUL.md` | Title, identity, API examples, + dynamic agent creation section |
| `agents/trend-analyzer/SOUL.md` | All "Jarvis"/"@jarvis" → "Jumbo"/"@jumbo" |
| `agents/copywriter/SOUL.md` | All "Jarvis"/"@jarvis" → "Jumbo"/"@jumbo" |
| `agents/visual-designer/SOUL.md` | All "Jarvis"/"@jarvis" → "Jumbo"/"@jumbo" |
| `agents/distributor/SOUL.md` | All "Jarvis"/"@jarvis" → "Jumbo"/"@jumbo" |
| `agents/analytics/SOUL.md` | All "Jarvis"/"@jarvis" → "Jumbo"/"@jumbo" |
| `apps/api/app/services/agent_orchestrator.py` | `from_agent_id`/`to_agent_id` → "jumbo", docstrings |
| `apps/api/app/routers/mission_control.py` | DEFAULT_AGENTS[0] → jumbo (id, name, about, workspace, skills), queries |
| `apps/web/src/app/mission-control/orchestrator/page.tsx` | All `jarvis` vars → `jumbo`, fallback names |
| `analytics/__init__.py` | Docstring examples → "jumbo" |
| `analytics/tracker.py` | Default params → "jumbo" |
| `analytics/cli.py` | Docstring + defaults → "jumbo" |
| `analytics/client.py` | Example → "jumbo" |
| `deploy/Dockerfile` | Added `notebooklm-mcp@latest`, added COPY for playbook |
| `deploy/env.example` | Comment update + NotebookLM MCP section |

---

## C. ARCHITECTURE PATTERNS

### Pattern: Systematic Cross-Codebase Rename

When renaming an identity across agent configs, backend, frontend, and documentation:

1. **Discover first** — Use grep/explore to find ALL references before editing anything
2. **Categorize by file type** — Config files, Python, TypeScript, Markdown all have different patterns
3. **Use `replace_all: true`** for bulk replacements within documentation files
4. **Use targeted edits** for code files where context matters (variable names, string literals, comments)
5. **Verify with tests** — All 30 existing tests must still pass

### Pattern: Dynamic Agent Creation in Multi-Agent Systems

```
Human requests new capability
  → Jumbo evaluates if existing agents cover it
  → If not: creates agents/{id}/SOUL.md from template
  → Spawns via sessions_spawn
  → New agent inherits root SOUL.md security rules
  → New agent communicates through Jumbo (no direct API access)
  → Registered in task_board.md for visibility
```

**Key constraints:**
- Cap total agents (8 max) to prevent runaway spawning
- Default to cheapest model tier (gpt-4o-mini)
- Require human confirmation for permanent roles
- All Brain access proxied through orchestrator

### Pattern: MCP Server Integration in OpenClaw

```json
{
  "mcp": {
    "servers": {
      "server-name": {
        "command": "npx",
        "args": ["package@latest"],
        "env": { "TOKEN": "${ENV_VAR}" }
      }
    }
  }
}
```
- MCP servers are declared in `openclaw.json`
- Environment variables use `${VAR}` syntax for runtime substitution
- Must also install the npm package in the Dockerfile
- Optional tokens documented in `env.example`

---

## D. BUILD VERIFICATION

| Check | Result |
|-------|--------|
| Python tests (`pytest tests/ -v`) | 30/30 passed (0.26s) |
| TypeScript (`tsc --noEmit`) | 0 errors |
| Python imports (8 modules) | All pass |
| Grep for remaining "jarvis" in agents/ | 0 results (clean) |
| Grep for remaining "jarvis" in backend code | 0 results (clean) |
| Agent directory structure | `agents/jumbo/` exists, `agents/jarvis/` removed |

---

## E. DEPLOYMENT READINESS

### What's Ready
- All agent SOUL.md files configured with "Jumbo" identity
- `openclaw.json` gateway config complete (6 agents, 3 crons, MCP, Telegram)
- `Dockerfile` builds with all dependencies (openclaw, notebooklm-mcp)
- `docker-compose.yml` with host networking
- `env.example` documents all required/optional variables

### What the Human Needs to Do
1. Provision VPS (Hostinger/Hetzner) or use existing one
2. Set up API keys: OpenAI, Anthropic, Telegram bot token
3. Generate `AGENT_API_KEY` (must match Vercel backend's `AGENT_API_KEY`)
4. Copy `env.example` → `.env` and fill in values
5. `docker compose up -d --build`
6. Test via SSH tunnel: `ssh -L 18789:localhost:18789 root@VPS_IP`
7. Open `http://localhost:18789` for OpenClaw Control UI

---

## F. WHAT'S NEXT

| Priority | Task | Description |
|----------|------|-------------|
| P0 | Deploy to VPS | Build Docker image, start container, verify Telegram bot responds |
| P1 | Test Agent Bridge | Verify Jumbo can call all 9 `/agent-api/*` endpoints |
| P1 | First content run | Trigger content pipeline through Jumbo to test full loop |
| P2 | NotebookLM setup | Get Google OAuth token, test MCP server integration |
| P2 | Analytics dashboard | Verify PostHog events flow from agent actions |
