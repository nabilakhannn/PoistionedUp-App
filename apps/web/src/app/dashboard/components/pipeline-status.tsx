"use client";

import Link from "next/link";
import { PipelineSettings } from "@/lib/api/pipeline-settings";
import { UsageSummary } from "@/lib/api/usage";

function timeUntil(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return "now";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  return `${Math.floor(hours / 24)}d`;
}

export function PipelineStatus({
  pipelineSettings,
  usage,
  onRunNow,
  onToggle,
  running,
  toggling,
  runError,
}: {
  pipelineSettings: PipelineSettings | null;
  usage: UsageSummary | null;
  onRunNow: () => void;
  onToggle: () => void;
  running: boolean;
  toggling: boolean;
  runError: string | null;
}) {
  const monthlyBudget = pipelineSettings?.monthly_budget_usd ?? 20;
  const monthlySpend = usage?.period_costs?.monthly ?? 0;
  const budgetPct = monthlyBudget > 0 ? Math.min(100, (monthlySpend / monthlyBudget) * 100) : 0;
  const enabled = pipelineSettings?.enabled ?? false;

  return (
    <div className="glass-card space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={onToggle}
            disabled={toggling || pipelineSettings === null}
            className="flex items-center gap-1.5 group"
            title={enabled ? "Click to turn pipeline OFF" : "Click to turn pipeline ON"}
          >
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                enabled ? "bg-emerald-400 animate-pulse" : "bg-zinc-500"
              } group-hover:opacity-70`}
            />
            <span className="text-xs font-medium text-zinc-200 group-hover:text-violet-400 transition-colors">
              Pipeline: {toggling ? "..." : enabled ? "ON" : "OFF"}
            </span>
          </button>
          {enabled && pipelineSettings?.next_run_at && (
            <span className="text-xs text-zinc-500">
              · Next run in {timeUntil(pipelineSettings.next_run_at)}
            </span>
          )}
          <button
            onClick={onRunNow}
            disabled={running || pipelineSettings?.run_now === true}
            className="glass-button text-xs px-2.5 py-1.5 text-violet-400 ring-violet-500/20 hover:ring-violet-500/40 disabled:opacity-40"
          >
            {running || pipelineSettings?.run_now ? "Starting..." : "Run Now"}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">
            ${monthlySpend.toFixed(2)} / ${monthlyBudget.toFixed(2)}
          </span>
          <div className="w-20 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                budgetPct >= 80 ? "bg-red-400" : budgetPct >= 50 ? "bg-amber-400" : "bg-emerald-400"
              }`}
              style={{ width: `${budgetPct}%` }}
            />
          </div>
          <span className="text-xs text-zinc-500">{Math.round(budgetPct)}%</span>
          <Link
            href="/brand?tab=settings"
            className="text-xs text-zinc-600 hover:text-zinc-300 transition-colors"
          >
            Edit
          </Link>
        </div>
      </div>

      {runError && (
        <p className="text-xs text-red-400 border-t border-white/[0.06] pt-2">{runError}</p>
      )}
    </div>
  );
}
