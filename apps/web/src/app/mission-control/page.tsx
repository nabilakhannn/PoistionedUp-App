"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  missionControlApi,
  Agent,
  AgentTask,
  AgentMessage,
  Deliverable,
  DashboardStats,
} from "@/lib/api/mission-control";
import { AgentSidebar } from "./components/agent-sidebar";
import { TaskBoard } from "./components/task-board";
import { AgentProfile } from "./components/agent-profile";
import { StatsBar } from "./components/stats-bar";
import { ActivityFeed } from "./components/activity-feed";
import { DeliverablesPanel } from "./components/deliverables-panel";

export default function MissionControlPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [showBroadcast, setShowBroadcast] = useState(false);
  const [broadcastMsg, setBroadcastMsg] = useState("");
  const [showNewTask, setShowNewTask] = useState(false);
  const [showLiveFeed, setShowLiveFeed] = useState(false);

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || null;

  const loadData = useCallback(async () => {
    try {
      const [agentsRes, tasksRes, messagesRes, statsRes, deliverablesRes] = await Promise.all([
        missionControlApi.listAgents(),
        missionControlApi.listTasks(),
        missionControlApi.listMessages({ limit: 100 }),
        missionControlApi.getStats(),
        missionControlApi.listDeliverables().catch(() => [] as Deliverable[]),
      ]);
      setAgents(agentsRes);
      setTasks(tasksRes);
      setMessages(messagesRes);
      setStats(statsRes);
      setDeliverables(deliverablesRes);
      setError(null);
    } catch (err: any) {
      console.error("Mission Control load error:", err);
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleSendMessage = async (message: string) => {
    if (!selectedAgentId) return;
    try {
      await missionControlApi.sendMessage({
        to_agent_id: selectedAgentId,
        message,
        message_type: "chat",
      });
      loadData();
    } catch (err) {
      console.error("Send message error:", err);
    }
  };

  const handleBroadcast = async () => {
    if (!broadcastMsg.trim()) return;
    try {
      await missionControlApi.broadcast(broadcastMsg.trim());
      setBroadcastMsg("");
      setShowBroadcast(false);
      loadData();
    } catch (err) {
      console.error("Broadcast error:", err);
    }
  };

  const handleTaskClick = (task: AgentTask) => {
    if (task.assignee_id) {
      setSelectedAgentId(task.assignee_id);
    }
  };

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading Mission Control...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-lg font-semibold text-foreground mb-2">Connection Error</h2>
          <p className="text-sm text-muted-foreground mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Stats Bar */}
      <StatsBar
        stats={stats}
        filterAgent={filterAgent}
        agentName={agents.find((a) => a.id === filterAgent)?.name || null}
        onBroadcast={() => setShowBroadcast(true)}
      />

      {/* Sub-navigation */}
      <div className="h-10 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        <Link
          href="/mission-control"
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary/15 text-primary border border-primary/20"
        >
          Dashboard
        </Link>
        <Link
          href="/mission-control/analytics"
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
        >
          Analytics
        </Link>
        <Link
          href="/mission-control/orchestrator"
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
        >
          Orchestrator
        </Link>
        <Link
          href="/mission-control/gateway"
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
        >
          Gateway
        </Link>
        <Link
          href="/mission-control/chat"
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
        >
          Chat
        </Link>

        <div className="flex-1" />

        <button
          onClick={() => setShowLiveFeed((v) => !v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
            showLiveFeed
              ? "bg-red-500/15 text-red-400 border-red-500/20"
              : "bg-accent text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          <span className="relative flex h-1.5 w-1.5">
            <span className={`absolute inline-flex h-full w-full rounded-full bg-red-400 ${showLiveFeed ? "animate-ping" : ""} opacity-75`} />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500" />
          </span>
          Live Feed
        </button>

        <button
          onClick={() => setShowNewTask(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs font-medium border border-amber-500/20 hover:bg-amber-500/20 transition"
        >
          <span>+</span> New Task
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Agent Sidebar */}
        <AgentSidebar
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          filterAgent={filterAgent}
          onFilterAgent={setFilterAgent}
        />

        {/* Center: Task Board + Deliverables */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <TaskBoard
            tasks={tasks}
            agents={agents}
            filterAgent={filterAgent}
            onTaskClick={handleTaskClick}
          />

          {/* Deliverables Review (collapsible at bottom) */}
          {deliverables.length > 0 && (
            <div className="border-t border-border px-4 py-3 bg-card/30">
              <DeliverablesPanel
                deliverables={deliverables}
                agents={agents}
                onUpdate={loadData}
              />
            </div>
          )}
        </div>

        {/* Right panel: Agent Profile OR Live Feed */}
        {selectedAgent && !showLiveFeed && (
          <AgentProfile
            agent={selectedAgent}
            messages={messages}
            tasks={tasks}
            onClose={() => setSelectedAgentId(null)}
            onSendMessage={handleSendMessage}
          />
        )}

        {showLiveFeed && (
          <ActivityFeed
            messages={messages}
            agents={agents}
            onClose={() => setShowLiveFeed(false)}
          />
        )}
      </div>

      {/* Broadcast modal */}
      {showBroadcast && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-sm font-bold text-foreground mb-1 flex items-center gap-2">
              <span>📢</span> Broadcast to All Agents
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Send a message to every agent in your squad. They will all receive this on their next heartbeat.
            </p>
            <textarea
              value={broadcastMsg}
              onChange={(e) => setBroadcastMsg(e.target.value)}
              placeholder="Type your broadcast message..."
              className="w-full bg-accent border border-border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-muted-foreground resize-none h-24"
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowBroadcast(false); setBroadcastMsg(""); }}
                className="px-4 py-2 rounded-lg text-xs text-muted-foreground hover:text-foreground transition"
              >
                Cancel
              </button>
              <button
                onClick={handleBroadcast}
                disabled={!broadcastMsg.trim()}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-40 transition"
              >
                Send Broadcast
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Task modal */}
      {showNewTask && (
        <NewTaskModal
          agents={agents}
          onClose={() => setShowNewTask(false)}
          onCreate={async (data) => {
            try {
              await missionControlApi.createTask(data);
              setShowNewTask(false);
              loadData();
            } catch (err) {
              console.error("Create task error:", err);
            }
          }}
        />
      )}
    </div>
  );
}

// ── New Task Modal ──────────────────────────────────────

function NewTaskModal({
  agents,
  onClose,
  onCreate,
}: {
  agents: Agent[];
  onClose: () => void;
  onCreate: (data: { id: string; title: string; brief?: string; priority?: string; assignee_id?: string; tags?: string[] }) => void;
}) {
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [priority, setPriority] = useState("P2");
  const [assigneeId, setAssigneeId] = useState("");
  const [tagsStr, setTagsStr] = useState("");

  // Generate next task ID
  const taskId = `PU-${String(Date.now()).slice(-4)}`;

  const handleSubmit = () => {
    if (!title.trim()) return;
    onCreate({
      id: taskId,
      title: title.trim(),
      brief: brief.trim() || undefined,
      priority,
      assignee_id: assigneeId || undefined,
      tags: tagsStr ? tagsStr.split(",").map((t) => t.trim()).filter(Boolean) : undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-lg shadow-2xl">
        <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
          <span>📋</span> New Agent Task
          <span className="text-[10px] text-muted-foreground font-mono ml-auto">{taskId}</span>
        </h3>

        <div className="space-y-3">
          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Task title..."
              className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-muted-foreground"
              autoFocus
            />
          </div>

          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Brief</label>
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What needs to be done..."
              className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-muted-foreground resize-none h-20"
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-muted-foreground"
              >
                <option value="P0">P0 - Critical</option>
                <option value="P1">P1 - High</option>
                <option value="P2">P2 - Normal</option>
                <option value="P3">P3 - Low</option>
              </select>
            </div>

            <div className="flex-1">
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Assign To</label>
              <select
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-muted-foreground"
              >
                <option value="">Unassigned</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.avatar_emoji} {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Tags (comma separated)</label>
            <input
              type="text"
              value={tagsStr}
              onChange={(e) => setTagsStr(e.target.value)}
              placeholder="research, content, social-media"
              className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-muted-foreground"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs text-muted-foreground hover:text-foreground transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim()}
            className="px-4 py-2 rounded-lg bg-amber-500 text-black text-xs font-bold hover:bg-amber-400 disabled:opacity-40 transition"
          >
            Create Task
          </button>
        </div>
      </div>
    </div>
  );
}
