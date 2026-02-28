"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  missionControlApi,
  Agent,
  AgentTask,
  AgentMessage,
  DashboardStats,
} from "@/lib/api/mission-control";
import { STATUS_COLORS, ROLE_TYPE_BADGES, MC_SUB_NAV } from "../constants";

/* ── Helpers ───────────────────────────────────────────── */

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function fmtDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/* ── Mini bar chart (pure CSS) ─────────────────────────── */

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-5 w-full bg-accent rounded-sm overflow-hidden">
      <div className={`h-full ${color} rounded-sm transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ── Page component ────────────────────────────────────── */

export default function AnalyticsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d">("7d");

  const loadData = useCallback(async () => {
    try {
      const [agentsRes, tasksRes, messagesRes, statsRes] = await Promise.all([
        missionControlApi.listAgents(),
        missionControlApi.listTasks(),
        missionControlApi.listMessages({ limit: 200 }),
        missionControlApi.getStats(),
      ]);
      setAgents(agentsRes);
      setTasks(tasksRes);
      setMessages(messagesRes);
      setStats(statsRes);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /* ── Computed metrics ─────────────────────────────────── */

  const agentMetrics = useMemo(() => {
    return agents.map((agent) => {
      const agentTasks = tasks.filter((t) => t.assignee_id === agent.id);
      const completed = agentTasks.filter((t) => t.status === "done" || t.status === "archived");
      const active = agentTasks.filter((t) => t.status === "in_progress" || t.status === "assigned");
      const agentMsgs = messages.filter(
        (m) => m.from_agent_id === agent.id || m.to_agent_id === agent.id
      );

      // Average completion time (in hours) for completed tasks
      let avgCompletionHours = 0;
      const completedWithTime = completed.filter((t) => t.completed_at);
      if (completedWithTime.length > 0) {
        const totalHours = completedWithTime.reduce((acc, t) => {
          const start = new Date(t.created_at).getTime();
          const end = new Date(t.completed_at!).getTime();
          return acc + (end - start) / 3600000;
        }, 0);
        avgCompletionHours = totalHours / completedWithTime.length;
      }

      return {
        agent,
        totalTasks: agentTasks.length,
        completed: completed.length,
        active: active.length,
        messageCount: agentMsgs.length,
        avgCompletionHours,
        completionRate: agentTasks.length > 0 ? (completed.length / agentTasks.length) * 100 : 0,
      };
    });
  }, [agents, tasks, messages]);

  const maxTasks = useMemo(
    () => Math.max(...agentMetrics.map((m) => m.totalTasks), 1),
    [agentMetrics]
  );

  const maxMessages = useMemo(
    () => Math.max(...agentMetrics.map((m) => m.messageCount), 1),
    [agentMetrics]
  );

  const statusBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of tasks) {
      counts[t.status] = (counts[t.status] || 0) + 1;
    }
    return counts;
  }, [tasks]);

  const messagesByType = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const m of messages) {
      counts[m.message_type] = (counts[m.message_type] || 0) + 1;
    }
    return counts;
  }, [messages]);

  /* ── Loading / Error ──────────────────────────────────── */

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-lg font-semibold text-foreground mb-2">Load Error</h2>
          <p className="text-sm text-muted-foreground mb-4">{error}</p>
          <button onClick={loadData} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <div className="flex items-center gap-2">
          <span className="text-amber-400 text-lg">◇</span>
          <h1 className="text-sm font-bold text-foreground tracking-wider uppercase">Agent Analytics</h1>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[10px] text-green-400 font-bold">ONLINE</span>
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="h-10 border-b border-border bg-card/50 flex items-center px-5 gap-1 overflow-x-auto">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
              item.href === "/mission-control/analytics"
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      <div className="p-5 space-y-5 max-w-7xl mx-auto">
        {/* ── Summary cards ────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard label="Total Agents" value={stats?.agents_total ?? 0} icon="🤖" />
          <SummaryCard label="Total Tasks" value={stats?.tasks_total ?? 0} icon="📋" />
          <SummaryCard label="Completed Today" value={stats?.tasks_completed_today ?? 0} icon="✅" accent="text-green-400" />
          <SummaryCard label="Messages Today" value={stats?.messages_today ?? 0} icon="💬" accent="text-primary" />
        </div>

        {/* ── Agent performance table ─────────────────────── */}
        <section className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              Agent Performance
            </h2>
            <span className="text-[10px] text-muted-foreground font-mono">{agents.length} agents</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Agent</th>
                  <th className="text-left px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Status</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Tasks</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Completed</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Active</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Completion %</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Avg Time</th>
                  <th className="text-center px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider">Messages</th>
                  <th className="text-left px-3 py-2.5 text-muted-foreground font-semibold uppercase tracking-wider w-32">Task Load</th>
                </tr>
              </thead>
              <tbody>
                {agentMetrics.map((m) => {
                  const statusStyle = STATUS_COLORS[m.agent.status] || STATUS_COLORS.idle;
                  const roleStyle = ROLE_TYPE_BADGES[m.agent.role_type] || ROLE_TYPE_BADGES.specialist;
                  return (
                    <tr key={m.agent.id} className="border-b border-border/50 hover:bg-accent/30 transition">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <span className="text-lg">{m.agent.avatar_emoji}</span>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium text-foreground">{m.agent.name}</span>
                              <span className={`text-[8px] px-1 py-0.5 rounded border font-bold ${roleStyle.color}`}>
                                {roleStyle.label}
                              </span>
                            </div>
                            <span className="text-[10px] text-muted-foreground">{m.agent.role}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${statusStyle.bg}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot}`} />
                          {statusStyle.label}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center text-foreground font-mono">{m.totalTasks}</td>
                      <td className="px-3 py-3 text-center text-green-400 font-mono">{m.completed}</td>
                      <td className="px-3 py-3 text-center text-primary font-mono">{m.active}</td>
                      <td className="px-3 py-3 text-center">
                        <span className={`font-mono font-bold ${
                          m.completionRate >= 80 ? "text-green-400" :
                          m.completionRate >= 50 ? "text-amber-400" :
                          "text-muted-foreground"
                        }`}>
                          {m.completionRate.toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center text-foreground font-mono">
                        {m.avgCompletionHours > 0
                          ? m.avgCompletionHours < 1
                            ? `${Math.round(m.avgCompletionHours * 60)}m`
                            : `${m.avgCompletionHours.toFixed(1)}h`
                          : "—"}
                      </td>
                      <td className="px-3 py-3 text-center text-foreground font-mono">{m.messageCount}</td>
                      <td className="px-3 py-3">
                        <MiniBar value={m.totalTasks} max={maxTasks} color="bg-primary" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Two-column layout: Task Breakdown + Message Types ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Task Status Breakdown */}
          <section className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                Task Status Breakdown
              </h2>
            </div>
            <div className="p-5 space-y-3">
              {[
                { key: "backlog", label: "Inbox / Backlog", color: "bg-muted-foreground" },
                { key: "assigned", label: "Assigned", color: "bg-amber-500" },
                { key: "in_progress", label: "In Progress", color: "bg-primary" },
                { key: "review", label: "Review", color: "bg-purple-500" },
                { key: "ready", label: "Ready", color: "bg-emerald-500" },
                { key: "done", label: "Done", color: "bg-green-500" },
              ].map((s) => {
                const count = statusBreakdown[s.key] || 0;
                return (
                  <div key={s.key} className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${s.color} flex-shrink-0`} />
                    <span className="text-xs text-muted-foreground w-24 flex-shrink-0">{s.label}</span>
                    <div className="flex-1">
                      <MiniBar value={count} max={Math.max(tasks.length, 1)} color={s.color} />
                    </div>
                    <span className="text-xs text-foreground font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Message Types Breakdown */}
          <section className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border">
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-chart-2" />
                Communication Breakdown
              </h2>
            </div>
            <div className="p-5 space-y-3">
              {[
                { key: "chat", label: "Chat", icon: "💬", color: "bg-primary" },
                { key: "delegation", label: "Delegations", icon: "📋", color: "bg-amber-500" },
                { key: "status", label: "Status Updates", icon: "📡", color: "bg-green-500" },
                { key: "deliverable", label: "Deliverables", icon: "📦", color: "bg-purple-500" },
                { key: "escalation", label: "Escalations", icon: "🚨", color: "bg-red-500" },
                { key: "broadcast", label: "Broadcasts", icon: "📢", color: "bg-cyan-500" },
              ].map((mt) => {
                const count = messagesByType[mt.key] || 0;
                return (
                  <div key={mt.key} className="flex items-center gap-3">
                    <span className="text-sm flex-shrink-0">{mt.icon}</span>
                    <span className="text-xs text-muted-foreground w-24 flex-shrink-0">{mt.label}</span>
                    <div className="flex-1">
                      <MiniBar value={count} max={Math.max(messages.length, 1)} color={mt.color} />
                    </div>
                    <span className="text-xs text-foreground font-mono w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        {/* ── Agent activity heatmap (messages per agent) ── */}
        <section className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Agent Communication Matrix
            </h2>
          </div>
          <div className="p-5 overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr>
                  <th className="px-2 py-1.5 text-muted-foreground font-semibold text-left">From \ To</th>
                  {agents.map((a) => (
                    <th key={a.id} className="px-2 py-1.5 text-muted-foreground font-semibold text-center whitespace-nowrap">
                      {a.avatar_emoji} {a.name.slice(0, 6)}
                    </th>
                  ))}
                  <th className="px-2 py-1.5 text-muted-foreground font-semibold text-center">📢 All</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((fromAgent) => (
                  <tr key={fromAgent.id} className="border-t border-border/30">
                    <td className="px-2 py-1.5 text-foreground font-medium whitespace-nowrap">
                      {fromAgent.avatar_emoji} {fromAgent.name}
                    </td>
                    {agents.map((toAgent) => {
                      const count = messages.filter(
                        (m) => m.from_agent_id === fromAgent.id && m.to_agent_id === toAgent.id
                      ).length;
                      return (
                        <td key={toAgent.id} className="px-2 py-1.5 text-center">
                          {count > 0 ? (
                            <span className={`inline-flex items-center justify-center w-7 h-6 rounded text-[10px] font-bold ${
                              count >= 10 ? "bg-primary/30 text-primary" :
                              count >= 5 ? "bg-primary/20 text-primary" :
                              "bg-accent text-muted-foreground"
                            }`}>
                              {count}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/50">·</span>
                          )}
                        </td>
                      );
                    })}
                    <td className="px-2 py-1.5 text-center">
                      {(() => {
                        const bc = messages.filter(
                          (m) => m.from_agent_id === fromAgent.id && m.message_type === "broadcast"
                        ).length;
                        return bc > 0 ? (
                          <span className="inline-flex items-center justify-center w-7 h-6 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-400">
                            {bc}
                          </span>
                        ) : (
                          <span className="text-muted-foreground/50">·</span>
                        );
                      })()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Recent completed tasks ──────────────────────── */}
        <section className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Recently Completed Tasks
            </h2>
          </div>
          <div className="divide-y divide-border/50">
            {tasks
              .filter((t) => t.status === "done" && t.completed_at)
              .sort((a, b) => new Date(b.completed_at!).getTime() - new Date(a.completed_at!).getTime())
              .slice(0, 10)
              .map((t) => {
                const assignee = agents.find((a) => a.id === t.assignee_id);
                return (
                  <div key={t.id} className="px-5 py-3 flex items-center gap-3 hover:bg-accent/20 transition">
                    <span className="text-sm">{assignee?.avatar_emoji || "❓"}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{t.title}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {assignee?.name || "Unassigned"} · Completed {timeAgo(t.completed_at!)}
                      </p>
                    </div>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                      t.priority === "P0" ? "bg-red-500/20 text-red-400" :
                      t.priority === "P1" ? "bg-amber-500/20 text-amber-400" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {t.priority}
                    </span>
                  </div>
                );
              })}
            {tasks.filter((t) => t.status === "done").length === 0 && (
              <div className="px-5 py-8 text-center text-xs text-muted-foreground">
                No completed tasks yet. Tasks will appear here as agents finish their work.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ── Summary Card ──────────────────────────────────────── */

function SummaryCard({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number;
  icon: string;
  accent?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">{label}</span>
        <span className="text-sm">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${accent || "text-card-foreground"} font-mono`}>{value}</div>
    </div>
  );
}
