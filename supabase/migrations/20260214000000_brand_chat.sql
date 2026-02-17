-- ============================================================
-- 20260214000000_brand_chat.sql -- Brand Discovery Chat Table
-- Supports the hybrid AI chat + form flow for ICA, Offer, Brand
-- ============================================================

-- brand_chats: stores conversational brand discovery sessions
-- Each row is one chat thread for a specific module (ica/offer/brand).
-- Messages are stored as JSONB array, extracted data as JSONB object.
-- When chat is marked complete, extracted data merges into profiles.profile_json.
CREATE TABLE public.brand_chats (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  module      TEXT NOT NULL CHECK (module IN ('ica', 'offer', 'brand')),
  messages    JSONB NOT NULL DEFAULT '[]'::jsonb,
  extracted   JSONB NOT NULL DEFAULT '{}'::jsonb,
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.brand_chats ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_brand_chats_user_module ON public.brand_chats(user_id, module);

-- RLS policies: users see only their own chats
CREATE POLICY brand_chats_select ON public.brand_chats
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY brand_chats_insert ON public.brand_chats
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY brand_chats_update ON public.brand_chats
  FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY brand_chats_delete ON public.brand_chats
  FOR DELETE USING (user_id = auth.uid());

-- Auto-update updated_at (reuses trigger function from 001_init.sql)
CREATE TRIGGER set_brand_chats_updated_at
  BEFORE UPDATE ON public.brand_chats
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
