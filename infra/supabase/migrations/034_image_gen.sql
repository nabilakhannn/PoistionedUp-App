-- Migration 034: Image Generation — Slice 91a
-- Nano Banana 2 (Gemini 3.1 Flash Image via Higgsfield) production pipeline
-- Claude Haiku structures prompts → Higgsfield/Gemini generates → saved here

CREATE TABLE IF NOT EXISTS generated_images (
    id           UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id      UUID         NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id     UUID         REFERENCES personal_brands(id) ON DELETE SET NULL,
    description  TEXT         NOT NULL,
    structured_prompt TEXT    NOT NULL DEFAULT '{}',  -- Claude-engineered prompt JSON
    image_url    TEXT,                                -- Higgsfield URL or Gemini data: URL
    style        VARCHAR(50)  DEFAULT 'photorealistic',
    format       VARCHAR(20)  DEFAULT 'square',
    model_used   VARCHAR(100),
    created_at   TIMESTAMPTZ  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS generated_images_user_created_idx
    ON generated_images(user_id, created_at DESC);

ALTER TABLE generated_images ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users access own images"
    ON generated_images
    USING (auth.uid() = user_id);
