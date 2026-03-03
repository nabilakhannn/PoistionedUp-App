-- Slice 85: True Agent Autonomy
-- Creates 4 tables: agent_playbooks, agent_ledger, user_connectors, sdk_agent_runs
-- All tables: RLS enabled, user-scoped policies, idempotent (safe to re-run)

-- ─────────────────────────────────────────────
-- Table 1: agent_playbooks
-- Stores per-agent SOPs that agents read before every task.
-- Users can propose edits → admin applies them (versioned).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agent_playbooks (
  id                        UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id                   UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  agent_id                  TEXT        NOT NULL,  -- "copywriter", "qa-reviewer", etc.
  agent_name                TEXT        NOT NULL,
  playbook_md               TEXT        NOT NULL DEFAULT '',
  version                   INT         NOT NULL DEFAULT 1,
  is_active                 BOOLEAN     NOT NULL DEFAULT true,
  pending_edit_md           TEXT,
  pending_edit_requested_at TIMESTAMPTZ,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, agent_id)
);

ALTER TABLE public.agent_playbooks ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'agent_playbooks'
      AND policyname = 'Users manage their own playbooks'
  ) THEN
    CREATE POLICY "Users manage their own playbooks"
      ON public.agent_playbooks FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_agent_playbooks_user_agent
  ON public.agent_playbooks(user_id, agent_id);

-- ─────────────────────────────────────────────
-- Table 2: agent_ledger
-- Append-only audit log of every action an agent takes.
-- No UPDATE/DELETE policy — immutable by design.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agent_ledger (
  id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id              UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  run_id               UUID        NOT NULL,  -- groups all entries for one agent run
  agent_id             TEXT        NOT NULL,
  action_type          TEXT        NOT NULL,  -- 'tool_call','decision','output','error'
  action_description   TEXT        NOT NULL,
  tool_name            TEXT,
  tool_input_summary   TEXT,  -- abbreviated, secrets redacted
  tool_result_summary  TEXT,
  tokens_used          INT         DEFAULT 0,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
  -- intentionally no updated_at — append-only
);

ALTER TABLE public.agent_ledger ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'agent_ledger'
      AND policyname = 'Users read their own ledger'
  ) THEN
    -- Read-only for users (only the API service role can INSERT)
    CREATE POLICY "Users read their own ledger"
      ON public.agent_ledger FOR SELECT
      USING (auth.uid() = user_id);
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_agent_ledger_user_run
  ON public.agent_ledger(user_id, run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_ledger_user_agent
  ON public.agent_ledger(user_id, agent_id, created_at DESC);

-- ─────────────────────────────────────────────
-- Table 3: user_connectors
-- Stores encrypted credentials for external services
-- (LinkedIn, Twitter/X, Instagram, custom webhooks).
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.user_connectors (
  id                    UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id               UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  service               TEXT        NOT NULL,  -- 'linkedin','twitter','instagram','webhook'
  display_name          TEXT        NOT NULL,
  encrypted_credentials TEXT        NOT NULL,  -- Fernet-encrypted JSON blob
  is_active             BOOLEAN     NOT NULL DEFAULT true,
  last_tested_at        TIMESTAMPTZ,
  last_test_status      TEXT,  -- 'ok','error','untested'
  last_test_error       TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, service)
);

ALTER TABLE public.user_connectors ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'user_connectors'
      AND policyname = 'Users manage their own connectors'
  ) THEN
    CREATE POLICY "Users manage their own connectors"
      ON public.user_connectors FOR ALL
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_user_connectors_user_service
  ON public.user_connectors(user_id, service);

-- ─────────────────────────────────────────────
-- Table 4: sdk_agent_runs
-- Summary record for each tool-use agent run.
-- Written at start (status=running) and updated at completion.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.sdk_agent_runs (
  id               UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  agent_id         TEXT        NOT NULL,
  task_type        TEXT        NOT NULL,
  status           TEXT        NOT NULL DEFAULT 'running',  -- 'running','completed','failed'
  prompt_summary   TEXT,
  result_summary   TEXT,
  error_text       TEXT,
  model_used       TEXT,
  total_tokens     INT         DEFAULT 0,
  tool_calls_count INT         DEFAULT 0,
  duration_ms      INT,
  brand_id         UUID,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at     TIMESTAMPTZ
);

ALTER TABLE public.sdk_agent_runs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'sdk_agent_runs'
      AND policyname = 'Users read their own agent runs'
  ) THEN
    CREATE POLICY "Users read their own agent runs"
      ON public.sdk_agent_runs FOR SELECT
      USING (auth.uid() = user_id);
  END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_sdk_agent_runs_user_created
  ON public.sdk_agent_runs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sdk_agent_runs_user_agent
  ON public.sdk_agent_runs(user_id, agent_id, created_at DESC);
