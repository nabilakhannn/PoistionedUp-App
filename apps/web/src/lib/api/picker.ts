/**
 * Resource Picker API -- unified search across Knowledge and Inspo.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface PickerItem {
  id: string;
  source: "knowledge" | "inspo";
  title: string;
  content_preview: string;
  tags: string[];
  is_gold: boolean;
  is_starred: boolean;
  source_tag: string | null;
  intent_note: string | null;
  resource_type: string | null;
  content_type: string | null;
  source_url: string | null;
  board_name: string | null;
  created_at: string;
}

export interface PickerSearchResponse {
  items: PickerItem[];
  total: number;
}

export interface PickerContentResponse {
  id: string;
  source: string;
  title: string;
  full_text: string;
  is_gold: boolean;
  is_starred: boolean;
  source_tag: string | null;
  intent_note: string | null;
  formatted_context: string;
}

// ── API Methods ──────────────────────────────────────────

export const pickerApi = {
  search: (params?: {
    q?: string;
    source?: "all" | "knowledge" | "inspo";
    brand_id?: string;
    gold_only?: boolean;
    starred_only?: boolean;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set("q", params.q);
    if (params?.source) searchParams.set("source", params.source);
    if (params?.brand_id) searchParams.set("brand_id", params.brand_id);
    if (params?.gold_only) searchParams.set("gold_only", "true");
    if (params?.starred_only) searchParams.set("starred_only", "true");
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiFetch<PickerSearchResponse>(
      `/picker/search${qs ? `?${qs}` : ""}`
    );
  },

  getContent: (source: "knowledge" | "inspo", itemId: string) =>
    apiFetch<PickerContentResponse>(`/picker/content/${source}/${itemId}`),
};
