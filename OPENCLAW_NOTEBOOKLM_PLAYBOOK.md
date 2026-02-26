# OpenClaw + NotebookLM: Integration Playbook

> NotebookLM researches, analyzes, and creates knowledge.
> OpenClaw agents take action, build, and automate.
> Together: an AI employee that researches, creates, builds, and delivers — 24/7.

---

## How It Works

```
NotebookLM (The Brain)          OpenClaw (The Builder)
  - Zero-hallucination research    - Autonomous task execution
  - Multi-source synthesis         - Multi-agent coordination
  - Citation-backed answers        - Tool usage (posting, scraping)
  - Grounded in YOUR docs          - Scheduled automation via HEARTBEAT
         |                                    |
         +------------ task_board.md ---------+
                   (shared state layer)
```

**The integration pattern**: OpenClaw agents query NotebookLM via the MCP server for research, then act on the findings through task_board.md. NotebookLM never acts — it only knows. OpenClaw never guesses — it only acts on verified knowledge.

---

## Setup Requirements

| Component | What You Need |
|-----------|--------------|
| NotebookLM MCP | `npx notebooklm-mcp@latest` in Cursor/Claude MCP config |
| NotebookLM Notebooks | Created at notebooklm.google.com with your source docs uploaded |
| OpenClaw Gateway | Node 22+ on your VPS, configured with openclaw.json |
| Telegram Bot | For human operator communication with the Orchestrator |
| VPS | Hostinger or any Linux VPS with Node 22+ |

---

## COMBINATION 1: The Content Repurposing Engine

**One piece of research becomes 12 pieces of content.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Orchestrator | Receives topic from human via Telegram | Task created in BACKLOG |
| 2 | Trend Analyzer | Queries NotebookLM: "What are the top pain points for [topic] in our research?" | research/topic-findings.md |
| 3 | Trend Analyzer | Queries NotebookLM: "What successful content formats have covered [topic]?" | Appended to findings |
| 4 | Copywriter | Reads findings, writes carousel script (5-7 slides) | drafts/WOW-XXX-carousel.md |
| 5 | Copywriter | Writes single-post caption from same research | drafts/WOW-XXX-caption.md |
| 6 | Copywriter | Writes newsletter snippet from same research | drafts/WOW-XXX-newsletter.md |
| 7 | Copywriter | Writes Twitter/X thread from same research | drafts/WOW-XXX-thread.md |
| 8 | Copywriter | Writes YouTube short script from same research | drafts/WOW-XXX-yt-short.md |
| 9 | Visual Designer | Creates carousel visuals from approved carousel copy | assets/WOW-XXX/ |
| 10 | Visual Designer | Creates single-post image | assets/WOW-XXX-single.png |
| 11 | Human | Reviews all drafts in REVIEW section | Approved or revision requested |
| 12 | Distributor | Posts approved content per schedule | Live URLs in ARCHIVE |

### NotebookLM Queries the Trend Analyzer Should Use

```
"What are the most common struggles BD online sellers face with [topic]?"
"What tips or strategies from our sources address [pain point]?"
"Give me 3 real examples or case studies related to [topic] from our docs."
"What questions do sellers commonly ask about [topic]?"
"What misconceptions exist about [topic] that we could correct?"
```

### task_board.md Entry Template

```markdown
- [ ] **Content Repurposing: [TOPIC]** [ID:WOW-XXX] [PRIORITY:P1] [ASSIGNEE:unassigned] [TAGS:research,repurpose]
  - **Brief**: Research [topic] via NotebookLM, then create 6 content pieces (carousel, caption, newsletter, thread, YT short, single post)
  - **Input**: NotebookLM notebook: [NOTEBOOK_LINK]
  - **Output**: 6 drafts in drafts/ folder
  - **Notes**: Start with NotebookLM research before any writing. Follow content lifecycle.
```

---

## COMBINATION 2: Weekly Competitor Intelligence

**Stay ahead without trying. Automated every Monday.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Cron (Monday 6AM) | Triggers Orchestrator via HEARTBEAT | Task created |
| 2 | Trend Analyzer | Scrapes competitor websites and social pages | Raw data saved |
| 3 | Trend Analyzer | Feeds findings to NotebookLM: "Compare these competitor posts to our content strategy" | Comparison report |
| 4 | Trend Analyzer | Queries NotebookLM: "What content gaps exist that competitors are not covering?" | Opportunity list |
| 5 | Orchestrator | Reviews findings, creates content tasks for top 3 opportunities | 3 tasks in BACKLOG |
| 6 | Orchestrator | Sends summary to human via Telegram | "3 new opportunities detected" |

### Cron Entry in openclaw.json

