-- ============================================================
-- 003_collections.sql -- Knowledge Base Collections + Voice DNA
-- Adds creator collections ("folders"), links resources to them,
-- and provides collection-scoped vector search.
-- ============================================================


-- 1. Collections table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.collections (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,                        -- "Alex Hormozi", "Lara Acosta"
  description  TEXT NOT NULL DEFAULT '',
  creator_url  TEXT,                                 -- Creator's main URL or channel
  voice_dna    JSONB NOT NULL DEFAULT '{}'::jsonb,   -- Extracted writing style profile
  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,   -- Cover image, stats, etc.
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_collections_user_id
  ON public.collections(user_id);

CREATE TRIGGER set_collections_updated_at
  BEFORE UPDATE ON public.collections
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- RLS: users can only access their own collections
CREATE POLICY "Users can view own collections"
  ON public.collections FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own collections"
  ON public.collections FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own collections"
  ON public.collections FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own collections"
  ON public.collections FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- 2. Add collection_id FK to resources (nullable — resources can exist without a collection)
-- ============================================================
ALTER TABLE public.resources
  ADD COLUMN IF NOT EXISTS collection_id UUID REFERENCES public.collections(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_resources_collection_id
  ON public.resources(collection_id)
  WHERE collection_id IS NOT NULL;


-- 3. Collection-scoped vector search function
-- ============================================================
-- Like match_resource_chunks but filtered to a single collection.
CREATE OR REPLACE FUNCTION match_collection_chunks(
  query_embedding vector(1536),
  match_collection_id UUID,
  match_count INT DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id UUID,
  resource_id UUID,
  chunk_index INT,
  chunk_text TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    rc.id,
    rc.resource_id,
    rc.chunk_index,
    rc.chunk_text,
    rc.metadata,
    1 - (rc.embedding <=> query_embedding) AS similarity
  FROM public.resource_chunks rc
  JOIN public.resources r ON r.id = rc.resource_id
  WHERE r.collection_id = match_collection_id
    AND rc.embedding IS NOT NULL
    AND 1 - (rc.embedding <=> query_embedding) > match_threshold
  ORDER BY rc.embedding <=> query_embedding
  LIMIT match_count;
$$;
