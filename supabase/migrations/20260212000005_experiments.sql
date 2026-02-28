-- ============================================================
-- 006_experiments.sql -- Experimentation + Self-Voice DNA
-- Lets the agent propose A/B experiments, track variants,
-- and build a Voice DNA from the user's own published content.
-- Also adds drift detection baseline to profiles.
-- ============================================================


-- 1. agent_experiments table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.agent_experiments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- What we're testing
  hypothesis        TEXT NOT NULL,                -- "Story hooks outperform question hooks"
  variable          TEXT NOT NULL,                -- hook_type, topic_category, posting_time, cta_style
  variant_a         TEXT NOT NULL,                -- "story"
  variant_b         TEXT NOT NULL,                -- "question"
  platform          TEXT NOT NULL,                -- youtube, linkedin, etc.

  -- Lifecycle
  target_posts      INT NOT NULL DEFAULT 4,       -- How many posts per variant before concluding
  status            TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN (
    'proposed',     -- Agent suggested, awaiting user approval
    'approved',     -- User approved, waiting for posts
    'running',      -- Posts are being tagged to variants
    'completed',    -- Enough data collected, winner determined
    'cancelled'     -- User cancelled or experiment abandoned
  )),

  -- Tracking
  variant_a_posts   UUID[] DEFAULT '{}',          -- content_post IDs assigned to variant A
  variant_b_posts   UUID[] DEFAULT '{}',          -- content_post IDs assigned to variant B
  variant_a_avg_engagement FLOAT,                 -- Calculated avg for variant A
  variant_b_avg_engagement FLOAT,                 -- Calculated avg for variant B

  -- Results
  winner            TEXT,                          -- 'variant_a', 'variant_b', 'inconclusive'
  conclusion        TEXT,                          -- Human-readable conclusion
  resulting_memory_id UUID REFERENCES public.agent_memory(id) ON DELETE SET NULL,

  -- Timestamps
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ
);

ALTER TABLE public.agent_experiments ENABLE ROW LEVEL SECURITY;


-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_experiments_user_id
  ON public.agent_experiments(user_id);

CREATE INDEX IF NOT EXISTS idx_experiments_status
  ON public.agent_experiments(user_id, status)
  WHERE status IN ('approved', 'running');

CREATE INDEX IF NOT EXISTS idx_experiments_platform
  ON public.agent_experiments(user_id, platform);


-- 3. Updated_at trigger
-- ============================================================
CREATE TRIGGER set_experiments_updated_at
  BEFORE UPDATE ON public.agent_experiments
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 4. RLS Policies
-- ============================================================
CREATE POLICY "Users can view own experiments"
  ON public.agent_experiments FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own experiments"
  ON public.agent_experiments FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own experiments"
  ON public.agent_experiments FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own experiments"
  ON public.agent_experiments FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- 5. Self-Voice DNA + Drift Baseline on profiles
-- ============================================================
-- self_voice_dna: extracted from user's OWN published content (vs voice_dna from reference creators)
-- voice_drift_baseline: statistical baseline for drift detection
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS self_voice_dna JSONB DEFAULT '{}'::jsonb;

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS voice_drift_baseline JSONB DEFAULT '{}'::jsonb;
