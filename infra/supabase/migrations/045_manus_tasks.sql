-- Migration 045: Manus Tasks — Slice 109
-- Tracks Manus AI task lifecycle for optional BYOK integration.

CREATE TABLE IF NOT EXISTS manus_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  brand_id UUID NOT NULL REFERENCES personal_brands(id),
  manus_task_id TEXT,
  workflow_slug TEXT NOT NULL,
  prompt_sent TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'timeout')),
  result_text TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'
);

ALTER TABLE manus_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY manus_tasks_select ON manus_tasks
  FOR SELECT USING (user_id = auth.uid());
CREATE POLICY manus_tasks_insert ON manus_tasks
  FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY manus_tasks_update ON manus_tasks
  FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY manus_tasks_delete ON manus_tasks
  FOR DELETE USING (user_id = auth.uid());

CREATE INDEX IF NOT EXISTS idx_manus_tasks_user ON manus_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_manus_tasks_status ON manus_tasks(status);
