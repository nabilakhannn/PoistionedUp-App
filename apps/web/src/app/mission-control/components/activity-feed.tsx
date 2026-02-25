"use client";

import { useState } from "react";
import { AgentMessage, Agent } from "@/lib/api/mission-control";
import { MESSAGE_TYPE_ICONS } from "../constants";

interface ActivityFeedProps {
  messages: AgentMessage[];
  agents: Agent[];
  onClose: () => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const TYPE_COLORS: Record<string, string> = {
  delegation: "border-l-amber-500",
  escalation: "border-l-red-500",
  deliverable: "border-l-green-500",
  status: "border-l-blue-500",
  broadcast: "border-l-purple-500",
  chat: "border-l-zinc-600",
};

const FILTER_OPTIONS = [
  { key: "all", label: "All" },
  { key: "delegation", label: "Delegations" },
  { key: "status", label: "Status" },
  { key: "deliverable", label: "Deliverables" },
  { key: "escalation", label: "Escalations" },
  { key: "broadcast", label: "Broadcasts" },
  { key: "chat", label: "Chat" },
];

export function ActivityFeed({ messages, agents, onClose }: ActivityFeedProps) {
  const [filter, setFilter] = useState("all");

  const agentMap = new Map(agents.map((a) => [a.id, a]));

  const filtered = filter === "all"
    ? messages
    : messages.filter((m) => m.message_type === filter);

  // Sort newest first
  const sorted = [...filtered].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="w-80 flex-shrink-0 border-l border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          LIVE FEED
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-600 font-mono">{sorted.length}</span>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition p-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="px-3 py-2 border-b border-zinc-800 flex flex-wrap gap-1">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setFilter(opt.key)}
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition ${
              filter === opt.key
                ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                : "bg-zinc-800 text-zinc-500 border border-zinc-700 hover:text-zinc-300"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-3xl mb-2">📡</div>
            <p className="text-xs text-zinc-600">No activity yet</p>
            <p className="text-[10px] text-zinc-700 mt-1">Agent messages will appear here in real-time</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {sorted.map((msg) => {
              const fromAgent = msg.from_agent_id ? agentMap.get(msg.from_agent_id) : null;
              const toAgent = msg.to_agent_id ? agentMap.get(msg.to_agent_id) : null;
              const borderColor = TYPE_COLORS[msg.message_type] || TYPE_COLORS.chat;
              const icon = MESSAGE_TYPE_ICONS[msg.message_type] || "💬";

              return (
                <div
                  key={msg.id}
                  className={`px-4 py-3 hover:bg-zinc-900/50 transition border-l-2 ${borderColor}`}
                >
                  {/* Header row */}
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-sm flex-shrink-0">{icon}</span>
                      {fromAgent ? (
                        <span className="text-[11px] font-semibold text-zinc-300 truncate flex items-center gap-1">
                          <span>{fromAgent.avatar_emoji}</span>
                          {fromAgent.name}
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-zinc-500 truncate">
                          {msg.from_agent_id || "System"}
                        </span>
                      )}
                      {toAgent && (
                        <>
                          <span className="text-[10px] text-zinc-600">→</span>
                          <span className="text-[11px] text-zinc-400 truncate flex items-center gap-1">
                            <span>{toAgent.avatar_emoji}</span>
                            {toAgent.name}
                          </span>
                        </>
                      )}
                    </div>
                    <span className="text-[10px] text-zinc-600 flex-shrink-0 ml-2">
                      {timeAgo(msg.created_at)}
                    </span>
                  </div>

                  {/* Message body */}
                  <p className="text-xs text-zinc-400 leading-relaxed line-clamp-3 ml-6">
                    {msg.message}
                  </p>

                  {/* Task reference */}
                  {msg.task_id && (
                    <div className="mt-1.5 ml-6">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700 font-mono">
                        {msg.task_id}
                      </span>
                    </div>
                  )}

                  {/* Type badge */}
                  <div className="mt-1.5 ml-6">
                    <span className={`text-[9px] uppercase tracking-wider font-bold ${
                      msg.message_type === "escalation" ? "text-red-400" :
                      msg.message_type === "delegation" ? "text-amber-400" :
                      msg.message_type === "deliverable" ? "text-green-400" :
                      msg.message_type === "broadcast" ? "text-purple-400" :
                      "text-zinc-600"
                    }`}>
                      {msg.message_type}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
