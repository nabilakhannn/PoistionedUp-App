# POSITIONEDUP — HEARTBEAT CHECKLIST

> **PURPOSE**: Execution rules for every heartbeat pulse.
> OpenClaw's native heartbeat triggers this every 15 minutes in the main session.
> The agent reads this file, evaluates rules in order, takes action or returns HEARTBEAT_OK.
>
> **MECHANISM**: Native OpenClaw heartbeat (agents.defaults.heartbeat)
> **INTERVAL**: Every 15 minutes
> **ACTIVE HOURS**: 07:00 - 23:00 ET (America/New_York)
> **SESSION**: Main session (context-aware, batches multiple checks)
> **COST SAVING**: Returns HEARTBEAT_OK when nothing needs attention (no message delivered)

---

## EXECUTION ORDER

Follow these steps in exact order. Stop at the FIRST rule that triggers.

```
PULSE START
  |-- Step 1: Parse task_board.md
  |-- Step 2: ROUTING — claim a task? -> If YES, execute, STOP
  |-- Step 3: COMPLETION — finish a task? -> If YES, submit, STOP
  |-- Step 4: SCHEDULING — time to post? -> If YES, distribute, STOP
  |-- Step 5: DELEGATION — spawn sub-agent? -> If YES, spawn, STOP
  |-- Step 6: MAINTENANCE — cleanup needed? -> If YES, perform, STOP
  +-- Step 7: Nothing to do -> return HEARTBEAT_OK, STOP
```

---

## RULE 1: ROUTING (Task Claiming)

**Trigger**: A task in BACKLOG has `[ASSIGNEE:unassigned]` AND at least one TAG matches your capability profile (see task_board.md).

**Steps**:
1. Scan BACKLOG top to bottom.
2. Filter for tasks where ASSIGNEE is unassigned AND at least one TAG matches you.
3. Sort by PRIORITY (P0 first), then DUE date (earliest first), then CREATED (oldest first).
4. Claim the top match: change ASSIGNEE to your agent ID, update UPDATED timestamp, move to IN PROGRESS.
5. Begin execution per the Brief and Input fields.
6. Add progress notes under the task.

**Rules**:
- Re-read the task before claiming to prevent race conditions.
- Never claim more than ONE task per pulse.
- If you already have a task in IN PROGRESS, do NOT claim another.

---

## RULE 2: COMPLETION (Task Submission)

**Trigger**: You have a task in IN PROGRESS where ASSIGNEE is your agent ID and work is done.

**Steps**:
1. Write output to the designated location (inline or file path).
2. Update UPDATED timestamp, mark checkbox [x].
3. Move entire task block to REVIEW / APPROVAL.
4. Add a note for the human reviewer.

**Quality gate**: Before submitting, verify output matches the Brief, follows all rules from SOUL.md, and formatting is clean.

---

## RULE 3: SCHEDULING (Content Distribution)

**Trigger**: ALL of these must be true:
- Current time (ET) is within 5 minutes of a Scheduled Time on a task in READY FOR DISTRIBUTION.
- The task checkbox is unchecked.
- Your agent ID is distributor.

**Steps**:
1. Find the topmost matching task.
2. Verify all assets exist (caption, visuals, hashtags, platform list).
3. Post to each platform.
4. Record live URLs and posting timestamp.
5. Mark [x], move to ARCHIVE.
6. Notify Orchestrator.

**Optimal posting windows (ET)**:

| Slot | ET Time | Best For |
|------|---------|----------|
| Morning | 08:00-09:00 | Tips, educational, LinkedIn |
| Midday | 11:30-13:00 | Quick tips, engagement posts |
| Afternoon | 15:00-16:00 | YouTube, longer content |
| Evening | 18:00-20:00 | Carousels, engagement, Twitter/X |

These are defaults. If the brand's performance data from the Brain shows different optimal times, use those instead.

If no scheduled post matches, skip this rule.

---

## RULE 4: DELEGATION (Sub-Agent Spawning)

**Trigger**: A task in BACKLOG or IN PROGRESS requires a specialist agent AND you are Jarvis (Orchestrator).

