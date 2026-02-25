/**
 * Performance API -- content analytics, voice analysis, and drift detection.
 */

import { apiFetch } from "./client";

// ── Content Post Types ───────────────────────────────────

export interface ContentPostSummary {
  id: string;
  title: string;
  content_type: string;
  platform: string;
  hook_type: string | null;
  topic: string | null;
  topic_category: string | null;
  performance_tier: string | null;
  engagement_rate: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  published_at: string | null;
  created_at: string;
}

export interface ContentPostDetail extends ContentPostSummary {
  hook_used: string | null;
  content_body: string | null;
  workflow_id: string | null;
  collection_id: string | null;
  published_url: string | null;
  day_of_week: string | null;
  shares: number | null;
  saves: number | null;
  watch_time_seconds: number | null;
  click_through_rate: number | null;
  impressions: number | null;
  reach: number | null;
  subscribers_gained: number | null;
  agent_analysis: Record<string, any>;
  tags: string[];
  metadata: Record<string, any>;
  updated_at: string;
}

// ── Analytics Types ──────────────────────────────────────

export interface PlatformBreakdown {
  platform: string;
  post_count: number;
  avg_engagement_rate: number | null;
  avg_views: number | null;
  top_tier_count: number;
}

export interface TopicBreakdown {
  topic_category: string;
  post_count: number;
  avg_engagement_rate: number | null;
  avg_views: number | null;
}

export interface HookBreakdown {
  hook_type: string;
  post_count: number;
  avg_engagement_rate: number | null;
  example_hooks: string[];
}

export interface PatternDetected {
  pattern: string;
  evidence: string;
  confidence: number;
}

export interface PerformanceAnalytics {
  total_posts: number;
  platforms: PlatformBreakdown[];
  top_topics: TopicBreakdown[];
  top_hook_types: HookBreakdown[];
  best_day_of_week: string | null;
  patterns: PatternDetected[];
  top_hooks: string[];
  anti_hooks: string[];
}

// ── Performance API ──────────────────────────────────────

export const performanceApi = {
  list: (platform?: string, tier?: string, brandId?: string) => {
    const params = new URLSearchParams();
    if (platform) params.set("platform", platform);
    if (tier) params.set("tier", tier);
    if (brandId) params.set("brand_id", brandId);
    const qs = params.toString();
    return apiFetch<ContentPostSummary[]>(
      `/content-posts${qs ? `?${qs}` : ""}`
    );
  },

  get: (id: string) => apiFetch<ContentPostDetail>(`/content-posts/${id}`),

  create: (data: {
    title: string;
    content_type: string;
    platform: string;
    hook_used?: string;
    hook_type?: string;
    topic?: string;
    topic_category?: string;
    content_body?: string;
    published_url?: string;
    published_at?: string;
    day_of_week?: string;
    tags?: string[];
    brand_id?: string;
  }) =>
    apiFetch<ContentPostSummary>("/content-posts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMetrics: (
    id: string,
    data: {
      views?: number;
      likes?: number;
      comments?: number;
      shares?: number;
      saves?: number;
      watch_time_seconds?: number;
      click_through_rate?: number;
      impressions?: number;
      reach?: number;
      subscribers_gained?: number;
    }
  ) =>
    apiFetch<ContentPostDetail>(`/content-posts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  analytics: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<PerformanceAnalytics>(`/content-posts/analytics${qs}`);
  },

  analyze: (id: string) =>
    apiFetch<{
      post_id: string;
      performance_tier: string | null;
      analysis: Record<string, any>;
      message: string;
    }>(`/content-posts/${id}/analyze`, { method: "POST" }),
};

// ── Voice / Drift Types ──────────────────────────────────

export interface SelfVoiceDNA {
  tone: string;
  sentence_style: string;
  vocabulary_level: string;
  avg_sentence_length: number | null;
  hook_patterns: string[];
  cta_patterns: string[];
  signature_phrases: string[];
  content_structure: string;
  personality_traits: string[];
  sample_hooks: string[];
  posts_analyzed: number;
}

export interface VoiceDriftResult {
  drift_score: number;
  drift_level: string;
  details: string[];
  recommendation: string;
  baseline_available: boolean;
}

// ── Voice API ────────────────────────────────────────────

export const voiceApi = {
  analyzeSelf: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<{ voice_dna: SelfVoiceDNA; message: string }>(
      `/voice/analyze-self${qs}`,
      { method: "POST" }
    );
  },

  getBaseline: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<SelfVoiceDNA | null>(`/voice/baseline${qs}`);
  },

  checkDrift: (text: string, brandId?: string) =>
    apiFetch<VoiceDriftResult>("/voice/drift-check", {
      method: "POST",
      body: JSON.stringify({ text, brand_id: brandId }),
    }),
};
