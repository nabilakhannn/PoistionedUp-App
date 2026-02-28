-- Migration 026: Formalize agent_notifications table
-- This table was created manually in Supabase during Slice 73 but never
-- had a migration file. Used by notifications router, agent bridge /notify,
-- agent_orchestrator _create_notification(), and competitor alert submissions.

CREATE TABLE IF NOT EXISTS agent_notifications (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  notification_type TEXT NOT NULL DEFAULT 'insight',
  -- Valid types: briefing, reminder, alert, suggestion, insight, goal_update
  priority TEXT NOT NULL DEFAULT 'medium',
  -- Valid priorities: low, medium, high, urgent
  from_agent_id TEXT,
  related_task_id TEXT,
  related_goal_id TEXT,
  status TEXT NOT NULL DEFAULT 'unread',
  -- Valid statuses: unread, read, dismissed, actioned
  action_url TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  read_at TIMESTAMPTZ,
  scheduled_for TIMESTAMPTZ
);

ALTER TABLE agent_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own notifications"
  ON agent_notifications FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_agent_notifications_user_status
  ON agent_notifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_notifications_created
  ON agent_notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_notifications_type
  ON agent_notifications(user_id, notification_type);
