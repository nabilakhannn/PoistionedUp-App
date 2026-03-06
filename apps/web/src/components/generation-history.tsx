"use client";

import { useCallback, useEffect, useState } from "react";
import { marketplaceApi, WorkflowRun } from "@/lib/api/marketplace";

interface GenerationHistoryProps {
  brandId: string;
  workflowSlug?: string;
  onViewOutput?: (output: string) => void;
}

export function GenerationHistory({
  brandId,
  workflowSlug,
  onViewOutput,
}: GenerationHistoryProps) {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const LIMIT = 20;

  const load = useCallback(
    async (reset = false) => {
      setLoading(true);
      try {
        const o = reset ? 0 : offset;
        const data = await marketplaceApi.getHistory(
          brandId,
          workflowSlug,
          LIMIT,
          o,
        );
        if (reset) {
          setRuns(data.runs);
          setOffset(LIMIT);
        } else {
          setRuns((prev) => [...prev, ...data.runs]);
          setOffset((prev) => prev + LIMIT);
        }
        setHasMore(data.runs.length === LIMIT);
      } catch {
        setError("Failed to load history");
      } finally {
        setLoading(false);
      }
    },
    [brandId, workflowSlug, offset],
  );

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId, workflowSlug]);

  if (loading && runs.length === 0) {
    return (
      <div className="space-y-2">
        <div className="h-3 w-20 rounded bg-zinc-800/50 animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-lg border border-zinc-800/50 bg-zinc-900/30 px-3 py-2.5 animate-pulse"
          >
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-zinc-700" />
              <div className="h-3 w-32 rounded bg-zinc-800/40" />
            </div>
            <div className="h-2.5 w-24 rounded bg-zinc-800/40 mt-1.5" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs text-red-400 py-3 text-center">
        {error}{" "}
        <button
          onClick={() => { setError(""); load(true); }}
          className="underline ml-1"
        >
          Retry
        </button>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="text-xs text-zinc-500 py-4 text-center">
        No previous runs yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-zinc-500 font-medium">Recent Runs</p>
      {runs.map((run) => (
        <div
          key={run.id}
          className="rounded-lg border border-zinc-800/50 bg-zinc-900/30 px-3 py-2 flex items-center justify-between gap-2"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  run.status === "completed"
                    ? "bg-green-400"
                    : run.status === "failed"
                      ? "bg-red-400"
                      : "bg-amber-400"
                }`}
              />
              <span className="text-xs text-zinc-300 truncate">
                {run.workflow_slug.replace(/-/g, " ")}
              </span>
              <span className="text-[10px] text-zinc-600">
                {run.engine === "manus" ? "Manus" : "Built-in"}
              </span>
            </div>
            <div className="text-[10px] text-zinc-600 mt-0.5">
              {new Date(run.created_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
              {run.duration_ms
                ? ` · ${(run.duration_ms / 1000).toFixed(1)}s`
                : ""}
            </div>
          </div>
          {run.output && onViewOutput && (
            <button
              onClick={() => onViewOutput(run.output!)}
              className="text-[10px] px-2 py-1 rounded border border-zinc-700/50 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition"
            >
              View
            </button>
          )}
        </div>
      ))}
      {hasMore && (
        <button
          onClick={() => load(false)}
          disabled={loading}
          className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-2 transition"
        >
          {loading ? "Loading..." : "Load more"}
        </button>
      )}
    </div>
  );
}
