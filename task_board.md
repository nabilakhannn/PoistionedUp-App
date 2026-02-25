# POSITIONEDUP — SHARED TASK BOARD

> **PURPOSE**: Central state and async database for all agents.
> Agents do NOT talk to each other directly. They only read/write this file.
>
> **RULES**:
> - Each task is a checklist item inside a status section.
> - Metadata is in square-bracket tags on the same line.
> - Never delete another agent's task. Only update status, assignee, or output.
> - Always use ISO 8601 UTC timestamps.

---

## METADATA SCHEMA

```
- [ ] **{TASK_TITLE}** [ID:{id}] [PRIORITY:{P0|P1|P2|P3}] [ASSIGNEE:{agent|unassigned}] [CREATED:{ISO}] [UPDATED:{ISO}] [DUE:{ISO|none}] [TAGS:{comma-separated}]
  - **Brief**: {One-line description}
  - **Input**: {Source material, URL, or upstream task ID}
  - **Output**: {Where to write result — inline or file path}
  - **Notes**: {Context, constraints, feedback}
```

**Tag Definitions**:

| Tag | Values | Meaning |
|-----|--------|---------|
| ID | PU-001, PU-002, ... | Unique task identifier |
| PRIORITY | P0 (critical), P1 (high), P2 (normal), P3 (low) | Execution priority |
| ASSIGNEE | orchestrator, trend-analyzer, copywriter, visual-designer, distributor, analytics, unassigned | Owner |
| TAGS | Comma-separated | Content type, platform, campaign |

**Checkbox States**:
- `- [ ]` = Not started / TODO
- `- [x]` = Completed

---

## AGENT CAPABILITY PROFILES

| Agent ID | Claims Tasks Tagged With |
|----------|--------------------------|
| orchestrator | strategy, planning |
| trend-analyzer | research, trends, analysis, competitor |
| copywriter | copywriting, carousel, caption, script, hook, linkedin, youtube, twitter |
| visual-designer | design, visual, template, image |
| distributor | post, distribute, schedule |
| analytics | analytics, performance, report |

---

## 1. BACKLOG

> Goals assigned by Orchestrator or human. Tasks here are unassigned until claimed.
> All brand context (voice, audience, pillars) is injected by Jarvis from the Brain at task creation time.

*(No tasks in backlog — add your first brand in the PositionedUp app, then tell Jarvis to start creating content)*

---

## 2. IN PROGRESS

> Tasks currently claimed by an agent. Only ONE task per agent at a time.

*(No tasks currently in progress)*

---

## 3. REVIEW / APPROVAL

> Completed drafts awaiting human review. Human marks [x] to approve or adds feedback.

*(No tasks awaiting review)*

---

## 4. READY FOR DISTRIBUTION

> Approved content ready to post. Distributor picks topmost when scheduled time arrives.

*(No content ready for distribution)*

---

## 5. ARCHIVE

> Posted content with performance data. Keep last 30 days.

*(No archived tasks yet)*

---

*Last sync: 2026-02-25T10:00:00Z*
