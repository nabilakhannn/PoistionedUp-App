"use client";

import { Agent } from "@/lib/api/mission-control";
import { ROLE_TYPE_BADGES, STATUS_COLORS } from "../constants";

interface AgentSidebarProps {
  agents: Agent[];
  selectedAgentId: string | null;
  onSelectAgent: (agentId: string | null) => void;
  filterAgent: string | null;
  onFilterAgent: (agentId: string | null) => void;
}

export function AgentSidebar({ agents, selectedAgentId, onSelectAgent, filterAgent, onFilterAgent }: AgentSidebarProps) {
  const activeCount = agents.filter((a) => a.status === "working").length;

  return (
    <div className="w-64 flex-shrink-0 border-r border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            Agents
          </h2>
          <span className="text-xs text-zinc-500 font-mono">{agents.length}</span>
        </div>
      </div>

      {/* All Agents button */}
      <button
        onClick={() => {
          onSelectAgent(null);
          onFilterAgent(null);
        }}
        className={`mx-3 mt-3 flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
          filterAgent === null && selectedAgentId === null
            ? "bg-blue-600/15 text-blue-400 border border-blue-500/20"
            : "text-zinc-300 hover:bg-zinc-800 border border-transparent"
        }`}
      >
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-sm">
          🌐
        </div>
        <div className="flex-1 text-left">
          <div>All Agents</div>
          <div className="text-[10px] text-zinc-500 font-normal">{agents.length} total</div>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          <span className="text-[10px] text-green-400 font-medium">{activeCount} ACTIVE</span>
        </div>
      </button>

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
        {agents.map((agent) => {
          const roleStyle = ROLE_TYPE_BADGES[agent.role_type] || ROLE_TYPE_BADGES.specialist;
          const statusStyle = STATUS_COLORS[agent.status] || STATUS_COLORS.idle;
          const isSelected = selectedAgentId === agent.id;
          const isFiltered = filterAgent === agent.id;

          return (
            <button
              key={agent.id}
              onClick={() => {
                onSelectAgent(agent.id);
                onFilterAgent(agent.id);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition ${
                isSelected || isFiltered
                  ? "bg-zinc-800 border border-zinc-700"
                  : "hover:bg-zinc-800/60 border border-transparent"
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-lg flex-shrink-0 border border-zinc-700">
                {agent.avatar_emoji}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-200 font-medium truncate">{agent.name}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold ${roleStyle.color}`}>
                    {roleStyle.label}
                  </span>
                </div>
                <div className="text-[11px] text-zinc-500 truncate">{agent.role}</div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot}`} />
                <span className={`text-[9px] font-bold ${statusStyle.dot.replace("bg-", "text-")}`}>
                  {statusStyle.label}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