```json
{
  "name": "Weekly Competitor Intelligence",
  "schedule": { "kind": "cron", "expr": "0 6 * * 1", "tz": "Asia/Dhaka" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "COMPETITOR SCAN TRIGGER. Create a competitor analysis task. Assign to trend-analyzer. Use NotebookLM for comparison. Priority P1."
  },
  "agentId": "jumbo"
}
```

---

## COMBINATION 3: Client/Customer Research Package

**8 hours of research done in 10 minutes.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Human | "Research [industry/niche] for a new client" via Telegram | Task created |
| 2 | Trend Analyzer | Web search: industry trends, pain points, key players | Raw research |
| 3 | Trend Analyzer | Uploads findings to NotebookLM notebook | Notebook link |
| 4 | Trend Analyzer | Queries NotebookLM: "Synthesize the top 5 opportunities in this industry" | Structured report |
| 5 | Trend Analyzer | Queries NotebookLM: "What are the biggest customer complaints in this space?" | Pain point list |
| 6 | Copywriter | Writes executive briefing from NotebookLM synthesis | drafts/client-briefing.md |
| 7 | Copywriter | Writes competitor comparison table | drafts/competitor-table.md |
| 8 | Visual Designer | Creates infographic from briefing data | assets/client-infographic.png |
| 9 | Human | Reviews package | Approved for delivery |

---

## COMBINATION 4: The Learning Accelerator

**Master any topic 10x faster with AI-generated curriculum.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Human | "I need to learn [topic] deeply" via Telegram | Task created |
| 2 | Trend Analyzer | Deep research on topic: best resources, key concepts, learning paths | research/learning-[topic].md |
| 3 | Trend Analyzer | Uploads top sources to a NotebookLM notebook | Notebook created |
| 4 | Trend Analyzer | Queries NotebookLM: "Create a structured learning path from beginner to advanced" | Curriculum outline |
| 5 | Trend Analyzer | Queries NotebookLM: "What are the 20 most important concepts to understand?" | Concept list |
| 6 | Copywriter | Writes study guide with key concepts explained simply | drafts/study-guide-[topic].md |
| 7 | Copywriter | Writes flashcard set (question/answer format) | drafts/flashcards-[topic].md |
| 8 | Copywriter | Writes quiz with answers | drafts/quiz-[topic].md |
| 9 | Orchestrator | Compiles all outputs into a learning package | Telegram notification |

---

## COMBINATION 5: Sales Call Prep System

**Show up more prepared than anyone.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Human | "Prep me for a call with [company/person]" | Task created |
| 2 | Trend Analyzer | Research: company website, LinkedIn, recent news, industry | Raw research |
| 3 | Trend Analyzer | Upload to NotebookLM, query: "What are their likely pain points based on their industry and size?" | Pain point analysis |
| 4 | Trend Analyzer | Query NotebookLM: "What questions should I ask to uncover their real needs?" | Question bank |
| 5 | Copywriter | Writes 2-minute briefing doc | drafts/call-prep-[company].md |
| 6 | Copywriter | Writes one-page cheat sheet | drafts/cheat-sheet-[company].md |
| 7 | Orchestrator | Delivers to human via Telegram | Ready for the call |

---

## COMBINATION 6: The Meeting Intelligence System

**Every meeting becomes actionable.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Human | Uploads meeting recording/transcript | Source material |
| 2 | Trend Analyzer | Uploads transcript to NotebookLM | Notebook created |
| 3 | Trend Analyzer | Queries: "Extract all action items with owners and deadlines" | Action item list |
| 4 | Trend Analyzer | Queries: "What were the key decisions made?" | Decision log |
| 5 | Trend Analyzer | Queries: "What topics need follow-up discussion?" | Follow-up list |
| 6 | Copywriter | Writes meeting summary (2-minute read format) | drafts/meeting-summary.md |
| 7 | Orchestrator | Creates follow-up tasks in task_board.md from action items | Tasks in BACKLOG |
| 8 | Orchestrator | Sends summary to human via Telegram | Immediate notification |

---

## COMBINATION 7: The Newsletter Curator

**Curate industry newsletters automatically, every week.**

### Agent Flow

| Step | Who | Action | Output |
|------|-----|--------|--------|
| 1 | Cron (Friday 9AM) | Triggers weekly newsletter curation | Task created |
| 2 | Trend Analyzer | Scrapes 20 industry sources for the week's top content | Raw article list |
| 3 | Trend Analyzer | Uploads top articles to NotebookLM | Notebook updated |
| 4 | Trend Analyzer | Queries: "Rank these by relevance to BD e-commerce sellers. Top 5 only." | Curated list |
| 5 | Trend Analyzer | Queries: "Write a one-sentence summary for each of the top 5" | Summaries |
| 6 | Copywriter | Writes newsletter draft with curated content + commentary | drafts/newsletter-YYYY-MM-DD.md |
| 7 | Human | Reviews and approves | Approved |
| 8 | Distributor | Sends via email tool | Delivered |

