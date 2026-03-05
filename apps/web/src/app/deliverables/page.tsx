"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { clientDeliverablesApi, type ClientDeliverable } from "@/lib/api/client-deliverables";

const TYPE_ICONS: Record<string, string> = {
  proposal: "📄",
  landing_page: "🌐",
  ad_creative: "🎨",
  nurture_sequence: "📧",
};

const TYPE_LABELS: Record<string, string> = {
  proposal: "Proposal",
  landing_page: "Landing Page",
  ad_creative: "Ad Creatives",
  nurture_sequence: "Nurture Sequence",
};

const FILTER_TABS = [
  { key: "all", label: "All" },
  { key: "proposal", label: "Proposals" },
  { key: "landing_page", label: "Landing Pages" },
  { key: "ad_creative", label: "Ad Creatives" },
  { key: "nurture_sequence", label: "Sequences" },
];

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function DeliverableCard({
  deliverable,
  onCopyShare,
  copied,
}: {
  deliverable: ClientDeliverable;
  onCopyShare: (id: string, token: string) => void;
  copied: string | null;
}) {
  const icon = TYPE_ICONS[deliverable.deliverable_type] || "📦";
  const label = TYPE_LABELS[deliverable.deliverable_type] || deliverable.deliverable_type;
  const shareUrl = deliverable.share_token
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/share/${deliverable.share_token}`
    : null;

  return (
    <div className="bg-[#0d1117] border border-white/10 rounded-2xl p-5 flex flex-col gap-4 hover:border-white/20 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <div>
            <div className="text-white font-semibold text-sm">{deliverable.title}</div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs text-slate-500">{label}</span>
              <span className="text-slate-700">·</span>
              <span className="text-xs text-slate-500">{timeAgo(deliverable.created_at)}</span>
            </div>
          </div>
        </div>
        {deliverable.version && (
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-900/30 text-indigo-400 border border-indigo-800/40">
            v{deliverable.version}
          </span>
        )}
      </div>

      {/* Preview snippet */}
      {deliverable.content && (
        <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
          {deliverable.content.replace(/<[^>]+>/g, "").slice(0, 120)}...
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {shareUrl && (
          <Link
            href={`/share/${deliverable.share_token}`}
            target="_blank"
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg font-medium transition-colors"
          >
            Preview
          </Link>
        )}

        {shareUrl && (
          <button
            onClick={() => onCopyShare(deliverable.id, deliverable.share_token!)}
            className="px-3 py-1.5 border border-white/10 hover:border-white/20 text-slate-400 text-xs rounded-lg font-medium transition-colors"
          >
            {copied === deliverable.id ? "✓ Copied!" : "🔗 Share Link"}
          </button>
        )}

        {deliverable.content && (
          <button
            onClick={() => {
              const blob = new Blob([deliverable.content], { type: "text/html" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${deliverable.title}.html`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="px-3 py-1.5 border border-white/10 hover:border-white/20 text-slate-400 text-xs rounded-lg font-medium transition-colors"
          >
            Download
          </button>
        )}
      </div>
    </div>
  );
}

export default function DeliverablesPage() {
  const { currentBrand } = useBrand();
  const [deliverables, setDeliverables] = useState<ClientDeliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBrand?.id) return;
    setLoading(true);
    clientDeliverablesApi
      .list(currentBrand.id)
      .then(setDeliverables)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [currentBrand?.id]);

  function handleCopyShare(id: string, token: string) {
    const url = `${window.location.origin}/share/${token}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  const filtered =
    filter === "all"
      ? deliverables
      : deliverables.filter((d) => d.deliverable_type === filter);

  return (
    <div className="min-h-screen bg-[#060810]">
      {/* Page header */}
      <div className="border-b border-white/10 bg-[#0d1117]">
        <div className="max-w-5xl mx-auto px-5 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-white font-bold text-xl">
                📦 Deliverables
                {currentBrand?.name ? (
                  <span className="text-slate-500 font-normal text-base ml-2">
                    — {currentBrand.name}
                  </span>
                ) : null}
              </h1>
              <p className="text-slate-500 text-xs mt-1">
                Proposals, landing pages, ad creatives, and nurture sequences
              </p>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 mt-4">
            {FILTER_TABS.map((tab) => {
              const count =
                tab.key === "all"
                  ? deliverables.length
                  : deliverables.filter((d) => d.deliverable_type === tab.key).length;
              return (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    filter === tab.key
                      ? "bg-indigo-600 text-white"
                      : "bg-white/5 text-slate-400 hover:text-white hover:bg-white/10"
                  }`}
                >
                  {tab.label}
                  {count > 0 && (
                    <span
                      className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                        filter === tab.key
                          ? "bg-white/20 text-white"
                          : "bg-white/10 text-slate-500"
                      }`}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-5 py-6">
        {loading ? (
          <div className="text-slate-500 text-sm py-10 text-center">Loading deliverables...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">📦</div>
            <p className="text-slate-400 text-sm font-medium">No deliverables yet</p>
            <p className="text-slate-600 text-xs mt-1">
              Analyze a client call to generate proposals, landing pages, and more.
            </p>
            <Link
              href="/mission-control"
              className="inline-block mt-4 px-4 py-2 rounded-xl text-sm font-semibold text-white"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
            >
              Analyze a Call
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtered.map((d) => (
              <DeliverableCard
                key={d.id}
                deliverable={d}
                onCopyShare={handleCopyShare}
                copied={copied}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
