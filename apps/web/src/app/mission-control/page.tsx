"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { missionControlApi, Agent, Deliverable } from "@/lib/api/mission-control";
import { notificationsApi, AgentNotification } from "@/lib/api/notifications";
import { scheduleApi, ScheduledItem } from "@/lib/api/schedule";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { MC_SUB_NAV } from "./constants";
import { QuickCapture } from "./components/quick-capture";

// ── Helpers ────────────────────────────────────────────────

function todayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function weekDays(): Date[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    return d;
  });
}

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
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

const REJECT_TAGS = ["Wrong voice", "Bad hook", "Needs research", "Off-topic"] as const;
type RejectTag = typeof REJECT_TAGS[number];

const AGENT_ICONS: Record<string, string> = {
  jumbo: "🧠",
  "trend-analyzer": "🔍",
  copywriter: "✍️",
  "qa-reviewer": "✅",
  "competitor-analyst": "🕵️",
  distributor: "📤",
  "visual-designer": "🎨",
  "analytics": "📊",
};

// ── Component ──────────────────────────────────────────────

export default function MissionControlHome() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [scheduled, setScheduled] = useState<ScheduledItem[]>([]);
  const [briefing, setBriefing] = useState<AgentNotification | null>(null);
  const [loading, setLoading] = useState(true);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [agentsRes, deliverablesRes, notifsRes, boardRes, briefingRes] = await Promise.all([
        missionControlApi.listAgents().catch(() => [] as Agent[]),
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
        notificationsApi.list({ status: "unread", limit: 10 }).catch(() => [] as AgentNotification[]),
        scheduleApi.getBoard().catch(() => ({ draft: [], scheduled: [], published: [], archived: [] })),
        notificationsApi.latestBriefing().catch(() => null),
      ]);
      setAgents(agentsRes);
      setDeliverables(deliverablesRes.filter((d) => d.status === "review"));
      setNotifications(notifsRes.filter((n) => n.priority === "high" || n.priority === "urgent"));
      // Merge scheduled + draft for the 7-day strip
      setScheduled([...boardRes.scheduled, ...boardRes.draft, ...boardRes.published]);
      setBriefing(briefingRes);
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
      // Post structured feedback to agent memory
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

  const approvalCount = deliverables.length + notifications.length;
  const days = weekDays();

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

      <div className="max-w-3xl mx-auto px-5 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Good morning!</h1>
            <p className="text-xs text-muted-foreground mt-0.5">{todayLabel()}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/mission-control/content"
              className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium hover:bg-amber-500/20 transition"
            >
              + New post
            </Link>
          </div>
        </div>

        {/* ── NEEDS YOUR APPROVAL ───────────────────────── */}
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
              {/* Deliverables */}
              {deliverables.map((d) => (
                <div key={d.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm">✍️</span>
                        <span className="text-sm font-medium text-foreground truncate">
                          {d.title}
                        </span>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {timeAgo(d.created_at)}
                        </span>
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

              {/* High-priority notifications */}
              {notifications.map((n) => (
                <div key={n.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm">
                          {n.priority === "urgent" ? "🚨" : "🔔"}
                        </span>
                        <span className="text-sm font-medium text-foreground truncate">
                          {n.title}
                        </span>
                        <span className="text-[10px] text-muted-foreground shrink-0">
                          {timeAgo(n.created_at)}
                        </span>
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

        {/* ── 7-DAY CONTENT STRIP ───────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              This week
            </h2>
            <Link
              href="/mission-control/content"
              className="text-xs text-muted-foreground hover:text-foreground transition"
            >
              Full calendar →
            </Link>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="grid grid-cols-7 gap-1">
              {days.map((day, i) => {
                const dayItems = scheduled.filter((item) => {
                  const itemDate = item.scheduled_at
                    ? new Date(item.scheduled_at)
                    : item.published_at
                    ? new Date(item.published_at)
                    : null;
                  return itemDate && isSameDay(itemDate, day);
                });
                const isToday = i === 0;
                const published = dayItems.filter((it) => it.status === "published");
                const hasDraft = dayItems.some((it) => it.status === "draft");
                const hasScheduled = dayItems.some((it) => it.status === "scheduled");

                return (
                  <div key={i} className="text-center space-y-1">
                    <div className="text-[10px] text-muted-foreground">
                      {day.toLocaleDateString("en-US", { weekday: "short" })}
                    </div>
                    <div
                      className={`text-xs font-bold rounded-full w-7 h-7 flex items-center justify-center mx-auto ${
                        isToday
                          ? "bg-amber-500 text-black"
                          : "text-foreground"
                      }`}
                    >
                      {day.getDate()}
                    </div>
                    <div className="text-sm leading-none">
                      {published.length > 0 ? "✅" : hasScheduled ? "📅" : hasDraft ? "📝" : "·"}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── AGENT STATUS ──────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Your agents
            </h2>
            <Link
              href="/mission-control/orchestrator"
              className="text-xs text-muted-foreground hover:text-foreground transition"
            >
              Full team →
            </Link>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border">
            {loading ? (
              <div className="px-4 py-3 text-xs text-muted-foreground">Loading agents...</div>
            ) : agents.length === 0 ? (
              <div className="px-4 py-3 text-xs text-muted-foreground">No agents found.</div>
            ) : (
              agents.slice(0, 4).map((agent) => {
                const icon = AGENT_ICONS[agent.id] || AGENT_ICONS[agent.name?.toLowerCase()] || "🤖";
                const isWorking = agent.status === "working";
                return (
                  <div key={agent.id} className="px-4 py-2.5 flex items-center gap-3">
                    <span className="text-base">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-foreground capitalize">
                        {agent.name}
                      </span>
                      {agent.status_reason && isWorking && (
                        <span className="text-xs text-muted-foreground ml-2 truncate">
                          — {agent.status_reason}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isWorking
                            ? "bg-green-400 animate-pulse"
                            : agent.status === "error"
                            ? "bg-red-400"
                            : "bg-zinc-400"
                        }`}
                      />
                      <span
                        className={`text-xs ${
                          isWorking
                            ? "text-green-400"
                            : agent.status === "error"
                            ? "text-red-400"
                            : "text-muted-foreground"
                        }`}
                      >
                        {agent.status === "working" ? "Working" : agent.status === "error" ? "Error" : "Idle"}
                      </span>
                      {agent.last_heartbeat_at && (
                        <span className="text-[10px] text-muted-foreground/60">
                          · {timeAgo(agent.last_heartbeat_at)}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* ── LATEST FROM JUMBO ─────────────────────────── */}
        {briefing && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                Latest from Jumbo
              </h2>
              <span className="text-[10px] text-muted-foreground">{timeAgo(briefing.created_at)}</span>
            </div>
            <div className="rounded-xl border border-border bg-card px-4 py-4">
              <p className="text-sm font-medium text-foreground mb-1">{briefing.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                {briefing.body}
              </p>
              <button
                onClick={() => notificationsApi.markRead(briefing.id).catch(() => {})}
                className="mt-3 text-xs text-muted-foreground hover:text-foreground transition"
              >
                Mark as read
              </button>
            </div>
          </section>
        )}
      </div>

      <QuickCapture />
    </div>
  );
}
