/**
 * Composer API — LinkedIn & X post creation, scheduling, publishing.
 *
 * Wraps the existing schedule + content-chat APIs into a composer-focused
 * interface. No new backend endpoints needed — composes existing ones.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface ComposerDraft {
  id?: string;
  platform: "linkedin" | "twitter";
  body: string;
  /** Attached image URLs (Supabase storage or external) */
  images: string[];
  /** Attached document URL */
  document_url?: string;
  /** Voice DNA collection ID (for AI generation) */
  voice_id?: string;
  /** Brand ID */
  brand_id?: string;
}

export interface ComposerPublishResult {
  id: string;
  status: "scheduled" | "draft" | "queued";
  scheduled_at?: string;
  message: string;
}

// ── LinkedIn formatting utils ────────────────────────────

export const LINKEDIN_CHAR_LIMIT = 3000;

export function countLinkedInChars(text: string): number {
  return text.length;
}

export function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

/**
 * Estimate reading time in minutes (avg 200 wpm for LinkedIn).
 */
export function estimateReadTime(text: string): number {
  const words = countWords(text);
  return Math.max(1, Math.ceil(words / 200));
}

/**
 * Format plain text as LinkedIn-style:
 * - Preserves line breaks
 * - Converts **bold** to Unicode bold (LinkedIn doesn't support markdown)
 */
export function formatForLinkedIn(text: string): string {
  // LinkedIn supports Unicode bold characters
  return text.replace(/\*\*(.*?)\*\*/g, (_match, p1: string) => {
    return toBoldUnicode(p1);
  });
}

function toBoldUnicode(text: string): string {
  const boldMap: Record<string, string> = {};
  // Map A-Z
  for (let i = 0; i < 26; i++) {
    boldMap[String.fromCharCode(65 + i)] = String.fromCharCode(0x1d400 + i);
    boldMap[String.fromCharCode(97 + i)] = String.fromCharCode(0x1d41a + i);
  }
  // Map 0-9
  for (let i = 0; i < 10; i++) {
    boldMap[String.fromCharCode(48 + i)] = String.fromCharCode(0x1d7ce + i);
  }
  return text
    .split("")
    .map((c) => boldMap[c] || c)
    .join("");
}

// ── API Methods ──────────────────────────────────────────

export const composerApi = {
  /**
   * Save draft to schedule board (status: draft).
   */
  saveDraft: (draft: ComposerDraft) =>
    apiFetch<{ id: string }>("/schedule", {
      method: "POST",
      body: JSON.stringify({
        title: draft.body.split("\n")[0]?.slice(0, 80) || "Untitled Post",
        platform: draft.platform,
        content_type: draft.platform === "linkedin" ? "linkedin_post" : "twitter_post",
        body_preview: draft.body.slice(0, 200),
        content_json: {
          body: draft.body,
          images: draft.images,
          document_url: draft.document_url,
        },
        status: "draft",
        brand_id: draft.brand_id,
      }),
    }),

  /**
   * Update existing draft.
   */
  updateDraft: (id: string, draft: ComposerDraft) =>
    apiFetch<{ id: string }>(`/schedule/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: draft.body.split("\n")[0]?.slice(0, 80) || "Untitled Post",
        body_preview: draft.body.slice(0, 200),
        content_json: {
          body: draft.body,
          images: draft.images,
          document_url: draft.document_url,
        },
      }),
    }),

  /**
   * Schedule a post for a specific date/time.
   */
  schedule: (draft: ComposerDraft, scheduledAt: string) =>
    apiFetch<ComposerPublishResult>("/schedule", {
      method: "POST",
      body: JSON.stringify({
        title: draft.body.split("\n")[0]?.slice(0, 80) || "Untitled Post",
        platform: draft.platform,
        content_type: draft.platform === "linkedin" ? "linkedin_post" : "twitter_post",
        body_preview: draft.body.slice(0, 200),
        content_json: {
          body: draft.body,
          images: draft.images,
          document_url: draft.document_url,
        },
        status: "scheduled",
        scheduled_at: scheduledAt,
        brand_id: draft.brand_id,
      }),
    }),

  /**
   * Add to publishing queue (next available slot).
   */
  addToQueue: (draft: ComposerDraft) =>
    apiFetch<ComposerPublishResult>("/schedule", {
      method: "POST",
      body: JSON.stringify({
        title: draft.body.split("\n")[0]?.slice(0, 80) || "Untitled Post",
        platform: draft.platform,
        content_type: draft.platform === "linkedin" ? "linkedin_post" : "twitter_post",
        body_preview: draft.body.slice(0, 200),
        content_json: {
          body: draft.body,
          images: draft.images,
          document_url: draft.document_url,
        },
        status: "scheduled",
        brand_id: draft.brand_id,
      }),
    }),

  /**
   * AI-generate content for the composer.
   */
  generateContent: (
    prompt: string,
    brandId?: string,
    settings?: {
      platform?: string;
      tone?: string;
      objective?: string;
    }
  ) =>
    apiFetch<{ id: string; messages: { role: string; content: string }[] }>(
      "/content-chat/message",
      {
        method: "POST",
        body: JSON.stringify({
          message: prompt,
          brand_id: brandId,
          settings: {
            platforms: [settings?.platform || "linkedin"],
            tone: settings?.tone || "conversational",
            objective: settings?.objective || "personal_branding",
          },
        }),
      }
    ),

  /**
   * Load drafts from schedule board.
   */
  loadDrafts: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{
      draft: Array<{
        id: string;
        title: string;
        platform: string;
        body_preview: string | null;
        content_json: Record<string, any>;
        created_at: string;
        updated_at: string;
      }>;
    }>(`/schedule${qs}`);
  },
};
