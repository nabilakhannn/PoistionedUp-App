"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { competitorsApi, ContentGapAnalysis } from "@/lib/api/competitors";

const SUB_NAV = [
  { href: "/mission-control", label: "Dashboard" },
  { href: "/mission-control/competitors", label: "Competitors" },
];

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-red-500/20 text-red-400",
  medium: "bg-yellow-500/20 text-yellow-400",
  low: "bg-zinc-500/20 text-zinc-400",
};

export default function GapAnalysisPage() {
  const [data, setData] = useState<ContentGapAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const result = await competitorsApi.getGaps();
        setData(result);
      } catch (e) {
        console.error("Failed to load gap analysis:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition"
          >
            {item.label}
          </Link>
        ))}
        <span className="px-3 py-1.5 text-xs font-medium text-foreground">
          Content Gap Analysis
        </span>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Content Gap Analysis</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Topics your competitors cover that you don&apos;t — and your unique strengths.
        </p>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Analyzing content gaps...</p>
      ) : !data ? (
        <p className="text-muted-foreground">Failed to load gap analysis.</p>
      ) : (
        <div className="space-y-6">
          {/* Gaps */}
          <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
            <h3 className="text-sm font-semibold mb-3">
              Content Gaps ({data.gaps.length})
            </h3>
            {data.gaps.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No gaps found — you cover the same topics as your competitors.
              </p>
            ) : (
              <div className="space-y-2">
                {data.gaps.map((gap) => (
                  <div
                    key={gap.topic}
                    className="flex items-center justify-between py-2 border-b border-zinc-800/50 last:border-0"
                  >
                    <div className="flex-1">
                      <span className="text-sm font-medium">{gap.topic}</span>
                      <div className="flex items-center gap-2 mt-1">
                        <span
                          className={`px-1.5 py-0.5 text-[10px] rounded ${
                            PRIORITY_STYLES[gap.priority] || PRIORITY_STYLES.medium
                          }`}
                        >
                          {gap.priority}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Covered by: {gap.covered_by_competitors.join(", ")}
                        </span>
                      </div>
                    </div>
                    <Link
                      href="/schedule"
                      className="text-xs text-primary hover:underline shrink-0 ml-3"
                    >
                      Create content
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Your unique topics */}
          <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
            <h3 className="text-sm font-semibold mb-3">
              Your Unique Topics ({data.your_unique_topics.length})
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Topics you cover that competitors don&apos;t — your competitive moat.
            </p>
            {data.your_unique_topics.length === 0 ? (
              <p className="text-xs text-muted-foreground">No unique topics found yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.your_unique_topics.map((topic) => (
                  <span
                    key={topic}
                    className="px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Shared topics */}
          <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
            <h3 className="text-sm font-semibold mb-3">
              Shared Topics ({data.shared_topics.length})
            </h3>
            {data.shared_topics.length === 0 ? (
              <p className="text-xs text-muted-foreground">No shared topics found yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {data.shared_topics.map((topic) => (
                  <span
                    key={topic}
                    className="px-2 py-1 bg-zinc-800 text-zinc-300 text-xs rounded"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
