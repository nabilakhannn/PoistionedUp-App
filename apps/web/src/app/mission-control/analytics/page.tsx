"use client";

import { useEffect, useState, useCallback } from "react";
import { useBrand } from "@/lib/brand-context";
import {
  analyticsDashboardApi,
  type AnalyticsDashboard,
} from "@/lib/api/analytics-dashboard";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

/* ── Shared components ────────────────────────────────── */

function StatCard({
  label,
  value,
  sub,
  accent = "text-violet-400",
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
      <div className="text-zinc-500 text-xs font-medium mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="text-zinc-600 text-[10px] mt-0.5">{sub}</div>}
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h2 className="text-zinc-300 text-sm font-semibold tracking-wide uppercase mb-4 flex items-center gap-2">
      <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
      {title}
    </h2>
  );
}

const PERIODS = ["7d", "30d", "90d"] as const;

const CHART_THEME = {
  grid: "#27272a",
  violet: "#8b5cf6",
  emerald: "#34d399",
  red: "#f87171",
  blue: "#60a5fa",
  amber: "#fbbf24",
  text: "#71717a",
};

const customTooltipStyle = {
  backgroundColor: "#18181b",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px",
  fontSize: "12px",
  color: "#e4e4e7",
};

/* ── Funnel bar ───────────────────────────────────────── */

function FunnelBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-zinc-500 text-xs w-20 text-right">{label}</span>
      <div className="flex-1 h-5 bg-white/[0.03] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-zinc-400 text-xs font-mono w-8 text-right">{value}</span>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────── */

