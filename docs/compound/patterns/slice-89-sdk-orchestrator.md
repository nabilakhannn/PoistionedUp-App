# Slice 89: SDK Orchestrator — True Agent Pipeline

**Date:** 2026-03-03
**Status:** Shipped
**Tests:** 35/35

---

## Problem

Agents ran in silos: Trend Analyzer wrote files, Copywriter wrote other files, no real handoffs.
Performance data from past posts never reached the Copywriter. Competitor intelligence never reached
research. Approved content never got published automatically. The "autonomous" system required manual
triggers for every step.

---

## Solution

Built a 3-phase SDK pipeline that chains agent work automatically:

```
Research (web + competitor + analytics)
  → Write (brand voice + rejection history + analytics)
  → QA (80+ score gate)
  → Deliverable saved → User notified → Approval inbox
  → Publishing cron auto-posts approved content hourly
```

---

## Architecture

```
VPS (Hostinger):
  openclaw-gateway.service  ← unchanged (Telegram + voice)
  jumbo-pipeline.service    ← NEW — runs every 2h, calls Vercel

Vercel (API):
  POST /orchestrator/pipeline/research  ← < 60s per phase
  POST /orchestrator/pipeline/write     ← < 60s per phase
  POST /orchestrator/pipeline/qa        ← < 60s per phase, saves deliverable
  GET  /orchestrator/pipeline/status    ← last 15 runs
  POST /cron/publish                    ← hourly Vercel cron
```

Why VPS runner + Vercel endpoints (not pure Vercel cron):
- Full chain takes 3-10 minutes (research + write + QA)
- Vercel has a 60-second serverless timeout
- Each individual phase runs in < 60s → Vercel handles it
- VPS runner chains them sequentially with no timeout limit

---

## Context Injection (What Makes It Smart)

### Research phase receives:
- **Analytics context**: Top 5 published posts by QA score (format + hook examples)
- **Competitor context**: Tracked competitors + threat levels + niches to avoid
- **Trend memory**: Last trend analyzer deliverable (avoid repeating topics)

### Writing phase receives:
- **Research brief**: Full output from phase 1 (3000 char cap)
- **Analytics context**: Performance patterns (which hooks got engagement)
- **Rejection history**: agent_memory entries with voice_feedback type (mistakes to avoid)

### QA phase receives:
- **Draft**: Full draft from phase 2
- **score_content_quality tool**: Mechanical baseline check
- **Scoring rubric**: Voice (25) + Hook (25) + Structure (20) + Value (20) + CTA (10)

---

## Files Changed

| File | Type | Change |
|------|------|--------|
| `apps/api/app/services/jumbo_pipeline.py` | NEW | Context helpers, prompt builders, save/notify |
| `apps/api/app/routers/pipeline.py` | NEW | 5 endpoints: research / write / qa / status / cron-publish |
| `apps/api/app/config.py` | MODIFIED | `pipeline_secret_key` + `cron_secret` settings |
| `apps/api/app/main.py` | MODIFIED | `app.include_router(pipeline.router)` |
| `apps/api/vercel.json` | MODIFIED | `"crons": [{"path": "/cron/publish", "schedule": "0 * * * *"}]` |
| `deploy/pipeline_runner.py` | NEW | VPS script — calls Vercel endpoints every 2h |
| `deploy/jumbo-pipeline.service` | NEW | systemd unit for VPS pipeline runner |
| `apps/api/tests/test_slice89.py` | NEW | 35 tests |

**Not modified:** `tool_use_agents.py`, `sdk_agents.py`, `agent_orchestrator.py`, `publishing.py`

---

## Security (OWASP)

| Risk | Mitigation |
|------|-----------|
| Unauthorized pipeline trigger | `X-Pipeline-Key` header, `hmac.compare_digest` (timing-safe) |
| brand_id / user_id injection | Strict UUID regex validated before any DB query (OWASP A03) |
| Publishing cron unauthorized | `Authorization: Bearer <CRON_SECRET>` validated with `hmac.compare_digest` |
| SSRF in web search | Already sanitised in `_exec_web_search()` — strips `<>"';;&`, caps 200 chars |
| Secrets in agent ledger | `_redact()` in `tool_use_agents.py` strips Bearer/sk-*/API keys |

---

## Testing

```
pytest apps/api/tests/test_slice89.py -v
→ 35/35 pass

npx tsc --noEmit
→ 0 errors
```

### Test Classes

| Class | Count | Covers |
|-------|-------|--------|
| `TestPipelineEndpoints` | 10 | All 5 endpoints exist, auth headers, UUID validation, main.py inclusion, config settings |
| `TestContextHelpers` | 5 | All 4 context functions return str, invalid UUID handled |
| `TestPromptBuilders` | 4 | Research/write/QA prompts include required sections and tool references |
| `TestQAScoreParser` | 5 | Score extraction from various response formats, clamping |
| `TestSaveDeliverable` | 4 | status=review on ≥80, status=failed_qa on <80, non-empty id, error-safe |
| `TestPublishingCron` | 7 | Cron endpoint, run_due_posts call, vercel.json, VPS files, service config |

---

## Gaps Closed

| Gap | Status |
|-----|--------|
| Research → Write → QA chain | ✅ Automated, no manual triggers |
| Analytics feedback loop | ✅ Top posts injected into Copywriter brief |
| Competitor data → research | ✅ Competitor context injected into Research brief |
| Rejection history → writer | ✅ Voice feedback memories injected before each write |
| Publishing cron | ✅ Vercel cron calls run_due_posts hourly |
| VPS pipeline runner | ✅ jumbo-pipeline.service + pipeline_runner.py |

---

## VPS Deployment

After merging:

```bash
# On VPS (46.202.92.233):
cd /home/openclaw/.openclaw/workspace
git pull origin main
pip3 install httpx schedule

# Add to /root/.openclaw/.env:
PIPELINE_VERCEL_URL=https://api-iota-puce.vercel.app
PIPELINE_SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">

# Install and start service:
cp deploy/jumbo-pipeline.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable jumbo-pipeline
systemctl start jumbo-pipeline
systemctl status jumbo-pipeline
```

Also add to Vercel env vars:
```
PIPELINE_SECRET_KEY=<same value as VPS>
CRON_SECRET=<Vercel generates this automatically when crons are enabled>
```

---

## Next Slices

- **Slice 90**: Email newsletter format + landing page analysis (`fetch_url` tool)
- **Slice 91**: LinkedIn outreach sequences + email nurture + basic CRM contacts
- **Slice 92**: Ad creative pipeline with Facebook/Google Ads API feedback loop
