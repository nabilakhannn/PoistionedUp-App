-- ============================================================
-- 005_agent_memory.sql -- Agent Memory System
-- Persistent memory that lets the AI agent learn and improve
-- over time. Stores observations, preferences, lessons, and
-- patterns extracted from interactions and performance data.
-- ============================================================


-- 1. agent_memory table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.agent_memory (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- What kind of memory
  memory_type       TEXT NOT NULL CHECK (memory_type IN (
    'observation',      -- Auto-detected pattern ("user prefers short hooks")
    'preference',       -- Explicit user preference ("no rhetorical questions")
    'lesson',           -- Strategic lesson requiring approval ("shift to 70% AI tools")
    'content_pattern',  -- Content structure pattern ("story→insight→CTA works best")
    'voice_note'        -- Voice/tone observation ("user writes in conversational style")
  )),

  -- The memory itself
  content           TEXT NOT NULL,
  evidence          JSONB NOT NULL DEFAULT '[]'::jsonb,   -- Supporting data points
  confidence        FLOAT NOT NULL DEFAULT 0.5,           -- 0.0-1.0 confidence score

  -- Lifecycle
  status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
    'pending_approval',  -- Lesson waiting for user approval
    'active',            -- Actively used in prompts
    'dismissed',         -- User rejected this memory
    'superseded',        -- Replaced by a newer memory
    'expired'            -- No longer relevant
  )),

  -- Context
  platform          TEXT,                                  -- Platform-specific memory
  category          TEXT,                                  -- Topic category
  source            TEXT,                                  -- Where this came from (auto, user_edit, metrics, synthesis)

  -- Relationships
  related_post_ids  UUID[] DEFAULT '{}',                   -- Posts that support this memory
  supersedes_id     UUID REFERENCES public.agent_memory(id) ON DELETE SET NULL,

  -- Semantic search
  embedding         vector(1536),

  -- Timestamps
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at      TIMESTAMPTZ                            -- When was this memory last used in a prompt
);

ALTER TABLE public.agent_memory ENABLE ROW LEVEL SECURITY;


-- 2. Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_agent_memory_user_id
  ON public.agent_memory(user_id);

CREATE INDEX IF NOT EXISTS idx_agent_memory_type
  ON public.agent_memory(user_id, memory_type);

CREATE INDEX IF NOT EXISTS idx_agent_memory_status
  ON public.agent_memory(user_id, status)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_agent_memory_pending
  ON public.agent_memory(user_id, status)
  WHERE status = 'pending_approval';

CREATE INDEX IF NOT EXISTS idx_agent_memory_platform
  ON public.agent_memory(user_id, platform)
  WHERE platform IS NOT NULL;

-- IVFFlat index for vector search (needs sufficient rows to build)
-- Using ivfflat with 100 lists — safe for up to ~100k rows
-- If table is empty at migration time, this still works but
-- the index won't be optimally trained until REINDEX.
CREATE INDEX IF NOT EXISTS idx_agent_memory_embedding
  ON public.agent_memory
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);


-- 3. Updated_at trigger
-- ============================================================
CREATE TRIGGER set_agent_memory_updated_at
  BEFORE UPDATE ON public.agent_memory
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- 4. RLS Policies
-- ============================================================
CREATE POLICY "Users can view own agent memories"
  ON public.agent_memory FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own agent memories"
  ON public.agent_memory FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own agent memories"
  ON public.agent_memory FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own agent memories"
  ON public.agent_memory FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);


-- 5. Semantic search function for agent memories
-- ============================================================
-- Finds memories most relevant to a context query.
-- Used by pipeline nodes to pull relevant memories before generating content.
CREATE OR REPLACE FUNCTION match_agent_memories(
  query_embedding vector(1536),
  match_user_id UUID,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.6
)
RETURNS TABLE (
  id UUID,
  memory_type TEXT,
  content TEXT,
  confidence FLOAT,
  platform TEXT,
  category TEXT,
  last_used_at TIMESTAMPTZ,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    am.id,
    am.memory_type,
    am.content,
    am.confidence,
    am.platform,
    am.category,
    am.last_used_at,
    1 - (am.embedding <=> query_embedding) AS similarity
  FROM public.agent_memory am
  WHERE am.user_id = match_user_id
    AND am.status = 'active'
    AND am.embedding IS NOT NULL
    AND 1 - (am.embedding <=> query_embedding) > match_threshold
  ORDER BY am.embedding <=> query_embedding
  LIMIT match_count;
$$;
