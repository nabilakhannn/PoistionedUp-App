/**
 * Research API -- multi-platform content research.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface ResearchResult {
  title: string;
  url: string;
  snippet?: string;
  description?: string;
  publisher?: string;
  views?: string;
  source: string;
}

export interface ResearchResponse {
  web_results: ResearchResult[];
  youtube_trends: ResearchResult[];
  reddit_discussions: ResearchResult[];
  competitor_analysis: Record<string, unknown>[];
  signal_count: number;
  summary: string;
}

export interface QuickSearchResponse {
  results: ResearchResult[];
  source: string;
}

// ── API Methods ──────────────────────────────────────────

export const researchApi = {
  /** Full multi-source research */
  run: (
    topic: string,
    sources?: { web?: boolean; youtube?: boolean; reddit?: boolean },
    competitorUrls?: string[],
    maxResults?: number
  ) =>
    apiFetch<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify({
        topic,
        sources: sources || { web: true, youtube: true, reddit: true },
        competitor_urls: competitorUrls || [],
        max_results: maxResults || 8,
      }),
    }),

  /** Quick web search */
  quickSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/quick", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),

  /** YouTube trend search */
  youtubeSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/youtube", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),

  /** Reddit discussion search */
  redditSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/reddit", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 5 }),
    }),

  /** LinkedIn post search */
  linkedinSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/linkedin", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 8 }),
    }),

  /** TikTok content search */
  tiktokSearch: (query: string, maxResults?: number) =>
    apiFetch<QuickSearchResponse>("/research/tiktok", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults || 8 }),
    }),

  /** Multi-platform feed search */
  feed: (
    topic: string,
    sources?: Record<string, boolean>,
    maxResults?: number
  ) =>
    apiFetch<ResearchResponse>("/research/feed", {
      method: "POST",
      body: JSON.stringify({
        topic,
        sources: sources || {
          reddit: true,
          youtube: true,
          linkedin: true,
          tiktok: true,
        },
        max_results: maxResults || 10,
      }),
    }),
};
