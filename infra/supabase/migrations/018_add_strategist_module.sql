-- ============================================================
-- 018_add_strategist_module.sql
-- Add 'strategist' to the brand_chats module CHECK constraint
-- for the new PositionedUp Strategist v2 conversation
-- ============================================================

-- Drop the old constraint
ALTER TABLE public.brand_chats DROP CONSTRAINT IF EXISTS brand_chats_module_check;

-- Add the expanded constraint with all 8 brand modules + content + strategist
ALTER TABLE public.brand_chats ADD CONSTRAINT brand_chats_module_check
  CHECK (module = ANY (ARRAY[
    'foundation'::text,
    'ica'::text,
    'offer'::text,
    'brand'::text,
    'authority'::text,
    'messaging'::text,
    'positioning'::text,
    'competitors'::text,
    'content'::text,
    'strategist'::text
  ]));
