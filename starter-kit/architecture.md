# Architecture — AI Second Brain Agent System

> How the pieces connect. Read this before editing any config files.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  YOU                                                            │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │ Telegram     │  │ Dashboard (Mission Control)           │    │
│  │ @YourBot     │  │ Tasks / Deliverables / Analytics      │    │
│  └──────┬───────┘  └──────────────────┬───────────────────┘    │
│         │                             │                         │
└─────────┼─────────────────────────────┼─────────────────────────┘
          │ messages                    │ approve/reject
          ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  OPENCLAW GATEWAY (your VPS)                                    │
│  Agent runtime: heartbeat, sessions, tools, cron, Telegram      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ORCHESTRATOR (Jumbo)                                     │   │
│  │ - Reads user.md on first contact                         │   │
│  │ - Talks to Brain API for brand context                   │   │
│  │ - Manages task_board.md                                  │   │
│  │ - Spawns specialist agents                               │   │
│  │ - Handles Telegram voice notes (→ transcribe → pipeline) │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │ spawns + delegates                    │
│     ┌───────────────────┼───────────────────────┐              │
│     ▼                   ▼                        ▼              │
│  ┌──────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │Researcher│  │    Writer     │  │       QA Reviewer        │  │
│  │Web search│  │Platform drafts│  │6-dim scoring + revisions │  │
│  └──────────┘  └───────────────┘  └─────────────────────────┘  │
│     ▼                                       ▼                   │
│  ┌────────────────────┐  ┌──────────────────────────────────┐   │
│  │     Publisher      │  │          Analytics               │   │
│  │Posts to platforms  │  │Metrics → memory → reports        │   │
│  └────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │ Brain API calls (X-Agent-Key auth)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRAIN (your knowledge system)                                  │
│                                                                  │
│  Brand Profile    Content Pillars    Voice DNA                  │
│  Knowledge Library  Agent Memory    Performance Data            │
│  Inspo Boards       Experiments     Published Content           │
│                                                                  │
│  /context/{brand_id}   /knowledge/search   /pipeline/trigger   │
│  /report               /tasks/sync         /voice/transcribe    │
└─────────────────────────────────────────────────────────────────┘
          │ reads/writes
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  DATABASE (Supabase / your DB)                                  │
│  scheduled_items  agent_deliverables  agent_memory              │
│  resources (knowledge)  agent_notifications  user_connectors    │
└─────────────────────────────────────────────────────────────────┘
```

---

## The 5 Core Components

### 1. The Brain (Your Knowledge System)

The Brain is the central nervous system. Every agent gets context from it, never from hardcoded files.

**What it stores:**
- Your brand profile (who you are, who your audience is, what you stand for)
- Voice DNA (your writing patterns, tone, what to avoid)
- Content pillars (your core themes)
- Knowledge library (PDFs, transcripts, notes you've uploaded)
- Agent memory (what worked, what failed, lessons learned)
- Performance data (engagement rates, top posts, patterns)
- Inspiration boards (saved examples with your intent notes)

**Why it matters:**
Agents don't need to be reconfigured when you change your focus or add a new platform.
They just call the Brain and get current context.

**Minimum Brain implementation:**
```json
{
  "brand_name": "Your Name",
  "voice_dna": "Direct, data-driven, no corporate filler",
  "content_pillars": ["AI for business", "Building in public", "Sales process"],
  "writing_rules": ["No em dashes", "Max 3 bullet points per section", "Always lead with a number or bold claim"],
  "recent_memories": []
}
```

---

### 2. The Orchestrator (Your Agent Manager)

The only agent that talks to you. Everyone else talks through the task board.

**What it does:**
- Reads `user.md` on first contact to understand who you are
- Calls the Brain before every content task (gets voice DNA, performance, knowledge)
- Decomposes your goals into atomic tasks
- Assigns tasks to the right specialist
- Collects deliverables and surfaces them for your review
- Handles your Telegram messages and voice notes
- Runs morning briefings and proactive checks

**The rule:** Specialists never talk to the Brain directly. The Orchestrator is the bridge.

---

### 3. Specialist Agents (Your Squad)

Each specialist has one job. They never do each other's jobs.

| Agent | Job | Key rule |
|-------|-----|---------|
| Researcher | Web research, trend finding | Check knowledge base FIRST before searching |
| Writer | Draft content for your platforms | Never publish directly — deliverable only |
| QA Reviewer | Score content on 6 dimensions | Never lower the bar to "just ship it" |
| Publisher | Post approved content at scheduled times | NEVER post without approval in task status |
| Analytics | Fetch metrics, detect patterns, generate reports | Report specific numbers, never vague |

---

### 4. The Task Board (Inter-Agent Communication)

A single `task_board.md` file in the Orchestrator's workspace.

Why a file (not a database)?
- Agents can read/write it with basic file tools
- Git tracks every change (audit trail)
- Human-readable (you can see exactly what's happening)
- No race conditions if agents follow the "one task per pulse" rule

**State machine:** `BACKLOG → IN PROGRESS → REVIEW → ARCHIVE`

---

### 5. The Heartbeat (Autonomous Execution)

OpenClaw fires a pulse every [CUSTOMIZE] minutes during [CUSTOMIZE] active hours.

On each pulse, each agent follows this protocol:
1. Do I have a task? → Work on it.
2. Is there a new task I can claim? → Claim it.
3. Is content due to publish? → Post it.
4. Does anything need cleanup? → Handle it.
5. Otherwise → Return `HEARTBEAT_OK` (zero tokens, zero cost).

**Why this matters:**
The system works while you sleep. Research runs at 6 AM. Content goes live at the optimal
posting time. Reports arrive in your inbox before your morning coffee.

---

## Data Flow: Content Creation Example

```
You (Telegram): "Create a LinkedIn post about AI agents replacing SDRs"
    ↓
