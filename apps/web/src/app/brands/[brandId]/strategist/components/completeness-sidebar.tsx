"use client";

import React from "react";
import type { FieldCompleteness } from "@/lib/api/strategist";

const MODULE_ORDER = [
  "foundation",
  "authority",
  "ica",
  "positioning",
  "voice",
  "offer",
  "content_pillars",
  "competitive",
];

const MODULE_ICONS: Record<string, string> = {
  foundation: "🏗",
  authority: "🏆",
  ica: "🎯",
  positioning: "📍",
  voice: "🎙",
  offer: "💎",
  content_pillars: "📝",
  competitive: "⚔",
};

interface CompletenessSidebarProps {
  completeness: FieldCompleteness | null;
  loading: boolean;
}

export function CompletenessSidebar({
  completeness,
  loading,
}: CompletenessSidebarProps) {
  if (loading || !completeness) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-4 w-32 bg-zinc-700 rounded" />
        <div className="h-3 w-full bg-zinc-800 rounded-full" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-3 w-24 bg-zinc-700 rounded" />
            <div className="h-2 w-full bg-zinc-800 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  const overallPercent = completeness.overall_percent;
  const modules = completeness.modules || {};

  return (
    <div className="space-y-5">
      {/* Overall progress */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-zinc-200">Brand DNA</h3>
          <span
            className={`text-sm font-bold ${
              overallPercent >= 100
                ? "text-green-400"
                : overallPercent >= 50
                ? "text-blue-400"
                : "text-zinc-400"
            }`}
          >
            {overallPercent}%
          </span>
        </div>
        <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              overallPercent >= 100
                ? "bg-green-500"
                : overallPercent >= 50
                ? "bg-blue-500"
                : "bg-zinc-600"
            }`}
            style={{ width: `${Math.min(overallPercent, 100)}%` }}
          />
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          {completeness.overall_filled}/{completeness.overall_total} fields
          completed
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-zinc-800" />

      {/* Module breakdown */}
      <div className="space-y-3">
        {MODULE_ORDER.map((modKey) => {
          const mod = modules[modKey];
          if (!mod) return null;

          const percent = mod.percent || 0;
          const isComplete = percent >= 100;

          return (
            <div key={modKey}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs">{MODULE_ICONS[modKey] || "📋"}</span>
                  <span
                    className={`text-xs font-medium ${
                      isComplete ? "text-green-400" : "text-zinc-300"
                    }`}
                  >
                    {mod.label}
                  </span>
                </div>
                <span
                  className={`text-xs ${
                    isComplete ? "text-green-400" : "text-zinc-500"
                  }`}
                >
                  {mod.filled}/{mod.total}
                </span>
              </div>
              <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isComplete
                      ? "bg-green-500"
                      : percent > 0
                      ? "bg-blue-500/70"
                      : "bg-transparent"
                  }`}
                  style={{ width: `${Math.min(percent, 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Milestone messages */}
      {overallPercent >= 100 && (
        <div className="rounded-lg border border-green-500/20 bg-green-500/5 px-3 py-2">
          <div className="text-xs font-medium text-green-400">
            Brand DNA Complete
          </div>
          <div className="text-xs text-green-400/70 mt-0.5">
            Ready for content creation
          </div>
        </div>
      )}
      {overallPercent >= 50 && overallPercent < 100 && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2">
          <div className="text-xs font-medium text-blue-400">
            Past Halfway
          </div>
          <div className="text-xs text-blue-400/70 mt-0.5">
            Content generation unlocked
          </div>
        </div>
      )}
      {overallPercent > 0 && overallPercent < 50 && (
        <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2">
          <div className="text-xs font-medium text-zinc-400">
            Keep Going
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            {50 - overallPercent}% more to unlock content creation
          </div>
        </div>
      )}
    </div>
  );
}
