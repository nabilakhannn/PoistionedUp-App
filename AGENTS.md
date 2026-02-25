# POSITIONEDUP — AGENTS (Operations Manual)

> This file defines HOW the system works. Workflows, processes, step-by-step procedures.
> SOUL.md says "be engaging." This file says exactly how to be engaging.
> This file can be updated frequently as processes improve.

---

## FILE MAP

| File | Purpose | Who Reads | Who Writes |
|------|---------|-----------|------------|
| SOUL.md | Identity, rules, boundaries | All agents | Human only |
| AGENTS.md | This file — workflows and processes | All agents | Orchestrator + Human |
| task_board.md | Shared state, task tracking | All agents | All agents |
| HEARTBEAT.md | Pulse execution rules | All agents | Orchestrator + Human |
| AGENT_BRIDGE_PLAYBOOK.md | How agents use the PositionedUp Brain | All agents | Human only |
| openclaw.json | Gateway configuration | Gateway process | Human only |
| drafts/ | Work-in-progress content files | Copywriter, Designer | Copywriter, Designer |
| assets/ | Final approved visual assets | Distributor | Visual Designer |
| archive/ | Completed and posted content | Analytics | Distributor |
| research/ | Research findings and data | Copywriter, Orchestrator | Trend Analyzer |

---

## COMMUNICATION FLOW

```
Human gives high-level goal via Telegram or Mission Control
    |
    v
Orchestrator queries PositionedUp Brain (Agent Bridge API) for brand context
    |
    v
Orchestrator breaks it into tasks -> writes to task_board.md BACKLOG (with Brain context)
    |
    v
Specialists poll task_board.md every 15 min (HEARTBEAT)
    |
    +-- Trend Analyzer claims research tasks
    |       +-- Writes findings to research/ and updates task_board.md
    |
    +-- Copywriter claims writing tasks (after research is done)
    |       +-- Writes drafts to drafts/ and updates task_board.md
    |
    +-- Visual Designer claims design tasks (after copy is done)
    |       +-- Saves assets to assets/ and updates task_board.md
    |
    +-- Distributor claims posting tasks (after human approval)
    |       +-- Posts to platforms and updates task_board.md
    |
    +-- Analytics reviews posted content
            +-- Appends performance data to archive/
```

---

## ORCHESTRATOR WORKFLOWS

### O1: Receive Human Goal
1. Parse the human's message for intent.
2. Classify: new content request (O2), status check (O3), feedback on draft (O4), strategy change (O5), or unknown (ask to clarify).
3. Acknowledge receipt and summarize what you understood.

### O2: Decompose Goal into Tasks
1. **Call `GET /active-brand`** to get the current brand_id.
2. **Call `GET /context/{brand_id}`** to get voice DNA, content pillars, performance data, writing rules.
3. Identify content type (post, carousel, video script, thread, etc.).
4. Identify target platforms (LinkedIn, YouTube, Twitter/X, Instagram, Facebook, etc.).
5. Break goal into atomic tasks — each completable by ONE specialist in ONE session.
6. **Include Brain context in every task brief** (voice, pillars, performance, writing rules, relevant knowledge).
7. Write each task to task_board.md BACKLOG with full metadata.
8. Set dependencies: if Task B needs Task A output, note upstream ID in Input field.
9. Set priorities: research P1, writing P2 (depends on research), design P2, posting P1 (time-sensitive).
10. Confirm to human with task count and expected timeline.

### O3: Status Report
1. Parse task_board.md.
2. Count tasks by section (Backlog, In Progress, Review, Ready, Archive).
3. Flag stale or blocked tasks.
4. Report concise summary to human.

### O4: Process Human Feedback
1. Find the task in Review/Approval section.
2. If approved: mark complete, move to Ready for Distribution, set schedule.
3. If change requested: add feedback to task, move back to In Progress, reassign.
4. If rejected: cancel task, move to Archive with reason.

### O5: Strategy Adjustment
1. If change affects SOUL.md: tell human to edit SOUL.md manually.
2. If change affects workflows: update AGENTS.md.
3. If change affects current tasks: update task_board.md.

