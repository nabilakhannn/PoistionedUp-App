/**
 * Hook Library API client — Slice 102 (Fix F)
 * Users manage their hook library; agents pull from it before writing.
 */
import { apiFetch } from "./client";

export type HookType = "anxiety" | "benefit" | "story" | "competitor" | "belief" | "curiosity" | "custom";

export interface Hook {
  id: string;
  user_id: string;
  brand_id: string | null;
  hook_text: string;
  hook_type: HookType;
  source: string;
  times_used: number;
  engagement_score: number | null;
  created_at: string;
  updated_at: string;
}

export const hooksApi = {
  list: (params?: { brand_id?: string; hook_type?: HookType; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.brand_id) qs.set("brand_id", params.brand_id);
    if (params?.hook_type) qs.set("hook_type", params.hook_type);
    if (params?.limit) qs.set("limit", String(params.limit));
    return apiFetch<Hook[]>(`/hooks${qs.toString() ? `?${qs}` : ""}`);
  },

  create: (params: {
    brand_id?: string;
    hook_text: string;
    hook_type?: HookType;
    source?: string;
  }) =>
    apiFetch<Hook>("/hooks", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  update: (hookId: string, params: {
    hook_text?: string;
    hook_type?: HookType;
    engagement_score?: number;
  }) =>
    apiFetch<Hook>(`/hooks/${hookId}`, {
      method: "PATCH",
      body: JSON.stringify(params),
    }),

  delete: (hookId: string) =>
    apiFetch<void>(`/hooks/${hookId}`, { method: "DELETE" }),

  getForAgent: (brandId: string) =>
    apiFetch<{ hooks: Hook[]; formatted: string; total: number }>(
      `/hooks/for-agent?brand_id=${brandId}`
    ),
};

export const HOOK_TYPE_LABELS: Record<HookType, { label: string; color: string; description: string }> = {
  anxiety:    { label: "Anxiety",    color: "bg-red-500/15 text-red-400 border-red-500/20",      description: "Speaks to ICA fears" },
  benefit:    { label: "Benefit",    color: "bg-green-500/15 text-green-400 border-green-500/20", description: "Highlights desired outcomes" },
  story:      { label: "Story",      color: "bg-blue-500/15 text-blue-400 border-blue-500/20",    description: "Real experience or case study" },
  competitor: { label: "Competitor", color: "bg-orange-500/15 text-orange-400 border-orange-500/20", description: "Contrast with alternatives" },
  belief:     { label: "Belief",     color: "bg-purple-500/15 text-purple-400 border-purple-500/20", description: "Challenges a common assumption" },
  curiosity:  { label: "Curiosity",  color: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",   description: "Creates a knowledge gap" },
  custom:     { label: "Custom",     color: "bg-zinc-500/15 text-zinc-400 border-zinc-500/20",    description: "User-defined hook type" },
};
