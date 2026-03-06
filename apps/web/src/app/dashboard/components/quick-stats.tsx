"use client";

import Link from "next/link";

interface AnalyticsSummary {
  posts: {
    total_generated: number;
    approved: number;
    rejected: number;
    approval_rate: number;
    avg_qa_score: number;
  };
  agents: { tasks_completed: number; tasks_failed: number; by_agent: Record<string, number> };
  rejection_reasons: Record<string, number>;
}

interface LeadsPulse {
  new_leads: number;
  unreviewed: number;
  active_sequences: number;
}

export function QuickStats({
  perf,
  leadsPulse,
}: {
  perf: AnalyticsSummary | null;
  leadsPulse: LeadsPulse | null;
}) {
  const topRejectionReason = perf?.rejection_reasons
    ? Object.entries(perf.rejection_reasons).sort((a, b) => b[1] - a[1])[0]?.[0]
    : null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Leads Pulse */}
      <div className="glass-card space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Leads Pulse</h3>
        {leadsPulse === null ? (
          <p className="text-xs text-zinc-600">Loading...</p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center">
              <div className="text-2xl font-bold tabular-nums text-zinc-100">{leadsPulse.new_leads}</div>
              <div className="text-[10px] text-zinc-600 mt-0.5">new today</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold tabular-nums ${leadsPulse.unreviewed > 0 ? "text-amber-400" : "text-zinc-100"}`}>
                {leadsPulse.unreviewed}
              </div>
              <div className="text-[10px] text-zinc-600 mt-0.5">unreviewed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold tabular-nums text-zinc-100">{leadsPulse.active_sequences}</div>
              <div className="text-[10px] text-zinc-600 mt-0.5">sequences</div>
            </div>
          </div>
        )}
        <Link href="/growth" className="block text-[10px] text-violet-400 hover:text-violet-300 transition-colors">
          Open Growth room →
        </Link>
      </div>

      {/* Performance */}
      <div className="glass-card space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Performance</h3>
        {perf === null ? (
          <p className="text-xs text-zinc-600">Loading...</p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center">
              <div className="text-2xl font-bold tabular-nums text-zinc-100">
                {perf.posts.total_generated > 0 ? Math.round(perf.posts.approval_rate * 100) : "—"}
                {perf.posts.total_generated > 0 ? "%" : ""}
              </div>
              <div className="text-[10px] text-zinc-600 mt-0.5">approval</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold tabular-nums ${
                perf.posts.avg_qa_score >= 80 ? "text-emerald-400"
                : perf.posts.avg_qa_score >= 60 ? "text-amber-400"
                : "text-zinc-100"
              }`}>
                {perf.posts.avg_qa_score > 0 ? Math.round(perf.posts.avg_qa_score) : "—"}
              </div>
              <div className="text-[10px] text-zinc-600 mt-0.5">avg QA</div>
            </div>
            <div className="text-center">
              <div className="text-xs font-semibold text-zinc-300 leading-tight mt-1">
                {topRejectionReason ? topRejectionReason.replace(/_/g, " ") : "—"}
              </div>
              <div className="text-[10px] text-zinc-600 mt-0.5">top rejection</div>
            </div>
          </div>
        )}
        <Link href="/content/results" className="block text-[10px] text-violet-400 hover:text-violet-300 transition-colors">
          Full results →
        </Link>
      </div>
    </div>
  );
}
