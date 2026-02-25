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

  const jarvis = agents.find((a) => a.id === "jarvis");
  const subAgents = orchestratorData?.sub_agent_statuses || [];

  const loadData = useCallback(async () => {
    try {
      const [orchRes, agentsRes, delivRes] = await Promise.all([
        missionControlApi.getOrchestratorActivity(hours),
        missionControlApi.listAgents(),
        missionControlApi.listDeliverables({ status: "review" }),
      ]);
      setOrchestratorData(orchRes);
      setAgents(agentsRes);
      setDeliverables(delivRes);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load orchestrator data");
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  /* ── Loading / Error ──────────────────────────────────── */

  if (loading) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-zinc-400">Loading Orchestrator view...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-lg font-semibold text-zinc-200 mb-2">Load Error</h2>
          <p className="text-sm text-zinc-400 mb-4">{error}</p>
          <button onClick={loadData} className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 transition">
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
    <div className="h-screen bg-zinc-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <span className="text-amber-400 text-lg">◇</span>
          <h1 className="text-sm font-bold text-zinc-200 tracking-wider uppercase">Orchestrator View</h1>
          {jarvis && (
            <div className="flex items-center gap-2 ml-3 px-3 py-1 rounded-full bg-zinc-800 border border-zinc-700">
              <span className="text-lg">{jarvis.avatar_emoji}</span>
              <span className="text-xs font-medium text-zinc-300">{jarvis.name}</span>
              <span className={`w-1.5 h-1.5 rounded-full ${
                (STATUS_COLORS[jarvis.status] || STATUS_COLORS.idle).dot
              } ${jarvis.status === "working" ? "animate-pulse" : ""}`} />
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Time range selector */}
          <div className="flex items-center gap-1 bg-zinc-800 rounded-lg border border-zinc-700 p-0.5">
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
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-zinc-500 hover:text-zinc-300"
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
      <div className="h-10 border-b border-zinc-800 bg-zinc-900/50 flex items-center px-5 gap-1">
        <Link href="/mission-control" className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition">
          Dashboard
        </Link>
        <Link href="/mission-control/analytics" className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition">
          Analytics
        </Link>
        <Link href="/mission-control/orchestrator" className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600/15 text-blue-400 border border-blue-500/20">
          Orchestrator
        </Link>
      </div>

      {/* Main content: 2-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left panel: Sub-agents + Stats ─────────────── */}
        <div className="w-72 flex-shrink-0 border-r border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
          {/* Jarvis stats */}
          <div className="px-4 py-4 border-b border-zinc-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-full bg-zinc-800 border-2 border-amber-500/30 flex items-center justify-center text-2xl">
                {jarvis?.avatar_emoji || "🎯"}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-100">{jarvis?.name || "Jarvis"}</h3>
                <p className="text-[10px] text-zinc-500">{jarvis?.role || "Orchestrator"}</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="text-center px-2 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800">
                <div className="text-lg font-bold text-zinc-100 font-mono">{delegations.length}</div>
                <div className="text-[8px] text-zinc-500 uppercase">Delegated</div>
              </div>
              <div className="text-center px-2 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800">
                <div className="text-lg font-bold text-zinc-100 font-mono">{recentTasks.length}</div>
                <div className="text-[8px] text-zinc-500 uppercase">Created</div>
              </div>
              <div className="text-center px-2 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800">
                <div className="text-lg font-bold text-zinc-100 font-mono">{timeline.length}</div>
                <div className="text-[8px] text-zinc-500 uppercase">Messages</div>
              </div>
            </div>
          </div>

          {/* Sub-agent roster */}
          <div className="px-4 py-2.5 border-b border-zinc-800">
            <h3 className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold flex items-center gap-1.5">
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
                  className="px-4 py-3 border-b border-zinc-800/50 hover:bg-zinc-800/20 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-base border border-zinc-700 flex-shrink-0">
                      {agent.avatar_emoji}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-medium text-zinc-200 truncate">{agent.name}</span>
                        <span className={`text-[8px] px-1 py-0.5 rounded border font-bold ${roleStyle.color}`}>
                          {roleStyle.label}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-500">{agent.role}</span>
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
                    <p className="text-[10px] text-zinc-400 mt-1.5 ml-10 line-clamp-2">
                      {agent.status_reason}
                    </p>
                  )}
                  {agent.last_heartbeat_at && (
                    <p className="text-[9px] text-zinc-600 mt-0.5 ml-10">
                      Last heartbeat: {timeAgo(agent.last_heartbeat_at)}
                    </p>
                  )}
                </div>
              );
            })}
            {subAgents.length === 0 && (
              <div className="text-center py-8 text-xs text-zinc-600">
                No sub-agents found
              </div>
            )}
          </div>
        </div>

        {/* ── Right panel: Activity feed ─────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="h-10 border-b border-zinc-800 flex items-center px-5 gap-4">
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
                    ? "text-blue-400 border-blue-400"
                    : "text-zinc-500 border-transparent hover:text-zinc-300"
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                  activeTab === tab.key ? "bg-blue-500/20 text-blue-400" : "bg-zinc-800 text-zinc-500"
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
                          className="w-full text-left px-4 py-2.5 rounded-lg hover:bg-zinc-800/40 transition group"
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
                                  <span className="text-xs font-medium text-zinc-200">
                                    {fromAgent.avatar_emoji} {fromAgent.name}
                                  </span>
                                ) : (
                                  <span className="text-xs font-medium text-amber-400">👤 You</span>
                                )}
                                {toAgent && (
                                  <>
                                    <span className="text-zinc-600 text-[10px]">→</span>
                                    <span className="text-xs text-zinc-400">
                                      {toAgent.avatar_emoji} {toAgent.name}
                                    </span>
                                  </>
                                )}
                                {!toAgent && msg.message_type === "broadcast" && (
                                  <>
                                    <span className="text-zinc-600 text-[10px]">→</span>
                                    <span className="text-xs text-cyan-400">📢 All Agents</span>
                                  </>
                                )}
                              </div>
                              <p className={`text-xs text-zinc-400 ${isExpanded ? "" : "line-clamp-2"}`}>
                                {msg.message}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                                  msg.message_type === "delegation" ? "bg-amber-500/15 text-amber-400" :
                                  msg.message_type === "escalation" ? "bg-red-500/15 text-red-400" :
                                  msg.message_type === "deliverable" ? "bg-purple-500/15 text-purple-400" :
                                  msg.message_type === "broadcast" ? "bg-cyan-500/15 text-cyan-400" :
                                  msg.message_type === "status" ? "bg-green-500/15 text-green-400" :
                                  "bg-zinc-700/50 text-zinc-500"
                                }`}>
                                  {msg.message_type.toUpperCase()}
                                </span>
                                <span className="text-[9px] text-zinc-600">{fmtDateTime(msg.created_at)}</span>
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
                    description={`Jarvis hasn't delegated any tasks in the last ${hours} hours.`}
                  />
                ) : (
                  <div className="space-y-2">
                    {delegations.map((msg) => {
                      const toAgent = agents.find((a) => a.id === msg.to_agent_id);
                      const isExpanded = expandedMessage === msg.id;
                      return (
                        <div
                          key={msg.id}
                          className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden hover:border-zinc-700 transition"
                        >
                          <button
                            onClick={() => setExpandedMessage(isExpanded ? null : msg.id)}
                            className="w-full text-left px-4 py-3"
                          >
                            <div className="flex items-center gap-2.5 mb-1.5">
                              <span className="text-amber-400 text-sm">📋</span>
                              <span className="text-xs font-medium text-zinc-200 flex-1">
                                Delegated to {toAgent ? `${toAgent.avatar_emoji} ${toAgent.name}` : "Unknown Agent"}
                              </span>
                              <span className="text-[9px] text-zinc-600">{timeAgo(msg.created_at)}</span>
                            </div>
                            <p className={`text-xs text-zinc-400 ml-6 ${isExpanded ? "" : "line-clamp-3"}`}>
                              {msg.message}
                            </p>
                          </button>

                          {isExpanded && msg.task_id && (
                            <div className="px-4 py-2.5 bg-zinc-800/30 border-t border-zinc-800/50">
                              <p className="text-[10px] text-zinc-500">
                                Task: <span className="text-zinc-300 font-mono">{msg.task_id}</span>
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
                          className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 hover:border-zinc-700 transition"
                        >
                          <div className="flex items-start justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-zinc-600 font-mono">{task.id}</span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                task.priority === "P0" ? "bg-red-500/20 text-red-400" :
                                task.priority === "P1" ? "bg-amber-500/20 text-amber-400" :
                                task.priority === "P2" ? "bg-blue-500/20 text-blue-400" :
                                "bg-zinc-700/50 text-zinc-500"
                              }`}>
                                {task.priority}
                              </span>
                            </div>
                            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                              task.status === "done" ? "bg-green-500/15 text-green-400" :
                              task.status === "in_progress" ? "bg-blue-500/15 text-blue-400" :
                              task.status === "review" ? "bg-purple-500/15 text-purple-400" :
                              task.status === "assigned" ? "bg-amber-500/15 text-amber-400" :
                              "bg-zinc-700/50 text-zinc-500"
                            }`}>
                              {task.status.replace("_", " ").toUpperCase()}
                            </span>
                          </div>

                          <h4 className="text-sm font-medium text-zinc-200 mb-1">{task.title}</h4>

                          {task.brief && (
                            <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{task.brief}</p>
                          )}

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {assignee ? (
                                <span className="flex items-center gap-1 text-[11px] text-zinc-400">
                                  {assignee.avatar_emoji} {assignee.name}
                                </span>
                              ) : (
                                <span className="text-[11px] text-zinc-600 italic">Unassigned</span>
                              )}
                            </div>
                            <span className="text-[10px] text-zinc-600">{fmtDateTime(task.created_at)}</span>
                          </div>

                          {task.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {task.tags.map((tag) => (
                                <span key={tag} className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700">
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
                          className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden hover:border-zinc-700 transition"
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
                                <h4 className="text-sm font-medium text-zinc-200">{d.title}</h4>
                              </div>
                              <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                                d.status === "approved" ? "bg-green-500/15 text-green-400" :
                                d.status === "rejected" ? "bg-red-500/15 text-red-400" :
                                d.status === "review" ? "bg-amber-500/15 text-amber-400" :
                                "bg-zinc-700/50 text-zinc-500"
                              }`}>
                                {d.status.toUpperCase()}
                              </span>
                            </div>

                            {creator && (
                              <p className="text-[11px] text-zinc-500 mb-2">
                                Created by {creator.avatar_emoji} {creator.name}
                              </p>
                            )}

                            {d.content && (
                              <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
                                <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-sans leading-relaxed">
                                  {d.content}
                                </pre>
                              </div>
                            )}

                            {d.file_path && (
                              <p className="text-[10px] text-zinc-600 mt-2 font-mono">
                                📁 {d.file_path}
                              </p>
                            )}

                            {d.feedback && (
                              <div className="mt-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/20">
                                <p className="text-[10px] text-amber-500 uppercase tracking-wider font-bold mb-0.5">Feedback</p>
                                <p className="text-xs text-zinc-300">{d.feedback}</p>
                              </div>
                            )}
                          </div>

                          {d.status === "review" && (
                            <div className="px-4 py-2.5 bg-zinc-800/20 border-t border-zinc-800/50 flex items-center justify-end gap-2">
                              <button
                                onClick={async () => {
                                  try {
                                    await missionControlApi.listDeliverables({ task_id: d.task_id });
                                    // TODO: Implement approve/reject via deliverable status update
                                  } catch {}
                                }}
                                className="px-3 py-1.5 rounded-lg text-[10px] font-bold text-red-400 border border-red-500/30 hover:bg-red-500/10 transition"
                              >
                                Reject
                              </button>
                              <button
                                onClick={async () => {
                                  try {
                                    await missionControlApi.listDeliverables({ task_id: d.task_id });
                                    // TODO: Implement approve
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
      <h3 className="text-sm font-semibold text-zinc-300 mb-1">{title}</h3>
      <p className="text-xs text-zinc-500 max-w-xs mx-auto">{description}</p>
    </div>
  );
}