---

## TREND ANALYZER WORKFLOWS

### T1: Weekly Trend Research
1. **Read the brand profile from the task brief** — know exactly who the target audience is.
2. Search sources relevant to the brand's niche: Reddit, LinkedIn, YouTube, Twitter/X, Google Trends, industry news, niche communities.
3. For each source extract: topic, pain point, content angle, evidence (link/quote).
4. Score each finding: relevance (1-5), freshness (1-5), content potential (1-5).
5. Output the top 5 findings sorted by total score.
6. Save detailed findings to research/YYYY-MM-DD-weekly-trends.md.
7. Move task to Review.

### T2: Competitor Content Scan
1. Check competitors listed in the brand's profile (from Brain context).
2. Note high-engagement content types and topics.
3. Identify gaps they are NOT covering.
4. Write findings to research/ folder.

---

## COPYWRITER WORKFLOWS

### C1: Carousel Script Writing
1. Read upstream research from Input field. If upstream not done, do NOT start — wait.
2. Plan structure: Hook slide, 3-5 content slides, CTA slide.
3. Write each slide (max 30 words per slide).
4. Write the caption (hook first line, 3-5 lines total, end with engagement CTA, 5-8 hashtags).
5. Run self-review checklist (see below).
6. Save to drafts/PU-XXX-carousel.md.
7. Move task to Review.

### C2: Single Post / Caption
1. Read upstream context from Input field.
2. Write: hook line, body (2-3 lines), CTA + engagement prompt.
3. Follow platform-specific length guidelines from Brain context.
4. Run self-review checklist.
5. Save to drafts/PU-XXX-caption.md.
6. Move to Review.

### C3: YouTube / Video Script
1. Read upstream research and brand context.
2. Structure: Hook (first 5 seconds), intro, main content, CTA, outro.
3. Match the brand's voice DNA for spoken content.
4. Save to drafts/PU-XXX-script.md.
5. Move to Review.

### C4: Revision from Feedback
1. Read human feedback carefully.
2. Make ONLY the changes requested. Do not rewrite everything.
3. Note what changed in revision notes.
4. Move back to Review.

### Copywriter Self-Review Checklist
- [ ] Read every line out loud. Does it sound natural?
- [ ] Does it match the Voice DNA provided in the brief?
- [ ] Would the target audience (from brand profile) understand every word?
- [ ] One clear takeaway per piece?
- [ ] Hook is genuinely interesting (not generic motivation)?
- [ ] CTA is specific?
- [ ] Writing rules from the Brain are followed exactly?
- [ ] Reference material and inspiration from the brief are used?
- [ ] Patterns from performance data are applied?

### Content Language & Style

**There is no hardcoded language or style guide here.** All style rules come from the active brand's Voice DNA and Writing Rules in the Brain.

When writing, always follow:
1. **Voice DNA** from the task brief — this is how the brand sounds
2. **Writing Rules** from the task brief — these are non-negotiable style constraints
3. **Performance Data** from the task brief — this is what works for this specific audience

---

## VISUAL DESIGNER WORKFLOWS

### V1: Carousel Visual Creation
1. Read approved copy from upstream copywriting task.
2. Select template based on brand's visual identity (from Brain context).
3. For each slide: place text with readable font size, use brand colors, keep backgrounds clean.
4. Export as PNG (1080x1080 for Instagram, 1200x628 for Facebook, 1080x1920 for Stories).
5. Save to assets/PU-XXX/slide-1.png, slide-2.png, etc.
6. Move to Review.

**Design rules**:
- Mobile-first always.
- Text must be legible without zooming.
- Max 2 fonts per carousel.
- Brand logo on last slide only (small, bottom corner).
- Follow the brand's visual preferences from the Brain context.

### V2: Template Creation
1. Design reusable templates for carousel, single image, story format.
2. Save to assets/templates/.
3. Document usage in this file.

---

## DISTRIBUTOR WORKFLOWS

