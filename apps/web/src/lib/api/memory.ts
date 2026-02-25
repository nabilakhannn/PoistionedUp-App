/**
 * Agent Memory API -- observations, lessons, and synthesis.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface AgentMemorySummary {
  id: string;
  memory_type: string;
  content: string;
  confidence: number;
  status: string;
  platform: string | null;
  category: string | null;
  source: string | null;
  last_used_at: string | null;
  created_at: string;
}

export interface AgentMemoryDetail extends AgentMemorySummary {
  evidence: any[];
  related_post_ids: string[];
  supersedes_id: string | null;
  updated_at: string;
}

export interface MemorySynthesisResponse {
  new_memories_created: number;
  memories_superseded: number;
  patterns_detected: string[];
  message: string;
}

// ── API Methods ──────────────────────────────────────────

export const memoryApi = {
  list: (
    memoryType?: string,
    status?: string,
    platform?: string,
    brandId?: string
  ) => {
    const params = new URLSearchParams();
    if (memoryType) params.set("memory_type", memoryType);
    if (status) params.set("status", status);
    if (platform) params.set("platform", platform);
    if (brandId) params.set("brand_id", brandId);
    const qs = params.toString();
    return apiFetch<AgentMemorySummary[]>(`/memory${qs ? `?${qs}` : ""}`);
  },

  pending: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<AgentMemorySummary[]>(`/memory/pending${qs}`);
  },

  get: (id: string) => apiFetch<AgentMemoryDetail>(`/memory/${id}`),

  create: (data: {
    memory_type: string;
    content: string;
    confidence?: number;
    platform?: string;
    category?: string;
    source?: string;
    brand_id?: string;
  }) =>
    apiFetch<AgentMemorySummary>("/memory", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    id: string,
    data: {
      content?: string;
      confidence?: number;
      platform?: string;
      category?: string;
    }
  ) =>
    apiFetch<AgentMemorySummary>(`/memory/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  approve: (
    id: string,
    action: "approve" | "dismiss" = "approve",
    editedContent?: string
  ) =>
    apiFetch<AgentMemorySummary>(`/memory/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ action, edited_content: editedContent }),
    }),

  synthesize: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<MemorySynthesisResponse>(`/memory/synthesize${qs}`, {
      method: "POST",
    });
  },

  delete: (id: string) =>
    apiFetch<void>(`/memory/${id}`, { method: "DELETE" }),
};
