"use client";

/**
 * Intelligence Room — Slice 90
 * 4 tabs: Research / Brand Profile / Journal / YouTube Clips
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { journalApi, JournalEntry, SourceType } from "@/lib/api/journal";

type Tab = "research" | "brand" | "journal" | "youtube";

const TABS: { key: Tab; label: string; emoji: string }[] = [
  { key: "research", label: "Research", emoji: "🔬" },
  { key: "brand", label: "Brand Profile", emoji: "🎯" },
  { key: "journal", label: "Journal", emoji: "📒" },
  { key: "youtube", label: "YouTube Clips", emoji: "▶️" },
];

const SOURCE_TYPE_LABELS: Record<SourceType, { label: string; emoji: string }> = {
  call_recording: { label: "Call Recording", emoji: "🎙️" },
  transcript: { label: "Transcript", emoji: "📝" },
  note: { label: "Note", emoji: "📒" },
  case_study: { label: "Case Study", emoji: "📊" },
};

// ── Journal Tab ────────────────────────────────────────────

function JournalTab({ brandId }: { brandId: string }) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    title: "",
    source_type: "note" as SourceType,
    raw_content: "",
    tags: "",
  });
  const [saving, setSaving] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    try {
      const data = await journalApi.list(brandId);
      setEntries(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { loadEntries(); }, [loadEntries]);

  const handleSave = async () => {
    if (!form.raw_content.trim()) return;
    setSaving(true);
    try {
      const entry = await journalApi.create({
        brand_id: brandId,
        title: form.title || undefined,
        source_type: form.source_type,
        raw_content: form.raw_content,
        tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      });
      setEntries((prev) => [entry, ...prev]);
      setForm({ title: "", source_type: "note", raw_content: "", tags: "" });
      setAdding(false);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleteLoading(id);
    try {
      await journalApi.delete(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // ignore
    } finally {
      setDeleteLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Experience Journal</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Your real calls, transcripts, notes, and case studies. Agents use these to write from your actual experience.
          </p>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
        >
          + Add Experience
        </button>
      </div>

      {/* Add form */}
      {adding && (
        <div className="rounded-xl border border-primary/30 bg-card p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Title (optional)</label>
              <input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. 'Discovery call with SaaS founder'"
                className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Type</label>
              <select
                value={form.source_type}
                onChange={(e) => setForm((f) => ({ ...f, source_type: e.target.value as SourceType }))}
                className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {(Object.keys(SOURCE_TYPE_LABELS) as SourceType[]).map((type) => (
                  <option key={type} value={type}>
                    {SOURCE_TYPE_LABELS[type].emoji} {SOURCE_TYPE_LABELS[type].label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-muted-foreground mb-1">
              Content (paste transcript, notes, or describe what happened)
            </label>
            <textarea
              value={form.raw_content}
              onChange={(e) => setForm((f) => ({ ...f, raw_content: e.target.value }))}
              placeholder="Paste your call transcript, notes, or describe the case study..."
              rows={5}
              className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>

          <div>
            <label className="block text-xs text-muted-foreground mb-1">Tags (comma-separated)</label>
            <input
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              placeholder="e.g. SaaS, pricing, objections"
              className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving || !form.raw_content.trim()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Entry"}
            </button>
            <button
              onClick={() => setAdding(false)}
              className="px-4 py-2 border border-border rounded text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Entries list */}
      {loading ? (
        <div className="text-xs text-muted-foreground">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
          <div className="text-3xl mb-3">📒</div>
          <p className="text-sm font-medium text-foreground mb-1">No journal entries yet</p>
          <p className="text-xs text-muted-foreground">
            Add a call transcript or note — agents will write content from your real experiences.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => {
            const typeInfo = SOURCE_TYPE_LABELS[entry.source_type] || { label: entry.source_type, emoji: "📝" };
            return (
              <div key={entry.id} className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base">{typeInfo.emoji}</span>
                      <span className="text-sm font-medium text-foreground truncate">
                        {entry.title || typeInfo.label}
                      </span>
                      <span className="text-[10px] text-muted-foreground shrink-0">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 ml-7">{entry.raw_content}</p>
                    {entry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2 ml-7">
                        {entry.tags.map((tag) => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleDelete(entry.id)}
                    disabled={deleteLoading === entry.id}
                    className="text-[10px] text-muted-foreground/50 hover:text-red-400 transition shrink-0"
                  >
                    {deleteLoading === entry.id ? "..." : "Delete"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────

export default function IntelligencePage() {
  const [activeTab, setActiveTab] = useState<Tab>("research");
  const { currentBrand } = useBrand();

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              🧠 Intelligence
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Research briefs, brand profile, experience journal, and YouTube clip research.
            </p>
          </div>
          {currentBrand && (
            <span className="text-xs text-muted-foreground border border-border rounded-lg px-3 py-1.5">
              {currentBrand.name}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 mt-4 -mb-px">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-6 py-6">
        {/* ── RESEARCH TAB ───────────────────────────── */}
        {activeTab === "research" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Latest Research Brief</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Generated by the Trend Analyzer agent. Sales agents read this automatically.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card/50 p-5">
              <p className="text-xs text-muted-foreground">
                Run the pipeline to generate a research brief. The latest brief will appear here and be automatically used by Sales agents.
              </p>
              <Link
                href="/mission-control"
                className="inline-block mt-3 text-xs text-primary hover:underline"
              >
                Go to Command Center → Run Now
              </Link>
            </div>
          </div>
        )}

        {/* ── BRAND PROFILE TAB ──────────────────────── */}
        {activeTab === "brand" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Brand Profile</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Voice pattern, ICA, positioning, and top topics from your brand research.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card/50 p-5 space-y-3">
              <p className="text-xs text-muted-foreground">
                Your brand profile is built by the Strategist. View and refine it in the Brand Strategist.
              </p>
              {currentBrand ? (
                <Link
                  href={`/brands/${currentBrand.id}/strategist`}
                  className="inline-block text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
                >
                  Open Brand Strategist →
                </Link>
              ) : (
                <Link href="/brands" className="text-xs text-primary hover:underline">Select a brand first →</Link>
              )}
            </div>
          </div>
        )}

        {/* ── JOURNAL TAB ────────────────────────────── */}
        {activeTab === "journal" && (
          currentBrand ? (
            <JournalTab brandId={currentBrand.id} />
          ) : (
            <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
              <div className="text-3xl mb-3">📒</div>
              <p className="text-sm text-muted-foreground">Select a brand to access your experience journal.</p>
              <Link href="/brands" className="inline-block mt-3 text-xs text-primary hover:underline">Select brand →</Link>
            </div>
          )
        )}

        {/* ── YOUTUBE CLIPS TAB ──────────────────────── */}
        {activeTab === "youtube" && (
          <div className="space-y-4 max-w-2xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground">YouTube Research</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Agents search YouTube and return video title + timestamp + exact quote to cite in content.
              </p>
            </div>
            <div className="rounded-xl border border-border/50 bg-card/30 px-6 py-12 text-center opacity-60">
              <div className="text-3xl mb-3">▶️</div>
              <p className="text-sm font-medium text-foreground mb-1">YouTube Research Tool</p>
              <p className="text-xs text-muted-foreground">
                YouTube Data API v3 integration. Agents cite: "As shown by [channel] at 2:34: '[quote]'"
              </p>
              <span className="inline-block mt-3 text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded-full">Slice 91</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
