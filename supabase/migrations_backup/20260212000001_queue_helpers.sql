-- ============================================================
-- 002_queue_helpers.sql -- Thin wrappers around pgmq functions
-- Purpose: Expose pgmq operations via Supabase PostgREST .rpc()
-- pgmq functions live in the 'pgmq' schema which PostgREST
-- cannot reach directly, so we wrap them in 'public'.
-- ============================================================

-- Enqueue a workflow job
CREATE OR REPLACE FUNCTION public.enqueue_workflow_job(payload jsonb)
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT pgmq.send('workflow_jobs', payload);
$$;

-- Dequeue one workflow job with configurable visibility timeout
CREATE OR REPLACE FUNCTION public.dequeue_workflow_job(vt integer DEFAULT 300)
RETURNS TABLE(msg_id bigint, read_ct integer, enqueued_at timestamptz, vt timestamptz, message jsonb)
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT * FROM pgmq.read('workflow_jobs', $1, 1);
$$;

-- Acknowledge (archive) a processed job
CREATE OR REPLACE FUNCTION public.ack_workflow_job(id bigint)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT pgmq.archive('workflow_jobs', id);
$$;

-- Send a failed job to the dead-letter queue
CREATE OR REPLACE FUNCTION public.dlq_workflow_job(payload jsonb)
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
AS $$
  SELECT pgmq.send('workflow_jobs_dlq', payload);
$$;
