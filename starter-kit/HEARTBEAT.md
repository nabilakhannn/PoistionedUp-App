# HEARTBEAT.md — Agent Execution Protocol

> Paste this into each agent's workspace. It defines what the agent does on every
> heartbeat pulse. Agents follow this protocol from top to bottom, stopping at the
> first rule that triggers action.

---

## CONFIGURATION

```
HEARTBEAT_INTERVAL=15m          # How often the pulse fires [CUSTOMIZE]
ACTIVE_HOURS_START=07:00        # Don't run outside these hours [CUSTOMIZE]
ACTIVE_HOURS_END=23:00          # [CUSTOMIZE]
TIMEZONE=America/New_York       # Your timezone [CUSTOMIZE]
MAX_TOKENS_PER_PULSE=4000       # Hard limit — return HEARTBEAT_OK if you'd exceed this
MAX_API_CALLS_PER_PULSE=3       # Hard limit
MAX_CONCURRENT_SUBAGENTS=4
MAX_CHILDREN_PER_AGENT=3
MAX_SPAWN_DEPTH=2
SUBAGENT_TIMEOUT=900s           # 15 minutes per sub-agent session
```

---

## EXECUTION ORDER

**STOP at the first rule that triggers. Do not execute multiple rules in one pulse.**

### Rule 1: ROUTING — Claim a Task
```
IF there is an unassigned task in task_board.md matching my capability tags
  AND I have no task currently IN PROGRESS
THEN
  Claim the highest-priority matching task (P0 > P1 > P2, then by DUE date)
  Update task: status=IN PROGRESS, assignee=my-id, updated=now
  BEGIN working on it
  STOP
```

### Rule 2: COMPLETION — Submit Finished Work
```
IF I have a task in IN PROGRESS and I have completed all steps
THEN
  Save output to appropriate folder (drafts/, research/, assets/)
  Update task: status=REVIEW, completion_note="[summary] File: [path]"
  Write: REQUEST @orchestrator please submit [task_id] as deliverable to Mission Control
  STOP
```

### Rule 3: SCHEDULING — Post Due Content (Distributor only)
```
IF I am the Distributor agent
AND there is a scheduled item in the Brain with scheduled_at within ±5 minutes of now
AND the item has status=scheduled (meaning it was approved by the human)
THEN
  Post to platform via connector credentials
  Record live URL in Brain
  Update item status=published
  STOP
```

### Rule 4: DELEGATION — Spawn Sub-Agents (Orchestrator only)
```
IF I am the Orchestrator
AND there are 2+ tasks for the same specialist AND I have capacity
THEN
  Spawn a sub-agent session for that specialist
  Assign the tasks
  STOP
```

### Rule 5: MAINTENANCE — Cleanup
```
IF any of the following are true:
  - A task has been IN PROGRESS for >24 hours without update
  - Archive has items older than 30 days that haven't been pruned
  - A sub-agent session has been running >15 minutes with no output
  - There are 3+ consecutive heartbeat failures on any agent
THEN
  Stale task: escalate to P0, add "needs-human" tag, notify orchestrator
  Old archive: move to archive/YYYY-MM.md
  Hung sub-agent: terminate session, create retry task
  3+ failures: escalate to P0, alert human via notification
  STOP
```

### Rule 6: DEFAULT — Do Nothing (Cost Saver)
```
IF none of the above triggered
THEN
  Return HEARTBEAT_OK
  (No API calls, no content generated, no cost)
```

---

## AGENT-SPECIFIC PULSE PRIORITIES

### Orchestrator
1. Check for stale tasks → escalate if needed
2. Check sub-agent health → terminate hung sessions
3. Delegate tasks to idle specialists
4. Check goal progress → create catch-up tasks if behind
5. HEARTBEAT_OK

### Researcher
1. Check for completed task → submit if done
2. Claim a research task if available
3. Continue in-progress research (next step)
4. HEARTBEAT_OK

### Writer
1. Check dependencies (research must be complete before writing starts)
2. Check for completed task → submit if done
3. Claim a writing task if deps met
4. Continue in-progress draft
5. HEARTBEAT_OK

### QA Reviewer
1. Check for pending content in REVIEW status
2. Score and provide feedback
3. If pass: mark ready for scheduling, notify orchestrator
4. If fail: create revision task for writer
5. HEARTBEAT_OK

### Publisher (Distributor)
1. **Check scheduling rule FIRST** (Rule 3 above)
2. Check for newly approved content → create scheduled item
3. HEARTBEAT_OK

### Analytics
1. Check for posts published 48+ hours ago without analysis
2. Fetch engagement metrics
3. Score against averages → create memory if viral or flop
4. Check if weekly report is due → generate and submit
5. HEARTBEAT_OK

---

## TASK BOARD FORMAT

```markdown
## [TASK_ID] [Task Title]
[ASSIGNEE:unassigned|agent-id] [PRIORITY:P0|P1|P2] [STATUS:BACKLOG|IN PROGRESS|REVIEW|ARCHIVE]
[TAGS:research,content,analysis] [DUE:YYYY-MM-DD] [CREATED:ISO] [UPDATED:ISO]

**Description:** What needs to be done.
**Brief:** Context from the Brain (voice DNA, performance data, relevant knowledge).
**Dependencies:** Which other tasks must complete first.
**Completion Note:** (filled when done) Summary + file path + any requests.
```

**Task ID format:** `[PROJECT_PREFIX]-NNN` — e.g., `PB-042`, `SK-001` [CUSTOMIZE prefix]

---

## ERROR HANDLING

- **Catch all errors gracefully** — never crash the heartbeat pulse
- **Log errors on the task** in the completion note or a status update
- **Do NOT retry** in the same pulse — let the next heartbeat try again
- **After 3 consecutive failures on the same task:** escalate to P0, add "needs-human" tag

---

## AUTOMATED SCHEDULES [CUSTOMIZE]

These run via the cron system, not the heartbeat:

| Schedule | What | Agent |
|----------|------|-------|
| Daily 8 AM | Morning briefing (schedule, tasks, performance, goals) | Orchestrator |
| Daily 9 AM | Content calendar check (fill gaps) | Orchestrator |
| Daily 10 AM | QA review of pending drafts | QA Reviewer |
| Monday 6 AM | Weekly competitor intelligence scan | Researcher |
| Saturday 10 AM | Weekly trend research | Researcher |
| Sunday 8 PM | Weekly analytics report | Analytics |
