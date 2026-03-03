-- Slice 84: Infrastructure Hardening
-- Ensures agent_deliverables exists (may not exist if migration 021 was skipped),
-- adds approval persistence columns, and adds an index for efficient lookups.

-- Step 1: Create table if it doesn't exist (idempotent — safe to re-run)
CREATE TABLE IF NOT EXISTS public.agent_deliverables (
  id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id              UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  task_id              TEXT        NOT NULL,
  title                TEXT        NOT NULL,
  file_path            TEXT,
  content              TEXT,
  deliverable_type     TEXT        NOT NULL DEFAULT 'document',
  created_by_agent_id  TEXT,
  status               TEXT        NOT NULL DEFAULT 'draft',
  feedback             TEXT,
  brand_id             UUID,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Step 2: Enable RLS (idempotent)
ALTER TABLE public.agent_deliverables ENABLE ROW LEVEL SECURITY;

-- Step 3: RLS policy (idempotent via DO block)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename  = 'agent_deliverables'
      AND policyname = 'Users can manage their own deliverables'
  ) THEN
    CREATE POLICY "Users can manage their own deliverables"
      ON public.agent_deliverables FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END;
$$;

-- Step 4: Add Slice 84 approval columns (idempotent — IF NOT EXISTS)
ALTER TABLE public.agent_deliverables
  ADD COLUMN IF NOT EXISTS approved_variation_ids  TEXT[]      DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS dismissed_variation_ids TEXT[]      DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS approvals_updated_at    TIMESTAMPTZ;

-- Step 5: Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_agent_deliverables_task
  ON public.agent_deliverables(user_id, task_id);

CREATE INDEX IF NOT EXISTS idx_deliverables_brand_type_created
  ON public.agent_deliverables(brand_id, deliverable_type, created_at DESC)
  WHERE brand_id IS NOT NULL;