### D1: Scheduled Posting
1. Read topmost approved task from Ready for Distribution.
2. Verify all assets exist (caption, visuals, hashtags, platform list).
3. Post to each specified platform using the posting tool.
4. Verify post is live and copy the URL.
5. Record live URL and posting timestamp on the task.
6. Move to Archive.
7. Notify Orchestrator.

**Critical**: If ANY asset is missing or API fails, do NOT post. Mark error and alert Orchestrator.

### D2: Cross-Platform Adaptation
1. Take approved content for one platform.
2. Adapt for other platforms (shorter caption for Twitter, more hashtags for Instagram, etc.).
3. Save adapted versions as separate tasks in Review.

---

## ANALYTICS WORKFLOWS

### A1: Post Performance Check (48h after posting)
1. Fetch engagement metrics: reach, likes, comments, shares, saves, clicks.
2. Calculate engagement rate: (likes + comments + shares) / reach * 100.
3. Classify: Viral (>5%), Strong (2-5%), Average (1-2%), Underperforming (<1%).
4. Append metrics to archived task.
5. Note success patterns for high performers.

### A2: Weekly Performance Report
1. Scan all archived posts from the past 7 days.
2. Generate summary: total posts, average engagement, best/worst performers, top topics.
3. Save to research/weekly-report-YYYY-MM-DD.md.
4. Send to Orchestrator for forwarding to human.

### A3: Pattern Detection (after 20+ posts)
1. Analyze: which content types, topics, posting times, hook styles, and formats perform best.
2. Write insights to research/content-patterns.md.
3. Orchestrator uses these to inform future task decomposition.

---

## CONTENT LIFECYCLE

```
1. IDEA (Human or Trend Analyzer identifies topic)
2. TASK (Orchestrator creates task in Backlog with Brain context)
3. RESEARCH (Trend Analyzer gathers data)
4. DRAFT (Copywriter writes content using brand voice)
5. DESIGN (Visual Designer creates assets)
6. REVIEW (Human approves or rejects)
     +-- REVISION (if rejected, back to step 4 or 5)
7. SCHEDULE (Distributor sets posting time)
8. PUBLISH (Distributor posts to platforms)
9. MEASURE (Analytics tracks performance at 48h)
10. LEARN (Analytics feeds patterns back to Brain -> step 1)
```

Average time from idea to publish: 2-3 days.

---

## WEEKLY RHYTHM

| Day | Focus | Key Tasks |
|-----|-------|-----------|
| Saturday | Research | Trend Analyzer runs weekly research. Orchestrator plans content calendar. |
| Sunday | Planning | Orchestrator creates all tasks for the week. Copywriter starts first batch. |
| Monday | Writing | Copywriter completes 2-3 drafts. Visual Designer starts on completed copy. |
| Tuesday | Design + Review | Visual Designer completes assets. Human reviews first batch. |
| Wednesday | Posting Day 1 | Distributor posts approved content. Copywriter writes next batch. |
| Thursday | Writing + Design | Second batch through the pipeline. |
| Friday | Posting Day 2 + Analytics | Second batch posted. Analytics runs. Weekly report generated. |

Target posting frequency: 3-5 posts per week (adjustable per brand).

---

## ESCALATION PROCEDURES

### Agent is stuck
1. Agent adds BLOCKED note to its task with reason.
2. Orchestrator detects on next pulse.
3. Orchestrator reassigns, provides missing info, or escalates to human.

### Quality is poor (draft rejected 2+ times)
1. Orchestrator flags task as P0 with context about what is wrong.
2. If same issue repeats 3 times, Orchestrator asks human if writing rules need adjustment.

### Costs are high
1. If daily token usage exceeds 80% before 6 PM: pause P2/P3 tasks, only P0/P1 continue.
2. Notify human.

### System is idle (no tasks for 48h)
1. Orchestrator proactively creates a trend research task.
2. Notify human and ask for new ideas.

---

*Last updated: 2026-02-25*
*Version: 2.0 — Brand-agnostic rewrite*
