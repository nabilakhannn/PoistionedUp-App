"use client";

import { DashboardStats } from "@/lib/api/mission-control";

interface StatsBarProps {
  stats: DashboardStats | null;
  filterAgent: string | null;
  agentName: string | null;
  onBroadcast: () => void;
}

export function StatsBar({ stats, filterAgent, agentName, onBroadcast }: StatsBarProps) {
  const now = new Date();
  const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  const dateStr = now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }).toUpperCase();

  return (
    <div className="h-14 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between px-5">
      {/* Left: Title and stats */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-amber-400 text-lg">◇</span>
          <h1 className="text-sm font-bold text-zinc-200 tracking-wider uppercase">Mission Control</h1>
        </div>

        {stats && (
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-lg font-bold text-zinc-100 leading-none">{stats.agents_active}</div>
              <div className="text-[9px] text-zinc-500 uppercase tracking-wider">Agents Active</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-zinc-100 leading-none">{stats.tasks_total}</div>
              <div className="text-[9px] text-zinc-500 uppercase tracking-wider">Tasks in Queue</div>
            </div>
          </div>
        )}

        {filterAgent && agentName && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-800 border border-zinc-700">
            <span className="text-[10px] text-zinc-500 uppercase">Filtering by</span>
            <span className="text-xs font-medium text-amber-400">{agentName}</span>
          </div>
        )}
      </div>

      {/* Right: Actions and time */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBroadcast}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 hover:bg-zinc-700 transition"
        >
          <span>📢</span> Broadcast
        </button>

        <div className="text-right">
          <div className="text-sm font-mono text-zinc-200 leading-none">{timeStr}</div>
          <div className="text-[9px] text-zinc-500">{dateStr}</div>
        </div>

        <div className="flex items-center gap-1 ml-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[10px] text-green-400 font-bold">ONLINE</span>
        </div>
      </div>
    </div>
  );
}
