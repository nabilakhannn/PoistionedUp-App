# ADR-02: Brain Layer + Poppy-Style UI (v1.1 Roadmap)

**Status:** PLANNED (after MVP pipeline ships)
**Date:** 2026-02-12
**Decision maker:** Product owner

---

## What the Product Owner Wants

The app should NOT be "just another research + write tool." It should be a **content brain** with:

1. **Its own thinking and personality** -- not just executing prompts, but reasoning about WHY
2. **Self-measurement** -- tracks what works, what doesn't, and tells the user
3. **Proactive advice** -- "you should make a video about X because Y"
4. **Self-improvement** -- gets better at matching the user's style over time
5. **Video link ingestion** -- paste YouTube/TikTok/Instagram/Facebook links, auto-extract transcripts
6. **Poppy-style canvas UI** -- spatial, visual, drag-and-drop (not flat lists)

---

## Poppy UI Reference (from screenshot)

The desired UI is a **canvas/whiteboard** style, not a traditional dashboard:

### Two-layer UI structure:
1. **Home/Dashboard** -- clean list of boards, folders, starred items, templates, "New Board" button. Simple table showing board name, last opened, created by, date. Sidebar: All Boards, Starred, Templates, Shared with me, Create Folder.
2. **Inside a Board** -- free-form canvas (see below)

### Canvas (inside a board) patterns observed:
- **Free-form canvas** -- drag items anywhere, group them visually (not rows/lists)
- **Mixed media cards** -- video thumbnails, text notes, AI chat panels, all on one board
- **Spatial organization** -- related items clustered together by the user
- **Embedded AI chat** -- "Poppy Chat" panels live on the canvas alongside content
- **Video preview cards** -- YouTube thumbnails with titles, directly on the canvas
- **Text/note cards** -- brand voice docs, strategies, script notes
- **Left toolbar** -- tools for adding different content types (text, media, shapes, etc.)
- **Multiple boards/tabs** -- top navigation for different projects or topics (e.g., "Research - Copy", "Hiring", "Affiliate")
- **Folder-like organization by purpose** -- user groups videos into "titles" folder, scripts into "script" folder, etc.

### How this maps to our app:
| Poppy pattern | Our v1.1 equivalent |
|--------------|-------------------|
| Canvas boards | Workspace boards per project/topic |
| Video cards | Resource cards with auto-thumbnail + transcript |
| Text cards | Notes, scripts, brand voice snippets |
| AI chat panels | Inline agent conversations per topic |
| Spatial grouping | Drag-and-drop folders: "Hooks", "Scripts", "Case Studies", "Competitors" |
| Left toolbar | Add resource (link/video/note/file), add AI chat, add section |
| Multiple tabs | Multiple boards per workspace |

---

## Brain Capabilities (v1.1)

### A. Thinking & Personality Layer
- Persistent agent persona with opinions (not just outputs)
- Every suggestion includes WHY reasoning: "I noticed your contrarian hooks get 2x more approvals. Let's lean into that."
- Agent has a name/personality the user can customize
- Chain-of-thought visible to user (optional "show me your thinking" toggle)

### B. Self-Measurement & Analytics
- Track approval vs rejection rates per asset type
- Track which hook types the user prefers
- Track which topics perform best (based on user feedback)
- Agent scores its own performance: "My approval rate is 73%, up from 60%"
- Dashboard: "Here's what I've learned about you so far"

### C. Proactive Advisor Mode
- Weekly briefing: "Based on your approved content and current trends, here are 3 video ideas for this week"
- Notifications: "I found a trending topic that matches your niche"
- Not just reactive (wait for Generate click) -- comes to the user with ideas

### D. Video Link Ingestion
- Paste YouTube URL → auto-extract transcript (via YouTube captions API or Whisper)
- Paste TikTok/Instagram/Facebook video URL → download + transcribe
- Analyze competitor videos: extract structure, hooks, pacing, topics
- Auto-tag extracted content (hooks, case studies, opinions, data points)
- Store as resources with visual thumbnail preview

### E. Folder-Based Resource Organization
- Resources organized in draggable folders by purpose:
  - "Hooks" -- reference hooks from competitors
  - "Scripts" -- full scripts for analysis
  - "Case Studies" -- examples to use in content
  - "Competitors" -- competitor channel analysis
  - "My Opinions" -- creator's unique takes
  - Custom folders
- Drag resources between folders
- Each workflow can reference specific folders

### F. Learning & Improvement Loop
- **Approval learning:** When user approves, extract patterns (hook type, tone, structure, topic category) and weight them higher next time
- **Rejection learning:** When user rejects, store the reason and enforce it as a constraint in future generations
- **Style drift detection:** If the agent notices the user's preferences are changing, it asks: "I noticed you've been approving more story-driven hooks lately. Should I prioritize those?"
- **Golden Library:** Approved assets automatically tagged and stored as reference material for future generations

---

## Cost Impact of v1.1 Features

| Feature | Additional cost per use |
|---------|----------------------|
| Video transcription (Whisper API) | ~$0.006/min of video ($0.06 for 10-min video) |
| Proactive trend scanning (daily) | ~$0.10-0.20/day (1-2 research calls) |
| Self-measurement analytics | No additional LLM cost (pure database queries) |
| Canvas UI | No additional API cost (frontend only) |
| Personality/reasoning layer | ~$0.05 extra per generation (additional system prompt context) |

---

## Video/Content Ingestion Technical Plan

| Capability | Tool/Method | Cost |
|-----------|------------|------|
| Extract all videos from a YouTube channel | YouTube Data API v3 (free: 10K units/day) | Free |
| Get video transcripts/captions | YouTube Captions API or yt-dlp subtitle extraction | Free |
| Transcribe videos without captions | OpenAI Whisper API | $0.006/min |
| Analyze visual content in video frames | GPT-4o vision (key frame extraction) | ~$0.01-0.05/video |
| Extract from TikTok/Instagram/Facebook | yt-dlp (supports 1000+ sites) + Whisper | Free + Whisper |
| PDF/docs/pictures | pypdf2, python-docx (already in MVP Slice 5) | Free |
| Drop entire YouTube channel link | YouTube Data API → batch import all videos as resources | Free |

### How "drop a YouTube channel" works:
1. User pastes a channel URL
2. Backend calls YouTube Data API to list all videos (title, URL, thumbnail, stats)
3. Each video becomes a resource card with thumbnail preview
4. User can select which videos to transcribe (or transcribe all)
5. Transcripts are chunked and stored as resource_chunks
6. Agent can now reference any of these in research/script generation

## Build Order for v1.1

1. Video link ingestion (YouTube first, then TikTok/Instagram)
2. YouTube channel bulk import (drop channel URL → import all videos)
3. Folder-based resource UI (canvas-style boards)
4. Learning loop (approval/rejection pattern extraction)
5. Self-measurement dashboard ("what I've learned about you")
6. Agent personality layer (custom persona + reasoning visibility)
7. Proactive advisor mode (weekly briefings + trend alerts)

---

## Why After MVP (not now)

1. The pipeline must work first -- if research and scripts are bad, no amount of personality helps
2. Video ingestion needs the resource system to be solid (Slice 5 must be done)
3. Learning requires data -- we need the user to approve/reject several workflows before patterns emerge
4. Canvas UI is a significant frontend rewrite -- MVP ships with a functional dashboard first, then we upgrade

The MVP proves: "Can the pipeline produce scripts worth approving?"
v1.1 proves: "Can the agent become a trusted content strategist?"
