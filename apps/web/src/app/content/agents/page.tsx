"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  marketplaceApi,
  RegistryResponse,
  WorkflowInfo,
} from "@/lib/api/marketplace";

const CATEGORY_ICONS: Record<string, string> = {
  rocket: "M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.58-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z",
  pencil:
    "m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10",
  users:
    "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
  envelope:
    "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
  lightbulb:
    "M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
};

export default function AgentMarketplacePage() {
  const { currentBrand } = useBrand();
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await marketplaceApi.getRegistry();
      setRegistry(data);
    } catch {
      setError("Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Select a brand first.</p>
          <Link href="/brand" className="glass-button-primary text-sm">
            Go to Brand →
          </Link>
        </div>
      </div>
    );
  }

  // Group workflows by category
  const workflowsByCategory: Record<string, WorkflowInfo[]> = {};
  if (registry) {
    Object.values(registry.workflows).forEach((w) => {
      if (!workflowsByCategory[w.category]) {
        workflowsByCategory[w.category] = [];
      }
      workflowsByCategory[w.category].push(w);
    });
  }

  const sortedCategories = registry
    ? Object.entries(registry.categories).sort(
        ([, a], [, b]) => a.order - b.order,
      )
    : [];

  const filteredCategories =
    activeCategory === "all"
      ? sortedCategories
      : sortedCategories.filter(([key]) => key === activeCategory);

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-zinc-100">AI Agents</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            24 workflows powered by your brand intelligence. Each one uses your
            dossier, stories, hooks, and competitor intel.
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2.5 rounded-lg text-sm flex items-center gap-3">
            <span className="flex-1">{error}</span>
            <button
              onClick={() => { setError(""); load(); }}
              className="underline shrink-0"
            >
              Retry
            </button>
            <button
              onClick={() => setError("")}
              className="text-red-400/60 hover:text-red-400 shrink-0"
            >
              ✕
            </button>
          </div>
        )}

        {loading ? (
          <div className="space-y-6">
            <div className="h-4 w-32 rounded bg-zinc-800/50 animate-pulse" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-4 space-y-3 animate-pulse"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-4 w-28 rounded bg-zinc-800/50" />
                    <div className="h-4 w-12 rounded bg-zinc-800/50" />
                  </div>
                  <div className="h-3 w-full rounded bg-zinc-800/40" />
                  <div className="h-3 w-3/4 rounded bg-zinc-800/40" />
                  <div className="flex gap-1">
                    <div className="h-4 w-14 rounded bg-zinc-800/50" />
                    <div className="h-4 w-14 rounded bg-zinc-800/50" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Category tabs */}
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setActiveCategory("all")}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  activeCategory === "all"
                    ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                    : "glass-button"
                }`}
              >
                All
              </button>
              {sortedCategories.map(([key, cat]) => (
                <button
                  key={key}
                  onClick={() => setActiveCategory(key)}
                  className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                    activeCategory === key
                      ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                      : "glass-button"
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            {/* Empty filtered state */}
            {activeCategory !== "all" &&
              filteredCategories.every(
                ([catKey]) => (workflowsByCategory[catKey] || []).length === 0,
              ) && (
                <div className="rounded-xl border border-dashed border-zinc-700/50 bg-white/[0.02] px-6 py-12 text-center">
                  <p className="text-sm text-zinc-400 mb-1">No workflows in this category</p>
                  <p className="text-xs text-zinc-600">Try selecting a different category or &ldquo;All&rdquo;.</p>
                </div>
              )}

            {/* Workflow cards by category */}
            {filteredCategories.map(([catKey, cat]) => {
              const workflows = workflowsByCategory[catKey] || [];
              if (workflows.length === 0) return null;

              return (
                <div key={catKey} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-4 h-4 text-zinc-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d={CATEGORY_ICONS[cat.icon] || CATEGORY_ICONS.rocket}
                      />
                    </svg>
                    <h2 className="text-sm font-semibold text-zinc-300">
                      {cat.name}
                    </h2>
                    <span className="text-[10px] text-zinc-600">
                      {workflows.length} workflows
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {workflows.map((w) => {
                      const isComingSoon = w.status === "coming_soon";
                      return (
                        <div key={w.slug} className="relative">
                          {isComingSoon ? (
                            <div className="glass-card opacity-60 cursor-not-allowed p-4 space-y-2">
                              <div className="flex items-center justify-between">
                                <h3 className="text-sm font-medium text-zinc-300">
                                  {w.name}
                                </h3>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700/50 text-zinc-500">
                                  Coming Soon
                                </span>
                              </div>
                              <p className="text-xs text-zinc-500 line-clamp-2">
                                {w.description}
                              </p>
                              <div className="flex gap-1 flex-wrap">
                                {w.tags.map((tag) => (
                                  <span
                                    key={tag}
                                    className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/50 text-zinc-600"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <Link
                              href={`/content/agents/${w.slug}`}
                              className="glass-card-hover block p-4 space-y-2 group"
                            >
                              <div className="flex items-center justify-between">
                                <h3 className="text-sm font-medium text-zinc-200 group-hover:text-zinc-100">
                                  {w.name}
                                </h3>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">
                                  Active
                                </span>
                              </div>
                              <p className="text-xs text-zinc-500 line-clamp-2">
                                {w.description}
                              </p>
                              <div className="flex items-center gap-2">
                                <div className="flex gap-1 flex-wrap flex-1">
                                  {w.tags.map((tag) => (
                                    <span
                                      key={tag}
                                      className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800/50 text-zinc-500"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                                {w.multi_step && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400">
                                    {w.steps.length} steps
                                  </span>
                                )}
                                {w.engine === "manus_beneficial" && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                                    Manus
                                  </span>
                                )}
                              </div>
                              <div className="flex gap-1 flex-wrap">
                                {w.enhancements.map((e) => (
                                  <span
                                    key={e}
                                    className="text-[9px] text-zinc-600"
                                  >
                                    +{e.replace("_", " ")}
                                  </span>
                                ))}
                              </div>
                            </Link>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}
