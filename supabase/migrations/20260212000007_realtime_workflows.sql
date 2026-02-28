-- Enable Supabase Realtime on the workflows table
-- so the frontend can subscribe to status changes

-- Add workflows to the supabase_realtime publication (skip if already added)
DO $$ BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE workflows;
EXCEPTION WHEN duplicate_object THEN
  NULL;
END $$;

-- Add index for faster status-based queries (worker polling + dashboard)
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows (status);
CREATE INDEX IF NOT EXISTS idx_workflows_user_status ON workflows (user_id, status);

-- Add index on content_assets for workflow lookup
CREATE INDEX IF NOT EXISTS idx_content_assets_workflow ON content_assets (workflow_id);
