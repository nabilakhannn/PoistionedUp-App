"use client";

import { STEP_LABELS } from "../types";

export function RunningState({ step }: { step: string | null }) {
  return (
    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-8 text-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-4" />
      <h3 className="text-lg font-medium text-white mb-1">
        {step ? STEP_LABELS[step] || step : "Starting pipeline..."}
      </h3>
      <p className="text-zinc-400 text-sm">
        This page will update automatically when the next step is ready.
      </p>
    </div>
  );
}
