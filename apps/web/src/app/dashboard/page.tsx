"use client";

/**
 * Dashboard — Slice 110 rewrite
 * AI Agents Hub: 24 workflows + right sidebar (approvals / pipeline / stats).
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { marketplaceApi, RegistryResponse } from "@/lib/api/marketplace";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { usageApi, UsageSummary } from "@/lib/api/usage";
import { hooksApi } from "@/lib/api/hooks";
import { useBrand } from "@/lib/brand-context";
import { GettingStartedChecklist } from "@/components/getting-started-checklist";
import { WorkflowCard } from "@/components/workflow-card";

/* ── Constants ── */

const QUICK_CHIPS = [
  { label: "30 Hooks",         href: "/content/hooks" },
  { label: "Nurture Sequence", href: "/content/agents/email-sequence-writer" },
  { label: "Offer Outline",    href: "/content/agents/offer-creation" },
  { label: "Content Calendar", href: "/content/agents/content-calendar-gen" },
] as const;

const CATEGORY_ICONS: Record<string, string> = {
  rocket:
    "M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z",
  pencil:
    "m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10",
  users:
    "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
  envelope:
    "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
  lightbulb:
    "M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
};

function timeUntil(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return "now";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  return hours < 24 ? `${hours}h ${mins % 60}m` : `${Math.floor(hours / 24)}d`;
}

/* ── Component ── */

