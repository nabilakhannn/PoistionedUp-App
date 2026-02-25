"use client";

import { AgentTask, Agent } from "@/lib/api/mission-control";
import { PRIORITY_COLORS } from "../constants";

interface TaskCardProps {
  task: AgentTask;
  agents: Agent[];
  onClick: (task: AgentTask) => void;
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

export function TaskCard({ task, agents, onClick }: TaskCardProps) {
  const assignee = agents.find((a) => a.id === task.assignee_id);
  const priorityBorder = PRIORITY_COLORS[task.priority] || "border-l-zinc-600";

  return (
    <button
      onClick={() => onClick(task)}
      className={`w-full text-left bg-zinc-900 border border-zinc-800 rounded-lg p-3.5 hover:border-zinc-700 transition group border-l-[3px] ${priorityBorder}`}
    >
      {/* Priority badge */}
      <div className="flex items-start justify-between mb-1.5">
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
          task.priority === "P0" ? "bg-red-500/20 text-red-400" :
          task.priority === "P1" ? "bg-amber-500/20 text-amber-400" :
          task.priority === "P2" ? "bg-blue-500/20 text-blue-400" :
          "bg-zinc-700/50 text-zinc-500"
        }`}>
          {task.priority}
        </span>
      </div>

      {/* Title */}
      <h4 className="text-sm font-medium text-zinc-200 mb-1 line-clamp-2">{task.title}</h4>

      {/* Brief */}
      {task.brief && (
        <p className="text-xs text-zinc-500 line-clamp-2 mb-3">{task.brief}</p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between">
        {/* Assignee */}
        {assignee ? (
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{assignee.avatar_emoji}</span>
            <span className="text-[11px] text-zinc-400 font-medium">{assignee.name}</span>
          </div>
        ) : (
          <span className="text-[11px] text-zinc-600 italic">Unassigned</span>
        )}

        {/* Time */}
        <span className="text-[10px] text-zinc-600">{timeAgo(task.updated_at)}</span>
      </div>

      {/* Tags */}
      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {task.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700">
              {tag}
            </span>
          ))}
          {task.tags.length > 3 && (
            <span className="text-[10px] text-zinc-600">+{task.tags.length - 3}</span>
          )}
        </div>
      )}
    </button>
  );
}
