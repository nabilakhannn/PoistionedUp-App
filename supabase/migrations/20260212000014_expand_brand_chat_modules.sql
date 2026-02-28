-- ============================================================
-- 015_expand_brand_chat_modules.sql
-- Expand the brand_chats module CHECK constraint from 4 to 8 modules
-- ============================================================

-- Drop the old constraint
ALTER TABLE public.brand_chats DROP CONSTRAINT IF EXISTS brand_chats_module_check;

-- Add the expanded constraint with all 8 modules
ALTER TABLE public.brand_chats ADD CONSTRAINT brand_chats_module_check
  CHECK (module = ANY (ARRAY[
    'foundation'::text,
    'ica'::text,
    'offer'::text,
    'brand'::text,
    'authority'::text,
    'messaging'::text,
    'positioning'::text,
    'competitors'::text
  ]));
