"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { scheduleApi, ScheduledItem } from "@/lib/api/schedule";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { orchestratorApi, OrchestratorStatus } from "@/lib/api/orchestrator";
import { MC_SUB_NAV } from "../constants";
import { QuickCapture } from "../components/quick-capture";

// ── Pipeline stages derived from deliverable + task statuses ──────

interface PipelineStage {
  label: string;
  count: number;
  color: string;
}

type ContentFilter = "draft" | "scheduled" | "published";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const PLATFORM_COLORS: Record<string, string> = {
  linkedin: "bg-blue-500/20 text-blue-400",
  twitter: "bg-sky-500/20 text-sky-400",
  instagram: "bg-pink-500/20 text-pink-400",
  youtube: "bg-red-500/20 text-red-400",
  tiktok: "bg-purple-500/20 text-purple-400",
  carousel: "bg-amber-500/20 text-amber-400",
  ad: "bg-orange-500/20 text-orange-400",
};

// Example trending topics — populated from last Trend Analyzer run if available
const FALLBACK_TRENDS = [
  "AI hooks that stop the scroll",
  "Founder burnout — the silent epidemic",
  "Why consistency beats talent",
];

export default function ContentPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<ContentFilter>("draft");
  const [items, setItems] = useState<ScheduledItem[]>([]);
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([]);
  const [trendingTopics, setTrendingTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    try {
      const [boardRes, deliverablesRes, statusRes] = await Promise.all([
        scheduleApi.getBoard().catch(() => ({ draft: [], scheduled: [], published: [], archived: [] })),
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
        orchestratorApi.status().catch(() => null as OrchestratorStatus | null),
      ]);

      setItems([...boardRes.draft, ...boardRes.scheduled, ...boardRes.published]);

      // Build pipeline stage counts from deliverables + active tasks
      const researching = statusRes?.active_tasks?.filter(
        (t: Record<string, unknown>) => String(t.status || "") === "assigned" || String(t.tags || "").includes("research")
      ).length ?? 0;
      const writing = deliverablesRes.filter((d) => d.status === "draft").length;
      const qa = deliverablesRes.filter((d) => d.status === "review").length;
      const ready = deliverablesRes.filter((d) => d.status === "approved").length;

      setPipelineStages([
        { label: "Researching", count: researching, color: "bg-blue-500" },
        { label: "Writing", count: writing, color: "bg-amber-500" },
        { label: "QA", count: qa, color: "bg-purple-500" },
        { label: "Ready", count: ready, color: "bg-green-500" },
      ]);

      // Try to get trending topics from last trend-analyzer deliverable
      const trendDeliverable = deliverablesRes.find(
        (d) => d.deliverable_type === "report" && d.content?.toLowerCase().includes("trend")
      );
      if (trendDeliverable?.content) {
        // Extract lines that look like topics
        const lines = trendDeliverable.content
          .split("\n")
          .map((l) => l.replace(/^[\d\.\-\*\s]+/, "").trim())
          .filter((l) => l.length > 10 && l.length < 80)
          .slice(0, 3);
        setTrendingTopics(lines.length >= 2 ? lines : FALLBACK_TRENDS);
      } else {
        setTrendingTopics(FALLBACK_TRENDS);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000);
    return () => clearInterval(t);
  }, [loadAll]);

  const filtered = items.filter((item) => item.status === filter);
  const totalPipeline = pipelineStages.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="min-h-screen bg-background">
      {/* Sub-nav */}
      <div className="h-12 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/content"
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      <div className="max-w-3xl mx-auto px-5 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-foreground">Content</h1>
          <Link
            href="/composer"
            className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium hover:bg-amber-500/20 transition"
          >
            + Write post
          </Link>
        </div>

        {/* ── PIPELINE STATUS ───────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Pipeline status
            </h2>
            {totalPipeline > 0 && (
              <span className="text-xs text-muted-foreground">{totalPipeline} items in progress</span>
            )}
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            {loading ? (
              <div className="text-xs text-muted-foreground">Loading...</div>
            ) : (
              <div className="flex items-stretch gap-0">
                {pipelineStages.map((stage, i) => (
                  <div key={stage.label} className="flex-1 text-center">
                    <div className="flex items-center justify-center gap-1 mb-2">
                      <div
                        className={`w-2 h-2 rounded-full ${stage.color}`}
                      />
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                        {stage.label}
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-foreground">{stage.count}</div>
                    {i < pipelineStages.length - 1 && (
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 text-muted-foreground/30 hidden" />
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Flow bar */}
            {!loading && totalPipeline > 0 && (
              <div className="flex rounded-full overflow-hidden h-1.5 mt-4 gap-0.5">
                {pipelineStages.map((stage) =>
                  stage.count > 0 ? (
                    <div
                      key={stage.label}
                      className={`${stage.color} transition-all`}
                      style={{ flex: stage.count }}
                    />
                  ) : null
                )}
              </div>
            )}
          </div>
        </section>

        {/* ── TRENDING THIS WEEK ───────────────────── */}
        <section>
          <div className="mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Trending this week
            </h2>
            <p className="text-[10px] text-muted-foreground mt-0.5">From your last Trend Analyzer run</p>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
            {trendingTopics.map((topic, i) => (
              <div key={i} className="px-4 py-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-xs font-bold text-muted-foreground shrink-0">{i + 1}</span>
                  <span className="text-sm text-foreground truncate">{topic}</span>
                </div>
                <button
                  onClick={() => router.push(`/composer?topic=${encodeURIComponent(topic)}`)}
                  className="text-xs text-amber-400 hover:text-amber-300 shrink-0 transition"
                >
                  Create post →
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* ── CONTENT QUEUE ───────────────────────── */}
        <section>
          <div className="mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Content queue
            </h2>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 mb-3">
            {(["draft", "scheduled", "published"] as ContentFilter[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition capitalize ${
                  filter === tab
                    ? "bg-primary/15 text-primary border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                {tab}
                <span className="ml-1.5 text-[10px] opacity-70">
                  ({items.filter((it) => it.status === tab).length})
                </span>
              </button>
            ))}
          </div>

          {loading ? (
            <div className="text-xs text-muted-foreground">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="rounded-xl border border-border bg-card/30 px-5 py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No {filter} content yet.{" "}
                {filter === "draft" && (
                  <Link href="/composer" className="text-amber-400 hover:text-amber-300">
                    Write something →
                  </Link>
                )}
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
              {filtered.map((item) => (
                <div key={item.id} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase ${
                          PLATFORM_COLORS[item.platform] || "bg-muted text-muted-foreground"
                        }`}
                      >
                        {item.platform}
                      </span>
                      <span className="text-sm text-foreground truncate">{item.title}</span>
                    </div>
                    <div className="text-[10px] text-muted-foreground ml-0">
                      {item.scheduled_at
                        ? `Scheduled ${new Date(item.scheduled_at).toLocaleDateString()}`
                        : item.published_at
                        ? `Published ${timeAgo(item.published_at)}`
                        : `Created ${timeAgo(item.created_at)}`}
                    </div>
                  </div>
                  <Link
                    href={`/composer?item=${item.id}`}
                    className="text-xs text-muted-foreground hover:text-foreground shrink-0 transition"
                  >
                    Edit →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <QuickCapture />
    </div>
  );
}
