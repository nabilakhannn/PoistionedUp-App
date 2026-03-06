"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  clientDeliverablesApi,
  type ClientDeliverable,
  type ProposalStatus,
} from "@/lib/api/client-deliverables";

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

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  draft: { label: "Draft", bg: "bg-slate-700/30", text: "text-slate-400" },
  sent: { label: "Sent", bg: "bg-blue-500/10", text: "text-blue-400" },
  accepted: { label: "Accepted", bg: "bg-green-500/10", text: "text-green-400" },
  rejected: { label: "Rejected", bg: "bg-red-500/10", text: "text-red-400" },
  closed_won: { label: "Won", bg: "bg-emerald-500/10", text: "text-emerald-400" },
  closed_lost: { label: "Lost", bg: "bg-zinc-500/10", text: "text-zinc-500" },
};

const STATUS_OPTIONS: ProposalStatus[] = [
  "draft", "sent", "accepted", "rejected", "closed_won", "closed_lost",
];

function DeliverableCard({
  deliverable,
  onCopyShare,
  onStatusChange,
  onRegenerate,
  copied,
  regeneratingId,
}: {
  deliverable: ClientDeliverable;
  onCopyShare: (id: string, token: string) => void;
  onStatusChange: (id: string, status: ProposalStatus, dealValue?: number) => void;
  onRegenerate: (id: string) => void;
  copied: string | null;
  regeneratingId: string | null;
}) {
  const [showDealInput, setShowDealInput] = useState(false);
  const [dealAmount, setDealAmount] = useState("");
  const icon = TYPE_ICONS[deliverable.deliverable_type] || "📦";
  const label = TYPE_LABELS[deliverable.deliverable_type] || deliverable.deliverable_type;
  const shareUrl = deliverable.share_token
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/share/${deliverable.share_token}`
    : null;

  function handleStatusSelect(newStatus: ProposalStatus) {
    if (newStatus === "closed_won") {
      setShowDealInput(true);
    } else {
      setShowDealInput(false);
      onStatusChange(deliverable.id, newStatus);
    }
  }

  function handleDealSubmit() {
    const val = parseFloat(dealAmount);
    onStatusChange(deliverable.id, "closed_won", val > 0 ? val : undefined);
    setShowDealInput(false);
    setDealAmount("");
  }

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
              {deliverable.deal_value && (
                <>
                  <span className="text-slate-700">·</span>
                  <span className="text-xs text-emerald-400 font-medium">${deliverable.deal_value.toLocaleString()}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Proposal status dropdown */}
          {deliverable.client_brand && (
            <select
              value={deliverable.proposal_status || "draft"}
              onChange={(e) => handleStatusSelect(e.target.value as ProposalStatus)}
              className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border-0 cursor-pointer appearance-none ${
                STATUS_CONFIG[deliverable.proposal_status || "draft"]?.bg || "bg-slate-700/30"
              } ${STATUS_CONFIG[deliverable.proposal_status || "draft"]?.text || "text-slate-400"}`}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
              ))}
            </select>
          )}
          {deliverable.version && (
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-900/30 text-indigo-400 border border-indigo-800/40">
              v{deliverable.version}
            </span>
          )}
        </div>
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

        <button
          onClick={() => onRegenerate(deliverable.id)}
          disabled={regeneratingId === deliverable.id}
          className="px-3 py-1.5 border border-white/10 hover:border-white/20 text-slate-400 text-xs rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {regeneratingId === deliverable.id ? "Regenerating..." : "Regenerate"}
        </button>
      </div>

      {/* Deal value input — appears when closed_won selected */}
      {showDealInput && (
        <div className="flex items-center gap-2 pt-1 border-t border-white/5">
          <span className="text-xs text-slate-500">Deal value:</span>
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-400">$</span>
            <input
              type="number"
              value={dealAmount}
              onChange={(e) => setDealAmount(e.target.value)}
              placeholder="0"
              className="w-24 px-2 py-1 bg-slate-800 border border-white/10 rounded-lg text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50"
              onKeyDown={(e) => e.key === "Enter" && handleDealSubmit()}
              autoFocus
            />
          </div>
          <button
            onClick={handleDealSubmit}
            className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-lg font-medium transition-colors"
          >
            Save
          </button>
          <button
            onClick={() => { setShowDealInput(false); setDealAmount(""); }}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default function DeliverablesPage() {
  const { currentBrand } = useBrand();
  const [deliverables, setDeliverables] = useState<ClientDeliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [copied, setCopied] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

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

  async function handleStatusChange(id: string, status: ProposalStatus, dealValue?: number) {
    try {
      await clientDeliverablesApi.updateStatus(id, status, dealValue);
      setDeliverables((prev) =>
        prev.map((d) => (d.id === id ? { ...d, proposal_status: status, deal_value: dealValue ?? d.deal_value } : d)),
      );
    } catch {
      // silent — status badge reverts on next load
    }
  }

  async function handleRegenerate(id: string) {
    if (!currentBrand?.id) return;
    setRegeneratingId(id);
    try {
      await clientDeliverablesApi.regenerate(id);
      // Reload the list to show new version
      const data = await clientDeliverablesApi.list(currentBrand.id);
      setDeliverables(data);
    } catch {
      // silent
    } finally {
      setRegeneratingId(null);
    }
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
                onStatusChange={handleStatusChange}
                onRegenerate={handleRegenerate}
                copied={copied}
                regeneratingId={regeneratingId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
