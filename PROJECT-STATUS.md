# PositionedUp — Project Status & Master Plan

> Last updated: 2026-02-25
> This document captures everything built, planned, fixed, and in progress.

---

## 1. WHAT IS POSITIONEDUP

An **AI-powered personal branding + content automation platform** for SaaS founders, creators, and agencies. The system combines:

- **A web app** (Next.js 15) where users build their brand profile, upload knowledge, save inspiration, and manage content
- **A backend API** (FastAPI) with an 8-node AI content pipeline, semantic search, voice DNA analysis, and performance analytics
- **An autonomous agent squad** (OpenClaw) — 6+ AI agents that research, write, design, distribute, and analyze content 24/7
- **A Mission Control dashboard** — Kanban board + live feed showing what agents are doing in real-time

The architecture is **brand-agnostic** — one agent squad can serve multiple brands. All brand-specific context (voice, audience, pillars, style rules) comes from the Brain API dynamically.

---

## 2. TECH STACK

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS 3.4 |
| Backend API | FastAPI (Python), Vercel deployment |
| Database | Supabase (PostgreSQL + pgvector + RLS + Realtime) |
| Auth | Supabase Auth (SSR, JWT) |
| AI Pipeline | LangGraph 8-node pipeline (Claude/GPT) |
| Embeddings | OpenAI text-embedding-3-small via pgvector |
| Agent System | OpenClaw (multi-agent gateway) |
| Agent Comms | Agent Bridge API (9 endpoints) + Mission Control API (16 endpoints) |
| Analytics | PostHog |
| Deploy (agents) | Docker + VPS (DigitalOcean/similar) |
| Deploy (app) | Vercel (frontend + API) |

---

## 3. WHAT HAS BEEN BUILT

### 3.1 Web App (Frontend)

| Page | Status | What It Does |
|------|--------|-------------|
| `/brands` | Done | List/create/switch between brands |
| `/brand` | Done | Brand profile editor (8 modules) |
| `/knowledge` | Done | Upload PDFs, YouTube links, notes → AI chunks + embeddings |
| `/inspo` | Done | Save inspiration with intent notes |
| `/content` | Done | Create content via 8-node pipeline, chat interface |
| `/research` | Done | Multi-platform research tools |
| `/schedule` | Done | Content calendar + Kanban view |
| `/performance` | Done | Analytics, voice DNA, post tracking |
| `/experiments` | Done | A/B testing management |
| `/memory` | Done | View/manage agent memory |
| `/usage` | Done | Token/cost tracking |
| `/mission-control` | Done | Agent dashboard (Kanban + sidebar + stats + chat) |
| `/mission-control/analytics` | Done | Agent analytics sub-page |
| `/mission-control/orchestrator` | Done | Jarvis activity view |
| `/admin/training` | Done | Agent training interface |
| `/login`, `/signup` | Done | Authentication |

### 3.2 Backend API

| Module | Endpoints | Status |
|--------|-----------|--------|
| Brand Profile | CRUD for 8 modules | Done |
| Knowledge Library | Upload, chunk, embed, search | Done |
| Inspo Boards | CRUD, search, star | Done |
| Content Pipeline | 8-node LangGraph (research → approve) | Done |
| Voice DNA | Analyze, drift detect | Done |
| Performance | Track posts, engagement, patterns | Done |
| Experiments | A/B test CRUD | Done |
| Agent Memory | Store/search with embeddings | Done |
| Schedule | Calendar CRUD | Done |
| Usage | Token tracking | Done |
| Agent Bridge API | 9 endpoints for OpenClaw agents | Done |
| Mission Control API | 16 endpoints for dashboard | Done |

### 3.3 Database (Supabase)

- **21 migrations** applied
- Tables: profiles, resources, resource_chunks, collections, workflows, agent_memory, personal_brands, inspo_boards, inspo_items, openclaw_agents, agent_tasks, agent_messages, agent_deliverables, and more
- Row Level Security (RLS) on all tables
- pgvector extension for semantic search
- Multi-brand architecture (brand_id foreign keys everywhere)

