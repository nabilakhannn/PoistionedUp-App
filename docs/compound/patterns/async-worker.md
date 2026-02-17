# Pattern: Async Worker (Table-Based Polling)

**Slice:** 4 — Worker: Queue + Run Lifecycle
**Date:** 2026-02-12

---

## What this pattern does

A background worker process polls the database for workflows with `status = 'queued'`, claims one at a time using optimistic locking, runs a stub pipeline, and updates workflow status through its lifecycle.

## Key design decisions

### Table-based polling (not pgmq)

pgmq is set up in the database but isn't accessible via the Supabase REST API (PostgREST only exposes the `public` schema, pgmq functions live in the `pgmq` schema). For MVP, we use table-based polling:

- `status = 'queued'` IS the queue
- Worker polls every 2 seconds
- Atomically claims via `UPDATE ... WHERE status = 'queued'` (optimistic locking)
- No separate enqueue step needed — `POST /workflows` inserts with `status = 'queued'`

**Future upgrade path:** When a direct Postgres connection (via `SUPABASE_DB_URL`) is configured, swap to pgmq for exactly-once delivery and visibility timeouts.

### Optimistic locking for claim

```python
# Find oldest queued workflow
resp = client.table("workflows").select("id").eq("status", "queued").order("created_at").limit(1).execute()
wf_id = resp.data[0]["id"]

# Atomically claim — only works if still queued
claim = client.table("workflows").update({"status": "running"}).eq("id", wf_id).eq("status", "queued").execute()
if not claim.data:
    # Another worker got it, skip
    return None
```

If two workers SELECT the same row, only one UPDATE succeeds (the other returns empty).

### Status transition validation

Every status change is validated against a transition map before executing:

```python
VALID_TRANSITIONS = {
    "queued": {"running"},
    "running": {"awaiting_topic", "awaiting_hook", "awaiting_approval", "approved", "failed"},
    "awaiting_topic": {"running"},
    "awaiting_hook": {"running"},
    "awaiting_approval": {"approved", "rejected"},
}
```

Invalid transitions raise `ValueError` immediately.

### Stub executor (replaced in Slice 6)

The stub executor simulates the 8-step pipeline:
1. Runs non-interrupt steps with 1-second delays
2. Creates a `workflow_snapshot` row after each step
3. At interrupt steps (`topic_selection`, `hook_lab`, `approval`), sets the appropriate `awaiting_*` status and returns
4. Resume action: reads `current_step`, starts from the next step in the pipeline

### Failure handling

- On exception: `mark_failed()` sets `status = 'failed'`, writes `error_message`, logs audit event
- No automatic retry in MVP (user initiates retry manually)
- Worker handles its own exceptions — never crashes the loop

### Graceful shutdown

Signal handlers for SIGTERM and SIGINT set a `_running = False` flag. The worker finishes its current job, then exits.

## Files

| File | Purpose |
|------|---------|
| `worker/queue.py` | `claim_next_job()` — table-based polling with optimistic lock |
| `worker/lifecycle.py` | `update_status()`, `create_snapshot()`, `mark_failed()` |
| `worker/executor.py` | `run_stub_pipeline()` — simulates 8 steps with interrupts |
| `worker/main.py` | Entry point: poll loop, signal handling, error recovery |

## How to run

```bash
cd apps/api
python -m worker.main
```

## Gotchas

1. **Stale queued workflows:** If tests leave workflows in `queued` status, the worker (or next test) picks them up. Always clean up test data.
2. **Service role key required:** Worker uses `SUPABASE_SERVICE_ROLE_KEY` to bypass RLS. Never expose this key.
3. **Python path:** Worker imports from both `app/` and `worker/`. Run from `apps/api/` directory so both are on the path.
