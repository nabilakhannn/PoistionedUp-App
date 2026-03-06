"use client";

/**
 * Dashboard — Slice 108
 * Daily command center. Approvals, pipeline, agent activity, stats.
 */

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { notificationsApi, AgentNotification } from "@/lib/api/notifications";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { hooksApi } from "@/lib/api/hooks";
import { leadsApi } from "@/lib/api/leads";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { usageApi, UsageSummary } from "@/lib/api/usage";
import { researchBriefsApi, ResearchBrief } from "@/lib/api/research-briefs";
import { contentPlanningApi } from "@/lib/api/content-planning";
import { useBrand } from "@/lib/brand-context";
import { GettingStartedChecklist } from "@/components/getting-started-checklist";
import { ContentPlanChat } from "@/components/content-plan-chat";
import { PipelineStatus } from "./components/pipeline-status";
import { ApprovalInbox } from "./components/approval-inbox";
import { QuickStats } from "./components/quick-stats";
import { AgentActivity } from "./components/agent-sidebar";

/* ── Helpers ── */

function todayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

/* ── Types ── */

interface ActivityItem {
  id: string;
  agent_id: string;
  task_type: string;
  summary: string;
  status: string;
  created_at: string;
  brand_id: string | null;
  emoji: string;
}

interface AnalyticsSummary {
  posts: {
    total_generated: number;
    approved: number;
    rejected: number;
    approval_rate: number;
    avg_qa_score: number;
  };
  agents: { tasks_completed: number; tasks_failed: number; by_agent: Record<string, number> };
  rejection_reasons: Record<string, number>;
}

interface Suggestion {
  id: string;
  priority: "urgent" | "high" | "normal";
  trigger_type: string;
  title: string;
  body: string;
  action_url: string;
  cta: string;
}

interface LeadsPulse {
  new_leads: number;
  unreviewed: number;
  active_sequences: number;
}

const PRIORITY_DOT: Record<string, string> = {
  urgent: "bg-red-400 animate-pulse",
  high: "bg-amber-400",
  normal: "bg-blue-400",
};

/* ── Component ── */

