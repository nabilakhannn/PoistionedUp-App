-- ============================================================
-- 049_brand_id_on_deliverables.sql — Slice Phase 0 fixes
--
-- 1. Add brand_id to agent_deliverables (nullable — existing rows unaffected)
--    Enables per-brand filtering in the approval inbox.
-- ============================================================

ALTER TABLE public.agent_deliverables
  ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES public.personal_brands(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_agent_deliverables_brand_id
  ON public.agent_deliverables(brand_id)
  WHERE brand_id IS NOT NULL;
