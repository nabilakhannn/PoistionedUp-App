/** Image Generation API — Slice 91a
 *
 * Two-step production-line pipeline:
 *   1. Plain English → Claude Haiku structures a locked JSON prompt
 *   2. Structured prompt → Higgsfield Nano Banana 2 (or Gemini fallback)
 *
 * Raises usable generation rate from ~68% → ~92%.
 */

import { apiFetch } from "./client";

// ── Types ──────────────────────────────────────────────────────────────────

export interface StructuredPrompt {
  subject: string;
  composition: string;
  camera: string;
  lighting: string;
  color_palette: string;
  mood: string;
  style: string;
  negative_prompt: string;
  final_prompt: string;
  error?: string;
}

export interface GeneratedImage {
  id: string;
  brand_id: string | null;
  description: string;
  structured_prompt: string;
  image_url: string | null;
  style: string;
  format: string;
  model_used: string | null;
  created_at: string;
}

export interface GenerateRequest {
  brand_id: string;
  description: string;
  style?: ImageStyle;
  format?: ImageFormat;
}

export interface GenerateResponse {
  url: string | null;
  structured_prompt: string;
  model_used: string | null;
  error: string | null;
}

export type ImageStyle =
  | "photorealistic"
  | "cinematic"
  | "branded"
  | "editorial"
  | "lifestyle";

export type ImageFormat = "square" | "landscape" | "portrait" | "story";

// ── Format labels ──────────────────────────────────────────────────────────

export const FORMAT_LABELS: Record<ImageFormat, string> = {
  square: "Square (1:1) — LinkedIn / Instagram",
  landscape: "Landscape (16:9) — YouTube / Twitter",
  portrait: "Portrait (4:5) — Instagram Feed",
  story: "Story (9:16) — Instagram / TikTok",
};

export const STYLE_LABELS: Record<ImageStyle, string> = {
  photorealistic: "Photorealistic",
  cinematic: "Cinematic",
  branded: "Branded",
  editorial: "Editorial",
  lifestyle: "Lifestyle",
};

// ── API client ─────────────────────────────────────────────────────────────

export const imageGenApi = {
  /** Preview prompt engineering only — no image API call (free). */
  structurePrompt: (
    description: string,
    style: ImageStyle = "photorealistic",
    brand_id: string = "",
  ): Promise<StructuredPrompt> =>
    apiFetch<StructuredPrompt>("/image-gen/structure", {
      method: "POST",
      body: JSON.stringify({ description, style, brand_id }),
    }),

  /** Full pipeline: engineer prompt → generate image → save to DB. */
  generate: (req: GenerateRequest): Promise<GenerateResponse> =>
    apiFetch<GenerateResponse>("/image-gen/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  /** List recent generated images for a brand. */
  listHistory: (brandId: string, limit = 20): Promise<GeneratedImage[]> =>
    apiFetch<GeneratedImage[]>(
      `/image-gen/history?brand_id=${encodeURIComponent(brandId)}&limit=${limit}`,
    ),
};
