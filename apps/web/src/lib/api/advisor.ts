/**
 * Advisor API -- AI-driven suggestions for brand improvement.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface AdvisorSuggestion {
  title: string;
  body: string;
  category: string;
  priority: string;
  action_type: string;
}

// ── API Methods ──────────────────────────────────────────

export const advisorApi = {
  getSuggestions: (brandId?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (brandId) params.set("brand_id", brandId);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return apiFetch<AdvisorSuggestion[]>(
      `/advisor/suggestions${qs ? `?${qs}` : ""}`
    );
  },
};
