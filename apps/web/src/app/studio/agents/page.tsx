"use client";

/**
 * Agents Page — extracted from intelligence/page.tsx (Slice 107)
 *
 * Live status of all 8 agents + send task + training panel + activity feed.
 * Accessible via /studio/agents (linked from Jumbo Hub sidebar).
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { gatewayApi, GatewayAgent } from "@/lib/api/gateway";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import AgentTrainingPanel from "@/components/agent-training-panel";

const AGENT_EMOJIS: Record<string, string> = {
  jumbo: "🧠",
  copywriter: "✍️",
  "qa-reviewer": "✔️",
  "trend-analyzer": "🔍",
  "competitor-analyst": "🎯",
  "visual-designer": "🎨",
  distributor: "📤",
  analytics: "📊",
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  jumbo: "Lead orchestrator. Directs all agents, reads playbooks, makes strategic decisions.",
  copywriter: "Writes LinkedIn posts, emails, hooks, carousels, and ad copy.",
  "qa-reviewer": "Scores every piece of content across 6 dimensions before it goes live.",
  "trend-analyzer": "Researches trending topics and writes the intel brief each pipeline run.",
  "competitor-analyst": "Monitors competitors daily — threat scores, gaps, and alerts.",
  "visual-designer": "Generates image prompts and directs visual identity for posts.",
  distributor: "Publishes approved content to LinkedIn, Twitter, Instagram.",
  analytics: "Tracks performance and flags what's working vs. what needs to change.",
};

const DEFAULT_AGENTS = [
  "jumbo", "copywriter", "qa-reviewer", "trend-analyzer",
  "competitor-analyst", "visual-designer", "distributor", "analytics",
];

interface ActivityItem {
  id: string;
  agent_id: string;
  task_type: string;
  summary: string;
  status: string;
  created_at: string;
  emoji: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<GatewayAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [sendingTo, setSendingTo] = useState<string | null>(null);
  const [taskInputs, setTaskInputs] = useState<Record<string, string>>({});
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [activityFeed, setActivityFeed] = useState<ActivityItem[]>([]);
  const [activityLoading, setActivityLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    gatewayApi.agents()
      .then((data) => {
        setAgents(data);
        setConnected(data.length > 0);
      })
      .catch(() => setConnected(false))
      .finally(() => setLoading(false));
  }, []);

  // Activity feed (polls every 15s)
  useEffect(() => {
    const load = () => {
      agentBridgeApi.getActivityFeed(20)
        .then((res) => setActivityFeed(res.items))
        .catch(() => {})
        .finally(() => setActivityLoading(false));
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  const handleSendTask = useCallback(async (agentId: string) => {
    const msg = taskInputs[agentId]?.trim();
    if (!msg) return;
    setSendingTo(agentId);
    try {
      const res = await gatewayApi.sendMessage(agentId, msg);
      setResponses((prev) => ({ ...prev, [agentId]: res.response || "Task delivered." }));
      setTaskInputs((prev) => ({ ...prev, [agentId]: "" }));
    } catch {
      setResponses((prev) => ({ ...prev, [agentId]: "Failed to reach agent. Check gateway connection." }));
    } finally {
      setSendingTo(null);
    }
  }, [taskInputs]);

  const displayAgents = agents.length > 0
    ? agents
    : DEFAULT_AGENTS.map((id) => ({ id, name: id, status: "offline" as const }));

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="flex items-center gap-3">
          <Link href="/intelligence" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            ← Back to Jumbo Hub
          </Link>
        </div>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2 mt-2">
          🤖 Manage Agents
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Monitor, task, and train your 8-agent squad.
        </p>
      </div>

      <div className="px-6 py-6 max-w-5xl space-y-4">
        {/* Connection status */}
        <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${connected ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
          {connected ? `${agents.length} agents connected via OpenClaw gateway` : "Gateway offline — showing cached agent list. Check VPS."}
          <Link href="/mission-control/gateway" className="ml-auto underline">Gateway status →</Link>
        </div>

        {/* Agent cards */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-card/30 p-4 animate-pulse h-28" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {displayAgents.map((agent) => {
              const emoji = AGENT_EMOJIS[agent.id] || "🤖";
              const desc = AGENT_DESCRIPTIONS[agent.id] || "Specialist agent.";
              const isOnline = connected;
              const isSending = sendingTo === agent.id;
              const response = responses[agent.id];
              return (
                <div key={agent.id} className={`rounded-xl border bg-card ${isOnline ? "border-border" : "border-border/50 opacity-70"}`}>
                  <div className="p-4 space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="text-2xl">{emoji}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-foreground capitalize">{agent.name || agent.id}</p>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${isOnline ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-500"}`}>
                            {isOnline ? "ONLINE" : "OFFLINE"}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{desc}</p>
                      </div>
                      <button
                        onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
                        className={`shrink-0 text-[10px] px-2 py-1 rounded-lg border transition ${expandedAgent === agent.id ? "border-indigo-500/50 text-indigo-400 bg-indigo-950/30" : "border-border text-muted-foreground hover:text-foreground hover:border-border"}`}
                      >
                        {expandedAgent === agent.id ? "▲ Close" : "🎓 Train"}
                      </button>
                    </div>
                    {isOnline && (
                      <div className="flex gap-2">
                        <input
                          value={taskInputs[agent.id] || ""}
                          onChange={(e) => setTaskInputs((prev) => ({ ...prev, [agent.id]: e.target.value }))}
                          onKeyDown={(e) => e.key === "Enter" && handleSendTask(agent.id)}
                          placeholder={`Give ${agent.name || agent.id} a task...`}
                          className="flex-1 bg-muted/30 border border-border rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                        <button
                          onClick={() => handleSendTask(agent.id)}
                          disabled={isSending || !taskInputs[agent.id]?.trim()}
                          className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-40"
                        >
                          {isSending ? "..." : "Send"}
                        </button>
                      </div>
                    )}
                    {response && (
                      <p className="text-[10px] text-muted-foreground bg-muted/20 rounded p-2 line-clamp-3 italic">{response}</p>
                    )}
                  </div>
                  {expandedAgent === agent.id && (
                    <div className="border-t border-border/50 p-4 bg-[#0d1117]">
                      <AgentTrainingPanel agentId={agent.id} agentName={agent.name || agent.id} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Activity Feed */}
        <div className="rounded-xl border border-border bg-card/50">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Agent Activity Feed</h3>
            <span className="text-[10px] text-muted-foreground">Live · updates every 15s</span>
          </div>
          {activityLoading ? (
            <div className="p-4 space-y-2">
              {[...Array(5)].map((_, i) => <div key={i} className="h-8 rounded bg-muted/20 animate-pulse" />)}
            </div>
          ) : activityFeed.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No agent activity yet. Run the pipeline to see agents in action.
            </div>
          ) : (
            <div className="divide-y divide-border/50 max-h-80 overflow-y-auto">
              {activityFeed.map((item) => (
                <div key={item.id} className="flex items-start gap-3 px-4 py-2.5">
                  <span className="text-base shrink-0 mt-0.5">{item.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground capitalize">{item.agent_id}</span>
                      <span className={`text-[9px] px-1 py-0.5 rounded font-mono ${item.status === "done" ? "bg-green-500/15 text-green-400" : item.status === "error" ? "bg-red-500/15 text-red-400" : "bg-zinc-500/15 text-zinc-400"}`}>
                        {item.status}
                      </span>
                      <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                        {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate mt-0.5">{item.summary}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
