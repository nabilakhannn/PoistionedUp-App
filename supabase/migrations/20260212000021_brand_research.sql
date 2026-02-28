-- Migration 022: Brand Research Sessions
-- Tracks automated research pipelines that run when a user starts building a brand.
-- Each session has 7 stages that run sequentially, producing deliverables.

CREATE TABLE IF NOT EXISTS brand_research_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id    UUID NOT NULL REFERENCES personal_brands(id) ON DELETE CASCADE,

    -- User-provided seed data for research
    seed_input  JSONB NOT NULL DEFAULT '{}',
    -- e.g. { "name": "...", "industry": "...", "description": "...", "target_audience": "..." }

    -- Pipeline progress
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    current_stage TEXT NOT NULL DEFAULT 'niche_analysis',
    stages_completed TEXT[] NOT NULL DEFAULT '{}',

    -- Results per stage (accumulated as pipeline runs)
    results     JSONB NOT NULL DEFAULT '{}',
    -- e.g. { "niche_analysis": { ... }, "audience_research": { ... }, ... }

    -- Error tracking
    error       TEXT,

    -- Timing
    started_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast lookup by user + brand
CREATE INDEX IF NOT EXISTS idx_brand_research_user_brand
    ON brand_research_sessions(user_id, brand_id);

-- RLS
ALTER TABLE brand_research_sessions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "Users see own research sessions"
      ON brand_research_sessions FOR SELECT
      USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Users create own research sessions"
      ON brand_research_sessions FOR INSERT
      WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Users update own research sessions"
      ON brand_research_sessions FOR UPDATE
      USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Service role bypass (for API server)
DO $$ BEGIN
  CREATE POLICY "Service role full access on brand_research_sessions"
      ON brand_research_sessions FOR ALL
      USING (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
