"use client";

/**
 * Mission Control Home — Slice 94
 * Pipeline Dashboard: funnel view of content stages + research brief card
 */

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { notificationsApi, AgentNotification } from "@/lib/api/notifications";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { usageApi, UsageSummary } from "@/lib/api/usage";
import { scheduleApi } from "@/lib/api/schedule";
import { researchBriefsApi, ResearchBrief } from "@/lib/api/research-briefs";
import { useBrand } from "@/lib/brand-context";
import { MC_SUB_NAV } from "./constants";
import { QuickCapture } from "./components/quick-capture";
import { AgentOffice } from "@/components/agent-office";
import TranscriptDrop from "@/components/transcript-drop";

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
  const monthlyBudget = 20;
  const monthlySpend = usage?.period_costs?.monthly ?? 0;
  const budgetPct = monthlyBudget > 0 ? Math.min(100, (monthlySpend / monthlyBudget) * 100) : 0;
  const enabled = pipelineSettings?.enabled ?? false;

  return (
    <div className="rounded-xl border border-border bg-card/50 px-4 py-3 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Clickable toggle */}
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

      {/* Error feedback */}
      {runError && (
        <p className="text-xs text-red-400 border-t border-border/50 pt-2">{runError}</p>
      )}
    </div>
  );
}

// ── Pipeline Funnel ─────────────────────────────────────────

interface StageCardProps {
  emoji: string;
  label: string;
  count: number;
  note: string;
  highlight?: boolean;
  isLast?: boolean;
}

