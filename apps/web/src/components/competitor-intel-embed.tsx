"use client";

/**
 * Competitor Intel Embed — Slice 92c
 *
 * Inline competitor intelligence summary card for the Marketing room.
 * Shows: active competitor count, avg threat, open alerts, top 3 threats,
 * latest alert, last scan date.
 *
 * "Full Dashboard →" links to /mission-control/competitors for deep-dive.
 */

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  competitorsApi,
  THREAT_LEVELS,
  type IntelligenceFeed,
  type Competitor,
} from "@/lib/api/competitors";

interface Props {
  brandId: string;
}

function getThreatStyle(level: number): string {
  const found = THREAT_LEVELS.find(t => t.value === level);
  return found ? found.color : "text-muted-foreground";
}

function getThreatLabel(level: number): string {
  const found = THREAT_LEVELS.find(t => t.value === level);
  return found ? found.label.toUpperCase() : "N/A";
}

function ThreatBar({ level }: { level: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <div
          key={i}
          className={`h-1.5 w-4 rounded-sm ${
            i <= level
              ? level >= 4
                ? "bg-red-400"
                : level === 3
                ? "bg-yellow-400"
                : "bg-green-400"
              : "bg-muted"
          }`}
        />
      ))}
    </div>
  );
}

function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "< 1 hour ago";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function CompetitorIntelEmbed({ brandId }: Props) {
  const [feed, setFeed] = useState<IntelligenceFeed | null>(null);
  const [topThreats, setTopThreats] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!brandId) return;
    setLoading(true);
    try {
      const [feedData, listData] = await Promise.all([
        competitorsApi.getIntelligenceFeed(brandId),
        competitorsApi.list({ brand_id: brandId, status: "active" }),
      ]);
      setFeed(feedData);
      // Top 3 by threat level descending
      const sorted = [...listData].sort((a, b) => b.threat_level - a.threat_level);
      setTopThreats(sorted.slice(0, 3));
    } catch {
      // Silent — non-critical
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-5 space-y-3 animate-pulse">
        <div className="flex justify-between">
          <div className="h-4 w-40 bg-muted/50 rounded" />
          <div className="h-4 w-24 bg-muted/30 rounded" />
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-14 bg-muted/30 rounded-lg" />
          ))}
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-10 bg-muted/20 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  // Empty state — no competitors tracked
  if (!feed || feed.active_competitors === 0) {
    return (
      <div className="rounded-xl border border-border bg-card/30 px-6 py-10 text-center">
        <div className="text-2xl mb-2">🕵️</div>
        <p className="text-sm font-medium text-foreground mb-1">
          No competitors tracked yet
        </p>
        <p className="text-xs text-muted-foreground mb-4">
          Add competitors to get threat scores, gap analysis, and daily intel.
        </p>
        <Link
          href="/mission-control/competitors"
          className="text-xs text-primary hover:underline"
        >
          Add your first competitor →
        </Link>
      </div>
    );
  }

  const latestAlert = feed.recent_alerts?.[0];

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Competitor Intelligence
        </h3>
        <Link
          href="/mission-control/competitors"
          className="text-xs text-primary hover:underline"
        >
          Full Dashboard →
        </Link>
      </div>

      {/* ── Stats row ─────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-muted/30 p-3 text-center">
          <div className="text-lg font-bold text-foreground">
            {feed.active_competitors}
          </div>
          <div className="text-[10px] text-muted-foreground mt-0.5">
            Active
          </div>
        </div>
        <div className="rounded-lg bg-muted/30 p-3 text-center">
          <div
            className={`text-lg font-bold ${getThreatStyle(
              Math.round(feed.avg_threat_level)
            )}`}
          >
            {feed.avg_threat_level.toFixed(1)}
            <span className="text-xs text-muted-foreground">/5</span>
          </div>
          <div className="text-[10px] text-muted-foreground mt-0.5">
            Avg Threat
          </div>
        </div>
        <div className="rounded-lg bg-muted/30 p-3 text-center">
          <div
            className={`text-lg font-bold ${
              feed.open_alerts > 0 ? "text-amber-400" : "text-foreground"
            }`}
          >
            {feed.open_alerts}
          </div>
          <div className="text-[10px] text-muted-foreground mt-0.5">
            Open Alerts
          </div>
        </div>
      </div>

      {/* ── Top Threats ──────────────────────────────────── */}
      {topThreats.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            Top Threats
          </h4>
          <div className="space-y-2">
            {topThreats.map(comp => (
              <div
                key={comp.id}
                className="flex items-center gap-3 rounded-lg bg-muted/20 px-3 py-2"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground truncate">
                      {comp.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground shrink-0 capitalize">
                      {comp.platform}
                    </span>
                  </div>
                  <ThreatBar level={comp.threat_level} />
                </div>
                <span
                  className={`text-[10px] font-semibold shrink-0 ${getThreatStyle(
                    comp.threat_level
                  )}`}
                >
                  {getThreatLabel(comp.threat_level)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Latest Alert ─────────────────────────────────── */}
      {latestAlert && (
        <div className="flex items-start gap-2 rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2">
          <span className="text-sm shrink-0 mt-0.5">⚠️</span>
          <div className="flex-1 min-w-0">
            <span className="text-xs text-foreground line-clamp-2">
              <span className="font-medium">{latestAlert.competitor_name}:</span>{" "}
              {latestAlert.detail}
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground shrink-0 whitespace-nowrap">
            {formatRelativeTime(latestAlert.created_at)}
          </span>
        </div>
      )}

      {/* ── Last Scan ────────────────────────────────────── */}
      {feed.latest_analysis_date && (
        <p className="text-[10px] text-muted-foreground text-right">
          Last scan: {formatRelativeTime(feed.latest_analysis_date)}
        </p>
      )}
    </div>
  );
}