Orchestrator receives message
    ↓
GET /brain/context/{brand_id}
→ Voice DNA: "Direct, no hype, data-driven"
→ Performance: "Posts starting with a statistic get 2x engagement"
→ Pillars: "AI for B2B sales is your #1 pillar"
    ↓
POST /brain/knowledge/search {"query": "AI SDR tools"}
→ Found: 3 relevant knowledge chunks from uploaded PDFs
    ↓
Creates task in task_board.md:
"TASK PB-047: LinkedIn post — AI replacing SDRs
 Voice: [DNA injected]
 Start with a statistic
 Reference material: [3 chunks]
 Platforms: linkedin"
    ↓
Researcher claims task → web search → finds new stat → updates brief
    ↓
Writer claims task → drafts 3 hook options → writes full post
    ↓
QA Reviewer scores post → 87/100 (pass) → marks ready
    ↓
Deliverable appears in your Mission Control dashboard
    ↓
You approve ✓
    ↓
Publisher schedules at optimal time → posts live → records URL
    ↓
Analytics fetches metrics 48h later → "Strong performance (3.2% engagement)"
→ Creates memory: "Stat-led AI posts perform above average"
```

---

## What You Need to Build (The Brain)

The starter kit has everything except the Brain. The Brain is your knowledge system.

**Minimal viable Brain:**
A FastAPI endpoint that returns brand context:
```python
@app.get("/context/{brand_id}")
def get_context(brand_id: str):
    return {
        "brand_name": "Your Name",
        "voice_dna": "Your tone...",
        "content_pillars": [...],
        "writing_rules": [...],
        "recent_memories": [],
        "performance_summary": {}
    }
```

**Production Brain:**
The full PositionedUp app — pgvector semantic search, agent memory synthesis, performance
analytics, knowledge library with 1M+ tokens of searchable context.

Start minimal. The system works with even a hardcoded JSON file.
Graduate to a real database as you collect more data.
