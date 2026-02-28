-- Slice 73: Autonomous Agent System
-- Tables for goals, notifications, and agent autonomy controls.

-- ── agent_goals ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agent_goals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id      UUID REFERENCES public.personal_brands(id) ON DELETE CASCADE,

  title         TEXT NOT NULL,
  description   TEXT,
  goal_type     TEXT NOT NULL CHECK (goal_type IN (
    'posting_frequency', 'engagement_growth', 'research_cadence',
    'content_pipeline', 'custom'
  )),

  target_value  FLOAT NOT NULL,
  target_unit   TEXT NOT NULL DEFAULT 'per_week' CHECK (target_unit IN (
    'per_week', 'per_month', 'percent', 'count'
  )),
  current_value FLOAT NOT NULL DEFAULT 0,
  platform      TEXT,

  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
    'active', 'paused', 'completed', 'archived'
  )),
  priority      TEXT NOT NULL DEFAULT 'P2',

  deadline_at        TIMESTAMPTZ,
  last_evaluated_at  TIMESTAMPTZ,
  last_action_at     TIMESTAMPTZ,

  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_goals_user_status ON public.agent_goals(user_id, status);
CREATE INDEX idx_agent_goals_user_brand_type ON public.agent_goals(user_id, brand_id, goal_type);

ALTER TABLE public.agent_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own goals"
  ON public.agent_goals FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ── agent_notifications ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agent_notifications (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  title             TEXT NOT NULL,
  body              TEXT NOT NULL,
  notification_type TEXT NOT NULL CHECK (notification_type IN (
    'briefing', 'reminder', 'alert', 'suggestion', 'insight', 'goal_update'
  )),
  priority          TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN (
    'low', 'medium', 'high', 'urgent'
  )),

  from_agent_id     TEXT,
  related_task_id   TEXT,
  related_goal_id   UUID REFERENCES public.agent_goals(id) ON DELETE SET NULL,

  status            TEXT NOT NULL DEFAULT 'unread' CHECK (status IN (
    'unread', 'read', 'dismissed', 'actioned'
  )),
  action_url        TEXT,
  scheduled_for     TIMESTAMPTZ,
  metadata          JSONB DEFAULT '{}',

  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  read_at           TIMESTAMPTZ
);

CREATE INDEX idx_agent_notif_user_unread ON public.agent_notifications(user_id, status) WHERE status = 'unread';
CREATE INDEX idx_agent_notif_user_type ON public.agent_notifications(user_id, notification_type);

ALTER TABLE public.agent_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own notifications"
  ON public.agent_notifications FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ── Autonomy columns on openclaw_agents ─────────────────
ALTER TABLE public.openclaw_agents
  ADD COLUMN IF NOT EXISTS autonomy_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT NOT NULL DEFAULT 0.8,
  ADD COLUMN IF NOT EXISTS auto_execute BOOLEAN NOT NULL DEFAULT false;
