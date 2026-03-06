/** Analytics Dashboard API — Slice 112 */

import { apiFetch } from "./client";

export interface DailyBreakdown {
  date: string;
  generated: number;
  approved: number;
  rejected: number;
  avg_qa: number;
}

export interface ContentROI {
  posts_per_day: number;
  approval_rate: number;
  avg_qa_score: number;
  total_generated: number;
  approved: number;
  rejected: number;
  in_review: number;
  daily_breakdown: DailyBreakdown[];
}

export interface PhaseStats {
  count: number;
  avg_ms: number;
  fail_count: number;
}

export interface DailyRuns {
  date: string;
  completed: number;
  failed: number;
}

export interface PipelinePerformance {
  total_runs: number;
  completed: number;
  failed: number;
  success_rate: number;
  avg_duration_ms: number;
  phase_breakdown: Record<string, PhaseStats>;
  daily_runs: DailyRuns[];
}

export interface RevenueAttribution {
  total_closed_won: number;
  total_proposals_sent: number;
  proposal_funnel: Record<string, number>;
  win_rate: number;
}

export interface TopPost {
  title: string;
  engagement_rate: number;
  platform: string;
  hook_type: string;
  published_at: string;
}

export interface GroupedMetric {
  hook_type?: string;
  topic_category?: string;
  day_of_week?: string;
  avg_engagement: number;
  count: number;
}

export interface EngagementTrends {
  avg_engagement_rate: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  tier_distribution: Record<string, number>;
  top_posts: TopPost[];
  hook_type_performance: GroupedMetric[];
  topic_performance: GroupedMetric[];
  best_posting_days: GroupedMetric[];
}

export interface LeadFunnel {
  total_leads: number;
  status_distribution: Record<string, number>;
  bant_distribution: Record<string, number>;
  conversion_rate: number;
  new_leads_period: number;
}

export interface DailySpend {
  date: string;
  tokens: number;
  cost: number;
}

export interface CostTracking {
  total_tokens: number;
  estimated_cost: number;
  monthly_budget: number;
  budget_utilization: number;
  cost_per_content: number;
  daily_spend: DailySpend[];
}

export interface AnalyticsDashboard {
  period: string;
  period_start: string;
  period_end: string;
  content_roi: ContentROI;
  pipeline: PipelinePerformance;
  revenue: RevenueAttribution;
  engagement: EngagementTrends;
  leads: LeadFunnel;
  cost: CostTracking;
}

export const analyticsDashboardApi = {
  getDashboard: (params: { brand_id?: string; period?: string }) => {
    const qs = new URLSearchParams();
    if (params.brand_id) qs.set("brand_id", params.brand_id);
    if (params.period) qs.set("period", params.period);
    return apiFetch<AnalyticsDashboard>(`/analytics/dashboard?${qs.toString()}`);
  },
};