---

## COMBINATION 8: Personal Knowledge Base ("Second Brain")

**Build a searchable knowledge base that actually works.**

### How It Works

1. Every time research is completed, Trend Analyzer uploads findings to a master NotebookLM notebook.
2. Over time, this notebook accumulates all your research, competitor data, content performance insights, and industry knowledge.
3. Any agent can query this master notebook before starting work: "What do we already know about [topic]?"
4. Prevents duplicate research and builds institutional memory.

### Master Notebook Query Patterns

```
"What have we learned about [topic] from our past research?"
"Have we created content about [topic] before? What performed well?"
"What are the recurring themes in our high-performing content?"
"Based on everything we know, what should we focus on next?"
```

---

## COMBINATION 9: Due Diligence / Market Research

**Evaluate any market, product, or partnership.**

### Agent Flow

| Step | Who | Action |
|------|-----|--------|
| 1 | Human | "Research [market/product/company] for potential investment/partnership" |
| 2 | Trend Analyzer | Web research: financials, news, competitors, leadership, reviews |
| 3 | Trend Analyzer | Upload all findings to NotebookLM |
| 4 | Trend Analyzer | Query: "What are the top 3 risks and top 3 opportunities?" |
| 5 | Trend Analyzer | Query: "Compare to competitors on price, features, and market position" |
| 6 | Copywriter | Write risk assessment briefing |
| 7 | Copywriter | Write competitor positioning table |
| 8 | Copywriter | Write executive summary with recommendation |
| 9 | Human | Reviews the full package |

---

## COMBINATION 10: The Explainer Factory

**Turn complex topics into simple, shareable content.**

### Agent Flow

| Step | Who | Action |
|------|-----|--------|
| 1 | Human | "Explain [complex topic] simply for our audience" |
| 2 | Trend Analyzer | Research fundamentals + latest developments |
| 3 | Trend Analyzer | Upload to NotebookLM, query: "Explain this at a 5th grade level" |
| 4 | Trend Analyzer | Query: "What are the 5 key terms someone must understand?" |
| 5 | Copywriter | Write ELI5 (explain like I'm 5) briefing |
| 6 | Copywriter | Write carousel breaking it down visually |
| 7 | Copywriter | Write flashcards for key terms |
| 8 | Visual Designer | Create infographic |
| 9 | Human | Reviews and approves for posting |

---

## NotebookLM Best Practices for OpenClaw Agents

### Token Savings
- Use `source_get_content` to extract only what you need before querying
- 12,000 tokens vs 150,000+ tokens = 10x faster, 10x cheaper

### Notebook Organization
- **One notebook per domain**: "BD E-commerce Trends", "Competitor Analysis", "Content Performance"
- **Tag notebooks** in the library for easy agent selection
- **Sync Drive sources** to keep notebooks updated when source docs change

### Query Patterns That Work Best
- Be specific: "What are the top 3 delivery problems for BD sellers?" not "Tell me about delivery"
- Ask for comparisons: "Compare X and Y based on [criteria]"
- Ask for evidence: "Give me data or quotes that support [claim]"
- Ask for gaps: "What is NOT covered in our sources about [topic]?"

### What NotebookLM Cannot Do (OpenClaw handles these)
- Execute actions (posting, emailing, scheduling)
- Generate images or visual content
- Access real-time data (it only knows what is uploaded)
- Write in a specific brand voice without examples (upload voice guide as a source)

---

## File Structure

```
project-root/
  |-- SOUL.md              # Agent identity (the "who")
  |-- AGENTS.md            # Operations manual (the "how")
  |-- HEARTBEAT.md         # Polling loop rules
  |-- task_board.md        # Shared async state
  |-- openclaw.json        # Gateway configuration
  |-- agents/              # Per-agent workspaces
  |   |-- jumbo/SOUL.md
  |   |-- trend-analyzer/SOUL.md
  |   |-- copywriter/SOUL.md
  |   |-- visual-designer/SOUL.md
  |   |-- distributor/SOUL.md
  |   +-- analytics/SOUL.md
  |-- drafts/              # Work-in-progress content
  |-- assets/              # Approved visual assets
  |-- research/            # Research findings
  +-- archive/             # Posted content + performance data
```

---

*Last updated: 2026-02-25*
*Playbook version: 1.0*
