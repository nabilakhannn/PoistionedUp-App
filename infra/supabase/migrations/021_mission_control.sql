-- Mission Control: Agent dashboard, task management, communications
-- Slice 51: Mirrors OpenClaw agent state into Supabase for the web dashboard

-- ─── Agent Registry ────────────────────────────────────
CREATE TABLE IF NOT EXISTS openclaw_agents (
  id TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  role_type TEXT NOT NULL DEFAULT 'specialist',  -- lead, specialist, integrator
  model_provider TEXT,
  model_name TEXT,
  status TEXT NOT NULL DEFAULT 'idle',  -- idle, working, error, paused
  status_reason TEXT,
  avatar_emoji TEXT DEFAULT '🤖',
  skills TEXT[] DEFAULT '{}',
  about TEXT,
  workspace_path TEXT,
  last_heartbeat_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id, user_id)
);

ALTER TABLE openclaw_agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own agents"
  ON openclaw_agents FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ─── Agent Tasks (Kanban Board) ────────────────────────
CREATE TABLE IF NOT EXISTS agent_tasks (
  id TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  brief TEXT,
  priority TEXT NOT NULL DEFAULT 'P2',  -- P0, P1, P2, P3
  status TEXT NOT NULL DEFAULT 'backlog',  -- backlog, assigned, in_progress, review, ready, done, archived
  assignee_id TEXT,
  tags TEXT[] DEFAULT '{}',
  input_ref TEXT,
  output_ref TEXT,
  notes TEXT,
  due_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  PRIMARY KEY (id, user_id)
);

ALTER TABLE agent_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own tasks"
  ON agent_tasks FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_agent_tasks_status ON agent_tasks(user_id, status);
CREATE INDEX idx_agent_tasks_assignee ON agent_tasks(user_id, assignee_id);

-- ─── Agent Messages (Squad Chat / Delegation Log) ──────
CREATE TABLE IF NOT EXISTS agent_messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  from_agent_id TEXT,
  to_agent_id TEXT,
  message TEXT NOT NULL,
  message_type TEXT NOT NULL DEFAULT 'chat',  -- chat, delegation, status, deliverable, escalation, broadcast
  task_id TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own messages"
  ON agent_messages FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_agent_messages_task ON agent_messages(user_id, task_id);
CREATE INDEX idx_agent_messages_from ON agent_messages(user_id, from_agent_id);
CREATE INDEX idx_agent_messages_created ON agent_messages(user_id, created_at DESC);

-- ─── Deliverables ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_deliverables (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  task_id TEXT NOT NULL,
  title TEXT NOT NULL,
  file_path TEXT,
  content TEXT,
  deliverable_type TEXT NOT NULL DEFAULT 'document',  -- document, image, code, report, content
  created_by_agent_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',  -- draft, review, approved, rejected
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE agent_deliverables ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own deliverables"
  ON agent_deliverables FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_agent_deliverables_task ON agent_deliverables(user_id, task_id);
