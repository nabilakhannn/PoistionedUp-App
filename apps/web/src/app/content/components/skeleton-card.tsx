"use client";

/* ────────────────────────────────────────────────────────
   Skeleton Card (Content Dashboard Loading State)
   ──────────────────────────────────────────────────────── */

export function SkeletonCard() {
  return (
    <div className="bg-zinc-900 border border-zinc-800 border-l-4 border-l-zinc-700 rounded-xl p-5 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-5 w-16 bg-zinc-800 rounded-full" />
        <div className="h-3 w-12 bg-zinc-800 rounded" />
      </div>
      <div className="h-4 bg-zinc-800 rounded w-full mb-2" />
      <div className="h-3 bg-zinc-800 rounded w-3/4 mb-3" />
      <div className="flex gap-2 mb-3">
        <div className="h-4 w-14 bg-zinc-800 rounded-md" />
        <div className="h-4 w-14 bg-zinc-800 rounded-md" />
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/50">
        <div className="h-3 w-16 bg-zinc-800 rounded" />
        <div className="h-3 w-8 bg-zinc-800 rounded" />
      </div>
    </div>
  );
}
