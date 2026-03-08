# PositionedUp

An AI-powered personal branding and content automation platform. Autonomous agents research trends, write content, score quality, and publish across LinkedIn, Twitter, and Instagram — while you approve and steer from a command centre.

## What It Does

| Room | What you get |
|------|-------------|
| **Today** | Morning briefing, approval queue, priorities, overnight activity feed |
| **Create** | Content pipeline, marketing calendar, landing page generator, hook library, ad creative engine |
| **Brand** | 8-section brand intelligence dossier, voice analysis, Jumbo brand chat |
| **Grow** | Lead CRM, ICP research, BANT scoring, outreach sequences, newsletter drafts |
| **Jumbo** | Persistent multi-turn chat with your AI orchestrator, saved notes, quick-action chips |
| **Studio** | Agent marketplace (24 workflows), agent training, deliverables gallery |

### Autonomous Agent System

Eight specialised agents run on a VPS via OpenClaw and collaborate through a shared pipeline:

| Agent | Role |
|-------|------|
| **Jumbo** | Orchestrator — plans, delegates, briefs |
| **Trend Analyzer** | Finds trending topics and content gaps |
| **Copywriter** | Writes posts, scripts, hooks, ad copy |
| **Visual Designer** | Image generation briefs + Higgsfield/Gemini image calls |
| **Distributor** | Schedules and publishes to connected platforms |
| **Analytics** | Tracks performance and feeds learning loop |
| **QA Reviewer** | 6-dimension quality gate before any content is approved |
| **Competitor Analyst** | Dynamic threat scoring, gap analysis, daily intel |

Pipeline runs every 2 hours: **Research → Write → QA → Approval queue**.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, React 19, Tailwind CSS, TypeScript |
| Backend API | FastAPI (Python 3.9+), deployed on Vercel |
| Agent Runtime | OpenClaw 2026.2.26, native systemd on Hostinger VPS |
| Database | Supabase Postgres + RLS (49 migrations) |
| Auth | Supabase Auth (JWT + Google OAuth) |
| LLM routing | Claude Sonnet 4.6 (writing), Perplexity sonar-pro (search), Gemini 2.0 Flash (synthesis) |
| Image generation | Higgsfield Nano Banana 2 → Gemini fallback |
| Publishing | Twitter (tweepy OAuth 1.0a), LinkedIn (webhook), Instagram (Graph API) |
| Search | DuckDuckGo + Tavily (optional) + Perplexity |
| Transcription | YouTube captions + OpenAI Whisper |
| OCR | GPT-4 Vision (scanned PDFs + images) |
| Observability | PostHog event tracking, append-only agent ledger |
| Testing | Pytest (1730+ tests) + Playwright E2E |

## Project Structure

```
apps/
  api/
    app/
      main.py              # FastAPI app (200+ endpoints, 31 routers)
      routers/             # leads, marketplace, pipeline, brand, agents, analytics, …
      services/            # jumbo_pipeline, publishing, ad_creative, brand_chat, …
      utils/               # url_validation (SSRF), connectors (Fernet-encrypted)
    tests/                 # 60+ test files
  web/
    src/
      app/                 # Next.js pages — dashboard, brand, content, sales, jumbo, studio
      components/          # workflow-card, leads-crm, getting-started-checklist, …
      lib/api/             # typed API clients per domain
    tests/                 # Playwright E2E (new-features.spec.ts, new-features-auth.spec.ts)
agents/                    # OpenClaw SOUL.md files for all 8 agents
deploy/                    # Dockerfile (legacy), Caddyfile, setup-vps.sh, runbooks
analytics/                 # PostHog event definitions
infra/
  supabase/migrations/     # 49 SQL migrations
docs/
  compound/
    project-log.md         # Full build history (112 slices)
    patterns/              # Per-slice reusable patterns
    MASTER-SYSTEM-DESIGN.md
```

## Getting Started

### Prerequisites

- Python 3.9+, Node.js 20+, pnpm
- [Supabase](https://supabase.com) project
- [OpenAI](https://platform.openai.com) API key

### 1. Clone and install

```bash
git clone https://github.com/nabilakhannn/PoistionedUp-App.git
cd PoistionedUp-App

# Backend
cd apps/api && python3 -m venv venv && source venv/bin/activate
pip install -r requirements-full.txt   # full deps for local dev

# Frontend
cd ../web && pnpm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Required keys:

| Key | Where to get it |
|-----|----------------|
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Supabase dashboard → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API |
| `OPENAI_API_KEY` | platform.openai.com |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Same as above |

Optional (unlocks agent features):

```
PERPLEXITY_API_KEY     # ICP research, web search
GEMINI_API_KEY         # synthesis + image fallback
TAVILY_API_KEY         # enhanced web search
CONNECTOR_ENCRYPTION_KEY  # social publishing connectors
```

### 3. Run database migrations

Apply all SQL files from `infra/supabase/migrations/` (001 → 049) via Supabase SQL editor or CLI:

```bash
cd apps/api && supabase db push
```

### 4. Start development servers

```bash
# Terminal 1 — Backend
cd apps/api && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd apps/web && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Running Tests

```bash
# Backend (1730+ tests)
cd apps/api && python3 -m pytest tests/ -v

# Frontend type check
cd apps/web && npx tsc --noEmit

# Playwright E2E (requires dev server running or uses webServer config)
cd apps/web && TEST_EMAIL=test@positionedup.com TEST_PASSWORD=testpass123 npx playwright test tests/new-features.spec.ts tests/new-features-auth.spec.ts
```

## Deployment

| Service | Platform |
|---------|----------|
| Frontend | Vercel — `apps/web` |
| Backend API | Vercel — `apps/api` |
| Agent runtime | Hostinger VPS (systemd) — OpenClaw gateway on port 18790 |

### VPS agent setup

```bash
# On the VPS
openclaw gateway start   # starts 8 agents
# or via systemd
systemctl start openclaw-gateway
```

The Vercel backend connects to the VPS via `OPENCLAW_GATEWAY_URL` + `OPENCLAW_GATEWAY_TOKEN`. Set `OPENCLAW_MOCK_MODE=true` for local development without a live VPS.

## Content Pipeline

Runs every 2 hours via `jumbo-pipeline.service` on the VPS:

```
Research (Perplexity) → Write (Claude Sonnet 4.6) → QA (6-dimension scoring)
→ Approval queue (you approve/reject in the Today room)
→ Distribute (Twitter / LinkedIn / Instagram)
```

Three manual interrupt points let you steer topics, hooks, and final approval before content goes out.

## Security

- JWT auth on every endpoint via Supabase
- IDOR protection: all queries scoped by `user_id`
- SSRF protection on URL inputs (`url_validation.py`)
- Fernet AES-128-CBC for social connector credentials
- HMAC timing-safe comparison on agent bridge key
- Append-only agent ledger (no UPDATE/DELETE RLS)
- Secret redaction in logs (Bearer tokens, API keys)
- CORS locked to Vercel deployment URLs

## License

Private project.