### 3.4 Agent System (OpenClaw)

| Component | Status |
|-----------|--------|
| openclaw.json gateway config | Done |
| SOUL.md (brand-agnostic v3) | Done |
| AGENTS.md (operations manual v2) | Done |
| HEARTBEAT.md (ET timezone v3) | Done |
| 6 agent SOUL.md files | Done |
| task_board.md (shared async queue) | Done |
| AGENT_BRIDGE_PLAYBOOK.md | Done |
| Deploy scripts (Docker + VPS) | Done |

**Agents defined:**
1. **Jarvis** (Orchestrator) — GPT-4o, delegates tasks, queries Brain
2. **Trend Analyzer** — GPT-4o-mini, web research, competitor analysis
3. **Copywriter** — GPT-4o, content creation, voice matching
4. **Visual Designer** — GPT-4o, image/carousel creation
5. **Distributor** — GPT-4o-mini, platform posting
6. **Analytics** — GPT-4o-mini, performance tracking

### 3.5 Security Fixes Applied

| Fix | Severity | File |
|-----|----------|------|
| XSS prevention (escapeHtml before markdown) | Critical | canvas-utils.ts |
| Error handler (no stack trace leaks) | Critical | main.py |
| CORS (explicit methods/headers) | Critical | main.py |
| API client error sanitization | Critical | client.ts |
| SSRF protection (block private IPs) | High | brand.py |
| IDOR fix (validate user exists) | High | agent_bridge.py |
| Security headers (X-Frame-Options, nosniff) | High | next.config.js |
| Path traversal (os.path.basename) | High | resources.py |
| Query param whitelist validation | Medium | content/chat/page.tsx |
| Code deduplication (shared context module) | Medium | worker/graph/context.py |

### 3.6 Test Results

- **Backend**: 796/796 pytest passing
- **Frontend**: 2/2 Playwright passing, 50 skipped (expected)
- **TypeScript**: Clean build, no errors

---

## 4. WHAT WAS CHANGED TODAY (Feb 25, 2026)

### Rebranding: Wowly → PositionedUp (Brand-Agnostic)

13 files updated to remove hardcoded Wowly/Bangladesh identity:

| File | Change |
|------|--------|
| SOUL.md | "PositionedUp Content Engine" — brand context from Brain API |
| AGENTS.md | Removed BD-specific sources, Bangla style guide |
| HEARTBEAT.md | Timezone → America/New_York (ET) |
| openclaw.json | Comment + 3 cron timezones → ET |
| agents/jarvis/SOUL.md | API URL → $POSITIONEDUP_API_URL env var |
| agents/copywriter/SOUL.md | Output path WOW- → PU- |
| agents/visual-designer/SOUL.md | Output path WOW- → PU- |
| task_board.md | Cleaned, PU- prefix, empty backlog |
| analytics/tracker.py | system_id → "positionedup-squad" |
| analytics/__init__.py | Module docstring updated |
| analytics/config.py | Default system_id updated |
| deploy/env.example | API URL placeholder, system_id |

### Auth Middleware Fix

- `apps/web/src/lib/supabase/middleware.ts` — Skip `getUser()` on public routes without auth cookie + 5-second timeout with Promise.race

---

## 5. ARCHITECTURE: HOW AGENTS TALK TO THE APP

