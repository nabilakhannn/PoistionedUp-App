"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  missionControlApi,
  Agent,
  AgentTask,
  DashboardStats,
} from "@/lib/api/mission-control";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { useBrand } from "@/lib/brand-context";

type RealAnalytics = Awaited<ReturnType<typeof agentBridgeApi.getAnalyticsSummary>>;

export default function ContentResultsPage() {
  const { currentBrand } = useBrand();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realData, setRealData] = useState<RealAnalytics | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [agentsRes, tasksRes, statsRes] = await Promise.all([
        missionControlApi.listAgents(),
        missionControlApi.listTasks(),
        missionControlApi.getStats(),
      ]);
      setAgents(agentsRes);
      setTasks(tasksRes);
      setStats(statsRes);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    agentBridgeApi.getAnalyticsSummary(currentBrand?.id)
      .then(setRealData)
      .catch(() => {});
  }, [currentBrand?.id]);

  useEffect(() => { loadData(); }, [loadData]);

  const agentMetrics = useMemo(() => {
    return agents.map((agent) => {
      const agentTasks = tasks.filter((t) => t.assignee_id === agent.id);
      const completed = agentTasks.filter((t) => t.status === "done" || t.status === "archived");
      return {
        agent,
        totalTasks: agentTasks.length,
        completed: completed.length,
        completionRate: agentTasks.length > 0 ? (completed.length / agentTasks.length) * 100 : 0,
      };
    });
  }, [agents, tasks]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-violet-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-zinc-500">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">{error}</p>
          <button onClick={loadData} className="glass-button-primary text-sm">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Results</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Content performance and agent analytics.</p>
        </div>

        {/* Real Pipeline Analytics */}
        {realData && (
          <section className="glass-card space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Content Pipeline
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="bg-white/[0.03] rounded-xl p-3 text-center ring-1 ring-white/[0.05]">
                <div className="text-2xl font-bold text-zinc-100">{realData.posts.total_generated}</div>
                <div className="text-[10px] text-zinc-500 mt-0.5">Generated</div>
              </div>
              <div className="bg-emerald-500/5 rounded-xl p-3 text-center ring-1 ring-emerald-500/15">
                <div className="text-2xl font-bold text-emerald-400">{realData.posts.approved}</div>
                <div className="text-[10px] text-zinc-500 mt-0.5">Approved</div>
              </div>
              <div className="bg-red-500/5 rounded-xl p-3 text-center ring-1 ring-red-500/15">
                <div className="text-2xl font-bold text-red-400">{realData.posts.rejected}</div>
                <div className="text-[10px] text-zinc-500 mt-0.5">Rejected</div>
              </div>
              <div className="bg-blue-500/5 rounded-xl p-3 text-center ring-1 ring-blue-500/15">
                <div className="text-2xl font-bold text-blue-400">
                  {typeof realData.posts.approval_rate === "number"
                    ? Math.round(realData.posts.approval_rate * 100)
                    : realData.posts.approval_rate}%
                </div>
                <div className="text-[10px] text-zinc-500 mt-0.5">Approval Rate</div>
              </div>
              <div className="bg-amber-500/5 rounded-xl p-3 text-center ring-1 ring-amber-500/15">
                <div className="text-2xl font-bold text-amber-400">
                  {typeof realData.posts.avg_qa_score === "number" ? Math.round(realData.posts.avg_qa_score) : realData.posts.avg_qa_score}
                </div>
                <div className="text-[10px] text-zinc-500 mt-0.5">Avg QA</div>
              </div>
            </div>

            {/* Rejection reasons */}
            {Object.keys(realData.rejection_reasons).length > 0 && (
              <div className="border-t border-white/[0.05] pt-3">
                <p className="text-[10px] text-zinc-500 font-medium mb-2">Rejection Reasons</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(realData.rejection_reasons)
                    .sort((a, b) => b[1] - a[1])
                    .map(([reason, count]) => (
                      <span key={reason} className="glass-badge text-[10px]">
                        {reason.replace(/_/g, " ")} ({count})
                      </span>
                    ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Agent Performance */}
        {agentMetrics.length > 0 && (
          <section className="glass-card space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Agent Performance</h2>
            <div className="space-y-2">
              {agentMetrics
                .filter((m) => m.totalTasks > 0)
                .sort((a, b) => b.totalTasks - a.totalTasks)
                .map((m) => (
                  <div key={m.agent.id} className="flex items-center gap-3 bg-white/[0.02] rounded-xl px-4 py-2.5 ring-1 ring-white/[0.04]">
                    <span className="text-sm font-medium text-zinc-300 w-32 truncate capitalize">
                      {m.agent.name.replace(/-/g, " ")}
                    </span>
                    <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all"
                        style={{ width: `${m.completionRate}%` }}
                      />
                    </div>
                    <span className="text-xs text-zinc-500 w-20 text-right">
                      {m.completed}/{m.totalTasks} ({Math.round(m.completionRate)}%)
                    </span>
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* Summary Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass-card text-center py-4">
              <div className="text-2xl font-bold text-zinc-100">{stats.agents_total}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Agents</div>
            </div>
            <div className="glass-card text-center py-4">
              <div className="text-2xl font-bold text-zinc-100">{stats.tasks_total}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Total Tasks</div>
            </div>
            <div className="glass-card text-center py-4">
              <div className="text-2xl font-bold text-emerald-400">{stats.tasks_completed_today}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Completed Today</div>
            </div>
            <div className="glass-card text-center py-4">
              <div className="text-2xl font-bold text-zinc-100">{stats.messages_today}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Messages Today</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
