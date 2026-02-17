# Architecture -- Content Orchestrator v1.0 (MVP)

**Source of truth:** `Content_Orchestrator_MVP_PRD.md`
**Date:** 2026-02-12
**Status:** RC ARCHITECT phase

---

## 1. Component Diagram

```
+---------------------+
|   Browser (User)    |
+----------+----------+
           |
           | HTTPS (JWT via Supabase Auth)
           v
+----------+----------+     Supabase Realtime (postgres_changes)
|  Web (Next.js)      |<-------------------------------------------+
|  apps/web/           |                                            |
|  - Dashboard         |                                            |
|  - Profile           |                                            |
|  - Resources         |                                            |
|  - Workflows         |                                            |
|  - Approvals/Export  |                                            |
+----------+----------+                                            |
           |                                                        |
           | REST (Bearer JWT)                                      |
           v                                                        |
+----------+----------+                                            |
|  API (FastAPI)       |                                            |
|  apps/api/           |    +------------------+                   |
|  - /workflows CRUD   |--->| Supabase Queues  |                   |
|  - /resources CRUD   |    | (pgmq extension) |                   |
|  - /approve,reject   |    +--------+---------+                   |
|  - Auth middleware    |             |                              |
+----------+----------+             | poll / dequeue               |
           |                        v                               |
           | direct DB      +-------+----------+                    |
           | reads          |  Worker Process   |                   |
           |                |  apps/api/worker/ |                   |
           |                |  - Dequeue loop   |                   |
           |                |  - Run lifecycle  |                   |
           |                +-------+----------+                    |
           |                        |                               |
           |                        | invoke                        |
           |                        v                               |
           |                +-------+-----------+                   |
           |                | LangGraph Engine  |                   |
           |                | (State Machine)   |                   |
           |                | - 8 pipeline nodes|                   |
           |                | - Checkpoint/resume                   |
           |                | - interrupt()     |                   |
           |                +-------+-----------+                   |
           |                        |                               |
           |              on interrupt: update workflow.status       |
           |              on node complete: save checkpoint          |
           |                        |                               |
           |                        v                               |
           |                +-------+-----------+                   |
           |                | Agent Zero        |                   |
           |                | (Sandboxed Docker) |                  |
           |                | - Plan generation  |                  |
           |                | - Research calls   |                  |
           |                +-------------------+                   |
           |                        |                               |
           v                        v                               |
+----------+------------------------+----------+                    |
|          Supabase Postgres (+ RLS)           |--------------------+
|  - users, profiles, resources, workflows     |  status changes
|  - workflow_snapshots, content_assets        |  trigger Realtime
|  - audit_events, usage_costs                 |  notifications
|  - pgmq queues (workflow_jobs)               |
+----------------------------------------------+
           |
           v
+----------+----------+
| Supabase Storage    |
| - resource-uploads  |
| bucket (RLS)        |
+---------------------+
```

---

## 2. Async Worker: Job Dispatch

### Decision: Supabase Queues (pgmq) -- not Redis, not polling

**Why pgmq:**
- Postgres-native. No extra infrastructure to deploy or pay for.
- Exactly-once delivery within a configurable visibility timeout.
- Enqueue + status update happen in the same database transaction (atomic).
- Already available in Supabase Postgres.

**Queue name:** `workflow_jobs`

**Message format:**
```json
{
  "workflow_id": "uuid",
  "action": "run | resume | regenerate",
  "resume_from_step": "topic_selection | hook_lab | null",
  "resume_payload": { "selected_topic_id": "..." } | null,
  "enqueued_at": "ISO-8601"
}
```

**How the worker loop works (plain English):**
1. Worker asks pgmq: "Give me 1 job, and hide it for 300 seconds so nobody else grabs it."
2. If there's a job: run the pipeline for that workflow.
3. When done (or paused at interrupt): acknowledge the message so it's removed from the queue.
4. If worker crashes mid-job: the message reappears after 300 seconds. Another worker (or the same one after restart) picks it up. The pipeline resumes from its last checkpoint.
5. If a job fails 3 times: it moves to a dead-letter queue (`workflow_jobs_dlq`) for manual inspection.
6. If no jobs: sleep 2 seconds, then check again.

**Worker pseudocode:**
```python
async def worker_loop():
    while True:
        msg = await pgmq_read("workflow_jobs", visibility_timeout=300, qty=1)
        if msg:
            try:
                await process_job(msg.payload)
                await pgmq_archive("workflow_jobs", msg.id)   # ack
            except Exception as e:
                await handle_failure(msg, e)                    # log, maybe DLQ
        else:
            await asyncio.sleep(2)
```

**Scaling:** MVP uses 1 worker process. For scale, run N workers -- pgmq guarantees each message goes to exactly one consumer.

