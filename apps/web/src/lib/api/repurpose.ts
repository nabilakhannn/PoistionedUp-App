/**
 * Repurpose API — content repurposing across platforms.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface RepurposeRequest {
  source_id?: string;
  source_text?: string;
  source_platform: string;
  target_platforms: string[];
  brand_id?: string;
  auto_schedule?: boolean;
}

export interface RepurposedItem {
  platform: string;
  content_type: string;
  title: string;
  body: string;
  metadata: Record<string, any>;
}

export interface RepurposeResponse {
  source_platform: string;
  repurposed: RepurposedItem[];
  scheduled_items_created: number;
}

export interface PlatformInfo {
  platform: string;
  content_type: string;
  char_limit: number | null;
  description: string;
}

// ── Source platforms ──────────────────────────────────────

export const SOURCE_PLATFORMS = [
  { value: "youtube", label: "YouTube" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "Twitter/X" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "blog", label: "Blog" },
  { value: "email", label: "Email" },
  { value: "other", label: "Other" },
] as const;

// ── Target platforms ─────────────────────────────────────

export const TARGET_PLATFORMS = [
  { value: "linkedin", label: "LinkedIn Post" },
  { value: "twitter", label: "Twitter/X" },
  { value: "instagram", label: "Instagram Caption" },
  { value: "tiktok", label: "TikTok Script" },
  { value: "facebook", label: "Facebook Post" },
  { value: "ad_copy", label: "Ad Copy" },
  { value: "carousel", label: "Carousel" },
  { value: "email", label: "Email Snippet" },
  { value: "blog", label: "Blog Intro" },
] as const;

// ── API Methods ──────────────────────────────────────────

export const repurposeApi = {
  repurpose: (data: RepurposeRequest) =>
    apiFetch<RepurposeResponse>("/repurpose", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getPlatforms: () => apiFetch<PlatformInfo[]>("/repurpose/platforms"),
};
