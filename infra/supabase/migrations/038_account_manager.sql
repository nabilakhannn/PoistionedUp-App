-- Slice 98: Account Manager + Client Deliverables
-- account_manager_sessions table + deliverables versioning columns

-- ── 1. account_manager_sessions ───────────────────────────────────────────
-- One row per client call analyzed by the Account Manager agent.
-- Stores cross-call memory (call_number, cross_call_themes) + action plan.

CREATE TABLE IF NOT EXISTS account_manager_sessions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id          UUID NOT NULL,

  -- Optional links
  journal_entry_id  UUID,   -- links to experience_journal.id if transcript was stored there
  intake_form_id    UUID REFERENCES client_intake_forms(id),

  -- Call metadata
  client_name       VARCHAR(255),
  call_date         DATE,
  call_number       INTEGER DEFAULT 1,
  -- auto-incremented per brand — Account Manager computes this from previous sessions

  -- AI outputs
  summary           TEXT,
  cross_call_themes JSONB DEFAULT '[]',
  -- recurring topics across all calls, e.g. ["pricing objection", "impostor syndrome"]

  action_plan       JSONB DEFAULT '[]',
  -- [{ id, category, title, description, agent, priority, approved, executed, result }]
  -- categories: content | brand_profile | leads | knowledge | nurture | gaps | deliverable

  -- Lifecycle
  status            VARCHAR(30) NOT NULL DEFAULT 'pending_review',
  -- pending_review | approved | executing | completed

  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS am_sessions_brand
  ON account_manager_sessions(user_id, brand_id, created_at DESC);

ALTER TABLE account_manager_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own sessions" ON account_manager_sessions
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);


-- ── 2. agent_deliverables — add versioning + sharing columns ──────────────

ALTER TABLE agent_deliverables
  ADD COLUMN IF NOT EXISTS share_token  VARCHAR(64) UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
  ADD COLUMN IF NOT EXISTS version      INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS client_brand BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS deliverables_share_token
  ON agent_deliverables(share_token)
  WHERE share_token IS NOT NULL;

-- Public read for share links — clients view proposals/landing pages without auth
CREATE POLICY "Public read by share_token" ON agent_deliverables
  FOR SELECT
  USING (share_token IS NOT NULL);
