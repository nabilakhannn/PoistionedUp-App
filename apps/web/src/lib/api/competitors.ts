/**
 * Competitors API — competitor intelligence dashboard.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface Competitor {
  id: string;
  user_id: string;
  brand_id?: string | null;
  name: string;
  platform: string;
  profile_url: string;
  positioning?: string | null;
  niche?: string | null;
  estimated_followers?: number | null;
  pricing_tier?: string | null;
  notes?: string | null;
  threat_level: number;
  threat_level_override?: boolean;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  latest_metrics?: CompetitorMetric | null;
  metrics_history?: CompetitorMetric[];
  recent_content?: CompetitorContent[];
}

export interface CompetitorMetric {
  id?: string;
  competitor_id?: string;
  recorded_at?: string | null;
  followers?: number | null;
  engagement_rate?: number | null;
  post_frequency_weekly?: number | null;
  avg_post_engagement?: number | null;
  top_topic?: string | null;
  source?: string;
  created_at?: string | null;
}

export interface CompetitorContent {
  id?: string;
  competitor_id?: string;
  published_at?: string | null;
  platform?: string | null;
  title?: string | null;
  url?: string | null;
  content_preview?: string | null;
  topics?: string[];
  engagement_count?: number | null;
  engagement_rate?: number | null;
  format?: string;
  created_at?: string | null;
}

export interface CompetitorComparison {
  competitor_id: string;
  competitor_name: string;
  user_metrics: Record<string, any>;
  competitor_metrics: Record<string, any>;
  insights: string[];
}

export interface CompetitorAnalysisReport {
  competitor_id: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  content_pillars: string[];
  threat_assessment: string;
}

export interface ContentGap {
  topic: string;
  covered_by_competitors: string[];
  your_coverage: boolean;
  priority: string;
}

export interface ContentGapAnalysis {
  gaps: ContentGap[];
  your_unique_topics: string[];
  shared_topics: string[];
}

export interface CompetitorCreateData {
  name: string;
  platform?: string;
  profile_url: string;
  positioning?: string;
  niche?: string;
  pricing_tier?: string;
  notes?: string;
  threat_level?: number;
  brand_id?: string;
}

export interface CompetitorUpdateData {
  name?: string;
  platform?: string;
  profile_url?: string;
  positioning?: string;
  niche?: string;
  pricing_tier?: string;
  notes?: string;
  threat_level?: number;
  status?: string;
}

export interface ThreatScoreDetail {
  calculated_score: number;
  engagement_growth_factor: number;
  content_overlap_factor: number;
  frequency_factor: number;
  follower_ratio_factor: number;
  reasoning: string;
  is_overridden: boolean;
}

export interface CompetitorAlert {
  id?: string;
  competitor_id: string;
  competitor_name: string;
  alert_type: string;
  detail: string;
  metric_before?: number | null;
  metric_after?: number | null;
  severity: string;
  created_at?: string | null;
}

export interface IntelligenceFeedItem {
  item_type: string;
  competitor_id: string;
  competitor_name: string;
  summary: string;
  threat_level?: number | null;
  date?: string | null;
}

export interface IntelligenceFeed {
  active_competitors: number;
  avg_threat_level: number;
  latest_analysis_date?: string | null;
  open_alerts: number;
  recent_analyses: IntelligenceFeedItem[];
  recent_alerts: CompetitorAlert[];
  benchmarks: Record<string, any>;
}

// ── Platform options ────────────────────────────────────

export const PLATFORMS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "Twitter/X" },
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "website", label: "Website" },
  { value: "other", label: "Other" },
] as const;

export const THREAT_LEVELS = [
  { value: 1, label: "Low", color: "text-green-400" },
  { value: 2, label: "Minor", color: "text-green-300" },
  { value: 3, label: "Moderate", color: "text-yellow-400" },
  { value: 4, label: "High", color: "text-orange-400" },
  { value: 5, label: "Critical", color: "text-red-400" },
] as const;

// ── API Methods ─────────────────────────────────────────

export const competitorsApi = {
  list: (params?: { brand_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.brand_id) qs.set("brand_id", params.brand_id);
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString();
    return apiFetch<Competitor[]>(`/competitors${query ? `?${query}` : ""}`);
  },

  create: (data: CompetitorCreateData) =>
    apiFetch<Competitor>("/competitors", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (id: string) => apiFetch<Competitor>(`/competitors/${id}`),

  update: (id: string, data: CompetitorUpdateData) =>
    apiFetch<Competitor>(`/competitors/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  remove: (id: string) =>
    apiFetch<void>(`/competitors/${id}`, { method: "DELETE" }),

  getMetrics: (id: string, days = 30) =>
    apiFetch<CompetitorMetric[]>(`/competitors/${id}/metrics?days=${days}`),

  recordMetrics: (id: string, data: Partial<CompetitorMetric>) =>
    apiFetch<CompetitorMetric>(`/competitors/${id}/metrics`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getContent: (id: string, limit = 20) =>
    apiFetch<CompetitorContent[]>(
      `/competitors/${id}/content?limit=${limit}`,
    ),

  refresh: (id: string) =>
    apiFetch<{ competitor_id: string; content_items_added: number }>(
      `/competitors/${id}/refresh`,
      { method: "POST" },
    ),

  analyze: (id: string) =>
    apiFetch<CompetitorAnalysisReport>(`/competitors/${id}/analyze`, {
      method: "POST",
    }),

  compare: (competitorId: string) =>
    apiFetch<CompetitorComparison>(
      `/competitors/comparison?competitor_id=${competitorId}`,
    ),

  getGaps: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<ContentGapAnalysis>(`/competitors/gaps${qs}`);
  },

  getIntelligenceFeed: (brandId?: string) => {
    const qs = brandId ? `?brand_id=${brandId}` : "";
    return apiFetch<IntelligenceFeed>(`/competitors/intelligence${qs}`);
  },

  getAlerts: (limit = 20) =>
    apiFetch<CompetitorAlert[]>(`/competitors/alerts?limit=${limit}`),

  triggerFullAnalysis: (brandId?: string) =>
    apiFetch<{ analyzed: number; results: CompetitorAnalysisReport[] }>(
      "/competitors/full-analysis",
      {
        method: "POST",
        body: JSON.stringify(brandId ? { brand_id: brandId } : {}),
      },
    ),
};
