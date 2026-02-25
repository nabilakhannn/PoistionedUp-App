"use client";

import { useState } from "react";
import { Agent, AgentMessage, AgentTask } from "@/lib/api/mission-control";
import { ROLE_TYPE_BADGES, STATUS_COLORS, MESSAGE_TYPE_ICONS } from "../constants";

interface AgentProfileProps {
  agent: Agent;
  messages: AgentMessage[];
  tasks: AgentTask[];
  onClose: () => void;
  onSendMessage: (message: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function AgentProfile({ agent, messages, tasks, onClose, onSendMessage }: AgentProfileProps) {
  const [activeTab, setActiveTab] = useState<"attention" | "timeline" | "messages">("attention");
  const [messageInput, setMessageInput] = useState("");

  const roleStyle = ROLE_TYPE_BADGES[agent.role_type] || ROLE_TYPE_BADGES.specialist;
  const statusStyle = STATUS_COLORS[agent.status] || STATUS_COLORS.idle;

  const agentTasks = tasks.filter((t) => t.assignee_id === agent.id);
  const agentMessages = messages.filter(
    (m) => m.from_agent_id === agent.id || m.to_agent_id === agent.id
  );

  const handleSend = () => {
    if (!messageInput.trim()) return;
    onSendMessage(messageInput.trim());
    setMessageInput("");
  };

  return (
    <div className="w-96 flex-shrink-0 border-l border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          Agent Profile
        </h2>
        <button
          onClick={onClose}
          className="text-zinc-500 hover:text-zinc-300 transition p-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Agent info */}
      <div className="px-5 py-5 text-center border-b border-zinc-800">
        <div className="w-16 h-16 rounded-full bg-zinc-800 border-2 border-zinc-700 flex items-center justify-center text-3xl mx-auto mb-3">
          {agent.avatar_emoji}
        </div>
        <h3 className="text-lg font-semibold text-zinc-100">{agent.name}</h3>
        <p className="text-sm text-zinc-400">{agent.role}</p>
        <span className={`inline-block mt-1.5 text-[10px] px-2 py-0.5 rounded border font-bold ${roleStyle.color}`}>
          {roleStyle.label}
        </span>

        {/* Status badge */}
        <div className="mt-3">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${statusStyle.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot} ${agent.status === "working" ? "animate-pulse" : ""}`} />
            {statusStyle.label}
          </span>
        </div>

        {/* Status reason */}
        {agent.status_reason && (
          <div className="mt-3 mx-2 px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-left">
            <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-0.5">Status Reason:</p>
            <p className="text-xs text-zinc-300">{agent.status_reason}</p>
          </div>
        )}

        {/* Last heartbeat */}
        {agent.last_heartbeat_at && (
          <p className="text-[10px] text-zinc-600 mt-2">
            Since {timeAgo(agent.last_heartbeat_at)}
          </p>
        )}
      </div>

      {/* About */}
      <div className="px-5 py-3 border-b border-zinc-800">
        <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">About</p>
        <p className="text-xs text-zinc-300 leading-relaxed">{agent.about || "No description."}</p>
      </div>

      {/* Skills */}
      <div className="px-5 py-3 border-b border-zinc-800">
        <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Skills</p>
        <div className="flex flex-wrap gap-1.5">
          {agent.skills.map((skill) => (
            <span key={skill} className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="px-5 py-2 border-b border-zinc-800 flex items-center gap-4">
        {(["attention", "timeline", "messages"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`text-xs font-medium pb-1 border-b-2 transition capitalize ${
              activeTab === tab
                ? "text-blue-400 border-blue-400"
                : "text-zinc-500 border-transparent hover:text-zinc-300"
            }`}
          >
            {tab === "attention" && `⚠️ Attention`}
            {tab === "attention" && agentTasks.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-[9px]">
                {agentTasks.length}
              </span>
            )}
            {tab === "timeline" && "📅 Timeline"}
            {tab === "messages" && "💬 Messages"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
        {activeTab === "attention" && (
          <>
            {agentTasks.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-4">No active tasks</p>
            ) : (
              agentTasks.map((t) => (
                <div key={t.id} className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-zinc-200">{t.title}</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                      t.priority === "P0" ? "bg-red-500/20 text-red-400" : "bg-zinc-700 text-zinc-400"
                    }`}>{t.priority}</span>
                  </div>
                  {t.brief && <p className="text-zinc-500 line-clamp-2">{t.brief}</p>}
                </div>
              ))
            )}
          </>
        )}

        {activeTab === "timeline" && (
          <>
            {agentMessages.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-4">No activity yet</p>
            ) : (
              agentMessages.slice(0, 20).map((m) => (
                <div key={m.id} className="flex gap-2 text-xs">
                  <span>{MESSAGE_TYPE_ICONS[m.message_type] || "💬"}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-zinc-300 line-clamp-2">{m.message}</p>
                    <p className="text-[10px] text-zinc-600 mt-0.5">{timeAgo(m.created_at)}</p>
                  </div>
                </div>
              ))
            )}
          </>
        )}

        {activeTab === "messages" && (
          <p className="text-xs text-zinc-600 text-center py-4">
            Messages between you and {agent.name} will appear here.
          </p>
        )}
      </div>

      {/* Message input */}
      <div className="px-4 py-3 border-t border-zinc-800">
        <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-1.5">
          Send Message to {agent.name}
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder={`Message ${agent.name}... (@ to mention)`}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
          />
          <button
            onClick={handleSend}
            disabled={!messageInput.trim()}
            className="px-3 py-2 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