**Steps**:
1. Identify which specialist agent should handle the task based on tags and brief.
2. Use `sessions_spawn` to delegate:
   - `agentId`: the target specialist (trend-analyzer, copywriter, visual-designer, distributor, analytics)
   - `task`: clear description of what needs to be done, including file paths
   - `runTimeoutSeconds`: 900 (15 min max per sub-agent run)
3. Update task_board.md with delegation note.
4. The sub-agent will announce results back when done.

**Rules**:
- Max 3 active sub-agents at a time (maxChildrenPerAgent).
- Sub-agents use gpt-4o-mini by default (cost savings).
- Only Jarvis can spawn sub-agents. Other agents cannot spawn.
- If a sub-agent fails, log the error and retry on next pulse.

---

## RULE 5: MAINTENANCE

### 5a. Stale Task Detection
- Task in IN PROGRESS for more than 24 hours.
- Action: Add warning note, escalate priority.

### 5b. Archive Pruning
- Tasks in ARCHIVE older than 30 days.
- Action: Remove from task_board.md, save to archive/YYYY-MM.md.

### 5c. Dependency Resolution
- Task in BACKLOG has upstream dependency that is now complete.
- Action: Update notes to mark as unblocked, raise priority if needed.

### 5d. Sub-Agent Health Check
- Check for timed-out or failed sub-agent runs via `/subagents list`.
- Action: Log failures, retry if appropriate, alert human if repeated.

### 5e. Daily Summary (once per day at 23:00 ET)
- Trigger: Current time is 23:00-23:15 ET.
- Action: Append one-line summary to Daily Log section.

---

## RULE 6: RESOURCE SAVING (Default)

**Trigger**: NONE of Rules 1-5 triggered.

**Action**:
- Return HEARTBEAT_OK
- Do NOT modify task_board.md
- Do NOT generate any content
- Do NOT make any API calls
- Terminate immediately

This is critical for cost control. Most pulses should result in HEARTBEAT_OK.

---

## AGENT-SPECIFIC PULSE PRIORITIES

| Agent | Priority Order |
|-------|---------------|
| Orchestrator | Check stale tasks -> Check sub-agent health -> Delegate pending tasks -> Check empty backlog -> Decompose pending goals -> HEARTBEAT_OK |
| Trend Analyzer | Claim research tasks -> Continue in-progress research -> Submit findings -> HEARTBEAT_OK |
| Copywriter | Check upstream dependencies done -> Claim writing tasks -> Continue drafts -> Submit -> HEARTBEAT_OK |
| Visual Designer | Check copy dependencies done -> Claim design tasks -> Create assets -> Submit -> HEARTBEAT_OK |
| Distributor | Check scheduling rule FIRST -> Claim posting tasks -> HEARTBEAT_OK |
| Analytics | Check archive for unscored posts (48h+) -> Fetch metrics -> Generate reports -> HEARTBEAT_OK |

---

## LOBSTER WORKFLOWS (Deterministic Pipelines)

For multi-step operations that need approval gates, use Lobster workflows instead of ad-hoc tool calls:

| Workflow | File | When To Use |
|----------|------|-------------|
| content-review | workflows/content-review.lobster | Review and approve content before human review |
| weekly-review | workflows/weekly-review.lobster | Compile and deliver weekly performance summary |

Lobster workflows pause at approval gates and can be resumed later. Use them for any multi-step process where you need human sign-off between steps.

---

## ERROR HANDLING

1. Do NOT crash the pulse. Catch errors gracefully.
2. Log errors on the task: "ERROR [timestamp]: [description]"
3. Do NOT retry in the same pulse. Wait for next pulse.
4. If 3 consecutive pulses fail on the same task: escalate to P0, add tag "needs-human".
5. Always return after handling error.
6. Sub-agent failures: log the announce result, mark task as blocked, retry on next pulse.

---

## CONFIGURATION

```
HEARTBEAT_INTERVAL=15m
ACTIVE_HOURS=07:00-23:00
TIMEZONE=America/New_York
MAX_CONCURRENT_SUBAGENTS=4
MAX_CHILDREN_PER_AGENT=3
MAX_SPAWN_DEPTH=2
SUBAGENT_TIMEOUT=900s
MAX_TASKS_PER_AGENT=1
```

---

*Last updated: 2026-02-25*
*Version: 3.0 — Brand-agnostic, ET timezone*
