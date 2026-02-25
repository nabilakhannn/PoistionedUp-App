/**
 * Experiments API -- A/B testing and auto-propose.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface ExperimentSummary {
  id: string;
  hypothesis: string;
  variable: string;
  variant_a: string;
  variant_b: string;
  platform: string;
  status: string;
  target_posts: number;
  variant_a_count: number;
  variant_b_count: number;
  variant_a_avg_engagement: number | null;
  variant_b_avg_engagement: number | null;
  winner: string | null;
  conclusion: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ExperimentDetail extends ExperimentSummary {
  variant_a_posts: string[];
  variant_b_posts: string[];
  resulting_memory_id: string | null;
  updated_at: string;
}

export interface ExperimentActionResponse {
  id: string;
  status: string;
  message: string;
}

// ── API Methods ──────────────────────────────────────────

export const experimentsApi = {
  list: (status?: string, platform?: string, brandId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (platform) params.set("platform", platform);
    if (brandId) params.set("brand_id", brandId);
    const qs = params.toString();
    return apiFetch<ExperimentSummary[]>(
      `/experiments${qs ? `?${qs}` : ""}`
    );
  },

  get: (id: string) => apiFetch<ExperimentDetail>(`/experiments/${id}`),

  create: (data: {
    hypothesis: string;
    variable: string;
    variant_a: string;
    variant_b: string;
    platform: string;
    target_posts?: number;
    brand_id?: string;
  }) =>
    apiFetch<ExperimentSummary>("/experiments", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    id: string,
    data: { hypothesis?: string; target_posts?: number }
  ) =>
    apiFetch<ExperimentSummary>(`/experiments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  approve: (id: string) =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/approve`, {
      method: "POST",
    }),

  cancel: (id: string) =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/cancel`, {
      method: "POST",
    }),

  assign: (
    id: string,
    postId: string,
    variant: "variant_a" | "variant_b"
  ) =>
    apiFetch<ExperimentActionResponse>(`/experiments/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ post_id: postId, variant }),
    }),

  conclude: (id: string) =>
    apiFetch<ExperimentDetail>(`/experiments/${id}/conclude`, {
      method: "POST",
    }),

  autoPropose: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<ExperimentSummary[]>(
      `/experiments/auto-propose${qs}`,
      { method: "POST" }
    );
  },

  delete: (id: string) =>
    apiFetch<void>(`/experiments/${id}`, { method: "DELETE" }),
};
