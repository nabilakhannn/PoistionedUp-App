"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { notificationsApi, AgentNotification } from "@/lib/api/notifications";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { usageApi, UsageSummary } from "@/lib/api/usage";
import { MC_SUB_NAV } from "./constants";
import { QuickCapture } from "./components/quick-capture";
import { AgentOffice } from "@/components/agent-office";

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
  running,
}: {
  pipelineSettings: PipelineSettings | null;
  usage: UsageSummary | null;
  onRunNow: () => void;
  running: boolean;
}) {
  const monthlyBudget = 20;
  const monthlySpend = usage?.period_costs?.monthly ?? 0;
  const budgetPct = monthlyBudget > 0 ? Math.min(100, (monthlySpend / monthlyBudget) * 100) : 0;

  return (
    <div className="rounded-xl border border-border bg-card/50 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Pipeline status */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                pipelineSettings?.enabled ? "bg-green-400 animate-pulse" : "bg-zinc-400"
              }`}
            />
            <span className="text-xs font-medium text-foreground">
              Pipeline: {pipelineSettings?.enabled ? "ON" : "OFF"}
            </span>
          </div>
          {pipelineSettings?.enabled && pipelineSettings.next_run_at && (
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

        {/* Budget widget */}
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
    </div>
  );
}

// ── Component ──────────────────────────────────────────────

export default function MissionControlHome() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [runningNow, setRunningNow] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [deliverablesRes, notifsRes, pipelineRes, usageRes] = await Promise.all([
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
        notificationsApi.list({ status: "unread", limit: 10 }).catch(() => [] as AgentNotification[]),
        pipelineSettingsApi.get().catch(() => null),
        usageApi.getSummary().catch(() => null),
      ]);
      setDeliverables(deliverablesRes.filter((d) => d.status === "review"));
      setNotifications(notifsRes.filter((n) => n.priority === "high" || n.priority === "urgent"));
      setPipelineSettings(pipelineRes);
      setUsage(usageRes);
    } finally {
      setLoading(false);
    }
  }, []);

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
    try {
      await pipelineSettingsApi.runNow();
      await loadAll();
    } catch {
      // silent
    } finally {
      setRunningNow(false);
    }
  };

  const approvalCount = deliverables.length + notifications.length;

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
          running={runningNow}
        />

        {/* ── AGENT OFFICE ───────────────────────────── */}
        <AgentOffice />

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

        {/* ── ROOM SHORTCUTS ─────────────────────────── */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">
            Rooms
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              { href: "/marketing", emoji: "📣", label: "Marketing", desc: "Content pipeline, calendar, ads" },
              { href: "/sales", emoji: "💼", label: "Sales", desc: "Newsletter, leads, outreach" },
              { href: "/intelligence", emoji: "🧠", label: "Intelligence", desc: "Research, brand, journal" },
              { href: "/mission-control/settings", emoji: "⚙️", label: "Settings", desc: "Connectors, knowledge, team" },
            ].map((room) => (
              <Link
                key={room.href}
                href={room.href}
                className="rounded-xl border border-border bg-card/30 p-4 hover:border-primary/30 hover:bg-card/60 transition group"
              >
                <div className="text-xl mb-1">{room.emoji}</div>
                <div className="text-sm font-semibold text-foreground group-hover:text-primary transition">{room.label}</div>
                <div className="text-xs text-muted-foreground">{room.desc}</div>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <QuickCapture />
    </div>
  );
}
