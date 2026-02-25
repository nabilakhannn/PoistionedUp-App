/**
 * Knowledge API -- collections, resources, and channel import.
 */

import { apiFetch } from "./client";

// ── Collections ──────────────────────────────────────────

export interface VoiceDNA {
  tone: string;
  sentence_style: string;
  vocabulary_level: string;
  hook_patterns: string[];
  cta_patterns: string[];
  signature_phrases: string[];
  content_structure: string;
  personality_traits: string[];
  sample_hooks: string[];
  analysis_chunk_count: number;
}

export interface CollectionSummary {
  id: string;
  name: string;
  description: string;
  creator_url: string | null;
  resource_count: number;
  voice_dna_ready: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollectionResource {
  id: string;
  type: string;
  title: string;
  source_url: string | null;
  chunk_count: number;
  content_preview: string;
  has_transcript: boolean;
  created_at: string;
}

export interface CollectionDetail {
  id: string;
  name: string;
  description: string;
  creator_url: string | null;
  voice_dna: VoiceDNA;
  resources: CollectionResource[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CollectionSearchResult {
  chunk_text: string;
  resource_title: string;
  similarity: number;
  metadata: Record<string, any>;
}

export const collectionsApi = {
  list: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<CollectionSummary[]>(`/collections${qs}`);
  },

  get: (id: string) => apiFetch<CollectionDetail>(`/collections/${id}`),

  create: (data: {
    name: string;
    description?: string;
    creator_url?: string;
    brand_id?: string;
  }) =>
    apiFetch<CollectionSummary>("/collections", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    id: string,
    data: { name?: string; description?: string; creator_url?: string }
  ) =>
    apiFetch<CollectionSummary>(`/collections/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/collections/${id}`, { method: "DELETE" }),

  addResources: (id: string, resourceIds: string[]) =>
    apiFetch<{ message: string; updated: number }>(
      `/collections/${id}/resources`,
      {
        method: "POST",
        body: JSON.stringify({ resource_ids: resourceIds }),
      }
    ),

  removeResource: (collectionId: string, resourceId: string) =>
    apiFetch<{ message: string }>(
      `/collections/${collectionId}/resources/${resourceId}`,
      { method: "DELETE" }
    ),

  analyzeVoice: (id: string) =>
    apiFetch<{
      collection_id: string;
      collection_name: string;
      voice_dna: VoiceDNA;
      message: string;
    }>(`/collections/${id}/analyze-voice`, { method: "POST" }),

  search: (id: string, query: string, limit?: number) =>
    apiFetch<{
      collection_id: string;
      collection_name: string;
      query: string;
      results: CollectionSearchResult[];
    }>(`/collections/${id}/search`, {
      method: "POST",
      body: JSON.stringify({ query, limit: limit || 5 }),
    }),
};

// ── Resources ────────────────────────────────────────────

export interface ResourceDetail {
  id: string;
  type: string;
  title: string;
  source_url: string | null;
  content_text: string | null;
  tags: string[];
  is_gold: boolean;
  collection_id: string | null;
  brand_id: string | null;
  chunks: {
    id: string;
    chunk_index: number;
    chunk_text: string;
    metadata: Record<string, any>;
  }[];
  created_at: string;
  updated_at: string;
}

export const resourcesApi = {
  get: (id: string) => apiFetch<ResourceDetail>(`/resources/${id}`),
};

// ── Channel Import ───────────────────────────────────────

export interface ChannelVideoSummary {
  video_id: string;
  title: string;
  views_str: string;
  duration_str: string;
  resource_id?: string;
  status: "pending" | "processing" | "success" | "failed" | "skipped";
}

export interface ChannelImportResponse {
  channel_name: string;
  total_videos: number;
  imported: number;
  skipped: number;
  failed: number;
  videos: ChannelVideoSummary[];
  message: string;
}

export const channelApi = {
  importChannel: (data: {
    channel_url: string;
    max_videos?: number;
    extract_transcripts?: boolean;
    collection_id?: string;
    brand_id?: string;
    tags?: string[];
    is_gold?: boolean;
  }) =>
    apiFetch<ChannelImportResponse>("/resources/channel", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  reExtract: (collectionId: string) =>
    apiFetch<{ message: string; queued: number }>(
      `/resources/re-extract?collection_id=${collectionId}`,
      { method: "POST" }
    ),
};