export default function DashboardPage() {
  const { currentBrand } = useBrand();

  const [allDeliverables, setAllDeliverables] = useState<Deliverable[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [loading, setLoading] = useState(true);

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [overnight, setOvernight] = useState<ActivityItem[]>([]);
  const [perf, setPerf] = useState<AnalyticsSummary | null>(null);
  const [leadsPulse, setLeadsPulse] = useState<LeadsPulse | null>(null);
  const [priorities, setPriorities] = useState<Suggestion[]>([]);
  const [briefExpanded, setBriefExpanded] = useState(false);

  const [planningOpen, setPlanningOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<{ id: string; itemCount: number } | null>(null);

  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [runningNow, setRunningNow] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [deliverablesRes, notifsRes, pipelineRes, usageRes, overnightRes] = await Promise.all([
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
        notificationsApi.list({ status: "unread", limit: 10 }).catch(() => [] as AgentNotification[]),
        pipelineSettingsApi.get().catch(() => null),
        usageApi.getSummary().catch(() => null),
        agentBridgeApi.getActivityFeed(15).catch(() => ({ items: [], total: 0 })),
      ]);
      setAllDeliverables(deliverablesRes);
      setDeliverables(deliverablesRes.filter((d) => d.status === "review"));
      setNotifications(notifsRes.filter((n) => n.priority === "high" || n.priority === "urgent"));
      setPipelineSettings(pipelineRes);
      setUsage(usageRes);
      setOvernight(overnightRes.items ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!currentBrand?.id) return;
    const id = currentBrand.id;
    researchBriefsApi.getLatest(id).then((res) => setBrief(res.brief)).catch(() => {});
    agentBridgeApi.getAnalyticsSummary(id).then((res) => setPerf(res)).catch(() => {});
    leadsApi.getLeadsPulse(id).then((res) => setLeadsPulse(res)).catch(() => {});
    agentBridgeApi.getProactiveSuggestions(id)
      .then((res) => setPriorities((res.suggestions ?? []).slice(0, 3)))
      .catch(() => {});
  }, [currentBrand?.id]);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000);
    return () => clearInterval(t);
  }, [loadAll]);

  useEffect(() => {
    if (!activePlan) return;
    const poll = setInterval(async () => {
      try {
        const s = await contentPlanningApi.status(activePlan.id);
        if (s.status === "done" || s.status === "failed") {
          setActivePlan(null);
          loadAll();
        }
      } catch { /* keep polling */ }
    }, 15_000);
    return () => clearInterval(poll);
  }, [activePlan, loadAll]);

  /* ── Handlers ── */

  const handleApprove = async (id: string, postContent: string) => {
    setActionLoading(id);
    try {
      await missionControlApi.updateDeliverable(id, "approved", "");
      const openingLine = postContent.split("\n").find((l) => l.trim().length > 10)?.trim();
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

  const handleReject = async (id: string, tag: string, postText: string) => {
    setActionLoading(id);
    try {
      await missionControlApi.updateDeliverable(id, "rejected", tag);
      const excerpt = postText.slice(0, 300).trim();
      await agentBridgeApi.submitReport({
        agent_id: "jumbo",
        report_type: "voice_feedback",
        title: `Rejection: ${tag}`,
        content: `voice_feedback | tag: ${tag} | excerpt: "${excerpt}"`,
        tags: [tag.toLowerCase().replace(/\s+/g, "_")],
        save_to_memory: true,
      });
      setRejectTarget(null);
      await loadAll();
    } catch {
      setRunError("Failed to save rejection. Please try again.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunNow = async () => {
    setRunningNow(true);
    setRunError(null);
    try {
      await pipelineSettingsApi.runNow();
      await loadAll();
    } catch {
      setRunError("Could not trigger pipeline — check your connection and try again.");
      setTimeout(() => setRunError(null), 6000);
    } finally {
      setRunningNow(false);
    }
  };

  const handleToggle = async () => {
    if (!pipelineSettings) return;
    setToggling(true);
    try {
      await pipelineSettingsApi.update({ enabled: !pipelineSettings.enabled });
      await loadAll();
    } catch {
      setRunError("Could not update pipeline — check your connection and try again.");
      setTimeout(() => setRunError(null), 6000);
    } finally {
      setToggling(false);
    }
  };

  /* ── Render ── */

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Good morning!</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{todayLabel()}</p>
        </div>

        {/* Getting Started */}
        <GettingStartedChecklist currentBrand={currentBrand} deliverables={allDeliverables} />

        {/* Pipeline Status */}
        <PipelineStatus
          pipelineSettings={pipelineSettings}
          usage={usage}
          onRunNow={handleRunNow}
          onToggle={handleToggle}
          running={runningNow}
          toggling={toggling}
          runError={runError}
        />

        {/* Plan Content */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
              Plan Content
            </h2>
            {!planningOpen && !activePlan && currentBrand && (
              <button
                onClick={() => setPlanningOpen(true)}
                className="text-xs text-violet-400 hover:text-violet-300 transition-colors font-medium"
              >
                Chat with Jumbo →
              </button>
            )}
          </div>

          {activePlan ? (
            <div className="glass-card ring-amber-500/20 bg-amber-500/5 flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-amber-200/90 font-medium">
                  Jumbo is writing {activePlan.itemCount} post{activePlan.itemCount !== 1 ? "s" : ""} from your plan...
                </p>
                <p className="text-xs text-amber-400/60 mt-0.5">
                  Check approvals in a few minutes
                </p>
              </div>
            </div>
          ) : planningOpen && currentBrand ? (
            <ContentPlanChat
              brandId={currentBrand.id}
              onApproved={(planId, itemCount) => {
                setPlanningOpen(false);
                setActivePlan({ id: planId, itemCount });
              }}
              onClose={() => setPlanningOpen(false)}
            />
          ) : (
            !currentBrand && (
              <div className="glass-card text-center py-4">
                <p className="text-xs text-zinc-500">Select a brand to start planning content.</p>
              </div>
            )
          )}
        </section>

        {/* Approval Inbox */}
        <ApprovalInbox
          deliverables={deliverables}
          notifications={notifications}
          loading={loading}
          expandedIds={expandedIds}
          rejectTarget={rejectTarget}
          actionLoading={actionLoading}
          onToggleExpand={(id) => {
            setExpandedIds((prev) => {
              const next = new Set(prev);
              next.has(id) ? next.delete(id) : next.add(id);
              return next;
            });
          }}
          onApprove={handleApprove}
          onReject={handleReject}
          onSetRejectTarget={setRejectTarget}
          onMarkRead={async (id) => {
            await notificationsApi.markRead(id).catch(() => {});
            setNotifications((prev) => prev.filter((n) => n.id !== id));
          }}
        />

        {/* Today's Priorities */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
            Today&apos;s Priorities
          </h2>
          {priorities.length === 0 ? (
            <div className="glass-card py-5 text-center">
              <p className="text-sm text-zinc-500">Nothing urgent — agents are running.</p>
            </div>
          ) : (
            <div className="rounded-2xl ring-1 ring-white/[0.05] overflow-hidden divide-y divide-white/[0.05]">
              {priorities.map((s, i) => (
                <div key={s.id} className="bg-white/[0.02] px-5 py-3 flex items-start gap-3">
                  <span className="text-xs font-bold text-zinc-600 w-4 shrink-0 pt-0.5">{i + 1}.</span>
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${PRIORITY_DOT[s.priority]}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-zinc-200">{s.title}</p>
                    <p className="text-[11px] text-zinc-500 mt-0.5 line-clamp-2">{s.body}</p>
                  </div>
                  <Link
                    href={s.action_url}
                    className="shrink-0 text-[10px] glass-button px-2 py-1 text-violet-400"
                  >
                    {s.cta} →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Agent Activity */}
        <AgentActivity overnight={overnight} />

        {/* Quick Stats */}
        <QuickStats perf={perf} leadsPulse={leadsPulse} />

        {/* Latest Research */}
        {brief && (
          <section>
            <div className="glass-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
                  Latest Research
                </span>
                <span className="text-[10px] text-zinc-600">
                  Trend Analyzer
                </span>
              </div>
              <p className={`text-sm text-zinc-300 leading-relaxed ${briefExpanded ? "" : "line-clamp-3"}`}>
                {brief.content}
              </p>
              <button
                onClick={() => setBriefExpanded(!briefExpanded)}
                className="mt-2 text-xs text-violet-400 hover:text-violet-300 transition-colors"
              >
                {briefExpanded ? "Collapse" : "View full brief"}
              </button>
            </div>
          </section>
        )}

      </div>
    </div>
  );
}
