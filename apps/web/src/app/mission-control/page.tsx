"use client";

/**
 * Mission Control Home — Slice 103 (Morning Briefing)
 * Single screen: what happened, what needs you now, what to do today.
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
import { MC_SUB_NAV } from "./constants";
import { QuickCapture } from "./components/quick-capture";
import { ContentPlanChat } from "@/components/content-plan-chat";
import { GettingStartedChecklist } from "@/components/getting-started-checklist";

// ── Helpers ────────────────────────────────────────────────

function todayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function timeUntil(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return "now";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  return `${Math.floor(hours / 24)}d`;
}

const REJECT_TAGS = ["Wrong voice", "Bad hook", "Needs research", "Off-topic"] as const;
type RejectTag = typeof REJECT_TAGS[number];

// ── Status Bar ──────────────────────────────────────────────

function StatusBar({
  pipelineSettings,
  usage,
  onRunNow,
  onToggle,
  running,
  toggling,
  runError,
}: {
  pipelineSettings: PipelineSettings | null;
  usage: UsageSummary | null;
  onRunNow: () => void;
  onToggle: () => void;
  running: boolean;
  toggling: boolean;
  runError: string | null;
}) {
  const monthlyBudget = pipelineSettings?.monthly_budget_usd ?? 20;
  const monthlySpend = usage?.period_costs?.monthly ?? 0;
  const budgetPct = monthlyBudget > 0 ? Math.min(100, (monthlySpend / monthlyBudget) * 100) : 0;
  const enabled = pipelineSettings?.enabled ?? false;

  return (
    <div className="rounded-xl border border-border bg-card/50 px-4 py-3 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={onToggle}
            disabled={toggling || pipelineSettings === null}
            className="flex items-center gap-1.5 group"
            title={enabled ? "Click to turn pipeline OFF" : "Click to turn pipeline ON"}
          >
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                enabled ? "bg-green-400 animate-pulse" : "bg-zinc-400"
              } group-hover:opacity-70`}
            />
            <span className="text-xs font-medium text-foreground group-hover:text-primary transition-colors">
              Pipeline: {toggling ? "..." : enabled ? "ON" : "OFF"}
            </span>
          </button>
          {enabled && pipelineSettings?.next_run_at && (
            <span className="text-xs text-muted-foreground">
              · Next run in {timeUntil(pipelineSettings.next_run_at)}
            </span>
          )}
          <button
            onClick={onRunNow}
            disabled={running || pipelineSettings?.run_now === true}
            className="text-xs px-2.5 py-1 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 disabled:opacity-50 transition"
          >
            {running || pipelineSettings?.run_now ? "Starting..." : "▶ Run Now"}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            ${monthlySpend.toFixed(2)} of ${monthlyBudget.toFixed(2)}/mo
          </span>
          <div className="w-20 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                budgetPct >= 80 ? "bg-red-400" : budgetPct >= 50 ? "bg-amber-400" : "bg-green-400"
              }`}
              style={{ width: `${budgetPct}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground">{Math.round(budgetPct)}%</span>
          <Link
            href="/mission-control/settings"
            className="text-xs text-muted-foreground/60 hover:text-foreground transition"
          >
            Edit
          </Link>
        </div>
      </div>

      {runError && (
        <p className="text-xs text-red-400 border-t border-border/50 pt-2">{runError}</p>
      )}
    </div>
  );
}

// ── Types ───────────────────────────────────────────────────

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

// ── Component ──────────────────────────────────────────────

export default function MissionControlHome() {
  const { currentBrand } = useBrand();

  // Core state
  const [allDeliverables, setAllDeliverables] = useState<Deliverable[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [loading, setLoading] = useState(true);

  // Morning Briefing state
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [overnight, setOvernight] = useState<ActivityItem[]>([]);
  const [perf, setPerf] = useState<AnalyticsSummary | null>(null);
  const [leadsPulse, setLeadsPulse] = useState<LeadsPulse | null>(null);
  const [priorities, setPriorities] = useState<Suggestion[]>([]);

  // Research brief expand/collapse
  const [briefExpanded, setBriefExpanded] = useState(false);

  // Content planning state
  const [planningOpen, setPlanningOpen] = useState(false);
  const [activePlan, setActivePlan] = useState<{ id: string; itemCount: number } | null>(null);

  // Action state
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

  // Brand-specific data: brief, analytics, leads pulse, priorities
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

  // Poll active content plan status every 15s until done/failed
  useEffect(() => {
    if (!activePlan) return;
    const poll = setInterval(async () => {
      try {
        const s = await contentPlanningApi.status(activePlan.id);
        if (s.status === "done" || s.status === "failed") {
          setActivePlan(null);
          loadAll();
        }
      } catch {
        // silent — keep polling
      }
    }, 15_000);
    return () => clearInterval(poll);
  }, [activePlan, loadAll]);

  // ── Handlers ─────────────────────────────────────────────

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

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
    } catch (e) {
      console.error("Approve error:", e);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string, tag: RejectTag, postText: string) => {
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
    } catch (e) {
      console.error("Reject error:", e);
      setRunError("Failed to save rejection. Please try again.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkRead = async (id: string) => {
    await notificationsApi.markRead(id).catch(() => {});
    setNotifications((prev) => prev.filter((n) => n.id !== id));
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

  // ── Derived ───────────────────────────────────────────────

  const approvalCount = deliverables.length + notifications.length;

  // Group overnight activity by agent
  const overnightByAgent = overnight.reduce<Record<string, ActivityItem[]>>((acc, item) => {
    const key = item.agent_id ?? "unknown";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  // Top rejection reason
  const topRejectionReason = perf?.rejection_reasons
    ? Object.entries(perf.rejection_reasons).sort((a, b) => b[1] - a[1])[0]?.[0]
    : null;

  const PRIORITY_DOT: Record<string, string> = {
    urgent: "bg-red-400 animate-pulse",
    high: "bg-amber-400",
    normal: "bg-blue-400",
  };

  // ── Render ────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-background">
      {/* Sub-nav */}
      <div className="h-12 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control"
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      <div className="max-w-4xl mx-auto px-5 py-6 space-y-6">

        {/* ── HEADER ─────────────────────────────────────── */}
        <div>
          <h1 className="text-xl font-bold text-foreground">Good morning!</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{todayLabel()}</p>
        </div>

        {/* ── GETTING STARTED ──────────────────────────────── */}
        <GettingStartedChecklist
          currentBrand={currentBrand}
          deliverables={allDeliverables}
        />

        {/* ── STATUS BAR ─────────────────────────────────── */}
        <StatusBar
          pipelineSettings={pipelineSettings}
          usage={usage}
          onRunNow={handleRunNow}
          onToggle={handleToggle}
          running={runningNow}
          toggling={toggling}
          runError={runError}
        />

        {/* ── 📋 PLAN CONTENT ────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              📋 Plan Content
            </h2>
            {!planningOpen && !activePlan && currentBrand && (
              <button
                onClick={() => setPlanningOpen(true)}
                className="text-xs text-primary hover:text-primary/80 transition font-medium"
              >
                Chat with Jumbo →
              </button>
            )}
          </div>

          {activePlan ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-amber-200/90 font-medium">
                  Jumbo is writing {activePlan.itemCount} post{activePlan.itemCount !== 1 ? "s" : ""} from your plan...
                </p>
                <p className="text-xs text-amber-400/60 mt-0.5">
                  Check Needs Approval in a few minutes
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
              <div className="rounded-xl border border-border bg-card/30 px-4 py-3 text-center">
                <p className="text-xs text-muted-foreground">Select a brand to start planning content.</p>
              </div>
            )
          )}
        </section>

        {/* ── ⚡ NEEDS YOUR APPROVAL ──────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              ⚡ Needs Your Approval
            </h2>
            {approvalCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold">
                {approvalCount}
              </span>
            )}
          </div>

          {loading ? (
            <div className="text-xs text-muted-foreground">Loading...</div>
          ) : approvalCount === 0 ? (
            <div className="rounded-xl border border-border bg-card/30 px-5 py-6 text-center">
              <div className="text-2xl mb-2">✅</div>
              <p className="text-sm text-muted-foreground">All caught up — nothing needs review.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
              {deliverables.map((d) => {
                const isExpanded = expandedIds.has(d.id);
                const preview = (d.content ?? "").slice(0, 120).trim();
                return (
                  <div key={d.id} className="px-4 py-3 space-y-2">
                    {/* Title row */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-sm shrink-0">✍️</span>
                        <span className="text-sm font-medium text-foreground truncate">{d.title}</span>
                        {d.qa_score !== undefined && d.qa_score > 0 && (
                          <span className="text-[10px] shrink-0 px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 font-mono">
                            QA {d.qa_score}
                          </span>
                        )}
                        <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(d.created_at)}</span>
                      </div>

                      {rejectTarget === d.id ? (
                        <div className="flex flex-wrap gap-1 shrink-0">
                          {REJECT_TAGS.map((tag) => (
                            <button
                              key={tag}
                              onClick={() => handleReject(d.id, tag, d.content ?? "")}
                              disabled={actionLoading === d.id}
                              className="px-2 py-1 text-[10px] rounded bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition"
                            >
                              {tag}
                            </button>
                          ))}
                          <button
                            onClick={() => setRejectTarget(null)}
                            className="px-2 py-1 text-[10px] rounded border border-border text-muted-foreground hover:text-foreground transition"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            onClick={() => setRejectTarget(d.id)}
                            disabled={actionLoading === d.id}
                            className="px-2.5 py-1.5 text-xs rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-red-500/40 transition"
                          >
                            Reject
                          </button>
                          <button
                            onClick={() => handleApprove(d.id, d.content ?? "")}
                            disabled={actionLoading === d.id}
                            className="px-2.5 py-1.5 text-xs rounded-lg bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30 font-medium transition"
                          >
                            {actionLoading === d.id ? "..." : "Approve ✓"}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Preview + expand */}
                    {d.content && (
                      <div className="ml-6">
                        {isExpanded ? (
                          <div className="space-y-2">
                            <p className="text-xs text-foreground/90 leading-relaxed whitespace-pre-wrap bg-card/60 border border-border/50 rounded-lg px-3 py-2">
                              {d.content}
                            </p>
                            <button
                              onClick={() => toggleExpand(d.id)}
                              className="text-[10px] text-muted-foreground hover:text-foreground transition"
                            >
                              ▲ Collapse
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <p className="text-xs text-muted-foreground truncate flex-1">{preview}</p>
                            {(d.content ?? "").length > 120 && (
                              <button
                                onClick={() => toggleExpand(d.id)}
                                className="text-[10px] text-primary hover:text-primary/80 shrink-0 transition"
                              >
                                ▼ Show post
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {notifications.map((n) => (
                <div key={n.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm">{n.priority === "urgent" ? "🚨" : "🔔"}</span>
                        <span className="text-sm font-medium text-foreground truncate">{n.title}</span>
                        <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(n.created_at)}</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate ml-6">{n.body}</p>
                    </div>
                    <button
                      onClick={() => handleMarkRead(n.id)}
                      className="px-2.5 py-1.5 text-xs rounded-lg border border-border text-muted-foreground hover:text-foreground transition shrink-0"
                    >
                      Read
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── 📋 TODAY'S 3 PRIORITIES ─────────────────────── */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            📋 Today&apos;s Priorities
          </h2>
          {priorities.length === 0 ? (
            <div className="rounded-xl border border-border bg-card/30 px-4 py-4 flex items-center gap-3">
              <span className="text-lg">✅</span>
              <p className="text-sm text-muted-foreground">Nothing urgent — agents are running.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card/50 divide-y divide-border/50 overflow-hidden">
              {priorities.map((s, i) => (
                <div key={s.id} className="px-4 py-3 flex items-start gap-3">
                  <span className="text-xs font-bold text-muted-foreground w-4 shrink-0 pt-0.5">{i + 1}.</span>
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${PRIORITY_DOT[s.priority]}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-foreground leading-tight">{s.title}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed line-clamp-2">{s.body}</p>
                  </div>
                  <Link
                    href={s.action_url}
                    className="shrink-0 text-[10px] px-2 py-1 rounded-lg bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition font-medium"
                  >
                    {s.cta} →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── 🤖 WHAT HAPPENED OVERNIGHT ──────────────────── */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            🤖 What Happened Overnight
          </h2>
          <div className="rounded-xl border border-border bg-card/50 px-4 py-3">
            {overnight.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No activity yet today · Pipeline runs every 2h
              </p>
            ) : (
              <div className="space-y-1.5">
                {Object.entries(overnightByAgent).map(([agentId, items]) => {
                  const successCount = items.filter((i) => i.status === "success" || i.status === "completed").length;
                  const failCount = items.filter((i) => i.status === "failed" || i.status === "error").length;
                  const latestItem = items[0];
                  return (
                    <div key={agentId} className="flex items-start gap-2">
                      <span className="text-sm shrink-0">{latestItem.emoji ?? "🤖"}</span>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-medium text-foreground capitalize">{agentId.replace(/-/g, " ")}</span>
                        <span className="text-xs text-muted-foreground ml-1.5">
                          {items.length} task{items.length !== 1 ? "s" : ""}
                          {successCount > 0 && <span className="text-green-400 ml-1">· {successCount} ✓</span>}
                          {failCount > 0 && <span className="text-red-400 ml-1">· {failCount} ✗</span>}
                          <span className="ml-1 text-muted-foreground/60">· {timeAgo(latestItem.created_at)}</span>
                        </span>
                        {latestItem.summary && (
                          <p className="text-[10px] text-muted-foreground/70 truncate mt-0.5">{latestItem.summary}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div className="pt-1 border-t border-border/40">
                  <Link
                    href="/studio/agents"
                    className="text-[10px] text-primary hover:underline"
                  >
                    View full activity log →
                  </Link>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ── 📊 LEADS PULSE + 📈 PERFORMANCE (side by side on wide screens) ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          {/* Leads Pulse */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
              📊 Leads Pulse
            </h2>
            <div className="rounded-xl border border-border bg-card/50 px-4 py-3 space-y-3">
              {leadsPulse === null ? (
                <p className="text-xs text-muted-foreground">Loading...</p>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <div className="text-2xl font-bold tabular-nums text-foreground">{leadsPulse.new_leads}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">new today</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold tabular-nums ${leadsPulse.unreviewed > 0 ? "text-amber-400" : "text-foreground"}`}>
                      {leadsPulse.unreviewed}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">unreviewed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold tabular-nums text-foreground">{leadsPulse.active_sequences}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">sequences</div>
                  </div>
                </div>
              )}
              <Link href="/sales" className="block text-[10px] text-primary hover:underline">
                Open Sales room →
              </Link>
            </div>
          </section>

          {/* Performance Pulse */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
              📈 Performance
            </h2>
            <div className="rounded-xl border border-border bg-card/50 px-4 py-3 space-y-3">
              {perf === null ? (
                <p className="text-xs text-muted-foreground">Loading...</p>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <div className="text-2xl font-bold tabular-nums text-foreground">
                      {perf.posts.total_generated > 0
                        ? Math.round(perf.posts.approval_rate * 100)
                        : "—"}
                      {perf.posts.total_generated > 0 ? "%" : ""}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">approval rate</div>
                  </div>
                  <div className="text-center">
                    <div className={`text-2xl font-bold tabular-nums ${
                      perf.posts.avg_qa_score >= 80 ? "text-green-400"
                      : perf.posts.avg_qa_score >= 60 ? "text-amber-400"
                      : "text-foreground"
                    }`}>
                      {perf.posts.avg_qa_score > 0 ? Math.round(perf.posts.avg_qa_score) : "—"}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">avg QA</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-semibold text-foreground leading-tight mt-1">
                      {topRejectionReason
                        ? topRejectionReason.replace(/_/g, " ")
                        : "—"}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">top rejection</div>
                  </div>
                </div>
              )}
              <Link href="/mission-control/analytics" className="block text-[10px] text-primary hover:underline">
                Full results →
              </Link>
            </div>
          </section>
        </div>

        {/* ── 🔬 LATEST RESEARCH ──────────────────────────── */}
        {brief && (
          <section>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  🔬 Latest Research
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Trend Analyzer · {timeAgo(brief.created_at)}
                </span>
              </div>
              <p className={`text-sm text-foreground/90 leading-relaxed ${briefExpanded ? "" : "line-clamp-3"}`}>
                {brief.content}
              </p>
              <button
                onClick={() => setBriefExpanded(!briefExpanded)}
                className="mt-2 text-xs text-primary hover:underline"
              >
                {briefExpanded ? "▲ Collapse brief" : "▼ View full brief"}
              </button>
            </div>
          </section>
        )}

      </div>

      <QuickCapture />
    </div>
  );
}
