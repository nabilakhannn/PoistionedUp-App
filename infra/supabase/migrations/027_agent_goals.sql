-- Migration 027: Formalize agent_goals table
-- This table was created manually in Supabase during Slice 73 but never
-- had a migration file. Used by goals router (CRUD + evaluate),
-- and agent_orchestrator (goal evaluation + progress tracking).

CREATE TABLE IF NOT EXISTS agent_goals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  goal_type TEXT NOT NULL,
  -- Valid types: posting_frequency, engagement_growth, research_cadence, content_pipeline, custom
  target_value FLOAT NOT NULL,
  target_unit TEXT NOT NULL DEFAULT 'per_week',
  -- Valid units: per_week, per_month, percent, count
  current_value FLOAT NOT NULL DEFAULT 0,
  platform TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  -- Valid statuses: active, paused, completed, archived
  priority TEXT NOT NULL DEFAULT 'P2',
  -- Valid priorities: P0, P1, P2, P3
  deadline_at TIMESTAMPTZ,
  last_evaluated_at TIMESTAMPTZ,
  last_action_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE agent_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own goals"
  ON agent_goals FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_agent_goals_user_status
  ON agent_goals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_goals_brand
  ON agent_goals(user_id, brand_id);
