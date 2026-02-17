-- ============================================================
-- 002_vector_search.sql -- Semantic Search + AI Memory
-- Enables pgvector, adds embeddings to resource_chunks,
-- creates brand_chats table, and adds vector search function.
-- ============================================================

-- 0. Enable pgvector extension
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "vector";


-- 1. Add embedding column to resource_chunks
-- ============================================================
ALTER TABLE public.resource_chunks
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- IVFFlat index for fast cosine similarity search
-- (efficient for < 100K rows, simpler than HNSW)
CREATE INDEX IF NOT EXISTS idx_resource_chunks_embedding
  ON public.resource_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);


-- 2. brand_chats table (already used in app code, formalizing schema)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.brand_chats (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  module       TEXT NOT NULL CHECK (module IN ('foundation', 'ica', 'offer', 'brand')),
  messages     JSONB NOT NULL DEFAULT '[]'::jsonb,
  extracted    JSONB NOT NULL DEFAULT '{}'::jsonb,
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.brand_chats ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_brand_chats_user_module
  ON public.brand_chats(user_id, module);

CREATE TRIGGER set_brand_chats_updated_at
  BEFORE UPDATE ON public.brand_chats
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- RLS: users can only access their own chats
CREATE POLICY "Users can view own brand chats"
  ON public.brand_chats FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own brand chats"
  ON public.brand_chats FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own brand chats"
  ON public.brand_chats FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);


-- 3. Vector similarity search function
-- ============================================================
-- Called via Supabase RPC: admin.rpc("match_resource_chunks", {...})
-- Returns chunks ranked by cosine similarity to the query embedding.
CREATE OR REPLACE FUNCTION match_resource_chunks(
  query_embedding vector(1536),
  match_user_id UUID,
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
  WHERE r.user_id = match_user_id
    AND rc.embedding IS NOT NULL
    AND 1 - (rc.embedding <=> query_embedding) > match_threshold
  ORDER BY rc.embedding <=> query_embedding
  LIMIT match_count;
$$;
