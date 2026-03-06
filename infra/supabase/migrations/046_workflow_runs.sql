-- Migration 046: Workflow Runs — Slice 109
-- Tracks every workflow execution in the Agent Marketplace.

CREATE TABLE IF NOT EXISTS workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  brand_id UUID NOT NULL REFERENCES personal_brands(id),
  workflow_slug TEXT NOT NULL,
  inputs JSONB NOT NULL DEFAULT '{}',
  output TEXT,
  output_format TEXT DEFAULT 'text',
  status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
  engine TEXT DEFAULT 'builtin' CHECK (engine IN ('builtin', 'manus')),
  manus_task_id UUID REFERENCES manus_tasks(id),
  deliverable_id UUID REFERENCES agent_deliverables(id),
  duration_ms INT,
  tokens_used INT DEFAULT 0,
  model_used TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY workflow_runs_select ON workflow_runs
  FOR SELECT USING (user_id = auth.uid());
CREATE POLICY workflow_runs_insert ON workflow_runs
  FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY workflow_runs_update ON workflow_runs
  FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY workflow_runs_delete ON workflow_runs
  FOR DELETE USING (user_id = auth.uid());

CREATE INDEX IF NOT EXISTS idx_workflow_runs_user ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_slug ON workflow_runs(workflow_slug);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
