"use client";

import { HookCandidate } from "../types";

interface HookSelectionProps {
  hooks: HookCandidate[];
  onSelect: (id: string) => void;
  loading: boolean;
}

export function HookSelection({ hooks, onSelect, loading }: HookSelectionProps) {
  if (hooks.length === 0) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-6 text-center">
        <h3 className="text-lg font-medium text-yellow-400 mb-1">Waiting for hooks</h3>
        <p className="text-zinc-400 text-sm">
          The pipeline is generating hook candidates. This page will update when they are ready.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold text-white mb-1">Pick a Hook</h2>
      <p className="text-zinc-400 text-sm mb-4">
        Choose the opening hook for your content. This is what grabs attention in the first few seconds.
      </p>
      <div className="space-y-3">
        {hooks.map((hook) => (
          <div
            key={hook.id}
            className="bg-zinc-900 border border-zinc-700/50 rounded-xl p-5 hover:border-blue-500/50 transition cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-white font-medium flex-1 pr-4">&ldquo;{hook.hook_text}&rdquo;</p>
              <span className="bg-blue-500/20 text-blue-400 text-xs font-medium px-2 py-0.5 rounded-lg whitespace-nowrap">
                Score: {hook.total_score}
              </span>
            </div>
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <span className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-lg">
                {hook.hook_type}
              </span>
              {Object.entries(hook.score_breakdown || {}).map(([k, v]) => (
                <div key={k} className="flex items-center gap-1">
                  <span className="text-[10px] text-zinc-500 uppercase">{k}</span>
                  <div className="w-12 h-1.5 bg-zinc-800 rounded-full">
                    <div
                      className="h-1.5 bg-blue-500 rounded-full"
                      style={{ width: `${Math.min(100, (v as number) * 10)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={() => onSelect(hook.id)}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition disabled:opacity-50"
            >
              {loading ? "Selecting..." : "Use this hook"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
