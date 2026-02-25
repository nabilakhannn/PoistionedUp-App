"use client";

import { AgentTask, Agent } from "@/lib/api/mission-control";
import { TASK_STATUS_COLUMNS, TASK_FILTER_TABS } from "../constants";
import { TaskCard } from "./task-card";

interface TaskBoardProps {
  tasks: AgentTask[];
  agents: Agent[];
  filterAgent: string | null;
  onTaskClick: (task: AgentTask) => void;
}

export function TaskBoard({ tasks, agents, filterAgent, onTaskClick }: TaskBoardProps) {
  // Filter by agent if selected
  const filtered = filterAgent
    ? tasks.filter((t) => t.assignee_id === filterAgent)
    : tasks;

  // Group by status
  const grouped: Record<string, AgentTask[]> = {};
  for (const col of TASK_STATUS_COLUMNS) {
    grouped[col.key] = [];
  }
  for (const t of filtered) {
    if (grouped[t.status]) {
      grouped[t.status].push(t);
    } else {
      // put archived/unknown in done
      if (grouped["done"]) grouped["done"].push(t);
    }
  }

  const agentLabel = filterAgent
    ? agents.find((a) => a.id === filterAgent)?.name || filterAgent
    : null;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          {agentLabel ? `${agentLabel.toUpperCase()}'S TASKS` : "ALL TASKS"}
        </h2>
        <span className="text-xs text-zinc-500 font-mono">{filtered.length} tasks</span>
      </div>

      {/* Filter tabs */}
      <div className="px-5 py-2 border-b border-zinc-800 flex items-center gap-1 overflow-x-auto">
        {TASK_FILTER_TABS.map((tab) => {
          const count = tab.key === "all"
            ? filtered.length
            : grouped[tab.key]?.length || 0;
          return (
            <span
              key={tab.key}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700 whitespace-nowrap"
            >
              {tab.label} <span className="text-zinc-500 ml-0.5">{count}</span>
            </span>
          );
        })}
      </div>

      {/* Kanban columns */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex h-full min-w-max">
          {TASK_STATUS_COLUMNS.map((col) => (
            <div key={col.key} className="w-72 flex-shrink-0 flex flex-col border-r border-zinc-800/50 last:border-r-0">
              {/* Column header */}
              <div className="px-4 py-2.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    col.key === "backlog" ? "bg-zinc-500" :
                    col.key === "assigned" ? "bg-amber-500" :
                    col.key === "in_progress" ? "bg-blue-500" :
                    col.key === "review" ? "bg-purple-500" :
                    col.key === "ready" ? "bg-emerald-500" :
                    "bg-green-500"
                  }`} />
                  <span className={`text-xs font-bold uppercase tracking-wider ${col.color}`}>
                    {col.label}
                  </span>
                </div>
                <span className="text-[10px] text-zinc-600 font-mono bg-zinc-800/50 px-1.5 py-0.5 rounded">
                  {grouped[col.key]?.length || 0}
                </span>
              </div>

              {/* Cards */}
              <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
                {(grouped[col.key] || []).map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    agents={agents}
                    onClick={onTaskClick}
                  />
                ))}
                {(grouped[col.key] || []).length === 0 && (
                  <div className="text-center py-8 text-zinc-700 text-xs">
                    No tasks
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
