"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { contentApi, WorkflowSummary, brandApi, advisorApi, AdvisorSuggestion } from "../../lib/api";
import { useBrand } from "@/lib/brand-context";
import { trackEvent } from "@/lib/posthog";
import { StatusFilter } from "./dashboard-constants";
import { StatCard } from "./components/stat-card";
import { ContentCard } from "./components/content-card";
import { SkeletonCard } from "./components/skeleton-card";

/* ────────────────────────────────────────────────────────
   Main Dashboard
   ──────────────────────────────────────────────────────── */

export default function ContentDashboard() {
  const { brandId, loading: brandLoading } = useBrand();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [brandReady, setBrandReady] = useState<boolean | null>(null);
  const [suggestions, setSuggestions] = useState<AdvisorSuggestion[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (brandLoading) return;
    Promise.all([
      contentApi.list(brandId || undefined),
      brandApi.getCompleteness(brandId || undefined),
    ])
      .then(([wfs, comp]) => {
        setWorkflows(wfs);
        setBrandReady(comp.overall_percent >= 50);
        trackEvent("content_dashboard_viewed", {
          brand_id: brandId || "",
          workflow_count: wfs.length,
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    // Load advisor suggestions (non-blocking)
    advisorApi.getSuggestions(brandId || undefined, 3)
      .then(setSuggestions)
      .catch(() => {}); // Silent fail for suggestions
  }, [brandId, brandLoading]);

  // Filtering logic
  const filteredWorkflows = workflows.filter((wf) => {
    // Status filter
    if (statusFilter === "active" && !["running", "queued", "awaiting_topic", "awaiting_hook", "awaiting_approval"].includes(wf.status)) return false;
    if (statusFilter === "completed" && !["approved", "completed"].includes(wf.status)) return false;
    if (statusFilter === "failed" && !["failed", "rejected"].includes(wf.status)) return false;

    // Search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        wf.goal_text.toLowerCase().includes(q) ||
        wf.platforms.some((p) => p.toLowerCase().includes(q)) ||
        (wf.objective || "").toLowerCase().includes(q) ||
        (wf.content_type || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Stats
  const totalContent = workflows.length;
  const activeContent = workflows.filter((w) => ["running", "queued", "awaiting_topic", "awaiting_hook", "awaiting_approval"].includes(w.status)).length;
  const completedContent = workflows.filter((w) => ["approved", "completed"].includes(w.status)).length;
  const totalCost = workflows.reduce((sum, w) => sum + (w.estimated_cost || 0), 0);

  const STATUS_FILTERS: { id: StatusFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: workflows.length },
    { id: "active", label: "Active", count: activeContent },
    { id: "completed", label: "Completed", count: completedContent },
    { id: "failed", label: "Failed", count: workflows.filter((w) => ["failed", "rejected"].includes(w.status)).length },
  ];

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      {/* ── Header Bar ── */}
      <div className="border-b border-border bg-card/50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
                  <svg className="w-5 h-5 text-primary-foreground" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                  </svg>
                </div>
                <h1 className="text-xl font-bold text-card-foreground tracking-tight">Content</h1>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Content Studio button */}
              <Link
                href="/content/chat"
                className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-primary to-primary/90 text-primary-foreground rounded-xl text-xs font-semibold hover:from-primary/90 hover:to-primary/80 transition shadow-lg shadow-primary/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                Content Studio
              </Link>

              {/* Automation Pipeline button */}
              {brandReady !== false && (
                <Link
                  href="/content/new"
                  className="flex items-center gap-2 px-4 py-2.5 bg-accent border border-border text-foreground rounded-xl text-xs font-semibold hover:bg-accent hover:border-border transition"
                >
                  <svg className="w-4 h-4 text-chart-2" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                  + New Pipeline
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* ── Brand Gate Warning ── */}
        {brandReady === false && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 mb-6 flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <div>
              <p className="text-yellow-300 text-sm font-semibold">Brand profile incomplete</p>
              <p className="text-yellow-400/70 text-xs mt-0.5">
                Complete at least 50% of your brand profile before creating content. The AI needs your brand foundation, audience, and offer info to write well.
              </p>
              <Link
                href={brandId ? `/brands/${brandId}` : "/brands"}
                className="inline-flex items-center gap-1 mt-2 text-xs text-yellow-400 font-medium hover:text-yellow-300 transition"
              >
                Go to Brand Builder
                <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ── Stats Row ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Total Content"
            value={totalContent}
            color="bg-primary/15"
            icon={<svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>}
          />
          <StatCard
            label="In Progress"
            value={activeContent}
            color="bg-amber-500/15"
            icon={<svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            label="Completed"
            value={completedContent}
            color="bg-green-500/15"
            icon={<svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            label="Total Cost"
            value={`$${totalCost < 0.01 ? totalCost.toFixed(4) : totalCost.toFixed(2)}`}
            color="bg-emerald-500/15"
            icon={<svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
        </div>

        {/* ── Advisor Suggestions ── */}
        {suggestions.length > 0 && (
          <div className="mb-6">
            <div className="grid gap-3 sm:grid-cols-3">
              {suggestions.slice(0, 3).map((s, i) => {
                const priorityColors: Record<string, string> = {
                  high: "border-l-red-500",
                  medium: "border-l-yellow-500",
                  low: "border-l-primary",
                };
                const categoryIcons: Record<string, string> = {
                  performance: "📊",
                  content: "✍️",
                  experiment: "🧪",
                  voice: "🎙",
                  schedule: "📅",
                };
                const actionPaths: Record<string, string> = {
                  create_content: "/content/new",
                  run_experiment: "/experiments",
                  review_performance: "/performance",
                  update_schedule: "/schedule",
                  analyze_voice: "/experiments",
                  review_memory: "/memory",
                };
                const href = actionPaths[s.action_type] || "#";
                return (
                  <Link
                    key={i}
                    href={href}
                    onClick={() => trackEvent("advisor_suggestion_clicked", {
                      category: s.category,
                      action_type: s.action_type,
                      priority: s.priority,
                      brand_id: brandId || "",
                    })}
                    className={`block bg-card border border-border border-l-4 ${priorityColors[s.priority] || "border-l-border"} rounded-xl p-4 hover:border-border transition`}
                  >
                    <div className="flex items-start gap-2 mb-1">
                      <span className="text-sm">{categoryIcons[s.category] || "💡"}</span>
                      <h4 className="text-xs font-semibold text-foreground leading-tight">{s.title}</h4>
                    </div>
                    <p className="text-[11px] text-muted-foreground ml-6 leading-relaxed line-clamp-2">{s.body}</p>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Filter Bar ── */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-1 bg-card/80 border border-border rounded-xl p-1">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === f.id
                    ? "bg-accent text-card-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                {f.label}
                <span className={`text-[10px] ${statusFilter === f.id ? "text-muted-foreground" : "text-muted-foreground"}`}>
                  {f.count}
                </span>
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search content..."
              className="bg-card border border-border rounded-xl pl-9 pr-4 py-2 text-xs text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/50 w-48 transition"
            />
          </div>
        </div>

        {/* ── Content Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : filteredWorkflows.length === 0 && workflows.length > 0 ? (
          <div className="text-center py-16">
            <svg className="mx-auto h-10 w-10 text-muted-foreground mb-3" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <h3 className="text-sm font-medium text-muted-foreground mb-1">No matching content</h3>
            <p className="text-muted-foreground text-xs">Try adjusting your filters or search query.</p>
          </div>
        ) : workflows.length === 0 ? (
          <div className="text-center py-20 border-2 border-dashed border-border rounded-2xl bg-card/30">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
              <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-card-foreground mb-2">Start creating content</h2>
            <p className="text-muted-foreground text-sm max-w-md mx-auto mb-6">
              Use Content Studio for chat-based creation, or launch the Automation Pipeline for the full 8-step AI workflow.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link
                href="/content/chat"
                className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 transition"
              >
                Open Content Studio
              </Link>
              {brandReady !== false && (
                <Link
                  href="/content/new"
                  className="px-5 py-2.5 bg-accent text-foreground rounded-xl text-sm font-medium hover:bg-accent transition"
                >
                  + New Pipeline
                </Link>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredWorkflows.map((wf) => (
              <ContentCard key={wf.id} wf={wf} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
