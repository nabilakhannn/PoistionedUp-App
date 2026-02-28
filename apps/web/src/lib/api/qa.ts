/**
 * QA Review API — content quality assurance dashboard.
 */

import { apiFetch } from "./client";

// ── Types ────────────────────────────────────────────────

export interface QAScoreBreakdown {
  voice_score: number;
  hook_score: number;
  structure_score: number;
  ai_tell_score: number;
  virality_score: number;
  goal_alignment_score: number;
}

export interface QAIssue {
  category: string;
  severity: string;
  detail: string;
}

export interface QARiskFlag {
  type: string;
  detail: string;
}

export interface QAReviewResult {
  id: string;
  overall_score: number;
  scores: QAScoreBreakdown;
  verdict: string;
  feedback: string;
  issues: QAIssue[];
  risk_flags: QARiskFlag[];
  revision_number: number;
  revision_triggered: boolean;
  created_at: string;
}

export interface QAReviewOut {
  id: string;
  content_ref_type: string;
  content_ref_id?: string | null;
  platform?: string | null;
  overall_score: number;
  verdict: string;
  feedback?: string | null;
  revision_number: number;
  created_at: string;
}

export interface QAStats {
  total_reviews: number;
  pass_count: number;
  revise_count: number;
  fail_count: number;
  avg_score: number;
  avg_voice_score: number;
  avg_hook_score: number;
  avg_virality_score: number;
  common_issues: { category: string; count: number }[];
}

export interface QAReviewRequest {
  content_text: string;
  platform?: string;
  content_ref_type?: string;
  content_ref_id?: string;
  brand_id?: string;
}

// ── Constants ────────────────────────────────────────────

export const QA_PASS_THRESHOLD = 80;
export const QA_REVISE_THRESHOLD = 50;

export const VERDICT_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  pass: { label: "Pass", color: "text-green-400", bg: "bg-green-500/20" },
  revise: { label: "Revise", color: "text-yellow-400", bg: "bg-yellow-500/20" },
  fail: { label: "Fail", color: "text-red-400", bg: "bg-red-500/20" },
  pending: { label: "Pending", color: "text-zinc-400", bg: "bg-zinc-500/20" },
};

export const SCORE_DIMENSIONS: { key: keyof QAScoreBreakdown; label: string; weight: string }[] = [
  { key: "voice_score", label: "Voice", weight: "25%" },
  { key: "hook_score", label: "Hook", weight: "20%" },
  { key: "virality_score", label: "Virality", weight: "20%" },
  { key: "ai_tell_score", label: "AI-Tells", weight: "15%" },
  { key: "structure_score", label: "Structure", weight: "10%" },
  { key: "goal_alignment_score", label: "Goal Alignment", weight: "10%" },
];

// ── API Methods ──────────────────────────────────────────

export const qaApi = {
  /** Review content — POST /qa/review */
  review: (data: QAReviewRequest) =>
    apiFetch<QAReviewResult>("/qa/review", { method: "POST", body: JSON.stringify(data) }),

  /** List reviews — GET /qa/reviews */
  list: (params?: { days?: number; verdict?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.days) qs.set("days", String(params.days));
    if (params?.verdict) qs.set("verdict", params.verdict);
    if (params?.limit) qs.set("limit", String(params.limit));
    const query = qs.toString();
    return apiFetch<QAReviewOut[]>(`/qa/reviews${query ? `?${query}` : ""}`);
  },

  /** Get review detail — GET /qa/reviews/{id} */
  get: (id: string) => apiFetch<QAReviewResult>(`/qa/reviews/${id}`),

  /** Get QA stats — GET /qa/stats */
  stats: (days?: number) =>
    apiFetch<QAStats>(`/qa/stats${days ? `?days=${days}` : ""}`),
};