export default function AnalyticsDashboardPage() {
  const { currentBrand } = useBrand();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("30d");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyticsDashboardApi.getDashboard({
        brand_id: currentBrand?.id,
        period,
      });
      setData(result);
    } catch {
      setError("Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [currentBrand?.id, period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090B] p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white/[0.03] rounded-xl h-48 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#09090B] flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-3">{error || "No data available"}</p>
          <button onClick={loadData} className="px-4 py-2 bg-violet-600 text-white text-sm rounded-lg">
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { content_roi, pipeline, revenue, engagement, leads, cost } = data;
  const funnelMax = Math.max(...Object.values(revenue.proposal_funnel), 1);

  return (
    <div className="min-h-screen bg-[#09090B]">
      {/* Header */}
      <div className="border-b border-white/[0.05] bg-white/[0.02]">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <div>
            <h1 className="text-zinc-100 text-xl font-bold">Analytics & ROI</h1>
            <p className="text-zinc-600 text-xs mt-0.5">
              {data.period_start} — {data.period_end}
            </p>
          </div>
          <div className="flex gap-1 bg-white/[0.03] rounded-lg p-0.5">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  period === p
                    ? "bg-violet-600 text-white"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-8">
        {/* ── Section 1: Content ROI ─────────────────────── */}
        <section>
          <SectionHeader title="Content ROI" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <StatCard label="Posts / Day" value={content_roi.posts_per_day} />
            <StatCard label="Approval Rate" value={`${content_roi.approval_rate}%`} accent="text-emerald-400" />
            <StatCard label="Avg QA Score" value={content_roi.avg_qa_score} />
            <StatCard label="Total Generated" value={content_roi.total_generated} accent="text-zinc-200" />
          </div>
          {content_roi.daily_breakdown.length > 0 && (
            <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={content_roi.daily_breakdown}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: CHART_THEME.text }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                  <Tooltip contentStyle={customTooltipStyle} />
                  <Area type="monotone" dataKey="generated" stroke={CHART_THEME.violet} fill={CHART_THEME.violet} fillOpacity={0.15} name="Generated" />
                  <Area type="monotone" dataKey="approved" stroke={CHART_THEME.emerald} fill={CHART_THEME.emerald} fillOpacity={0.1} name="Approved" />
                  <Area type="monotone" dataKey="rejected" stroke={CHART_THEME.red} fill={CHART_THEME.red} fillOpacity={0.1} name="Rejected" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        {/* ── Section 2: Pipeline + Cost ─────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <SectionHeader title="Pipeline Performance" />
            <div className="grid grid-cols-3 gap-3 mb-4">
              <StatCard label="Success Rate" value={`${pipeline.success_rate}%`} accent="text-emerald-400" />
              <StatCard label="Avg Duration" value={`${(pipeline.avg_duration_ms / 1000).toFixed(1)}s`} />
              <StatCard label="Total Runs" value={pipeline.total_runs} accent="text-zinc-200" />
            </div>
            {Object.keys(pipeline.phase_breakdown).length > 0 && (
              <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={Object.entries(pipeline.phase_breakdown).map(([phase, stats]) => ({
                    phase: phase.replace("pipeline_", ""),
                    completed: stats.count - stats.fail_count,
                    failed: stats.fail_count,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                    <XAxis dataKey="phase" tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                    <YAxis tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                    <Tooltip contentStyle={customTooltipStyle} />
                    <Bar dataKey="completed" fill={CHART_THEME.violet} name="Completed" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="failed" fill={CHART_THEME.red} name="Failed" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>

          <section>
            <SectionHeader title="Cost Tracking" />
            <div className="grid grid-cols-3 gap-3 mb-4">
              <StatCard label="Monthly Spend" value={`$${cost.estimated_cost}`} accent="text-amber-400" />
              <StatCard label="Cost / Content" value={`$${cost.cost_per_content}`} />
              <StatCard label="Budget Used" value={`${cost.budget_utilization}%`} accent={cost.budget_utilization > 80 ? "text-red-400" : "text-emerald-400"} />
            </div>
            <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-zinc-500 text-xs">Budget: ${cost.monthly_budget}</span>
                <span className="text-zinc-400 text-xs font-mono">${cost.estimated_cost} / ${cost.monthly_budget}</span>
              </div>
              <div className="h-3 bg-white/[0.05] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    cost.budget_utilization > 80 ? "bg-red-500" : "bg-violet-500"
                  }`}
                  style={{ width: `${Math.min(cost.budget_utilization, 100)}%` }}
                />
              </div>
              <div className="text-zinc-600 text-[10px] mt-1.5">
                {cost.total_tokens.toLocaleString()} tokens used
              </div>
            </div>
          </section>
        </div>

        {/* ── Section 3: Engagement ──────────────────────── */}
        <section>
          <SectionHeader title="Engagement Trends" />
          {engagement.total_views === 0 && engagement.top_posts.length === 0 ? (
            <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-8 text-center">
              <p className="text-zinc-500 text-sm">No published post metrics yet</p>
              <p className="text-zinc-600 text-xs mt-1">Engagement data appears after posts are published and metrics are synced</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <StatCard label="Avg Engagement" value={`${(engagement.avg_engagement_rate * 100).toFixed(2)}%`} accent="text-blue-400" />
                <StatCard label="Total Views" value={engagement.total_views.toLocaleString()} />
                <StatCard label="Total Likes" value={engagement.total_likes.toLocaleString()} />
                <StatCard label="Total Comments" value={engagement.total_comments.toLocaleString()} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {engagement.hook_type_performance.length > 0 && (
                  <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
                    <div className="text-zinc-400 text-xs font-medium mb-3">Hook Type Performance</div>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={engagement.hook_type_performance.slice(0, 6)} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                        <XAxis type="number" tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                        <YAxis dataKey="hook_type" type="category" tick={{ fontSize: 10, fill: CHART_THEME.text }} width={80} />
                        <Tooltip contentStyle={customTooltipStyle} />
                        <Bar dataKey="avg_engagement" fill={CHART_THEME.blue} name="Avg Engagement" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {engagement.best_posting_days.length > 0 && (
                  <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
                    <div className="text-zinc-400 text-xs font-medium mb-3">Best Posting Days</div>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={engagement.best_posting_days}>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} />
                        <XAxis dataKey="day_of_week" tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                        <YAxis tick={{ fontSize: 10, fill: CHART_THEME.text }} />
                        <Tooltip contentStyle={customTooltipStyle} />
                        <Bar dataKey="avg_engagement" fill={CHART_THEME.emerald} name="Avg Engagement" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {engagement.top_posts.length > 0 && (
                <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4 mt-4">
                  <div className="text-zinc-400 text-xs font-medium mb-3">Top 5 Posts by Engagement</div>
                  <div className="space-y-2">
                    {engagement.top_posts.map((post, i) => (
                      <div key={i} className="flex items-center gap-3 py-1.5">
                        <span className="text-violet-400 font-bold text-sm w-5">#{i + 1}</span>
                        <span className="text-zinc-300 text-xs flex-1 truncate">{post.title}</span>
                        <span className="text-zinc-600 text-[10px]">{post.platform}</span>
                        <span className="text-emerald-400 text-xs font-mono">
                          {(post.engagement_rate * 100).toFixed(2)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        {/* ── Section 4: Revenue + Leads ─────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <SectionHeader title="Revenue Attribution" />
            {revenue.total_proposals_sent === 0 ? (
              <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-8 text-center">
                <p className="text-zinc-500 text-sm">No proposals sent yet</p>
                <p className="text-zinc-600 text-xs mt-1">Generate client proposals to track revenue</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <StatCard label="Total Won" value={`$${revenue.total_closed_won.toLocaleString()}`} accent="text-emerald-400" />
                  <StatCard label="Win Rate" value={`${revenue.win_rate}%`} />
                  <StatCard label="Proposals Sent" value={revenue.total_proposals_sent} accent="text-zinc-200" />
                </div>
                <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4 space-y-2">
                  <div className="text-zinc-400 text-xs font-medium mb-3">Proposal Funnel</div>
                  <FunnelBar label="Draft" value={revenue.proposal_funnel.draft || 0} max={funnelMax} color="bg-zinc-600" />
                  <FunnelBar label="Sent" value={revenue.proposal_funnel.sent || 0} max={funnelMax} color="bg-blue-500" />
                  <FunnelBar label="Accepted" value={revenue.proposal_funnel.accepted || 0} max={funnelMax} color="bg-violet-500" />
                  <FunnelBar label="Rejected" value={revenue.proposal_funnel.rejected || 0} max={funnelMax} color="bg-red-500" />
                  <FunnelBar label="Won" value={revenue.proposal_funnel.closed_won || 0} max={funnelMax} color="bg-emerald-500" />
                  <FunnelBar label="Lost" value={revenue.proposal_funnel.closed_lost || 0} max={funnelMax} color="bg-zinc-700" />
                </div>
              </>
            )}
          </section>

          <section>
            <SectionHeader title="Lead Funnel" />
            {leads.total_leads === 0 ? (
              <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-8 text-center">
                <p className="text-zinc-500 text-sm">No leads yet</p>
                <p className="text-zinc-600 text-xs mt-1">Import or generate leads in the Grow room</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <StatCard label="Total Leads" value={leads.total_leads} accent="text-zinc-200" />
                  <StatCard label="Conversion" value={`${leads.conversion_rate}%`} accent="text-emerald-400" />
                  <StatCard label={`New (${data.period})`} value={leads.new_leads_period} accent="text-blue-400" />
                </div>
                <div className="bg-white/[0.03] backdrop-blur-sm ring-1 ring-white/[0.05] rounded-xl p-4">
                  <div className="text-zinc-400 text-xs font-medium mb-3">Status Distribution</div>
                  <div className="space-y-2">
                    {Object.entries(leads.status_distribution).map(([status, count]) => (
                      <FunnelBar
                        key={status}
                        label={status}
                        value={count}
                        max={leads.total_leads}
                        color={
                          status === "customer" ? "bg-emerald-500" :
                          status === "hot" ? "bg-red-500" :
                          status === "warm" ? "bg-amber-500" :
                          status === "cold" ? "bg-blue-500" :
                          "bg-zinc-600"
                        }
                      />
                    ))}
                  </div>
                  {Object.keys(leads.bant_distribution).length > 0 && (
                    <>
                      <div className="text-zinc-400 text-xs font-medium mt-4 mb-3">BANT Score Distribution</div>
                      <div className="space-y-2">
                        {Object.entries(leads.bant_distribution).map(([score, count]) => (
                          <FunnelBar
                            key={score}
                            label={`BANT ${score}/4`}
                            value={count}
                            max={leads.total_leads}
                            color={
                              Number(score) >= 3 ? "bg-emerald-500" :
                              Number(score) >= 2 ? "bg-amber-500" :
                              "bg-zinc-600"
                            }
                          />
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
