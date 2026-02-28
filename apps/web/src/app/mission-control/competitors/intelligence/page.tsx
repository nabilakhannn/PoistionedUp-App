"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  competitorsApi,
  IntelligenceFeed,
  CompetitorAlert,
  THREAT_LEVELS,
} from "@/lib/api/competitors";
import { MC_SUB_NAV } from "../../constants";

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-green-900/30 text-green-400 border-green-800",
  medium: "bg-yellow-900/30 text-yellow-400 border-yellow-800",
  high: "bg-red-900/30 text-red-400 border-red-800",
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  follower_surge: "Follower Surge",
  engagement_drop: "Engagement Drop",
  positioning_shift: "Positioning Shift",
  content_spike: "Content Spike",
  new_strategy: "New Strategy",
};

export default function IntelligenceFeedPage() {
  const [feed, setFeed] = useState<IntelligenceFeed | null>(null);
  const [alerts, setAlerts] = useState<CompetitorAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const loadFeed = useCallback(async () => {
    try {
      const [feedData, alertData] = await Promise.all([
        competitorsApi.getIntelligenceFeed(),
        competitorsApi.getAlerts(20),
      ]);
      setFeed(feedData);
      setAlerts(alertData);
    } catch (e) {
      console.error("Failed to load intelligence feed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const handleScanAll = async () => {
    setScanning(true);
    try {
      const competitors = await competitorsApi.list({ status: "active" });
      for (const comp of competitors.slice(0, 10)) {
        await competitorsApi.refresh(comp.id);
      }
      await loadFeed();
    } catch (e) {
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  const handleFullAnalysis = async () => {
    setAnalyzing(true);
    try {
      await competitorsApi.triggerFullAnalysis();
      await loadFeed();
    } catch (e) {
      console.error("Full analysis failed:", e);
    } finally {
      setAnalyzing(false);
    }
  };

  const getThreatColor = (level: number) =>
    THREAT_LEVELS.find((t) => t.value === level)?.color || "text-zinc-400";

  const getThreatLabel = (level: number) =>
    THREAT_LEVELS.find((t) => t.value === level)?.label || "Unknown";

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/competitors"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Intelligence Feed</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Agent-generated competitive intelligence, threat scores, and alerts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/mission-control/competitors"
            className="px-3 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-accent transition"
          >
            All Competitors
          </Link>
          <button
            onClick={handleScanAll}
            disabled={scanning}
            className="px-3 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-accent transition disabled:opacity-50"
          >
            {scanning ? "Scanning..." : "Scan All"}
          </button>
          <button
            onClick={handleFullAnalysis}
            disabled={analyzing}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            {analyzing ? "Analyzing..." : "Full Analysis"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-12">
          Loading intelligence feed...
        </div>
      ) : !feed ? (
        <div className="text-center text-muted-foreground py-12">
          Failed to load intelligence feed.
        </div>
      ) : (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <span className="text-xs text-muted-foreground block">
                Active Competitors
              </span>
              <span className="text-2xl font-bold">
                {feed.active_competitors}
              </span>
            </div>
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <span className="text-xs text-muted-foreground block">
                Avg Threat Level
              </span>
              <span
                className={`text-2xl font-bold ${getThreatColor(Math.round(feed.avg_threat_level))}`}
              >
                {feed.avg_threat_level.toFixed(1)}
              </span>
              <span className="text-xs text-muted-foreground ml-1">
                / 5 ({getThreatLabel(Math.round(feed.avg_threat_level))})
              </span>
            </div>
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <span className="text-xs text-muted-foreground block">
                Latest Analysis
              </span>
              <span className="text-sm font-medium">
                {feed.latest_analysis_date
                  ? new Date(feed.latest_analysis_date).toLocaleDateString()
                  : "None yet"}
              </span>
            </div>
            <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
              <span className="text-xs text-muted-foreground block">
                Open Alerts
              </span>
              <span
                className={`text-2xl font-bold ${feed.open_alerts > 0 ? "text-orange-400" : "text-zinc-400"}`}
              >
                {feed.open_alerts}
              </span>
            </div>
          </div>

          {/* Two-column layout: Analyses + Alerts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Analyses */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                Recent Analyses
              </h2>
              {feed.recent_analyses.length === 0 ? (
                <div className="border border-dashed border-zinc-800 rounded-lg p-6 text-center text-sm text-muted-foreground">
                  No analyses yet. Click &quot;Full Analysis&quot; to generate
                  your first competitor intelligence report.
                </div>
              ) : (
                feed.recent_analyses.map((item, i) => (
                  <Link
                    key={i}
                    href={`/mission-control/competitors/${item.competitor_id}`}
                    className="block border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition bg-zinc-900/30"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="text-sm font-semibold">
                          {item.competitor_name}
                        </h3>
                        {item.date && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(item.date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      {item.threat_level != null && (
                        <span
                          className={`text-xs font-medium ${getThreatColor(item.threat_level)}`}
                        >
                          Threat {item.threat_level}/5
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-3">
                      {item.summary}
                    </p>
                  </Link>
                ))
              )}
            </div>

            {/* Recent Alerts */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                Alerts
              </h2>
              {alerts.length === 0 ? (
                <div className="border border-dashed border-zinc-800 rounded-lg p-6 text-center text-sm text-muted-foreground">
                  No alerts yet. Alerts appear when competitors make significant
                  moves (follower surges, engagement drops, strategy changes).
                </div>
              ) : (
                alerts.map((alert, i) => (
                  <div
                    key={alert.id || i}
                    className={`border rounded-lg p-4 ${SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.medium}`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium uppercase">
                          {ALERT_TYPE_LABELS[alert.alert_type] ||
                            alert.alert_type}
                        </span>
                        <span className="text-xs opacity-70">
                          {alert.severity}
                        </span>
                      </div>
                      {alert.created_at && (
                        <span className="text-xs opacity-70">
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium mb-1">
                      {alert.competitor_name}
                    </p>
                    <p className="text-xs opacity-80 line-clamp-2">
                      {alert.detail}
                    </p>
                    {alert.metric_before != null &&
                      alert.metric_after != null && (
                        <div className="mt-2 flex items-center gap-2 text-xs">
                          <span className="opacity-70">
                            {alert.metric_before.toLocaleString()}
                          </span>
                          <span>→</span>
                          <span className="font-medium">
                            {alert.metric_after.toLocaleString()}
                          </span>
                        </div>
                      )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Benchmarks */}
          {feed.benchmarks &&
            Object.keys(feed.benchmarks).length > 0 && (
              <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Benchmarks — You vs Competitors
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {feed.benchmarks.avg_engagement_rate != null && (
                    <div>
                      <span className="text-xs text-muted-foreground block">
                        Avg Engagement Rate
                      </span>
                      <span className="text-lg font-bold">
                        {feed.benchmarks.avg_engagement_rate.toFixed(1)}%
                      </span>
                      {feed.benchmarks.your_engagement_rate != null && (
                        <span className="text-xs text-muted-foreground ml-2">
                          (You: {feed.benchmarks.your_engagement_rate.toFixed(1)}
                          %)
                        </span>
                      )}
                    </div>
                  )}
                  {feed.benchmarks.avg_post_frequency != null && (
                    <div>
                      <span className="text-xs text-muted-foreground block">
                        Avg Post Frequency
                      </span>
                      <span className="text-lg font-bold">
                        {feed.benchmarks.avg_post_frequency.toFixed(1)}
                      </span>
                      <span className="text-xs text-muted-foreground ml-1">
                        /week
                      </span>
                      {feed.benchmarks.your_post_frequency != null && (
                        <span className="text-xs text-muted-foreground ml-2">
                          (You: {feed.benchmarks.your_post_frequency.toFixed(1)}
                          /wk)
                        </span>
                      )}
                    </div>
                  )}
                  {feed.benchmarks.avg_followers != null && (
                    <div>
                      <span className="text-xs text-muted-foreground block">
                        Avg Followers
                      </span>
                      <span className="text-lg font-bold">
                        {Math.round(
                          feed.benchmarks.avg_followers,
                        ).toLocaleString()}
                      </span>
                      {feed.benchmarks.your_followers != null && (
                        <span className="text-xs text-muted-foreground ml-2">
                          (You:{" "}
                          {feed.benchmarks.your_followers.toLocaleString()})
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
        </>
      )}
    </div>
  );
}