export default function DashboardPage() {
  const router = useRouter();
  const { currentBrand } = useBrand();

  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [usageMap, setUsageMap] = useState<Record<string, number>>({});
  const [allDeliverables, setAllDeliverables] = useState<Deliverable[]>([]);
  const [pendingDeliverables, setPendingDeliverables] = useState<Deliverable[]>([]);
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const [promptValue, setPromptValue] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [runningNow, setRunningNow] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    const brandId = currentBrand?.id;
    if (!brandId) {
      setLoading(false);
      return;
    }

    const [regRes, histRes, delRes, pipeRes, usageRes] = await Promise.allSettled([
      marketplaceApi.getRegistry(),
      marketplaceApi.getHistory(brandId, undefined, 200),
      missionControlApi.listDeliverables({ brand_id: brandId }),
      pipelineSettingsApi.get(),
      usageApi.getSummary(),
    ]);

    if (regRes.status === "fulfilled") setRegistry(regRes.value);

    if (histRes.status === "fulfilled") {
      const map: Record<string, number> = {};
      histRes.value.runs.forEach((r) => {
        map[r.workflow_slug] = (map[r.workflow_slug] ?? 0) + 1;
      });
      setUsageMap(map);
    }

    if (delRes.status === "fulfilled") {
      setAllDeliverables(delRes.value);
      setPendingDeliverables(delRes.value.filter((d) => d.status === "review").slice(0, 4));
    }

    if (pipeRes.status === "fulfilled") setPipelineSettings(pipeRes.value);
    if (usageRes.status === "fulfilled") setUsage(usageRes.value);

    setLoading(false);
  }, [currentBrand?.id]);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30_000);
    return () => clearInterval(t);
  }, [loadAll]);

  /* ── Handlers ── */

  const handlePrompt = () => {
    const q = promptValue.trim();
    if (q) router.push(`/intelligence?q=${encodeURIComponent(q)}`);
  };

  const handleApprove = async (id: string, content: string) => {
    setActionLoading(id);
    try {
      await missionControlApi.updateDeliverable(id, "approved", "", "linkedin");
      const openingLine = content.split("\n").find((l) => l.trim().length > 10)?.trim();
      if (openingLine && currentBrand?.id) {
        hooksApi.create({
          brand_id: currentBrand.id,
          hook_text: openingLine.slice(0, 300),
          hook_type: "custom",
          source: "pipeline_approved",
        }).catch(() => {});
      }
      await loadAll();
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggle = async () => {
    if (!pipelineSettings) return;
    setToggling(true);
    try {
      await pipelineSettingsApi.update({ enabled: !pipelineSettings.enabled });
      await loadAll();
    } catch {
      setRunError("Could not update pipeline — check your connection.");
      setTimeout(() => setRunError(null), 6000);
    } finally {
      setToggling(false);
    }
  };

  const handleRunNow = async () => {
    setRunningNow(true);
    setRunError(null);
    try {
      await pipelineSettingsApi.runNow();
      await loadAll();
    } catch {
      setRunError("Could not trigger pipeline — check your connection.");
      setTimeout(() => setRunError(null), 6000);
    } finally {
      setRunningNow(false);
    }
  };

  /* ── Derived ── */

  const sortedCategories = registry
    ? Object.entries(registry.categories).sort(([, a], [, b]) => a.order - b.order)
    : [];

  const activeCount = registry
    ? Object.values(registry.workflows).filter((w) => w.status === "active").length
    : 0;

  /* ── No brand guard ── */

  if (!loading && !currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center px-5">
        <div className="glass-card text-center py-10 max-w-sm mx-auto">
          <p className="text-sm text-zinc-400 mb-4">Select a brand to see your AI workflows.</p>
          <Link href="/brand" className="glass-button text-xs px-4 py-2">
            Create your first brand →
          </Link>
        </div>
      </div>
    );
  }

  /* ── Render ── */

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-5 py-8">

        {/* Getting Started (collapsible — auto-hides at ≥5/6 steps) */}
        <GettingStartedChecklist currentBrand={currentBrand} deliverables={allDeliverables} />

        {/* 2-column layout */}
        <div className="flex flex-col md:flex-row gap-6 mt-2">

          {/* ── LEFT MAIN ── */}
          <div className="flex-1 min-w-0 space-y-8">

            {/* Hero */}
            <div>
              <h1 className="text-2xl font-bold text-zinc-100">AI Agents Dashboard</h1>
              <p className="text-sm text-zinc-400 mt-1">
                Manage and monitor your AI-powered automation agents.
              </p>
              <div className="flex items-center gap-3 mt-3 flex-wrap">
                {currentBrand && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/[0.08] text-xs text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    {currentBrand.name}
                  </span>
                )}
                {!loading && registry && (
                  <span className="text-xs text-zinc-600">{activeCount} workflows available</span>
                )}
              </div>
            </div>

            {/* Jumbo Prompt Bar */}
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  value={promptValue}
                  onChange={(e) => setPromptValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handlePrompt(); }}
                  placeholder="What would you like to build today?"
                  className="flex-1 rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                />
                <button
                  onClick={handlePrompt}
                  className="glass-button px-4 py-2.5 rounded-xl text-sm text-zinc-300 hover:text-violet-400"
                >
                  →
                </button>
              </div>
              <div className="flex gap-2 flex-wrap">
                {QUICK_CHIPS.map((chip) => (
                  <Link
                    key={chip.label}
                    href={chip.href}
                    className="px-3 py-1.5 rounded-lg text-xs glass-button text-zinc-400 hover:text-zinc-200"
                  >
                    {chip.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* Workflow Sections */}
            {loading ? (
              <div className="space-y-6">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="space-y-3">
                    <div className="h-3 w-32 rounded bg-white/[0.05] animate-pulse" />
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {[0, 1, 2].map((j) => (
                        <div key={j} className="h-36 rounded-2xl bg-white/[0.03] animate-pulse" />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : registry ? (
              <div className="space-y-8">
                {sortedCategories.map(([catKey, cat]) => {
                  const workflows = Object.values(registry.workflows).filter(
                    (w) => w.category === catKey,
                  );
                  if (workflows.length === 0) return null;
                  const iconPath = CATEGORY_ICONS[cat.icon] ?? CATEGORY_ICONS.lightbulb;
                  return (
                    <section key={catKey}>
                      <div className="flex items-center gap-2.5 mb-3">
                        <svg className="w-3.5 h-3.5 text-zinc-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
                        </svg>
                        <h2 className="text-xs font-semibold text-zinc-400">{cat.name}</h2>
                        <span className="text-[10px] text-zinc-700">{workflows.length} workflows</span>
                        <div className="flex-1 h-px bg-white/[0.04]" />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {workflows.map((w) => (
                          <WorkflowCard
                            key={w.slug}
                            workflow={w}
                            usageCount={usageMap[w.slug] ?? 0}
                            href={`/content/agents/${w.slug}`}
                          />
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            ) : (
              <div className="glass-card text-center py-8">
                <p className="text-sm text-zinc-500">Could not load workflows. Try refreshing.</p>
              </div>
            )}
          </div>

          {/* ── RIGHT SIDEBAR ── */}
          <div className="w-full md:w-72 shrink-0 space-y-4 md:sticky md:top-8 self-start">

            {/* Widget 1: Pending Approvals */}
            <div className="glass-card space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                  Pending Approvals
                </h3>
                {pendingDeliverables.length > 0 && (
                  <span className="glass-badge-accent text-[10px]">{pendingDeliverables.length}</span>
                )}
              </div>

              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-8 rounded-xl bg-white/[0.03] animate-pulse" />
                  ))}
                </div>
              ) : pendingDeliverables.length === 0 ? (
                <p className="text-xs text-green-400">All caught up ✓</p>
              ) : (
                <div className="space-y-2">
                  {pendingDeliverables.map((d) => (
                    <div key={d.id} className="flex items-center gap-2">
                      <p className="text-xs text-zinc-300 flex-1 truncate line-clamp-1">{d.title}</p>
                      <button
                        onClick={() => handleApprove(d.id, d.content ?? "")}
                        disabled={actionLoading === d.id}
                        className="shrink-0 text-[10px] px-2 py-1 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-colors disabled:opacity-40"
                      >
                        {actionLoading === d.id ? "..." : "Approve"}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <Link
                href="/deliverables"
                className="block text-[10px] text-violet-400 hover:text-violet-300 transition-colors"
              >
                Review all →
              </Link>
            </div>

            {/* Widget 2: Pipeline Status */}
            <div className="glass-card space-y-3">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                Pipeline
              </h3>
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={handleToggle}
                  disabled={toggling || pipelineSettings === null}
                  className="flex items-center gap-1.5 group"
                >
                  <span
                    className={`w-2 h-2 rounded-full transition-colors ${
                      pipelineSettings?.enabled ? "bg-emerald-400 animate-pulse" : "bg-zinc-600"
                    }`}
                  />
                  <span className="text-xs text-zinc-300 group-hover:text-violet-400 transition-colors">
                    {toggling ? "..." : pipelineSettings?.enabled ? "ON" : "OFF"}
                  </span>
                </button>
                {pipelineSettings?.enabled && pipelineSettings.next_run_at && (
                  <span className="text-[10px] text-zinc-600">
                    · Next: {timeUntil(pipelineSettings.next_run_at)}
                  </span>
                )}
                <button
                  onClick={handleRunNow}
                  disabled={runningNow || pipelineSettings?.run_now === true}
                  className="ml-auto glass-button text-[10px] px-2.5 py-1 text-violet-400 disabled:opacity-40"
                >
                  {runningNow || pipelineSettings?.run_now ? "Starting..." : "Run Now"}
                </button>
              </div>
              {runError && (
                <p className="text-[10px] text-red-400">{runError}</p>
              )}
            </div>

            {/* Widget 3: This Week */}
            <div className="glass-card space-y-3">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                This Week
              </h3>
              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-5 rounded bg-white/[0.03] animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="divide-y divide-white/[0.04] text-xs">
                  <div className="flex justify-between py-1.5">
                    <span className="text-zinc-500">Workflows run</span>
                    <span className="text-zinc-200 font-medium tabular-nums">
                      {usage?.daily_workflows_used ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-zinc-500">Posts generated</span>
                    <span className="text-zinc-200 font-medium tabular-nums">
                      {allDeliverables.length}
                    </span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-zinc-500">Budget used</span>
                    <span className="text-zinc-200 font-medium tabular-nums">
                      ${(usage?.period_costs?.weekly ?? 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
