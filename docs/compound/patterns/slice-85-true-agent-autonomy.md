# Slice 85 — True Agent Autonomy: Tool Use, Playbooks, Ledger, Connectors

**Date:** 2026-03-02
**Status:** Complete
**Tests:** 1231 total (+32) | 32/32 slice tests pass | 0 TS errors

---

## What Was Built

Transformed agents from one-shot LLM callers into truly autonomous, multi-step reasoning
agents. Added four interlocking systems: an Anthropic Messages API tool-use loop engine,
an append-only agent ledger (audit trail), editable per-agent playbooks (SOPs), and
encrypted per-user social media / webhook connectors.

---

## Architecture

```
User request → FastAPI endpoint
                 ↓
         tool_use_agents.py          (new engine — replaces single LLM call)
         ┌────────────────────────────────────────────────────────────────┐
         │  1. Read playbook from agent_playbooks table (DB)             │
         │  2. Start Anthropic Messages API loop (MAX_TOOL_TURNS = 6)    │
         │  3. For each tool call:                                        │
         │     a. Execute tool (Perplexity / Gemini / Supabase / rules)  │
         │     b. Write to agent_ledger (append-only, secrets redacted)  │
         │     c. Return result → Claude reasons → next step             │
         │  4. Write sdk_agent_runs row (status + token counts)          │
         │  5. Return AgentResult (same public API as before)            │
         └────────────────────────────────────────────────────────────────┘
```

### LLM Routing Strategy (cost-optimised)

| Task Type | Model | Why |
|-----------|-------|-----|
| Copywriting, hooks, emails, ad creative | `claude-sonnet-4-6` | Best writer |
| Web research, trend analysis | Perplexity `sonar-pro` | Real-time web + citations |
| Multi-source research synthesis | Gemini 2.0 Flash | Huge context, low cost |
| QA review, structured scoring | `gpt-4o-mini` | Already integrated, cheapest |
| Embeddings | `text-embedding-3-small` | Already integrated |

**Key insight:** Claude handles writing only. Research uses dedicated search models
(Perplexity, Gemini) which are ~70% cheaper for retrieval-heavy operations.

---

## Tool Catalogue

| Tool | Implementation | Used by |
|------|----------------|---------|
| `web_search` | Perplexity REST → Tavily fallback | trend-analyzer, competitor-analyst |
| `synthesize_research` | Gemini 2.0 Flash REST | trend-analyzer, research tasks |
| `fetch_brand_profile` | Supabase admin query | copywriter, qa-reviewer |
| `read_playbook` | Supabase admin query | all agents |
| `score_content_quality` | Rule-based, no LLM | qa-reviewer |

---

## Database (Migration 030)

4 new tables, all idempotent `IF NOT EXISTS`, all with RLS:

```sql
-- 1. agent_playbooks — editable SOPs per agent per user
UNIQUE(user_id, agent_id)
-- Two-step edit: pending_edit_md → apply → playbook_md (version++)

-- 2. agent_ledger — append-only audit trail
-- No UPDATE or DELETE RLS policy — immutable once written
-- Secrets always redacted via _redact() before storage

-- 3. user_connectors — encrypted social credentials
UNIQUE(user_id, service)
-- Fernet AES-128-CBC; key from CONNECTOR_ENCRYPTION_KEY env var

-- 4. sdk_agent_runs — run metadata (not ledger entries)
-- status: running | completed | failed
```

---

## Key Patterns

### Anthropic Tool-Use Loop
```python
MAX_TOOL_TURNS = 6
MAX_TOKENS_PER_CALL = 2048
WRITING_MODEL = "claude-sonnet-4-6"

for turn in range(MAX_TOOL_TURNS):
    resp = client.messages.create(tools=TOOLS, messages=messages, ...)
    if resp.stop_reason == "end_turn":
        # extract text → write ledger output → return AgentResult
        break
    if resp.stop_reason == "tool_use":
        # execute each tool → write ledger → append results → continue
```

### Perplexity Search (primary web search)
```python
# POST https://api.perplexity.ai/chat/completions
# model: sonar-pro, returns citations in response
# Falls back to Tavily if PERPLEXITY_API_KEY not set
```

### Gemini Synthesis
```python
# POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent
# ?key=GEMINI_API_KEY
# Used for synthesize_research tool — combines multiple sources
```

### Secret Redaction for Ledger
```python
_SECRET_RE = re.compile(
    r"(Bearer\s+)\S+|sk-\S+|AQE\S+|AIza\S+|EAA\S+",
    re.IGNORECASE,
)

def _redact(text: str) -> str:
    return _SECRET_RE.sub(r"\1[REDACTED]", text)
```
Applied to ALL tool inputs/results before ledger write. Never blocks main task
(wrapped in `try/except`).

### Fernet Credential Encryption
```python
from cryptography.fernet import Fernet

def _get_fernet(key: str) -> Fernet:
    # Validates key is URL-safe base64 encoded 32 bytes
    # Raises ValueError if key missing, RuntimeError if cryptography not installed
    return Fernet(key.encode())
```
`CONNECTOR_ENCRYPTION_KEY` must be set at startup. Key validated on import.

### Backwards Compatibility in sdk_agents.py
```python
def run_copywriter_task(
    prompt: str,
    brand_context: str = "",
    model: str = "gpt-4o",
    user_id: str = "",          # NEW — optional
    brand_id: str = "",          # NEW — optional
    use_tool_use: bool = False,  # NEW — default False preserves existing callers
) -> AgentResult:
    if use_tool_use and user_id:
        return run_tool_use_agent(...)  # new multi-step path
    return _run_task(...)  # original single-call path (unchanged)
```

