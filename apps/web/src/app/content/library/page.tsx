"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";

type StatusFilter = "all" | "draft" | "review" | "approved" | "rejected";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "text-zinc-500 bg-zinc-500/10 ring-zinc-500/20",
  review: "text-amber-400 bg-amber-500/10 ring-amber-500/20",
  approved: "text-emerald-400 bg-emerald-500/10 ring-emerald-500/20",
  rejected: "text-red-400 bg-red-500/10 ring-red-500/20",
};

export default function ContentLibraryPage() {
  const { currentBrand } = useBrand();
  const [items, setItems] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    missionControlApi.listDeliverables()
      .then((res) => setItems(res))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [currentBrand?.id]);

  const filtered = items.filter((d) => {
    if (filter !== "all" && d.status !== filter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (d.title?.toLowerCase().includes(q) || d.content?.toLowerCase().includes(q));
    }
    return true;
  });

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand to view your content library.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        <div>
          <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
          <h1 className="text-xl font-bold text-zinc-100 mt-1">Content Library</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{items.length} pieces total</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search content..."
            className="glass-input max-w-xs"
          />
          <div className="flex gap-1.5">
            {(["all", "review", "approved", "rejected", "draft"] as StatusFilter[]).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
                  filter === s
                    ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                    : "text-zinc-500 hover:text-zinc-300 bg-white/[0.03] ring-1 ring-white/[0.05]"
                }`}
              >
                {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        {loading ? (
          <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="glass-card py-8 text-center">
            <p className="text-sm text-zinc-500">
              {search ? "No matching content found." : "No content yet. Start creating!"}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((d) => (
              <div key={d.id} className="glass-card py-3 px-4 group">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-zinc-200 truncate">{d.title}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full ring-1 ${STATUS_COLORS[d.status] || ""}`}>
                        {d.status}
                      </span>
                      {d.qa_score !== undefined && d.qa_score >= 85 && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20">
                          Top Performer
                        </span>
                      )}
                    </div>
                    {d.content && (
                      <p className="text-xs text-zinc-600 truncate mt-0.5">{d.content.slice(0, 100)}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {d.qa_score !== undefined && d.qa_score > 0 && (
                      <span className="text-[10px] text-zinc-500 font-mono">QA {d.qa_score}</span>
                    )}
                    <span className="text-[10px] text-zinc-600">{timeAgo(d.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
