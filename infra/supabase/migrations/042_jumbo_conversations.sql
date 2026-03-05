-- Slice 107: Jumbo Hub — persistent conversations
-- Stores multi-turn chat sessions between user and Jumbo (general-purpose AI partner).
-- Messages stored as JSONB array: [{role: "user"|"jumbo", content: str, created_at: str}]

CREATE TABLE IF NOT EXISTS jumbo_conversations (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id     UUID        NOT NULL,
  title        TEXT        NOT NULL DEFAULT 'New Chat',
  messages     JSONB       NOT NULL DEFAULT '[]',
  status       TEXT        NOT NULL DEFAULT 'active',
  -- values: 'active' | 'archived'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jumbo_conv_user_brand
  ON jumbo_conversations(user_id, brand_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS jumbo_conv_user_active
  ON jumbo_conversations(user_id, status, updated_at DESC)
  WHERE status = 'active';

ALTER TABLE jumbo_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own conversations" ON jumbo_conversations FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Auto-update updated_at on message append
CREATE OR REPLACE FUNCTION update_jumbo_conversations_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_jumbo_conversations_updated_at ON jumbo_conversations;
CREATE TRIGGER trg_jumbo_conversations_updated_at
  BEFORE UPDATE ON jumbo_conversations
  FOR EACH ROW EXECUTE FUNCTION update_jumbo_conversations_updated_at();
