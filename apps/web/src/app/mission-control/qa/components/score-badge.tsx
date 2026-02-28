"use client";

import { QA_PASS_THRESHOLD, QA_REVISE_THRESHOLD } from "@/lib/api/qa";

interface ScoreBadgeProps {
  score: number;
  size?: "sm" | "md";
}

export function ScoreBadge({ score, size = "sm" }: ScoreBadgeProps) {
  const color =
    score >= QA_PASS_THRESHOLD
      ? "text-green-400 bg-green-500/20"
      : score >= QA_REVISE_THRESHOLD
        ? "text-yellow-400 bg-yellow-500/20"
        : "text-red-400 bg-red-500/20";

  const sizeClass = size === "md" ? "px-2.5 py-1 text-sm" : "px-1.5 py-0.5 text-xs";

  return (
    <span className={`${color} ${sizeClass} rounded font-medium`}>
      {score}
    </span>
  );
}
