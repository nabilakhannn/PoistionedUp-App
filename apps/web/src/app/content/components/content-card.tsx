"use client";

import Link from "next/link";
import { WorkflowSummary } from "@/lib/api";
import {
  STATUS_CONFIG,
  PLATFORM_CONFIG,
  OBJECTIVE_CONFIG,
  CONTENT_TYPE_CONFIG,
  timeAgo,
  getStepProgress,
} from "../dashboard-constants";

/* ────────────────────────────────────────────────────────
   Content Card Component
   ──────────────────────────────────────────────────────── */

export function ContentCard({ wf }: { wf: WorkflowSummary }) {
  const st = STATUS_CONFIG[wf.status] || STATUS_CONFIG.queued;
  const obj = wf.objective ? OBJECTIVE_CONFIG[wf.objective] : null;
  const ct = wf.content_type ? CONTENT_TYPE_CONFIG[wf.content_type] : null;
  const borderColor = obj?.border || "border-l-zinc-700";

  return (
    <Link
      href={`/content/${wf.id}`}
      className={`group block bg-zinc-900 border border-zinc-800 ${borderColor} border-l-4 rounded-xl p-5 hover:border-zinc-700 hover:bg-zinc-900/80 transition-all h-full flex flex-col justify-between`}
    >
      <div>
        {/* Status + Time row */}
        <div className="flex items-center justify-between mb-3">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${st.bg} ${st.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
            {st.label}
          </span>
          <span className="text-[11px] text-zinc-600">{timeAgo(wf.updated_at)}</span>
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold text-zinc-100 mb-2 line-clamp-2 leading-snug group-hover:text-white transition">
          {wf.goal_text || "Untitled Content"}
        </h3>

        {/* Type + Objective badges */}
        <div className="flex items-center gap-2 flex-wrap mb-3">
          {ct && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-zinc-800 text-zinc-400">
              {ct.emoji} {ct.label}
            </span>
          )}
          {obj && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-zinc-800/60 ${obj.color}`}>
              {obj.label}
            </span>
          )}
        </div>

        {/* Current step indicator */}
        {wf.current_step && wf.status === "running" && (
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: getStepProgress(wf.current_step) + "%" }}
              />
            </div>
            <span className="text-[10px] text-zinc-500 font-mono whitespace-nowrap">
              {wf.current_step}
            </span>
          </div>
        )}
      </div>

      {/* Bottom: platforms + version + cost */}
      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/50">
        <div className="flex items-center gap-2">
          {wf.platforms.slice(0, 3).map((p) => {
            const pc = PLATFORM_CONFIG[p];
            return (
              <span
                key={p}
                className={`text-[10px] font-medium ${pc?.color || "text-zinc-500"}`}
              >
                {pc?.label || p}
              </span>
            );
          })}
          {wf.platforms.length > 3 && (
            <span className="text-[10px] text-zinc-600">+{wf.platforms.length - 3}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] text-zinc-600">
          <span>v{wf.active_version}</span>
          {wf.estimated_cost > 0 && (
            <span className="text-green-500">
              ${wf.estimated_cost < 0.01 ? wf.estimated_cost.toFixed(4) : wf.estimated_cost.toFixed(2)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
