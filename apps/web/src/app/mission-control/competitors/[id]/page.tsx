"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  competitorsApi,
  Competitor,
  CompetitorMetric,
  CompetitorContent,
  CompetitorAnalysisReport,
  THREAT_LEVELS,
} from "@/lib/api/competitors";
import { ComparisonCard } from "../components/comparison-card";

const SUB_NAV = [
  { href: "/mission-control", label: "Dashboard" },
  { href: "/mission-control/competitors", label: "Competitors" },
];

export default function CompetitorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [competitor, setCompetitor] = useState<Competitor | null>(null);
  const [metrics, setMetrics] = useState<CompetitorMetric[]>([]);
  const [content, setContent] = useState<CompetitorContent[]>([]);
  const [report, setReport] = useState<CompetitorAnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [comp, metricsData, contentData] = await Promise.all([
        competitorsApi.get(id),
        competitorsApi.getMetrics(id, 60),
        competitorsApi.getContent(id, 20),
      ]);
      setCompetitor(comp);
      setMetrics(metricsData);
      setContent(contentData);
    } catch (e) {
      console.error("Failed to load competitor:", e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await competitorsApi.refresh(id);
      await loadData();
    } catch (e) {
      console.error("Refresh failed:", e);
    } finally {
      setRefreshing(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const result = await competitorsApi.analyze(id);
      setReport(result);
    } catch (e) {
      console.error("Analysis failed:", e);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleArchive = async () => {
    try {
      await competitorsApi.remove(id);
      router.push("/mission-control/competitors");
    } catch (e) {
      console.error("Archive failed:", e);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6">
        <p className="text-muted-foreground">Loading competitor...</p>
      </div>
    );
  }

  if (!competitor) {
    return (
      <div className="min-h-screen bg-background p-6">
        <p className="text-muted-foreground">Competitor not found.</p>
        <Link href="/mission-control/competitors" className="text-primary text-sm">
          Back to competitors
        </Link>
      </div>
    );
  }

  const threatInfo = THREAT_LEVELS.find((t) => t.value === competitor.threat_level);

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
          >
            {item.label}
          </Link>
        ))}
        <span className="px-3 py-1.5 text-xs font-medium text-foreground">
          {competitor.name}
        </span>
      </div>

      {/* Profile header */}
      <div className="border border-zinc-800 rounded-lg p-6 bg-zinc-900/30">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold">{competitor.name}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
              <span className="px-2 py-0.5 bg-zinc-800 rounded text-xs">
                {competitor.platform}
              </span>
              {competitor.niche && (
                <span className="px-2 py-0.5 bg-zinc-800 rounded text-xs">
                  {competitor.niche}
                </span>
              )}
              <span className={`text-xs font-medium ${threatInfo?.color || ""}`}>
                Threat: {threatInfo?.label} ({competitor.threat_level}/5)
              </span>
            </div>
            {competitor.positioning && (
              <p className="text-sm text-muted-foreground mt-3">{competitor.positioning}</p>
            )}
            <a
              href={competitor.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline mt-2 inline-block"
            >
              {competitor.profile_url}
            </a>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-3 py-1.5 text-xs border border-zinc-700 rounded-lg hover:bg-accent transition disabled:opacity-50"
            >
              {refreshing ? "Scanning..." : "Refresh Data"}
            </button>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {analyzing ? "Analyzing..." : "Analyze"}
            </button>
            <button
              onClick={handleArchive}
              className="px-3 py-1.5 text-xs text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition"
            >
              Archive
            </button>
          </div>
        </div>
      </div>

      {/* Metrics snapshot */}
      {competitor.latest_metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Followers", value: competitor.latest_metrics.followers?.toLocaleString() ?? "—" },
            { label: "Engagement Rate", value: competitor.latest_metrics.engagement_rate != null ? `${competitor.latest_metrics.engagement_rate.toFixed(1)}%` : "—" },
            { label: "Posts/Week", value: competitor.latest_metrics.post_frequency_weekly?.toFixed(1) ?? "—" },
            { label: "Top Topic", value: competitor.latest_metrics.top_topic ?? "—" },
          ].map((stat) => (
            <div key={stat.label} className="border border-zinc-800 rounded-lg p-3 bg-zinc-900/30">
              <span className="text-xs text-muted-foreground block">{stat.label}</span>
              <span className="text-lg font-bold">{stat.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Comparison */}
      <ComparisonCard competitorId={id} competitorName={competitor.name} />

      {/* Metrics history */}
      {metrics.length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
          <h3 className="text-sm font-semibold mb-3">Metrics History</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground border-b border-zinc-800">
                  <th className="text-left py-2 pr-4">Date</th>
                  <th className="text-right py-2 pr-4">Followers</th>
                  <th className="text-right py-2 pr-4">Engagement</th>
                  <th className="text-right py-2 pr-4">Posts/Week</th>
                  <th className="text-left py-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m.id} className="border-b border-zinc-800/50">
                    <td className="py-2 pr-4">
                      {m.recorded_at
                        ? new Date(m.recorded_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="text-right py-2 pr-4">
                      {m.followers?.toLocaleString() ?? "—"}
                    </td>
                    <td className="text-right py-2 pr-4">
                      {m.engagement_rate != null ? `${m.engagement_rate.toFixed(1)}%` : "—"}
                    </td>
                    <td className="text-right py-2 pr-4">
                      {m.post_frequency_weekly?.toFixed(1) ?? "—"}
                    </td>
                    <td className="py-2">
                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-muted-foreground">
                        {m.source || "manual"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent content */}
      {content.length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
          <h3 className="text-sm font-semibold mb-3">Recent Content</h3>
          <div className="space-y-2">
            {content.map((item) => (
              <div
                key={item.id}
                className="flex items-start justify-between py-2 border-b border-zinc-800/50 last:border-0"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {item.title && (
                      <span className="text-sm font-medium truncate">{item.title}</span>
                    )}
                    {item.format && (
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-zinc-800 text-muted-foreground">
                        {item.format}
                      </span>
                    )}
                  </div>
                  {item.content_preview && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                      {item.content_preview}
                    </p>
                  )}
                  {item.topics && item.topics.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {item.topics.map((t) => (
                        <span
                          key={t}
                          className="px-1.5 py-0.5 text-[10px] rounded bg-primary/10 text-primary"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right text-xs text-muted-foreground ml-4 shrink-0">
                  {item.engagement_count != null && (
                    <span className="block">{item.engagement_count.toLocaleString()} eng.</span>
                  )}
                  {item.published_at && (
                    <span className="block">
                      {new Date(item.published_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analysis report */}
      {report && (
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
          <h3 className="text-sm font-semibold mb-3">Analysis Report</h3>
          <p className="text-sm text-muted-foreground mb-4">{report.summary}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {report.strengths.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-green-400 mb-2">Strengths</h4>
                <ul className="text-xs text-muted-foreground space-y-1">
                  {report.strengths.map((s, i) => (
                    <li key={i}>+ {s}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.weaknesses.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-red-400 mb-2">Weaknesses</h4>
                <ul className="text-xs text-muted-foreground space-y-1">
                  {report.weaknesses.map((w, i) => (
                    <li key={i}>- {w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {report.content_pillars.length > 0 && (
            <div className="mt-4">
              <h4 className="text-xs font-semibold mb-2">Content Pillars</h4>
              <div className="flex flex-wrap gap-1">
                {report.content_pillars.map((p) => (
                  <span
                    key={p}
                    className="px-2 py-0.5 bg-zinc-800 rounded text-xs text-muted-foreground"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          {report.threat_assessment && (
            <div className="mt-4">
              <h4 className="text-xs font-semibold mb-1">Threat Assessment</h4>
              <p className="text-xs text-muted-foreground">{report.threat_assessment}</p>
            </div>
          )}
        </div>
      )}

      {/* Notes */}
      {competitor.notes && (
        <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
          <h3 className="text-sm font-semibold mb-2">Notes</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {competitor.notes}
          </p>
        </div>
      )}
    </div>
  );
}
