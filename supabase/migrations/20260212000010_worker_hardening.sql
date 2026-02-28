-- Worker hardening: retry count, claimed_at timestamp for visibility timeout
ALTER TABLE public.workflows ADD COLUMN IF NOT EXISTS retry_count INT NOT NULL DEFAULT 0;
ALTER TABLE public.workflows ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;

-- Index for stale claim detection
CREATE INDEX IF NOT EXISTS idx_workflows_claimed_at
ON public.workflows(claimed_at)
WHERE status = 'running' AND claimed_at IS NOT NULL;
