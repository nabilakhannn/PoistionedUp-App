"use client";

/* ────────────────────────────────────────────────────────
   Skeleton Card (Research Feed Loading State)
   ──────────────────────────────────────────────────────── */

export function SkeletonCard() {
  return (
    <div className="bg-zinc-900 border border-zinc-800 border-l-4 border-l-zinc-700 rounded-xl p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-zinc-800" />
        <div className="space-y-1.5 flex-1">
          <div className="h-3.5 bg-zinc-800 rounded w-24" />
          <div className="h-2.5 bg-zinc-800 rounded w-16" />
        </div>
      </div>
      <div className="h-4 bg-zinc-800 rounded w-full mb-2" />
      <div className="h-3 bg-zinc-800 rounded w-5/6 mb-1" />
      <div className="h-3 bg-zinc-800 rounded w-4/6 mb-4" />
      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60">
        <div className="flex gap-4">
          <div className="h-3 bg-zinc-800 rounded w-10" />
          <div className="h-3 bg-zinc-800 rounded w-10" />
        </div>
        <div className="h-3 bg-zinc-800 rounded w-12" />
      </div>
    </div>
  );
}
