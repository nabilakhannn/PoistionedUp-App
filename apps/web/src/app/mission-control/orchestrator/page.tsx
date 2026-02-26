"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  missionControlApi,
  Agent,
  AgentTask,
  AgentMessage,
  Deliverable,
  OrchestratorActivity,
} from "@/lib/api/mission-control";
import { orchestratorApi, OrchestratorStatus, ScheduleState } from "@/lib/api/orchestrator";
import { STATUS_COLORS, ROLE_TYPE_BADGES, MESSAGE_TYPE_ICONS } from "../constants";

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

function fmtDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/* ── Page ──────────────────────────────────────────────── */

export default function OrchestratorPage() {
  const [orchestratorData, setOrchestratorData] = useState<OrchestratorActivity | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState(24);
  const [activeTab, setActiveTab] = useState<"timeline" | "delegations" | "sub-agents" | "deliverables">("timeline");
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const [orchStatus, setOrchStatus] = useState<OrchestratorStatus | null>(null);
  const [pulsingSchedule, setPulsingSchedule] = useState<string | null>(null);
  const [pulseRunning, setPulseRunning] = useState(false);
  const [pulseMessage, setPulseMessage] = useState<string | null>(null);

  const jumbo = agents.find((a) => a.id === "jumbo");
  const subAgents = orchestratorData?.sub_agent_statuses || [];

  const loadData = useCallback(async () => {
    try {
      const [orchRes, agentsRes, delivRes, statusRes] = await Promise.all([
        missionControlApi.getOrchestratorActivity(hours),
        missionControlApi.listAgents(),
        missionControlApi.listDeliverables({ status: "review" }),
        orchestratorApi.status().catch(() => null),
      ]);
      setOrchestratorData(orchRes);
      setAgents(agentsRes);
      setDeliverables(delivRes);
      if (statusRes) setOrchStatus(statusRes);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load orchestrator data");
    } finally {
      setLoading(false);
    }
  }, [hours]);

  const handlePulse = async () => {
    setPulseRunning(true);
    setPulseMessage(null);
    try {
      const result = await orchestratorApi.pulse({ auto_execute: true, force: false });
      const created = result.created_tasks.length;
      const executed = result.executed.length;
      setPulseMessage(
        created > 0
          ? `Created ${created} task${created > 1 ? "s" : ""}${executed > 0 ? `, executed ${executed}` : ""}`
          : "All schedules up to date"
      );
      await loadData();
    } catch (err: any) {
      setPulseMessage(`Pulse failed: ${err.message}`);
    } finally {
      setPulseRunning(false);
      setTimeout(() => setPulseMessage(null), 5000);
    }
  };

  const handleTrigger = async (scheduleId: string) => {
    setPulsingSchedule(scheduleId);
    setPulseMessage(null);
    try {
      const result = await orchestratorApi.trigger(scheduleId, true);
      const status = result.execution?.status || "created";
      setPulseMessage(`Triggered ${scheduleId}: ${status}`);
      await loadData();
    } catch (err: any) {
      setPulseMessage(`Trigger failed: ${err.message}`);
    } finally {
      setPulsingSchedule(null);
      setTimeout(() => setPulseMessage(null), 5000);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  /* ── Loading / Error ──────────────────────────────────── */

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading Orchestrator view...</p>
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

  const timeline = orchestratorData?.timeline || [];
  const delegations = orchestratorData?.delegations || [];
  const recentTasks = orchestratorData?.recent_tasks_created || [];

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <span className="text-amber-400 text-lg">◇</span>
          <h1 className="text-sm font-bold text-foreground tracking-wider uppercase">Orchestrator View</h1>
          {jumbo && (
            <div className="flex items-center gap-2 ml-3 px-3 py-1 rounded-full bg-accent border border-border">
              <span className="text-lg">{jumbo.avatar_emoji}</span>
              <span className="text-xs font-medium text-foreground">{jumbo.name}</span>
              <span className={`w-1.5 h-1.5 rounded-full ${
                (STATUS_COLORS[jumbo.status] || STATUS_COLORS.idle).dot
              } ${jumbo.status === "working" ? "animate-pulse" : ""}`} />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Pulse button */}
          <button
            onClick={handlePulse}
            disabled={pulseRunning}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition flex items-center gap-1.5 ${
              pulseRunning
                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 cursor-wait"
                : "bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25"
            }`}
          >
            {pulseRunning ? (
              <span className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <span>&#9889;</span>
            )}
            {pulseRunning ? "Running..." : "Run Pulse"}
          </button>

          {/* Time range selector */}
          <div className="flex items-center gap-1 bg-accent rounded-lg border border-border p-0.5">
            {([
              { val: 24, label: "24h" },
              { val: 72, label: "3d" },
              { val: 168, label: "7d" },
            ] as const).map((opt) => (
              <button
                key={opt.val}
                onClick={() => { setHours(opt.val); setLoading(true); }}
                className={`px-2.5 py-1 rounded-md text-[10px] font-bold transition ${
                  hours === opt.val
                    ? "bg-primary/20 text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 ml-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-green-400 font-bold">LIVE</span>
          </div>
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="h-10 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        <Link href="/mission-control" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Dashboard
        </Link>
        <Link href="/mission-control/analytics" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Analytics
        </Link>
        <Link href="/mission-control/orchestrator" className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary/15 text-primary border border-primary/20">
          Orchestrator
        </Link>
        <Link href="/mission-control/gateway" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Gateway
        </Link>
        <Link href="/mission-control/chat" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Chat
        </Link>
      </div>

      {/* Main content: 2-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left panel: Sub-agents + Stats ─────────────── */}
        <div className="w-72 flex-shrink-0 border-r border-border bg-background flex flex-col overflow-hidden">
          {/* Jumbo stats */}
          <div className="px-4 py-4 border-b border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-accent border-2 border-amber-500/30 flex items-center justify-center text-2xl">
                {jumbo?.avatar_emoji || "🎯"}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-card-foreground">{jumbo?.name || "Jumbo"}</h3>
                <p className="text-[10px] text-muted-foreground">{jumbo?.role || "Orchestrator"}</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="text-center px-2 py-1.5 rounded-lg bg-card border border-border">
                <div className="text-lg font-bold text-card-foreground font-mono">{delegations.length}</div>
                <div className="text-[8px] text-muted-foreground uppercase">Delegated</div>
              </div>
              <div className="text-center px-2 py-1.5 rounded-lg bg-card border border-border">
                <div className="text-lg font-bold text-card-foreground font-mono">{recentTasks.length}</div>
                <div className="text-[8px] text-muted-foreground uppercase">Created</div>
              </div>
              <div className="text-center px-2 py-1.5 rounded-lg bg-card border border-border">
                <div className="text-lg font-bold text-card-foreground font-mono">{timeline.length}</div>
                <div className="text-[8px] text-muted-foreground uppercase">Messages</div>
              </div>
            </div>
          </div>

          {/* Pulse message toast */}
          {pulseMessage && (
            <div className="px-4 py-2 border-b border-border bg-card/50">
              <p className="text-[10px] text-amber-400 font-medium">{pulseMessage}</p>
            </div>
          )}

          {/* Scheduled Automations */}
          <div className="px-4 py-2.5 border-b border-border">
            <h3 className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              Scheduled Automations
            </h3>
            {(orchStatus?.schedules || []).map((sched) => {
              const isTriggering = pulsingSchedule === sched.id;
              const agentMatch = agents.find((a) => a.id === sched.agent_id);
              const typeIcon = sched.task_type === "research" ? "&#128269;" :
                               sched.task_type === "analytics" ? "&#128202;" :
                               sched.task_type === "competitor" ? "&#9876;" : "&#9889;";
              return (
                <div key={sched.id} className="mb-2 px-3 py-2.5 rounded-lg bg-card border border-border hover:border-muted-foreground transition">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs" dangerouslySetInnerHTML={{ __html: typeIcon }} />
                      <span className="text-[11px] font-medium text-foreground">{sched.name}</span>
                    </div>
                    <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-bold ${
                      sched.is_due && !sched.has_recent_run
                        ? "bg-green-500/20 text-green-400"
                        : sched.has_recent_run
                        ? "bg-muted text-muted-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}>
                      {sched.is_due && !sched.has_recent_run ? "DUE" : sched.has_recent_run ? "RAN" : "WAITING"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] text-muted-foreground">
                      {agentMatch ? `${agentMatch.avatar_emoji} ${agentMatch.name}` : sched.agent_id}
                      {sched.last_run && (
                        <span className="ml-1.5 text-muted-foreground">
                          {sched.last_run.status === "done" ? "  OK" : sched.last_run.status === "failed" ? "  FAIL" : ""}
                          {" "}{timeAgo(sched.last_run.created_at)}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => handleTrigger(sched.id)}
                      disabled={isTriggering}
                      className={`px-2 py-1 rounded text-[9px] font-bold transition ${
                        isTriggering
                          ? "bg-muted text-muted-foreground cursor-wait"
                          : "bg-primary/15 text-primary border border-primary/20 hover:bg-primary/25"
                      }`}
                    >
                      {isTriggering ? "..." : "Run"}
                    </button>
                  </div>
                </div>
              );
            })}
            {(!orchStatus || orchStatus.schedules.length === 0) && (
              <p className="text-[10px] text-muted-foreground text-center py-2">Loading schedules...</p>
            )}
          </div>

          {/* Sub-agent roster */}
          <div className="px-4 py-2.5 border-b border-border">
            <h3 className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Sub-Agent Roster
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto">
            {subAgents.map((agent) => {
              const statusStyle = STATUS_COLORS[agent.status] || STATUS_COLORS.idle;
              const roleStyle = ROLE_TYPE_BADGES[agent.role_type] || ROLE_TYPE_BADGES.specialist;
              return (
                <div
                  key={agent.id}
                  className="px-4 py-3 border-b border-border/50 hover:bg-accent/20 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-base border border-border flex-shrink-0">
                      {agent.avatar_emoji}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-medium text-foreground truncate">{agent.name}</span>
                        <span className={`text-[8px] px-1 py-0.5 rounded border font-bold ${roleStyle.color}`}>
                          {roleStyle.label}
                        </span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">{agent.role}</span>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot} ${
                        agent.status === "working" ? "animate-pulse" : ""
                      }`} />
                      <span className={`text-[9px] font-bold ${statusStyle.bg.split(" ")[1]}`}>
                        {statusStyle.label}
                      </span>
                    </div>
                  </div>
                  {agent.status_reason && (
                    <p className="text-[10px] text-muted-foreground mt-1.5 ml-10 line-clamp-2">
                      {agent.status_reason}
                    </p>
                  )}
                  {agent.last_heartbeat_at && (
                    <p className="text-[9px] text-muted-foreground mt-0.5 ml-10">
                      Last heartbeat: {timeAgo(agent.last_heartbeat_at)}
                    </p>
                  )}
                </div>
              );
            })}
            {subAgents.length === 0 && (
              <div className="text-center py-8 text-xs text-muted-foreground">
                No sub-agents found
              </div>
            )}
          </div>
        </div>

        {/* ── Right panel: Activity feed ─────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="h-10 border-b border-border flex items-center px-5 gap-4">
            {([
              { key: "timeline" as const, label: "Timeline", icon: "📡", count: timeline.length },
              { key: "delegations" as const, label: "Delegations", icon: "📋", count: delegations.length },
              { key: "sub-agents" as const, label: "Tasks Created", icon: "📝", count: recentTasks.length },
              { key: "deliverables" as const, label: "Deliverables", icon: "📦", count: deliverables.length },
            ]).map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 pb-0 text-xs font-medium border-b-2 transition ${
                  activeTab === tab.key
                    ? "text-primary border-primary"
                    : "text-muted-foreground border-transparent hover:text-foreground"
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                  activeTab === tab.key ? "bg-primary/20 text-primary" : "bg-accent text-muted-foreground"
                }`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {/* ── Timeline tab ─────────────────────────────── */}
            {activeTab === "timeline" && (
              <div className="px-5 py-3">
                {timeline.length === 0 ? (
                  <EmptyState
                    icon="📡"
                    title="No activity yet"
                    description={`No agent messages in the last ${hours} hours. Activity will stream in as agents work.`}
                  />
                ) : (
                  <div className="space-y-1">
                    {timeline.map((msg) => {
                      const fromAgent = agents.find((a) => a.id === msg.from_agent_id);
                      const toAgent = agents.find((a) => a.id === msg.to_agent_id);
                      const isExpanded = expandedMessage === msg.id;

                      return (
                        <button
                          key={msg.id}
                          onClick={() => setExpandedMessage(isExpanded ? null : msg.id)}
                          className="w-full text-left px-4 py-2.5 rounded-lg hover:bg-accent/40 transition group"
                        >
                          <div className="flex items-start gap-3">
                            {/* Icon */}
                            <div className="flex-shrink-0 mt-0.5">
                              <span className="text-sm">{MESSAGE_TYPE_ICONS[msg.message_type] || "💬"}</span>
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                {fromAgent ? (
                                  <span className="text-xs font-medium text-foreground">
                                    {fromAgent.avatar_emoji} {fromAgent.name}
                                  </span>
                                ) : (
                                  <span className="text-xs font-medium text-amber-400">👤 You</span>
                                )}
                                {toAgent && (
                                  <>
                                    <span className="text-muted-foreground text-[10px]">→</span>
                                    <span className="text-xs text-muted-foreground">
                                      {toAgent.avatar_emoji} {toAgent.name}
                                    </span>
                                  </>
                                )}
                                {!toAgent && msg.message_type === "broadcast" && (
                                  <>
                                    <span className="text-muted-foreground text-[10px]">→</span>
                                    <span className="text-xs text-cyan-400">📢 All Agents</span>
                                  </>
                                )}
                              </div>
                              <p className={`text-xs text-muted-foreground ${isExpanded ? "" : "line-clamp-2"}`}>
                                {msg.message}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                                  msg.message_type === "delegation" ? "bg-amber-500/15 text-amber-400" :
                                  msg.message_type === "escalation" ? "bg-red-500/15 text-red-400" :
                                  msg.message_type === "deliverable" ? "bg-purple-500/15 text-purple-400" :
                                  msg.message_type === "broadcast" ? "bg-cyan-500/15 text-cyan-400" :
                                  msg.message_type === "status" ? "bg-green-500/15 text-green-400" :
                                  "bg-muted text-muted-foreground"
                                }`}>
                                  {msg.message_type.toUpperCase()}
                                </span>
                                <span className="text-[9px] text-muted-foreground">{fmtDateTime(msg.created_at)}</span>
                              </div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── Delegations tab ──────────────────────────── */}
            {activeTab === "delegations" && (
              <div className="px-5 py-3">
                {delegations.length === 0 ? (
                  <EmptyState
                    icon="📋"
                    title="No delegations"
                    description={`Jumbo hasn't delegated any tasks in the last ${hours} hours.`}
                  />
                ) : (
                  <div className="space-y-2">
                    {delegations.map((msg) => {
                      const toAgent = agents.find((a) => a.id === msg.to_agent_id);
                      const isExpanded = expandedMessage === msg.id;
                      return (
                        <div
                          key={msg.id}
                          className="bg-card border border-border rounded-lg overflow-hidden hover:border-muted-foreground transition"
                        >
                          <button
                            onClick={() => setExpandedMessage(isExpanded ? null : msg.id)}
                            className="w-full text-left px-4 py-3"
                          >
                            <div className="flex items-center gap-2.5 mb-1.5">
                              <span className="text-amber-400 text-sm">📋</span>
                              <span className="text-xs font-medium text-foreground flex-1">
                                Delegated to {toAgent ? `${toAgent.avatar_emoji} ${toAgent.name}` : "Unknown Agent"}
                              </span>
                              <span className="text-[9px] text-muted-foreground">{timeAgo(msg.created_at)}</span>
                            </div>
                            <p className={`text-xs text-muted-foreground ml-6 ${isExpanded ? "" : "line-clamp-3"}`}>
                              {msg.message}
                            </p>
                          </button>

                          {isExpanded && msg.task_id && (
                            <div className="px-4 py-2.5 bg-accent/30 border-t border-border/50">
                              <p className="text-[10px] text-muted-foreground">
                                Task: <span className="text-foreground font-mono">{msg.task_id}</span>
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── Tasks Created tab ────────────────────────── */}
            {activeTab === "sub-agents" && (
              <div className="px-5 py-3">
                {recentTasks.length === 0 ? (
                  <EmptyState
                    icon="📝"
                    title="No recent tasks"
                    description={`No tasks were created in the last ${hours} hours.`}
                  />
                ) : (
                  <div className="space-y-2">
                    {recentTasks.map((task) => {
                      const assignee = agents.find((a) => a.id === task.assignee_id);
                      return (
                        <div
                          key={task.id}
                          className="bg-card border border-border rounded-lg px-4 py-3 hover:border-muted-foreground transition"
                        >
                          <div className="flex items-start justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-muted-foreground font-mono">{task.id}</span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                task.priority === "P0" ? "bg-red-500/20 text-red-400" :
                                task.priority === "P1" ? "bg-amber-500/20 text-amber-400" :
                                task.priority === "P2" ? "bg-primary/20 text-primary" :
                                "bg-muted text-muted-foreground"
                              }`}>
                                {task.priority}
                              </span>
                            </div>
                            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                              task.status === "done" ? "bg-green-500/15 text-green-400" :
                              task.status === "in_progress" ? "bg-primary/15 text-primary" :
                              task.status === "review" ? "bg-purple-500/15 text-purple-400" :
                              task.status === "assigned" ? "bg-amber-500/15 text-amber-400" :
                              "bg-muted text-muted-foreground"
                            }`}>
                              {task.status.replace("_", " ").toUpperCase()}
                            </span>
                          </div>

                          <h4 className="text-sm font-medium text-foreground mb-1">{task.title}</h4>

                          {task.brief && (
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{task.brief}</p>
                          )}

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {assignee ? (
                                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                  {assignee.avatar_emoji} {assignee.name}
                                </span>
                              ) : (
                                <span className="text-[11px] text-muted-foreground italic">Unassigned</span>
                              )}
                            </div>
                            <span className="text-[10px] text-muted-foreground">{fmtDateTime(task.created_at)}</span>
                          </div>

                          {task.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {task.tags.map((tag) => (
                                <span key={tag} className="text-[9px] px-1.5 py-0.5 rounded bg-accent text-muted-foreground border border-border">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── Deliverables tab ─────────────────────────── */}
            {activeTab === "deliverables" && (
              <div className="px-5 py-3">
                {deliverables.length === 0 ? (
                  <EmptyState
                    icon="📦"
                    title="No deliverables pending review"
                    description="When agents complete tasks with deliverables, they will appear here for review."
                  />
                ) : (
                  <div className="space-y-2">
                    {deliverables.map((d) => {
                      const creator = agents.find((a) => a.id === d.created_by_agent_id);
                      return (
                        <div
                          key={d.id}
                          className="bg-card border border-border rounded-lg overflow-hidden hover:border-muted-foreground transition"
                        >
                          <div className="px-4 py-3">
                            <div className="flex items-center justify-between mb-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-sm">
                                  {d.deliverable_type === "document" ? "📄" :
                                   d.deliverable_type === "image" ? "🖼️" :
                                   d.deliverable_type === "code" ? "💻" :
                                   d.deliverable_type === "report" ? "📊" :
                                   "📦"}
                                </span>
                                <h4 className="text-sm font-medium text-foreground">{d.title}</h4>
                              </div>
                              <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                                d.status === "approved" ? "bg-green-500/15 text-green-400" :
                                d.status === "rejected" ? "bg-red-500/15 text-red-400" :
                                d.status === "review" ? "bg-amber-500/15 text-amber-400" :
                                "bg-muted text-muted-foreground"
                              }`}>
                                {d.status.toUpperCase()}
                              </span>
                            </div>

                            {creator && (
                              <p className="text-[11px] text-muted-foreground mb-2">
                                Created by {creator.avatar_emoji} {creator.name}
                              </p>
                            )}

                            {d.content && (
                              <div className="bg-accent/50 border border-border/50 rounded-lg p-3 max-h-40 overflow-y-auto">
                                <pre className="text-xs text-foreground whitespace-pre-wrap font-sans leading-relaxed">
                                  {d.content}
                                </pre>
                              </div>
                            )}

                            {d.file_path && (
                              <p className="text-[10px] text-muted-foreground mt-2 font-mono">
                                📁 {d.file_path}
                              </p>
                            )}

                            {d.feedback && (
                              <div className="mt-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/20">
                                <p className="text-[10px] text-amber-500 uppercase tracking-wider font-bold mb-0.5">Feedback</p>
                                <p className="text-xs text-foreground">{d.feedback}</p>
                              </div>
                            )}
                          </div>

                          {d.status === "review" && (
                            <div className="px-4 py-2.5 bg-accent/20 border-t border-border/50 flex items-center justify-end gap-2">
                              <button
                                onClick={async () => {
                                  const reason = prompt("Rejection reason (optional):");
                                  try {
                                    await missionControlApi.updateDeliverable(d.id, "rejected", reason || undefined);
                                    await loadData();
                                  } catch {}
                                }}
                                className="px-3 py-1.5 rounded-lg text-[10px] font-bold text-red-400 border border-red-500/30 hover:bg-red-500/10 transition"
                              >
                                Reject
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    await missionControlApi.updateDeliverable(d.id, "approved");
                                    await loadData();
                                  } catch {}
                                }}
                                className="px-3 py-1.5 rounded-lg text-[10px] font-bold bg-green-600 text-white hover:bg-green-500 transition"
                              >
                                Approve
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Empty state ───────────────────────────────────────── */

function EmptyState({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="text-center py-16">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-xs mx-auto">{description}</p>
    </div>
  );
}