```
Human (you)
  │
  ├─── Telegram ──→ Jarvis (Orchestrator)
  │                    │
  │                    ├─── GET /agent-api/active-brand
  │                    ├─── GET /agent-api/context/{brand_id}
  │                    ├─── POST /agent-api/knowledge/search
  │                    ├─── POST /agent-api/inspo/search
  │                    ├─── POST /agent-api/report
  │                    ├─── POST /agent-api/pipeline/trigger
  │                    ├─── POST /agent-api/tasks/sync
  │                    ├─── POST /agent-api/heartbeat
  │                    └─── GET /agent-api/brands
  │                    │
  │                    ├──→ Trend Analyzer (research tasks)
  │                    ├──→ Copywriter (content tasks)
  │                    ├──→ Visual Designer (design tasks)
  │                    ├──→ Distributor (posting tasks)
  │                    └──→ Analytics (performance tasks)
  │
  └─── Web App ──→ Mission Control Dashboard
                     ├── Agent sidebar (status, heartbeat)
                     ├── Kanban board (tasks by status)
                     ├── Live activity feed (agent messages)
                     ├── Deliverables review (approve/reject)
                     └── Broadcast (message all agents)
```

---

## 6. WHAT'S MISSING (GAPS TO FILL)

### Priority 1: Critical for Launch

| Gap | Why It Matters | Status |
|-----|---------------|--------|
| **Live Activity Feed** in Mission Control | Can't see what agents are doing in real-time (Bhanu's key feature) | Building |
| **Deliverables Review** in Mission Control | Can't approve/reject agent work output | Building |
| **WOW- prefix** still in Mission Control new task modal | Should be PU- | Fix needed |
| **VPS deployment** | Agents aren't running yet | Guide created |
| **Telegram bot setup** | Can't talk to Jarvis | Guide created |

### Priority 2: Enhancements

| Gap | Why It Matters |
|-----|---------------|
| **Brand Builder Pipeline** | Automated brand onboarding (like Co-Founder app) |
| **More specialized agents** | SEO, Outbound Scout, Brand Builder, Customer Research |
| **Mission Control mobile** | Responsive Kanban for phone |

### Priority 3: Future

| Gap | Why It Matters |
|-----|---------------|
| Rate limiting (slowapi) | API protection |
| OAuth token encryption at rest | Security hardening |
| Repository layer for Supabase | Code quality |
| Split large services | Maintainability |

---

## 7. POSITIONEDUP vs. BHANU'S SETUP

| Feature | Bhanu (SiteGPT) | PositionedUp | Winner |
|---------|-----------------|-------------|--------|
| Agents | 14 running 24/7 | 6 defined, not yet deployed | Bhanu (more agents, deployed) |
| Mission Control UI | Custom Kanban + live feed | Kanban + sidebar + stats + chat | Comparable |
| Content Pipeline | Manual (agents write directly) | 8-node automated LangGraph | **PositionedUp** |
| Knowledge Library | Not mentioned | Semantic search with embeddings | **PositionedUp** |
| Voice DNA | Not mentioned | Brand voice analysis + drift detection | **PositionedUp** |
| Multi-brand | Single brand (SiteGPT) | Multi-brand architecture | **PositionedUp** |
| Agent Memory | Agents learn over time | Embeddings-based long-term memory | **PositionedUp** |
| Inspo Boards | Not mentioned | Save inspiration with intent notes | **PositionedUp** |
| A/B Testing | Not mentioned | Experiments system built-in | **PositionedUp** |
| Database | Custom | Supabase with RLS, pgvector | **PositionedUp** |
| Deployment | Running on VPS | Docker scripts ready, not deployed | Bhanu (running) |

**Bottom line:** PositionedUp has a more powerful brain. Bhanu has agents actually running. The gap is deployment + more agents.

---

## 8. DEPLOYMENT PLAN

### Step 1: Deploy Backend API (Vercel)
The API is already designed for Vercel. Deploy to get a live URL.

### Step 2: Get a VPS
- DigitalOcean, Hetzner, or similar
- Ubuntu 22.04, 2GB RAM minimum
- Run `deploy/setup-vps.sh` to configure

### Step 3: Create Telegram Bot
1. Open Telegram, message @BotFather
2. Send `/newbot`
3. Choose name (e.g., "PositionedUp Jarvis")
4. Save the bot token
5. Get your chat ID from @userinfobot