---

## 3. LangGraph Checkpoint Strategy

### How checkpoints work (plain English)

Think of checkpoints like save points in a video game. After every step in the pipeline, LangGraph saves a "snapshot" of everything that's happened so far into Postgres. If anything goes wrong -- or if the pipeline pauses for your input -- it can pick up exactly where it left off.

### Technical details

**Checkpoint store:** `langgraph-checkpoint-postgres` library, pointing at Supabase Postgres.

**Connection:** Must use direct Postgres connection (port 5432), not the pooler, because the library uses `LISTEN/NOTIFY`.

**Thread ID = workflow_id.** Every workflow gets its own checkpoint timeline.

### Configurable Research Sources

The user controls WHERE the agent researches. Before starting a workflow, the user can toggle:

| Source | What it searches | Default |
|--------|-----------------|---------|
| **YouTube** | Top videos on the topic, sorted by views. Finds outliers (videos that overperformed relative to channel size). Extracts hooks, structures, topics. | ON |
| **Reddit** | Top posts/comments in relevant subreddits. Finds audience pain points and questions. | ON |
| **Twitter/X** | Trending threads and discussions on the topic. | OFF |
| **TikTok** | Top-performing short-form content on the topic. | OFF |
| **Instagram** | Reels and posts on the topic. | OFF |
| **Newsletters** | Searches newsletter platforms (Substack, Beehiiv) for recent coverage. | ON |
| **News** | Google News and news aggregators for timely angles. | ON |
| **Competitor channels** | User-specified YouTube channels to analyze. | OFF (user adds channels) |
| **User resources** | The user's own uploaded resources and gold-starred materials. | ON (always) |

**Outlier detection:** For YouTube and social media sources, the agent doesn't just find "most viewed." It finds **outliers** -- videos/posts that got 5-10x more views than the creator's average. These signal topics with unusually high audience demand.

### The 8-node pipeline

```
signal_research  (uses configured sources above)
      |
gap_analysis_topic_candidates
      |
topic_selection  <-- INTERRUPT (waits for user to pick a topic)
      |
hook_lab         <-- INTERRUPT (waits for user to pick a hook)
      |
script_generation
      |
editor
      |
testing
      |
approval         <-- INTERRUPT (waits for user to approve/reject)
```

### How interrupts work (plain English)

1. Pipeline runs step by step. After each step, a checkpoint is saved.
2. At `topic_selection`, the pipeline calls `interrupt()` -- it pauses and hands back the 10 topic candidates.
3. The worker sees the interrupt, updates `workflows.status` to `awaiting_topic`, and stops.
4. Your browser sees the status change via Realtime and shows the topic picker UI.
5. You pick a topic and click Submit.
6. The API enqueues a "resume" message with your choice.
7. The worker picks it up, loads the checkpoint, passes your choice back to the pipeline.
8. The pipeline continues from exactly where it paused -- no re-running prior steps.

Same pattern for hook selection and final approval.

### How resume works (code)

```python
from langgraph.types import Command

# Load checkpoint and resume with user's choice
result = await graph.ainvoke(
    Command(resume={"selected_topic_id": user_choice}),
    config={"configurable": {"thread_id": workflow_id}}
)
```

### Checkpoint tables vs workflow_snapshots

| Table | Purpose | Who writes |
|-------|---------|-----------|
| LangGraph checkpoint tables | Internal graph state for resume/replay | LangGraph (automatic) |
| `workflow_snapshots` | Application-level summaries for dashboard + audit | Our worker code (explicit) |

Both exist. They serve different purposes.

---

## 4. Agent Zero Sandbox

### Core principle: Agent Zero is untrusted.

It has LLM access and can execute code, so it must be fully isolated.

### Docker container setup

```yaml
services:
  agent-zero:
    image: agent0ai/agent-zero:latest
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=500M
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    # NO host mounts, NO privileged, NO host network
```

### Resource limits
- CPU: 2 cores max
- Memory: 4 GB max
- Disk: ephemeral tmpfs (destroyed after each run)
- Time: 120 second hard timeout per invocation

### Network restrictions
- **CAN reach:** LLM API endpoints (api.openai.com, api.anthropic.com)
- **CANNOT reach:** Supabase directly, host filesystem, other containers

### How the worker calls Agent Zero

1. Worker starts the Agent Zero container (or reuses a warm one).
2. Worker sends `POST /agent-zero/plan` with `{goal, profile_snapshot, resource_summary}`.
3. Agent Zero generates `workflow_plan.json`.
4. Worker validates the plan against a strict JSON schema.
5. If validation fails: one auto-repair attempt. If still invalid: workflow fails.
6. Worker stops the container.

### MVP simplification

