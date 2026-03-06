"use client";

import { useEffect, useState } from "react";
import { missionControlApi, Agent } from "@/lib/api/mission-control";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import AgentTrainingPanel from "@/components/agent-training-panel";

interface ActivityItem {
  id: string;
  agent_id: string;
  task_type: string;
  summary: string;
  status: string;
  created_at: string;
  emoji: string;
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

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-zinc-500",
  working: "bg-emerald-400",
  error: "bg-red-400",
  paused: "bg-amber-400",
};

export function BrandTeamTab({ brandId }: { brandId: string }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [trainingAgent, setTrainingAgent] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      missionControlApi.listAgents().catch(() => []),
      agentBridgeApi.getActivityFeed(20).catch(() => ({ items: [], total: 0 })),
    ]).then(([ag, act]) => {
      setAgents(ag);
      setActivity(act.items ?? []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading agents...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">Your Agent Team</h2>
        <p className="text-xs text-zinc-500 mt-0.5">These agents work behind the scenes. Train them to match your brand voice.</p>
      </div>

      {/* Agent cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {agents.map((agent) => {
          const agentActivity = activity.filter((a) => a.agent_id === agent.id);
          const latest = agentActivity[0];
          return (
            <div key={agent.id} className="glass-card space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[agent.status] ?? "bg-zinc-600"}`} />
                  <span className="text-sm font-medium text-zinc-200 capitalize">{agent.name.replace(/-/g, " ")}</span>
                </div>
                <button
                  onClick={() => setTrainingAgent(trainingAgent === agent.id ? null : agent.id)}
                  className={`text-[11px] px-2 py-1 rounded-lg transition-colors ${
                    trainingAgent === agent.id
                      ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                      : "glass-button"
                  }`}
                >
                  {trainingAgent === agent.id ? "Close" : "Train"}
                </button>
              </div>

              <p className="text-xs text-zinc-500 capitalize">{agent.role.replace(/-/g, " ")}</p>

              {latest && (
                <p className="text-[10px] text-zinc-600">
                  Last: {latest.summary?.slice(0, 60)} · {timeAgo(latest.created_at)}
                </p>
              )}

              {trainingAgent === agent.id && (
                <div className="pt-2 border-t border-white/[0.05]">
                  <AgentTrainingPanel agentId={agent.id} agentName={agent.name} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {agents.length === 0 && (
        <div className="glass-card text-center py-8">
          <p className="text-sm text-zinc-500">No agents found. They appear after your first pipeline run.</p>
        </div>
      )}
    </div>
  );
}