function StageCard({ emoji, label, count, note, highlight, isLast }: StageCardProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex-1 rounded-xl border px-3 py-3 text-center transition ${
          highlight
            ? "border-amber-500/40 bg-amber-500/5"
            : "border-border bg-card/40"
        }`}
      >
        <div className="text-xl mb-1">{emoji}</div>
        <div className={`text-2xl font-bold tabular-nums ${highlight ? "text-amber-400" : "text-foreground"}`}>
          {count}
        </div>
        <div className="text-[11px] font-medium text-foreground mt-0.5">{label}</div>
        <div className={`text-[10px] mt-0.5 ${highlight ? "text-amber-400 font-medium" : "text-muted-foreground"}`}>
          {highlight && count > 0 ? "● " : ""}{note}
        </div>
      </div>
      {!isLast && (
        <span className="text-muted-foreground/40 text-sm font-light shrink-0">→</span>
      )}
    </div>
  );
}

// ── Component ──────────────────────────────────────────────

export default function MissionControlHome() {
  const { currentBrand } = useBrand();
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [board, setBoard] = useState<{ draft: unknown[]; scheduled: unknown[] } | null>(null);
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [runningNow, setRunningNow] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [showTranscriptDrop, setShowTranscriptDrop] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [deliverablesRes, notifsRes, pipelineRes, usageRes, boardRes] = await Promise.all([
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
        notificationsApi.list({ status: "unread", limit: 10 }).catch(() => [] as AgentNotification[]),
        pipelineSettingsApi.get().catch(() => null),
        usageApi.getSummary().catch(() => null),
        scheduleApi.getBoard().catch(() => null),
      ]);
      setDeliverables(deliverablesRes.filter((d) => d.status === "review"));
      setNotifications(notifsRes.filter((n) => n.priority === "high" || n.priority === "urgent"));
      setPipelineSettings(pipelineRes);
      setUsage(usageRes);
      setBoard(boardRes);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load research brief separately when brand changes
  useEffect(() => {
    if (!currentBrand?.id) return;
    researchBriefsApi.getLatest(currentBrand.id)
      .then((res) => setBrief(res.brief))
      .catch(() => {});
  }, [currentBrand?.id]);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000);
    return () => clearInterval(t);
  }, [loadAll]);

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      await missionControlApi.updateDeliverable(id, "approved", "");
      await loadAll();
    } catch (e) {
      console.error("Approve error:", e);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string, tag: RejectTag) => {
    setActionLoading(id);
    try {
      await missionControlApi.updateDeliverable(id, "rejected", tag);
      await agentBridgeApi.submitReport({
        agent_id: "jumbo",
        report_type: "voice_feedback",
        title: `Rejection: ${tag}`,
        content: `Deliverable ${id} rejected with tag: ${tag}`,
        tags: [tag.toLowerCase().replace(/\s+/g, "_")],
        save_to_memory: true,
      }).catch(() => {});
      setRejectTarget(null);
      await loadAll();
    } catch (e) {
      console.error("Reject error:", e);
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

  const approvalCount = deliverables.length + notifications.length;

  // Pipeline stage counts
  const isResearching = runningNow || pipelineSettings?.run_now === true;
  const writingCount = Array.isArray((board as { draft?: unknown[] } | null)?.draft)
    ? ((board as { draft: unknown[] }).draft.length)
    : 0;
  const reviewCount = deliverables.length;
  const scheduledCount = Array.isArray((board as { scheduled?: unknown[] } | null)?.scheduled)
    ? ((board as { scheduled: unknown[] }).scheduled.length)
    : 0;

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
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-foreground">Good morning!</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{todayLabel()}</p>
        </div>

        {/* ── STATUS BAR ─────────────────────────────── */}
        <StatusBar
          pipelineSettings={pipelineSettings}
          usage={usage}
          onRunNow={handleRunNow}
          onToggle={handleToggle}
          running={runningNow}
          toggling={toggling}
          runError={runError}
        />

        {/* ── CONTENT PIPELINE FUNNEL ────────────────── */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            Content Pipeline
          </h2>
          <div className="flex items-center gap-0">
            <StageCard
              emoji="🔬"
              label="Research"
              count={isResearching ? 1 : 0}
              note={isResearching ? "Running now" : "Idle"}
            />
            <StageCard
              emoji="✍️"
              label="Writing"
              count={writingCount}
              note={writingCount === 1 ? "draft" : "drafts"}
            />
            <StageCard
              emoji="✅"
              label="QA"
              count={0}
              note="automated"
            />
            <StageCard
              emoji="👁"
              label="Your Review"
              count={reviewCount}
              note={reviewCount > 0 ? "needs you" : "all clear"}
              highlight={reviewCount > 0}
            />
            <StageCard
              emoji="📅"
              label="Scheduled"
              count={scheduledCount}
              note="queued"
              isLast
            />
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">
            Content flows: Research → Writing → QA → Your Review → Scheduled → Published
          </p>
        </section>

        {/* ── NEEDS YOUR APPROVAL ────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Needs your approval
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
            <div className="rounded-xl border border-border bg-card/30 px-5 py-8 text-center">
              <div className="text-2xl mb-2">✅</div>
              <p className="text-sm text-muted-foreground">All caught up! No items need review.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
              {deliverables.map((d) => (
                <div key={d.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm">✍️</span>
                        <span className="text-sm font-medium text-foreground truncate">{d.title}</span>
                        {d.qa_score !== undefined && d.qa_score > 0 && (
                          <span className="text-[10px] shrink-0 px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">
                            Score: {d.qa_score}
                          </span>
                        )}
                        <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(d.created_at)}</span>
                      </div>
                      {d.content && (
                        <p className="text-xs text-muted-foreground truncate ml-6">{d.content}</p>
                      )}
                    </div>

                    {rejectTarget === d.id ? (
                      <div className="flex flex-wrap gap-1 shrink-0">
                        {REJECT_TAGS.map((tag) => (
                          <button
                            key={tag}
                            onClick={() => handleReject(d.id, tag)}
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
                          onClick={() => handleApprove(d.id)}
                          disabled={actionLoading === d.id}
                          className="px-2.5 py-1.5 text-xs rounded-lg bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30 font-medium transition"
                        >
                          {actionLoading === d.id ? "..." : "Approve ✓"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}

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

        {/* ── LATEST RESEARCH ────────────────────────── */}
        {brief && (
          <section>
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  Latest Research
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Trend Analyzer · {timeAgo(brief.created_at)}
                </span>
              </div>
              <p className="text-sm text-foreground/90 line-clamp-3 leading-relaxed">
                {brief.content}
              </p>
              <Link
                href="/intelligence"
                className="inline-block mt-2 text-xs text-primary hover:underline"
              >
                View full brief →
              </Link>
            </div>
          </section>
        )}

        {/* ── CLIENT CALL ANALYSIS ──────────────────── */}
        <section>
          {showTranscriptDrop ? (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  🎙 Analyze Client Call
                </span>
                <button
                  onClick={() => setShowTranscriptDrop(false)}
                  className="text-muted-foreground hover:text-foreground text-xs transition"
                >
                  Close ✕
                </button>
              </div>
              <div className="p-4">
                <TranscriptDrop
                  brandId={currentBrand?.id ?? ""}
                  onSessionCreated={() => setShowTranscriptDrop(false)}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowTranscriptDrop(true)}
              className="w-full rounded-xl border border-dashed border-indigo-500/40 bg-indigo-950/10 hover:bg-indigo-950/20 hover:border-indigo-500/60 px-5 py-4 flex items-center gap-3 transition-colors group"
            >
              <span className="text-2xl">🎙</span>
              <div className="text-left">
                <p className="text-sm font-semibold text-indigo-300 group-hover:text-indigo-200 transition-colors">
                  Analyze a Client Call
                </p>
                <p className="text-xs text-muted-foreground">
                  Paste or upload a transcript — Account Manager extracts action items
                </p>
              </div>
              <span className="ml-auto text-indigo-500 group-hover:text-indigo-400 text-sm transition-colors">→</span>
            </button>
          )}
        </section>

        {/* ── AGENT OFFICE ───────────────────────────── */}
        <AgentOffice />
      </div>

      <QuickCapture />
    </div>
  );
}
