"use client";

import { useState } from "react";
import { STEP_ORDER, STEP_LABELS } from "../types";
import { StepSnapshot } from "@/lib/api";

const STEP_ICONS: Record<string, string> = {
  signal_research: "🔍",
  gap_analysis: "📊",
  topic_selection: "💡",
  hook_lab: "🎣",
  script_generation: "✍️",
  editor: "✏️",
  testing: "✅",
  approval: "👍",
};

interface PipelineStepperProps {
  currentStep: string | null;
  status: string;
  compact?: boolean;
  snapshots?: StepSnapshot[];
}

export function PipelineStepper({
  currentStep,
  status,
  compact,
  snapshots = [],
}: PipelineStepperProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);
  const currentStepIndex = currentStep
    ? STEP_ORDER.indexOf(currentStep as (typeof STEP_ORDER)[number])
    : -1;
  const isTerminal =
    status === "completed" || status === "approved" || status === "failed";

  const snapshotMap: Record<string, StepSnapshot> = {};
  for (const snap of snapshots) {
    snapshotMap[snap.step_id] = snap;
  }

  return (
    <div className="space-y-1">
      {STEP_ORDER.map((step, i) => {
        const isCompleted = isTerminal || currentStepIndex > i;
        const isCurrent = currentStepIndex === i && !isTerminal;
        const isWaiting = status.startsWith("awaiting") && isCurrent;
        const snap = snapshotMap[step];
        const canExpand = isCompleted && !!snap && !compact;
        const isExpanded = expandedStep === step;

        return (
          <div key={step}>
            <button
              onClick={() => {
                if (canExpand) {
                  setExpandedStep(isExpanded ? null : step);
                }
              }}
              className={`w-full flex items-center gap-2 rounded-lg px-1 py-1 transition-colors ${
                canExpand
                  ? "hover:bg-zinc-800/60 cursor-pointer"
                  : "cursor-default"
              }`}
            >
              {/* Step icon */}
              <div className="flex flex-col items-center w-6 shrink-0">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                    isCompleted
                      ? "bg-green-500/20 text-green-400"
                      : isCurrent
                      ? isWaiting
                        ? "bg-yellow-500/20 text-yellow-400 ring-2 ring-yellow-500/40"
                        : "bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/40 animate-pulse"
                      : "bg-zinc-800 text-zinc-600"
                  }`}
                >
                  {isCompleted ? "✓" : STEP_ICONS[step] || i + 1}
                </div>
                {i < STEP_ORDER.length - 1 && (
                  <div
                    className={`w-0.5 h-3 ${
                      isCompleted ? "bg-green-500/30" : "bg-zinc-800"
                    }`}
                  />
                )}
              </div>

              {/* Label */}
              {!compact && (
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                  <span
                    className={`text-xs truncate ${
                      isCompleted
                        ? "text-zinc-400"
                        : isCurrent
                        ? "text-white font-medium"
                        : "text-zinc-600"
                    }`}
                  >
                    {STEP_LABELS[step] || step}
                  </span>
                  {canExpand && (
                    <span className="text-zinc-600 text-[10px] ml-auto shrink-0">
                      {isExpanded ? "▼" : "▶"}
                    </span>
                  )}
                </div>
              )}
            </button>

            {/* Expanded snapshot detail */}
            {isExpanded && snap && (
              <div className="ml-8 mt-1 mb-2">
                <SnapshotDetail stepId={step} summary={snap.summary} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Snapshot Detail per step ──

function SnapshotDetail({
  stepId,
  summary,
}: {
  stepId: string;
  summary: Record<string, any>;
}) {
  switch (stepId) {
    case "signal_research":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Signals found:</span>
            <span className="text-xs text-white font-medium">
              {summary.signal_count || 0}
            </span>
          </div>
          {(summary.sources || []).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {(summary.sources as string[]).map((s, i) => (
                <span
                  key={i}
                  className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
          {(summary.top_signals || []).length > 0 && (
            <ul className="space-y-1">
              {(summary.top_signals as string[]).map((s, i) => (
                <li key={i} className="text-[11px] text-zinc-500 truncate">
                  {s}
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case "gap_analysis":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Topics scored:</span>
            <span className="text-xs text-white font-medium">
              {summary.topic_count || 0}
            </span>
          </div>
          {(summary.top_topics || []).length > 0 && (
            <ul className="space-y-1.5">
              {(summary.top_topics as any[]).map((t, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between text-[11px]"
                >
                  <span className="text-zinc-400 truncate mr-2">
                    {t.title}
                  </span>
                  <span className="text-green-400 font-mono shrink-0">
                    {t.score}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case "topic_selection":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
          <span className="text-xs text-zinc-400">Selected: </span>
          <span className="text-xs text-white font-medium">
            {summary.selected_topic || "None"}
          </span>
        </div>
      );

    case "hook_lab":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-400">Hooks generated:</span>
            <span className="text-xs text-white font-medium">
              {summary.hook_count || 0}
            </span>
          </div>
          {(summary.hooks || []).length > 0 && (
            <ul className="space-y-1.5">
              {(summary.hooks as any[]).map((h, i) => (
                <li key={i} className="text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <span className="bg-zinc-800 text-zinc-500 px-1 py-0.5 rounded text-[10px]">
                      {h.type}
                    </span>
                    <span className="text-green-400 font-mono text-[10px]">
                      {h.score}
                    </span>
                  </div>
                  <p className="text-zinc-400 mt-0.5 line-clamp-2">
                    {h.text}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case "script_generation":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-1.5">
          {summary.has_youtube_long && (
            <div className="text-[11px] text-zinc-400">
              YouTube Long: {summary.word_count || "?"} words
            </div>
          )}
          {(summary.youtube_shorts_count || 0) > 0 && (
            <div className="text-[11px] text-zinc-400">
              Shorts: {summary.youtube_shorts_count}
            </div>
          )}
          {(summary.linkedin_posts_count || 0) > 0 && (
            <div className="text-[11px] text-zinc-400">
              LinkedIn: {summary.linkedin_posts_count} posts
            </div>
          )}
          {(summary.twitter_posts_count || 0) > 0 && (
            <div className="text-[11px] text-zinc-400">
              Twitter: {summary.twitter_posts_count} tweets
            </div>
          )}
        </div>
      );

    case "editor":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
          <span className="text-[11px] text-zinc-400">
            {summary.edited
              ? `Edited (${summary.word_count || "?"} words)`
              : "No edits applied"}
          </span>
        </div>
      );

    case "testing":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3 space-y-1.5">
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-medium ${
                summary.passed ? "text-green-400" : "text-red-400"
              }`}
            >
              {summary.passed ? "PASSED" : "FAILED"}
            </span>
            <span className="text-[11px] text-zinc-500">
              {summary.checks_passed}/{summary.checks_total} checks
            </span>
          </div>
          {(summary.flags || []).length > 0 && (
            <ul className="space-y-0.5">
              {(summary.flags as string[]).map((f, i) => (
                <li key={i} className="text-[10px] text-yellow-400/80">
                  ⚠ {f}
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case "approval":
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
          <span className="text-[11px] text-zinc-400">
            Status: {summary.status || "pending"}
          </span>
        </div>
      );

    default:
      return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3">
          <pre className="text-[10px] text-zinc-500 overflow-auto max-h-24">
            {JSON.stringify(summary, null, 2)}
          </pre>
        </div>
      );
  }
}