In MVP, Agent Zero is **optional**. The LangGraph pipeline nodes themselves make direct LLM calls for research and generation. Agent Zero is only used for the planning step (generating `workflow_plan.json`). Set `AGENT_ZERO_ENABLED=false` to skip it entirely -- the pipeline uses a default plan.

---

## 5. Frontend Real-time Updates

### Decision: Supabase Realtime subscriptions

**How it works (plain English):**
- When the worker updates `workflows.status` in the database, Supabase automatically pushes that change to your browser over a WebSocket connection.
- No polling. No delay. You see "Running..." change to "Pick a topic" the instant it happens.

**What's subscribed to:**
- The `workflows` table (status changes)
- Filtered by your user_id (RLS ensures you only see your own)

**Frontend code pattern:**
```typescript
const channel = supabase
  .channel(`workflow-${workflowId}`)
  .on("postgres_changes", {
    event: "UPDATE",
    schema: "public",
    table: "workflows",
    filter: `id=eq.${workflowId}`,
  }, (payload) => {
    setStatus(payload.new.status);
  })
  .subscribe();
```

**Requirement:** Realtime must be enabled for the `workflows` table in the migration:
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE public.workflows;
```

---

## 6. Data Flow: Complete Workflow Run

Here's what happens from the moment you click "Generate" to getting your Content Pack:

| Step | Who | What happens | Database writes |
|------|-----|-------------|----------------|
| 1 | You | Click "Generate" with a goal | |
| 2 | API | Creates workflow row (status=queued), enqueues job | INSERT workflows, INSERT audit_events |
| 3 | Worker | Picks up job, sets status=running | UPDATE workflows.status |
| 4 | Pipeline | Runs signal_research (searches web, analyzes trends) | INSERT workflow_snapshots, INSERT usage_costs |
| 5 | Pipeline | Runs gap_analysis (generates 10 topic candidates) | INSERT content_assets (topic_candidates) |
| 6 | Pipeline | Hits interrupt at topic_selection | Checkpoint saved |
| 7 | Worker | Sets status=awaiting_topic | UPDATE workflows.status |
| 8 | Realtime | Pushes status change to your browser | (automatic) |
| 9 | You | Pick a topic, click Submit | |
| 10 | API | Enqueues resume message with your choice | INSERT audit_events (topic_selected) |
| 11 | Worker | Loads checkpoint, resumes pipeline | |
| 12 | Pipeline | Runs hook_lab (generates 7 hooks) | INSERT content_assets (hook_candidates) |
| 13 | Pipeline | Hits interrupt at hook_lab | Checkpoint saved |
| 14 | Worker | Sets status=awaiting_hook | UPDATE workflows.status |
| 15 | You | Pick a hook, click Submit | |
| 16 | API | Enqueues resume message | INSERT audit_events (hook_selected) |
| 17 | Worker | Resumes, runs script_generation | INSERT content_assets (long, 3 shorts, titles, desc, tags, pinned, thumbnail) |
| 18 | Pipeline | Runs editor (refines for voice/clarity) | UPDATE content_assets |
| 19 | Pipeline | Runs testing (quality checks) | INSERT content_assets (test_report) |
| 20 | Pipeline | Hits interrupt at approval | Checkpoint saved |
| 21 | Worker | Sets status=awaiting_approval | UPDATE workflows.status |
| 22 | You | Review pack, click Approve (or Reject) | |
| 23 | API | Updates assets to approved, sets workflow approved | UPDATE content_assets, UPDATE workflows, INSERT audit_events |

---

## 7. Error Handling and Retry Strategy

### Per-node retry
- Each LLM call retries up to 2 times with exponential backoff (2s, then 8s).
- On 3rd failure: the node fails.

### Workflow-level failure
- When a node fails, the worker catches it.
- Worker sets `workflows.status = 'failed'` and writes `error_message`.
- An audit_events row is logged.
- **The last checkpoint is preserved.** You can retry from the failed step.

### Queue-level recovery
- If the worker process crashes (kill -9, OOM), the pgmq message reappears after 300 seconds.
- Another worker picks it up. It checks `workflows.status` first -- if already `failed` or `approved`, it skips.
- After 3 failed dequeue attempts: message moves to dead-letter queue `workflow_jobs_dlq`.

### Schema validation failure
- Every LLM output is validated against a JSON schema.
- On failure: one auto-repair attempt (re-prompt with validation errors).
- If repair fails: node fails, workflow fails.

### Cost circuit breaker
- Per-step token ceiling: if one step exceeds `MAX_TOKENS_PER_STEP`, the step fails.
- Per-workflow token ceiling: if cumulative tokens exceed `MAX_TOKENS_PER_WORKFLOW`, workflow fails with reason `cost_limit_exceeded`.
- Per-user daily cap: checked before enqueueing a new workflow.
