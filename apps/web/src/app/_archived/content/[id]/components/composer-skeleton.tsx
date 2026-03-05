"use client";

/**
 * 3-panel skeleton that mirrors the ComposerLayout while data loads.
 * Shows pulsing placeholder blocks for sidebar, editor, and preview.
 */
export function ComposerSkeleton() {
  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-zinc-950 animate-pulse">
      {/* LEFT SIDEBAR skeleton */}
      <aside className="w-72 border-r border-zinc-800 flex-shrink-0 p-3 space-y-2">
        {/* Toggle bar */}
        <div className="h-8 bg-zinc-800/60 rounded-lg w-full" />
        {/* Pipeline section */}
        <div className="border border-zinc-800/50 rounded-lg p-3 space-y-3">
          <div className="h-4 bg-zinc-800/60 rounded w-20" />
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-6 h-6 bg-zinc-800/60 rounded-full flex-shrink-0" />
              <div className="h-3 bg-zinc-800/40 rounded flex-1" />
            </div>
          ))}
        </div>
        {/* Context section */}
        <div className="border border-zinc-800/50 rounded-lg p-3 space-y-2">
          <div className="h-4 bg-zinc-800/60 rounded w-16" />
          <div className="h-3 bg-zinc-800/40 rounded w-full" />
          <div className="h-3 bg-zinc-800/40 rounded w-3/4" />
        </div>
        {/* Insights section */}
        <div className="border border-zinc-800/50 rounded-lg p-3">
          <div className="h-4 bg-zinc-800/60 rounded w-16" />
        </div>
      </aside>

      {/* CENTER EDITOR skeleton */}
      <main className="flex-1 min-w-0 p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Title row */}
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-6 bg-zinc-800/60 rounded w-64" />
              <div className="h-3 bg-zinc-800/40 rounded w-40" />
            </div>
            <div className="h-7 w-20 bg-zinc-800/60 rounded-full" />
          </div>
          {/* Content block */}
          <div className="bg-zinc-800/30 border border-zinc-700/30 rounded-xl p-8 space-y-4">
            <div className="h-5 bg-zinc-800/50 rounded w-48 mx-auto" />
            <div className="h-3 bg-zinc-800/30 rounded w-full" />
            <div className="h-3 bg-zinc-800/30 rounded w-5/6" />
            <div className="h-3 bg-zinc-800/30 rounded w-4/6" />
            <div className="h-3 bg-zinc-800/30 rounded w-full" />
            <div className="h-3 bg-zinc-800/30 rounded w-3/4" />
          </div>
          {/* Secondary block */}
          <div className="bg-zinc-800/30 border border-zinc-700/30 rounded-xl p-6 space-y-3">
            <div className="h-4 bg-zinc-800/50 rounded w-32" />
            <div className="h-3 bg-zinc-800/30 rounded w-full" />
            <div className="h-3 bg-zinc-800/30 rounded w-2/3" />
          </div>
        </div>
      </main>

      {/* RIGHT PREVIEW skeleton */}
      <aside className="w-96 border-l border-zinc-800 flex-shrink-0 p-3 space-y-3">
        {/* Toggle bar */}
        <div className="h-8 bg-zinc-800/60 rounded-lg w-full" />
        {/* Tab bar */}
        <div className="flex gap-2 border-b border-zinc-800 pb-2">
          <div className="h-6 bg-zinc-800/60 rounded w-16" />
          <div className="h-6 bg-zinc-800/40 rounded w-16" />
        </div>
        {/* Preview placeholder */}
        <div className="bg-zinc-800/30 border border-zinc-700/30 rounded-lg p-4 space-y-3">
          <div className="h-4 bg-zinc-800/50 rounded w-28" />
          <div className="h-3 bg-zinc-800/30 rounded w-full" />
          <div className="h-3 bg-zinc-800/30 rounded w-full" />
          <div className="h-3 bg-zinc-800/30 rounded w-4/5" />
          <div className="h-20 bg-zinc-800/20 rounded w-full mt-4" />
        </div>
      </aside>
    </div>
  );
}
