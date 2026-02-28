"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  competitorsApi,
  Competitor,
  CompetitorCreateData,
  PLATFORMS,
  THREAT_LEVELS,
} from "@/lib/api/competitors";
import { MC_SUB_NAV } from "../constants";

const PLATFORM_ICONS: Record<string, string> = {
  linkedin: "in",
  twitter: "X",
  youtube: "YT",
  tiktok: "TT",
  instagram: "IG",
  website: "WEB",
  other: "?",
};

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"active" | "archived">("active");
  const [formData, setFormData] = useState<CompetitorCreateData>({
    name: "",
    platform: "website",
    profile_url: "",
    threat_level: 3,
  });

  const loadCompetitors = useCallback(async () => {
    try {
      const data = await competitorsApi.list({ status: statusFilter });
      setCompetitors(data);
    } catch (e) {
      console.error("Failed to load competitors:", e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadCompetitors();
  }, [loadCompetitors]);

  const handleCreate = async () => {
    if (!formData.name || !formData.profile_url) return;
    try {
      await competitorsApi.create(formData);
      setShowCreate(false);
      setFormData({ name: "", platform: "website", profile_url: "", threat_level: 3 });
      loadCompetitors();
    } catch (e) {
      console.error("Failed to create competitor:", e);
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await competitorsApi.remove(id);
      loadCompetitors();
    } catch (e) {
      console.error("Failed to archive competitor:", e);
    }
  };

  const getThreatColor = (level: number) =>
    THREAT_LEVELS.find((t) => t.value === level)?.color || "text-zinc-400";

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
          <h1 className="text-2xl font-bold">Competitor Intelligence</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track competitors, compare metrics, and find content gaps.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/mission-control/competitors/intelligence"
            className="px-3 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-accent transition"
          >
            Intelligence Feed
          </Link>
          <Link
            href="/mission-control/competitors/gaps"
            className="px-3 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-accent transition"
          >
            Gap Analysis
          </Link>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition"
          >
            + Add Competitor
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="border border-zinc-800 rounded-lg p-4 space-y-3 bg-zinc-900/50">
          <h3 className="text-sm font-semibold">Add New Competitor</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Competitor name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            />
            <input
              type="url"
              placeholder="Profile URL"
              value={formData.profile_url}
              onChange={(e) => setFormData({ ...formData, profile_url: e.target.value })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            />
            <select
              value={formData.platform}
              onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
            <select
              value={formData.threat_level}
              onChange={(e) => setFormData({ ...formData, threat_level: Number(e.target.value) })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            >
              {THREAT_LEVELS.map((t) => (
                <option key={t.value} value={t.value}>{t.label} (Level {t.value})</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Niche (optional)"
              value={formData.niche || ""}
              onChange={(e) => setFormData({ ...formData, niche: e.target.value })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            />
            <input
              type="text"
              placeholder="Positioning (optional)"
              value={formData.positioning || ""}
              onChange={(e) => setFormData({ ...formData, positioning: e.target.value })}
              className="px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleCreate}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90"
            >
              Add Competitor
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        {(["active", "archived"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
              statusFilter === s
                ? "bg-primary/10 text-primary border-primary/30"
                : "text-muted-foreground border-zinc-800 hover:border-zinc-600"
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Competitor Grid */}
      {loading ? (
        <div className="text-center text-muted-foreground py-12">Loading competitors...</div>
      ) : competitors.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-zinc-800 rounded-lg">
          <p className="text-muted-foreground mb-2">No competitors tracked yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="text-primary text-sm hover:underline"
          >
            Add your first competitor
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {competitors.map((comp) => {
            const metrics = comp.latest_metrics;
            return (
              <Link
                key={comp.id}
                href={`/mission-control/competitors/${comp.id}`}
                className="border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition bg-zinc-900/30 group"
              >
                {/* Card header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center text-xs font-bold">
                      {PLATFORM_ICONS[comp.platform] || "?"}
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold group-hover:text-primary transition">
                        {comp.name}
                      </h3>
                      <span className="text-xs text-muted-foreground">{comp.platform}</span>
                    </div>
                  </div>
                  <span className={`text-xs font-medium ${getThreatColor(comp.threat_level)}`}>
                    Threat {comp.threat_level}/5
                  </span>
                </div>

                {/* Positioning */}
                {comp.positioning && (
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                    {comp.positioning}
                  </p>
                )}

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-zinc-800/50 rounded px-2 py-1.5">
                    <span className="text-muted-foreground block">Followers</span>
                    <span className="font-medium">
                      {metrics?.followers?.toLocaleString() ?? "—"}
                    </span>
                  </div>
                  <div className="bg-zinc-800/50 rounded px-2 py-1.5">
                    <span className="text-muted-foreground block">Engagement</span>
                    <span className="font-medium">
                      {metrics?.engagement_rate != null
                        ? `${metrics.engagement_rate.toFixed(1)}%`
                        : "—"}
                    </span>
                  </div>
                </div>

                {/* Niche tag */}
                {comp.niche && (
                  <div className="mt-3">
                    <span className="px-2 py-0.5 bg-zinc-800 text-xs rounded text-muted-foreground">
                      {comp.niche}
                    </span>
                  </div>
                )}

                {/* Archive action */}
                {statusFilter === "active" && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleArchive(comp.id);
                    }}
                    className="mt-3 text-xs text-muted-foreground hover:text-red-400 transition opacity-0 group-hover:opacity-100"
                  >
                    Archive
                  </button>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