### Playbook Two-Step Edit
```
PATCH /playbooks/{agent_id}/propose → writes pending_edit_md
POST  /playbooks/{agent_id}/apply   → pending_edit_md → playbook_md, version++
```
Prevents accidental overwrites. Pending edits show badge in UI.

---

## SSRF Protection (Webhook Connectors)

```python
from app.utils.url_validation import validate_url_for_fetch as validate_url
# Blocks private IPs (10.x, 192.168.x, 127.x, 169.254.x, ::1)
# DNS failure blocks (not allows) — TOCTOU fix from Slice 84
# Applied to webhook URLs before save AND before test
```

---

## Security Checklist (OWASP)

| # | Risk | Mitigation |
|---|------|-----------|
| A01 | User reads another's ledger/playbook/connector | JWT + RLS `user_id = auth.uid()` |
| A02 | Credentials stored plaintext | Fernet AES-128-CBC; key in env var; never logged |
| A03 | Tool query injection to Perplexity | Strip HTML, max 200 chars input |
| A05 | Encryption key missing → silent fail | Config validator raises at startup |
| A07 | Connector test leaks creds in error | Catch all exceptions, return safe string only |
| A09 | Secrets in ledger audit trail | `_redact()` regex strips all known token patterns |
| A10 | Webhook SSRF → internal network | `validate_url_for_fetch()` blocks private IPs + DNS failures |

---

## Files Changed

### New Files (15)
| File | Purpose |
|------|---------|
| `infra/supabase/migrations/030_claude_agent_sdk.sql` | 4 tables + RLS policies |
| `apps/api/app/services/tool_use_agents.py` | Anthropic tool-use loop engine |
| `apps/api/app/services/playbooks.py` | Playbook CRUD + 8 default SOPs |
| `apps/api/app/services/connectors.py` | Connector encrypt/decrypt + service tests |
| `apps/api/app/routers/playbooks.py` | Playbook endpoints (list/get/seed/propose/apply) |
| `apps/api/app/routers/ledger.py` | Ledger read endpoints (runs/entries/summary) |
| `apps/api/app/routers/connectors.py` | Connector CRUD endpoints |
| `apps/web/src/app/mission-control/playbooks/page.tsx` | Playbooks Mission Control UI |
| `apps/web/src/app/mission-control/ledger/page.tsx` | Ledger/Audit Mission Control UI |
| `apps/web/src/app/mission-control/settings/page.tsx` | Connectors Settings UI |
| `apps/web/src/lib/api/playbooks.ts` | Playbooks API client |
| `apps/web/src/lib/api/ledger.ts` | Ledger API client |
| `apps/web/src/lib/api/connectors.ts` | Connectors API client |
| `apps/api/tests/test_slice85.py` | 32 new tests |
| `docs/compound/patterns/slice-85-true-agent-autonomy.md` | This file |

### Modified Files (6)
| File | Change |
|------|--------|
| `apps/api/app/services/sdk_agents.py` | Added `use_tool_use`, `user_id`, `brand_id` params (backwards compatible) |
| `apps/api/app/main.py` | Registered 3 new routers: playbooks, ledger, connectors |
| `apps/api/app/config.py` | Added `perplexity_api_key`, `gemini_api_key`, `connector_encryption_key` |
| `apps/web/src/app/mission-control/constants.ts` | Added Playbooks, Ledger, Settings to MC_SUB_NAV |
| `apps/api/requirements.txt` | Added `cryptography>=43.0.0` |
| `apps/api/requirements-full.txt` | Added `cryptography>=43.0.0` |

---

## Test Results

| Group | Tests | Result |
|-------|-------|--------|
| TestToolUseAgentLoop | 7 | ✅ pass |
| TestSecretRedaction | 3 | ✅ pass |
| TestPlaybooksService | 5 | ✅ pass |
| TestPlaybooksRouter | 2 | ✅ pass |
| TestLedgerRouter | 3 | ✅ pass |
| TestConnectorsService | 6 | ✅ pass |
| TestConnectorsRouter | 2 | ✅ pass |
| TestLLMRouting | 2 | ✅ pass |
| TestGeminiSynthesis | 2 | ✅ pass |
| **Total** | **32** | **32/32 passed** |

Full suite: **1203/1231 passing** (28 failures = pre-existing `test_resources.py` httpx.ReadTimeout network issues, same as Slice 84 baseline).

---

## Bugs Found and Fixed During Implementation

1. **`validate_url` import error** — `app/utils/url_validation.py` exports `validate_url_for_fetch`, not `validate_url`. Fixed with aliased import.
2. **`apiClient.get/post` does not exist** — Frontend API clients must use `apiFetch<T>()` from `./client`. Rewrote all 3 API client files.
3. **`cryptography` not installed locally** — Added to requirements.txt; `pip3 install cryptography>=43.0.0` to fix locally.

---

## New Env Vars Required

| Variable | Description |
|----------|-------------|
| `PERPLEXITY_API_KEY` | Perplexity AI API key (sonar-pro model) |
| `GEMINI_API_KEY` | Google Gemini API key (gemini-2.0-flash) |
| `CONNECTOR_ENCRYPTION_KEY` | Fernet key for connector credentials (generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |

---

## Manual Verification Steps

1. POST `/playbooks/seed` → check Mission Control → Playbooks shows 8 agent cards
2. Propose an edit on Copywriter → see "Pending Edit" badge → Apply → version shows v2
3. POST `/connectors/linkedin` with fake token → GET `/connectors/` → no raw credentials visible
4. POST `/connectors/linkedin/test` → see graceful error (not 500)
5. Check Mission Control → Ledger → (after any agent run) see timestamped tool call entries
6. Confirm `CONNECTOR_ENCRYPTION_KEY` missing → app raises ValueError at startup (check logs)
