# Slice 81 — NotebookLM MCP Activation

**Date:** 2026-02-27
**Status:** Complete (code side — requires manual token + notebook setup)
**Tests:** 1159 total (no new — config-only slice) | 0 TS errors

---

## What Was Built

Activated the NotebookLM MCP integration that was scaffolded in Slice 66. Added `mcp_notebooklm` to the tool allow-lists for 5 agents (Jumbo, Trend Analyzer, Copywriter, Competitor Analyst, QA Reviewer) and wrote detailed NotebookLM query instructions in each agent's SOUL.md.

## Files Changed

| Action | File | What |
|--------|------|------|
| MODIFY | `openclaw.json` | Added `mcp_notebooklm` to global `alsoAllow` + 5 agent allow-lists |
| MODIFY | `agents/jumbo/SOUL.md` | NotebookLM section + updated Brain workflow (step 5: query notebooks) |
| MODIFY | `agents/trend-analyzer/SOUL.md` | NotebookLM research workflow (query first, then web search) |
| MODIFY | `agents/copywriter/SOUL.md` | NotebookLM for voice examples, reference material, claim backing |
| MODIFY | `agents/competitor-analyst/SOUL.md` | NotebookLM for competitive intel + updated weekly workflow |
| MODIFY | `agents/qa-reviewer/SOUL.md` | NotebookLM for claim verification, voice comparison, quality grounding |

## How Each Agent Uses NotebookLM

| Agent | Primary Use | Query Pattern |
|-------|-------------|---------------|
| **Jumbo** | Brief enrichment — queries notebooks before creating task briefs for specialists | "What does our research say about [topic]?" |
| **Trend Analyzer** | Research deduplication — checks existing knowledge before web search | "What topics have we already covered?" |
| **Copywriter** | Voice grounding — references real examples from the owner's content | "How does the owner write about [topic]?" |
| **Competitor Analyst** | Historical context — compares past intel against current web findings | "What do we know about [competitor]?" |
| **QA Reviewer** | Claim verification — checks drafts against owner's real research | "What evidence do we have for [claim]?" |

## Manual Steps Required (Owner Must Do)

### Step 1: Create NotebookLM Notebooks
Go to [notebooklm.google.com](https://notebooklm.google.com) and create notebooks:

| Notebook | What to Upload |
|----------|----------------|
| Brand Voice Library | Top 20 LinkedIn posts, writing style guide, client testimonials |
| Competitor Intel | Competitor content screenshots, strategy analyses, market reports |
| Industry Research | PDFs, articles, books about your niche |
| Audience Insights | DM conversations, comments, survey results |
| Content Playbook | What hooks worked, engagement patterns, content strategies |

### Step 2: Get Google Access Token
- Go to Google Cloud Console
- Enable NotebookLM API
- Generate an OAuth access token

### Step 3: Add Token to VPS
```bash
ssh root@46.202.92.233
echo 'GOOGLE_ACCESS_TOKEN=your-token-here' >> /root/.openclaw/.env
```

### Step 4: Deploy Updated Config
Copy the updated `openclaw.json` and SOUL.md files to the VPS, then restart:
```bash
systemctl restart openclaw-gateway
```

## Security Checks

| Check | Status |
|-------|--------|
| Token stored in env var | `${GOOGLE_ACCESS_TOKEN}` — not hardcoded |
| Token is optional | System degrades gracefully without it |
| No new endpoints | Config-only changes |
| Agent sandboxing | All agents remain workspace-only |
| Tool scoping | Only 5 of 8 agents get NotebookLM (visual-designer, distributor, analytics excluded) |
