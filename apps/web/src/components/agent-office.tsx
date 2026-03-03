"use client";

/**
 * Agent Office — CSS animated agent desks (Slice 90)
 *
 * Shows all 8 agents in a 2-row grid. Each desk has:
 * - Green glow + typing animation when WORKING
 * - Grey / dim when IDLE
 * - Red tint when ERROR
 * - Speech bubble showing agent.status_reason (fades after 5s)
 *
 * Polled every 15s via missionControlApi.listAgents().
 */

import { useEffect, useState } from "react";
import { missionControlApi, Agent } from "@/lib/api/mission-control";

const AGENT_CONFIG: {
  id: string;
  name: string;
  emoji: string;
  role: string;
}[] = [
  { id: "trend-analyzer", name: "Researcher", emoji: "🔬", role: "Trends & Research" },
  { id: "copywriter", name: "Copywriter", emoji: "✍️", role: "Content Writing" },
  { id: "qa-reviewer", name: "QA Review", emoji: "✅", role: "Quality Gate" },
  { id: "competitor-analyst", name: "Competitors", emoji: "🕵️", role: "Intel & Gaps" },
  { id: "distributor", name: "Distributor", emoji: "📤", role: "Publishing" },
  { id: "analytics", name: "Analytics", emoji: "📊", role: "Performance" },
  { id: "visual-designer", name: "Designer", emoji: "🎨", role: "Visuals" },
  { id: "jumbo", name: "Jumbo", emoji: "🤖", role: "CEO Orchestrator" },
];

function AgentDesk({
  config,
  agent,
}: {
  config: (typeof AGENT_CONFIG)[0];
  agent?: Agent;
}) {
  const [showBubble, setShowBubble] = useState(false);
  const status = agent?.status || "idle";
  const statusReason = agent?.status_reason || "";

  useEffect(() => {
    if (status === "working" && statusReason) {
      setShowBubble(true);
      const timer = setTimeout(() => setShowBubble(false), 5000);
      return () => clearTimeout(timer);
    } else {
      setShowBubble(false);
    }
  }, [status, statusReason]);

  const isWorking = status === "working";
  const isError = status === "error";

  return (
    <div
      className={`relative rounded-xl border p-3 transition-all duration-500 ${
        isWorking
          ? "border-green-500/40 bg-green-500/5 shadow-[0_0_12px_rgba(34,197,94,0.15)]"
          : isError
          ? "border-red-500/30 bg-red-500/5"
          : "border-border/50 bg-card/50"
      }`}
    >
      {/* Desk header */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{config.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-foreground truncate">{config.name}</div>
          <div className="text-[10px] text-muted-foreground/70 truncate">{config.role}</div>
        </div>
        {/* Status indicator */}
        <div
          className={`w-2 h-2 rounded-full flex-shrink-0 ${
            isWorking
              ? "bg-green-400 animate-pulse"
              : isError
              ? "bg-red-400"
              : "bg-zinc-500"
          }`}
        />
      </div>

      {/* Status badge */}
      <div
        className={`text-center py-1 rounded text-[10px] font-mono uppercase tracking-wider ${
          isWorking
            ? "bg-green-500/15 text-green-400"
            : isError
            ? "bg-red-500/15 text-red-400"
            : "bg-zinc-500/10 text-zinc-500"
        }`}
      >
        {isWorking ? (
          <span className="flex items-center justify-center gap-1">
            <span className="inline-block w-1 h-1 bg-green-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="inline-block w-1 h-1 bg-green-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="inline-block w-1 h-1 bg-green-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </span>
        ) : isError ? (
          "error"
        ) : (
          "idle"
        )}
      </div>

      {/* Speech bubble */}
      {showBubble && statusReason && (
        <div className="absolute -top-8 left-0 right-0 z-10 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="mx-2 bg-popover border border-border rounded-lg px-2 py-1 text-[10px] text-foreground shadow-lg line-clamp-2">
            {statusReason}
          </div>
          <div className="w-2 h-2 bg-popover border-r border-b border-border rotate-45 mx-auto -mt-1" />
        </div>
      )}
    </div>
  );
}

export function AgentOffice({ className }: { className?: string }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await missionControlApi.listAgents();
        setAgents(data);
      } catch {
        // Silent — agents may not be reachable
      } finally {
        setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const getAgent = (agentId: string) =>
    agents.find((a) => a.id === agentId || a.name?.toLowerCase() === agentId);

  const workingCount = agents.filter((a) => a.status === "working").length;

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Agent Office
        </h2>
        {!loading && workingCount > 0 && (
          <span className="text-[10px] text-green-400 font-medium">
            {workingCount} working
          </span>
        )}
        {loading && (
          <span className="text-[10px] text-muted-foreground">Connecting...</span>
        )}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {AGENT_CONFIG.map((config) => (
          <AgentDesk key={config.id} config={config} agent={getAgent(config.id)} />
        ))}
      </div>
    </div>
  );
}
