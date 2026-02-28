"use client";

import { useEffect, useState } from "react";
import { competitorsApi, CompetitorComparison } from "@/lib/api/competitors";

interface ComparisonCardProps {
  competitorId: string;
  competitorName: string;
}

export function ComparisonCard({ competitorId, competitorName }: ComparisonCardProps) {
  const [data, setData] = useState<CompetitorComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const loadComparison = async () => {
    setLoading(true);
    try {
      const result = await competitorsApi.compare(competitorId);
      setData(result);
      setExpanded(true);
    } catch (e) {
      console.error("Comparison failed:", e);
    } finally {
      setLoading(false);
    }
  };

  if (!expanded) {
    return (
      <button
        onClick={loadComparison}
        disabled={loading}
        className="w-full border border-dashed border-zinc-700 rounded-lg p-4 text-sm text-muted-foreground hover:border-primary hover:text-primary transition disabled:opacity-50"
      >
        {loading ? "Loading comparison..." : `Compare your metrics vs ${competitorName}`}
      </button>
    );
  }

  if (!data) return null;

  const compMetrics = data.competitor_metrics;
  const userMetrics = data.user_metrics;

  const rows = [
    {
      label: "Followers",
      you: userMetrics.total_posts != null ? `${userMetrics.total_posts} posts` : "—",
      them: compMetrics.followers?.toLocaleString() ?? "—",
    },
    {
      label: "Engagement Rate",
      you: userMetrics.platforms?.[0]?.avg_engagement_rate != null
        ? `${userMetrics.platforms[0].avg_engagement_rate.toFixed(1)}%`
        : "—",
      them: compMetrics.engagement_rate != null
        ? `${compMetrics.engagement_rate.toFixed(1)}%`
        : "—",
    },
    {
      label: "Post Frequency",
      you: "—",
      them: compMetrics.post_frequency_weekly != null
        ? `${compMetrics.post_frequency_weekly.toFixed(1)}/week`
        : "—",
    },
    {
      label: "Top Topic",
      you: userMetrics.top_topics?.[0]?.topic_category ?? "—",
      them: compMetrics.top_topic ?? "—",
    },
  ];

  return (
    <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">You vs {competitorName}</h3>
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Collapse
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-muted-foreground border-b border-zinc-800">
              <th className="text-left py-2 pr-4">Metric</th>
              <th className="text-right py-2 pr-4 text-primary">You</th>
              <th className="text-right py-2">{competitorName}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-zinc-800/50 last:border-0">
                <td className="py-2 pr-4 text-muted-foreground">{row.label}</td>
                <td className="text-right py-2 pr-4 font-medium">{row.you}</td>
                <td className="text-right py-2 font-medium">{row.them}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Insights */}
      {data.insights.length > 0 && (
        <div className="mt-4 space-y-1">
          <h4 className="text-xs font-semibold text-muted-foreground">Insights</h4>
          {data.insights.map((insight, i) => (
            <p key={i} className="text-xs text-muted-foreground">
              {insight}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
