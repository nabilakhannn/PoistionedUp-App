-- ============================================================
-- 013_inspo_boards.sql -- Inspo Boards Feature
-- Multi-board inspiration system with source tagging + intent
-- ============================================================

-- 1. Inspo Boards table
-- ============================================================
CREATE TABLE public.inspo_boards (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  brand_id     UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL,
  name         TEXT NOT NULL,
  description  TEXT NOT NULL DEFAULT '',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.inspo_boards ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_inspo_boards_user_id ON public.inspo_boards(user_id);
CREATE INDEX idx_inspo_boards_brand_id ON public.inspo_boards(brand_id);

CREATE TRIGGER set_inspo_boards_updated_at
  BEFORE UPDATE ON public.inspo_boards
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 2. Inspo Item content type enum
-- ============================================================
CREATE TYPE public.inspo_item_type AS ENUM (
  'text',
  'link',
  'image',
  'video',
  'voice_note'
);


-- 3. Inspo Items table
-- ============================================================
CREATE TABLE public.inspo_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id      UUID NOT NULL REFERENCES public.inspo_boards(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content_type  public.inspo_item_type NOT NULL DEFAULT 'text',
  title         TEXT NOT NULL DEFAULT '',
  content_text  TEXT NOT NULL DEFAULT '',
  source_url    TEXT,
  source_tag    TEXT NOT NULL DEFAULT '',
  intent_note   TEXT NOT NULL DEFAULT '',
  media_path    TEXT,
  tags          TEXT[] NOT NULL DEFAULT '{}',
  is_starred    BOOLEAN NOT NULL DEFAULT FALSE,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  sort_order    INT NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.inspo_items ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_inspo_items_board_id ON public.inspo_items(board_id);
CREATE INDEX idx_inspo_items_user_id ON public.inspo_items(user_id);
CREATE INDEX idx_inspo_items_starred ON public.inspo_items(board_id, is_starred) WHERE is_starred = TRUE;
CREATE INDEX idx_inspo_items_tags ON public.inspo_items USING GIN(tags);

CREATE TRIGGER set_inspo_items_updated_at
  BEFORE UPDATE ON public.inspo_items
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 4. RLS Policies
-- ============================================================

-- Inspo Boards: users own their boards
CREATE POLICY "Users can view own inspo boards"
  ON public.inspo_boards FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own inspo boards"
  ON public.inspo_boards FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own inspo boards"
  ON public.inspo_boards FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own inspo boards"
  ON public.inspo_boards FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Inspo Items: users own their items
CREATE POLICY "Users can view own inspo items"
  ON public.inspo_items FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own inspo items"
  ON public.inspo_items FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own inspo items"
  ON public.inspo_items FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own inspo items"
  ON public.inspo_items FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
