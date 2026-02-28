-- ============================================================
-- 017_add_brand_chats_title.sql
-- Add 'title' column to brand_chats table for chat naming
-- Used by both brand coaching chat and content chat modules
-- ============================================================

ALTER TABLE public.brand_chats
  ADD COLUMN IF NOT EXISTS title TEXT;

COMMENT ON COLUMN public.brand_chats.title IS 'User-visible chat title, auto-generated from first message or set via rename';