### Step 4: Configure Environment
Copy `deploy/env.example` to `.env` and fill in:
- `OPENCLAW_GATEWAY_TOKEN` (generate with `openssl rand -hex 32`)
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_CHAT_ID`
- `AGENT_API_KEY` (must match backend config)
- `POSITIONEDUP_API_URL` (your deployed backend URL)

### Step 5: Deploy Agents
```bash
cd deploy/
docker compose up -d
```

### Step 6: Test
- Message Jarvis on Telegram
- Check Mission Control dashboard
- Verify heartbeats are coming through

---

## 9. BRAND BUILDER PIPELINE (PLANNED)

Automated brand onboarding (inspired by Co-Founder app):

```
Stage 1: INTAKE → Minimal user input (2-3 sentences + industry)
Stage 2: NICHE RESEARCH → Agent researches 3 niches with fit scores
Stage 3: COMPETITIVE INTELLIGENCE → 8 research modules auto-run
Stage 4: BRAND PROFILE → Auto-generates all 8 modules from research
Stage 5: VOICE DNA → Generates 3 voice options with example posts
Stage 6: CONTENT STRATEGY → Pillars + calendar + posting plan
Stage 7: FIRST CONTENT → Triggers 3-5 content pieces via pipeline
```

This requires: new API endpoints, new database table, new frontend pages, new agent task templates.

---

## 10. AGENT EXPANSION (PLANNED)

| Agent | Role | Why |
|-------|------|-----|
| SEO Specialist | Keywords, on-page, content gaps | Organic growth |
| Outbound Scout | Find leads, partnerships, podcast opps | Growth |
| Brand Builder | Runs automated brand onboarding | New user activation |
| Customer Research | Audience insights, pain points, forums | Better content |

These can be added to openclaw.json without code changes. Jarvis can spawn them via the existing sub-agent system.

---

## 11. FILES & STRUCTURE

```
positionedup/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── config.py       # Settings (cors_origins, agent_api_key)
│   │   │   ├── main.py         # App entry point
│   │   │   ├── routers/        # 15+ route modules
│   │   │   │   ├── agent_bridge.py    # 9 Agent Bridge endpoints
│   │   │   │   ├── mission_control.py # 16 Mission Control endpoints
│   │   │   │   ├── brand.py           # Brand profile CRUD
│   │   │   │   └── ...
│   │   │   ├── schemas/        # Pydantic models
│   │   │   └── services/       # Business logic
│   │   ├── worker/
│   │   │   └── graph/          # LangGraph 8-node pipeline
│   │   └── tests/              # 796 passing tests
│   └── web/                    # Next.js frontend
│       ├── src/app/            # 16+ pages
│       │   ├── mission-control/ # Agent dashboard
│       │   ├── content/        # Content pipeline UI
│       │   ├── brands/         # Multi-brand management
│       │   └── ...
│       └── src/lib/
│           ├── api/            # 15+ API client modules
│           └── brand-context.tsx # Brand state management
├── agents/                     # OpenClaw agent configs
│   ├── jarvis/SOUL.md
│   ├── trend-analyzer/SOUL.md
│   ├── copywriter/SOUL.md
│   ├── visual-designer/SOUL.md
│   ├── distributor/SOUL.md
│   └── analytics/SOUL.md
├── deploy/                     # Docker + VPS scripts
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── setup-vps.sh
│   └── env.example
├── infra/supabase/migrations/  # 21 SQL migrations
├── analytics/                  # PostHog tracking module
├── SOUL.md                     # System constitution (v3, brand-agnostic)
├── AGENTS.md                   # Operations manual (v2)
├── HEARTBEAT.md                # Pulse rules (v3, ET timezone)
├── openclaw.json               # Gateway config
├── task_board.md               # Shared agent task queue
└── AGENT_BRIDGE_PLAYBOOK.md    # Integration guide
```

---

*This is a living document. Update it as the project evolves.*
