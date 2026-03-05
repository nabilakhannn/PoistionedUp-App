/** Newsletter API — Slice 95
 *
 * Generates and retrieves weekly newsletter drafts.
 * Drafts are stored in agent_deliverables (type=newsletter).
 */

import { apiFetch } from "./client";

export interface NewsletterDraft {
  id: string | null;
  content: string;
  created_at: string;
}

export const newsletterApi = {
  /** Get the latest newsletter draft for a brand. Returns null if none exists. */
  getDraft: (brandId: string) =>
    apiFetch<NewsletterDraft | null>(
      `/newsletter/draft?brand_id=${encodeURIComponent(brandId)}`
    ),

  /** Generate a new newsletter from the latest research brief. */
  generate: (brandId: string) =>
    apiFetch<NewsletterDraft>("/newsletter/generate", {
      method: "POST",
      body: JSON.stringify({ brand_id: brandId }),
    }),
};
