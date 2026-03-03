# AI Second Brain — Starter Kit

> Battle-tested templates extracted from a production multi-agent content automation system.
> Built over 87 slices. Running live. Adapted here so you can clone the architecture.

---

## What This Is

A complete agent system for personal branding and content creation, packaged as a starter kit.
Not a tutorial. Not a toy demo. These are the exact files — generalized — from a system that:

- Posts content to LinkedIn, Twitter/X, and Instagram
- Runs 8 specialist agents autonomously (research, writing, QA, publishing, analytics)
- Wakes every 15 minutes to check what needs doing
- Learns from every post that goes viral or flops
- Lets you brief it via Telegram voice notes

---

## What You Get

```
starter-kit/
├── user.md                    ← Fill in once. Your agent reads this to know who you are.
├── SOUL.md                    ← System constitution. The rules every agent follows.
├── HEARTBEAT.md               ← Execution protocol. What agents do every 15 minutes.
├── openclaw-template.json     ← Agent runtime config (OpenClaw format).
├── architecture.md            ← How all the pieces connect.
└── agents/
    ├── orchestrator/SOUL.md   ← The agent that talks to you (like Jumbo).
    ├── researcher/SOUL.md     ← Web research + trend analysis.
    ├── writer/SOUL.md         ← Content drafting for your platforms.
    ├── qa-reviewer/SOUL.md    ← Quality gate (voice, structure, AI-tells).
    └── publisher/SOUL.md      ← Schedules and posts approved content.
```

---

## Prerequisites

| Requirement | What it is |
|-------------|-----------|
| [OpenClaw](https://openclaw.dev) | Agent runtime (heartbeat, tools, Telegram, cron) |
| OpenAI API key | LLM + Whisper transcription |
| Telegram Bot Token | How you talk to your agents on your phone |
| A "Brain" (knowledge system) | Where your brand context, memories, and performance data live |

**The Brain** can be:
- A custom FastAPI + Supabase app (what PositionedUp uses)
- A Notion database with an API wrapper
- A simple SQLite file with a query function
- Any system that returns brand context, memories, and performance data as JSON

---

## 5-Step Setup

### Step 1: Fill in user.md
Open `user.md` and fill in your name, goals, brand voice, and platforms.
This is the only file your agents need to know who you are.

### Step 2: Customize the agent SOUL.md files
Open each `agents/*/SOUL.md` and replace:
- `{YOUR_PROJECT_PREFIX}` → your task ID prefix (e.g., `BRAND-`, `PB-`, `ME-`)
- `{BRAIN_API_URL}` → your knowledge system's base URL
- `{YOUR_PLATFORMS}` → the platforms you actually use
- `{YOUR_TIMEZONE}` → your timezone (e.g., `America/New_York`)

### Step 3: Configure openclaw-template.json
Copy `openclaw-template.json` → `openclaw.json` and fill in:
- `TELEGRAM_BOT_TOKEN` — get from [@BotFather](https://t.me/botfather)
- `TELEGRAM_OWNER_CHAT_ID` — your Telegram chat ID
- `OPENCLAW_GATEWAY_TOKEN` — any strong random string
- `OPENAI_API_KEY` — from platform.openai.com

### Step 4: Start the agent runtime
```bash
# Install OpenClaw
npm install -g @openclaw/cli

# Start gateway
openclaw gateway --config openclaw.json

# Verify
openclaw agents list
```

### Step 5: Send your first message
Open Telegram and send a message to your bot:
```
Hey! Load my profile.
```

The orchestrator reads `user.md` and replies with your goals and a status check.

---

## Voice Note Workflow (Slice 87 feature)

Send a voice note to your Telegram bot:
- **"Create a post about [topic]"** → orchestrator transcribes + triggers content pipeline
- **"Remember that [insight]"** → saves to your knowledge library
- **"What's my engagement looking like?"** → pulls from analytics

No typing required. Idea capture on your phone → draft in Mission Control.

---

## Adapting for Your Use Case

The templates are built for personal branding content. To adapt:

| Domain | What to change |
|--------|---------------|
| SaaS marketing | Update content pillars, platform list, and writer agent to focus on product angles |
| Community management | Add a community manager agent, update distributor to handle Discord/Slack |
| Newsletter | Add an email specialist agent, update publisher for Beehiiv/Substack API |
| E-commerce | Add product copywriter + ad creative agents, update analytics to track conversions |

---

## Architecture

See [architecture.md](architecture.md) for the full component diagram.

---

## From the Production System

These templates were extracted from a live system with:
- 87 build iterations
- 1276+ automated tests
- 8 specialist agents
- Supabase (pgvector) memory with semantic search
- NotebookLM MCP for citation-backed research
- Real-time publishing to LinkedIn, Twitter/X, Instagram
- 6-dimension QA scoring before any content publishes

The production system is [PositionedUp](https://positionedup.com) — a personal branding platform.
This starter kit is the "bones" of the agent architecture, extracted and generalized.
