"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { storiesApi, StoryEntry } from "@/lib/api/stories";

const SOURCE_TYPES = [
  { value: "", label: "All" },
  { value: "transcript", label: "Transcripts" },
  { value: "note", label: "Notes" },
  { value: "idea", label: "Ideas" },
  { value: "opinion", label: "Opinions" },
  { value: "quote", label: "Quotes" },
  { value: "take", label: "Takes" },
  { value: "call_recording", label: "Call Recordings" },
  { value: "case_study", label: "Case Studies" },
  { value: "framework", label: "Frameworks" },
] as const;

export default function StoryBankPage() {
  const { currentBrand } = useBrand();
  const [entries, setEntries] = useState<StoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("note");
  const [saving, setSaving] = useState(false);
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!currentBrand?.id) return;
    setLoading(true);
    try {
      const data = await storiesApi.list(currentBrand.id, filter || undefined);
      setEntries(data);
    } catch {
      setError("Failed to load stories");
    } finally {
      setLoading(false);
    }
  }, [currentBrand?.id, filter]);

  useEffect(() => { load(); }, [load]);

  const handleIngest = async () => {
    if (!currentBrand?.id || !newContent.trim()) return;
    setSaving(true);
    setError("");
    try {
      await storiesApi.ingest({
        brand_id: currentBrand.id,
        title: newTitle || undefined,
        source_type: newType,
        raw_content: newContent,
      });
      setNewContent("");
      setNewTitle("");
      setShowAdd(false);
      await load();
    } catch {
      setError("Failed to save material");
    } finally {
      setSaving(false);
    }
  };

  const handleExtract = async (entryId: string) => {
    setExtractingId(entryId);
    try {
      await storiesApi.extract(entryId);
      await load();
    } catch {
      setError("Extraction failed");
    } finally {
      setExtractingId(null);
    }
  };

  const handleDelete = async (entryId: string) => {
    if (!confirm("Delete this entry?")) return;
    try {
      await storiesApi.delete(entryId);
      await load();
    } catch {
      setError("Failed to delete");
    }
  };

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Select a brand first.</p>
          <Link href="/brand" className="glass-button-primary text-sm">Go to Brand →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Story Bank</h1>
            <p className="text-xs text-zinc-500 mt-0.5">
              Your personal material — notes, transcripts, ideas, opinions. AI extracts stories for content.
            </p>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="glass-button-primary text-sm"
          >
            + Add Material
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2.5 rounded-lg text-sm flex items-center gap-3">
            <span className="flex-1">{error}</span>
            {error.includes("load") && (
              <button
                onClick={() => { setError(""); load(); }}
                className="underline shrink-0"
              >
                Retry
              </button>
            )}
            <button
              onClick={() => setError("")}
              className="text-red-400/60 hover:text-red-400 shrink-0"
            >
              ✕
            </button>
          </div>
        )}

        {/* Add form */}
        {showAdd && (
          <div className="glass-card space-y-3">
            <input
              className="glass-input w-full text-sm"
              placeholder="Title (optional)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
            />
            <select
              className="glass-input w-full text-sm"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            >
              {SOURCE_TYPES.filter(t => t.value).map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <textarea
              className="glass-input w-full text-sm min-h-[120px]"
              placeholder="Paste your transcript, note, idea, opinion..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                onClick={handleIngest}
                disabled={saving || !newContent.trim()}
                className="glass-button-primary text-sm"
              >
                {saving ? "Saving & Extracting..." : "Save & Extract Stories"}
              </button>
              <button onClick={() => setShowAdd(false)} className="glass-button text-sm">Cancel</button>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {SOURCE_TYPES.map(t => (
            <button
              key={t.value}
              onClick={() => setFilter(t.value)}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                filter === t.value
                  ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                  : "glass-button"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Entries list */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-5 animate-pulse"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="h-4 w-14 rounded-full bg-zinc-800/50" />
                  <div className="h-4 w-32 rounded bg-zinc-800/50" />
                </div>
                <div className="h-3 w-full rounded bg-zinc-800/40" />
                <div className="h-3 w-2/3 rounded bg-zinc-800/40 mt-1.5" />
                <div className="h-2.5 w-36 rounded bg-zinc-800/40 mt-2" />
              </div>
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="glass-card text-center py-12">
            <p className="text-zinc-400 text-sm">No stories yet. Add your first material above.</p>
            <p className="text-zinc-600 text-xs mt-1">
              Paste transcripts, notes, ideas — AI will extract stories for your content.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map(entry => (
              <div key={entry.id} className="glass-card">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="glass-badge text-xs">{entry.source_type}</span>
                      {entry.pinned && <span className="text-amber-400 text-xs">pinned</span>}
                      {entry.title && (
                        <span className="text-sm font-medium text-zinc-200 truncate">{entry.title}</span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 line-clamp-2">{entry.raw_content}</p>
                    <p className="text-xs text-zinc-600 mt-1">
                      {new Date(entry.created_at).toLocaleDateString()} · {entry.extracted_stories.length} stories extracted
                    </p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                      className="glass-button text-xs px-2 py-1"
                    >
                      {expandedId === entry.id ? "▲" : "▼"}
                    </button>
                    <button
                      onClick={() => handleExtract(entry.id)}
                      disabled={extractingId === entry.id}
                      className="glass-button text-xs px-2 py-1"
                    >
                      {extractingId === entry.id ? "..." : "Re-extract"}
                    </button>
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className="glass-button text-xs px-2 py-1 text-red-400"
                    >
                      Del
                    </button>
                  </div>
                </div>

                {/* Expanded: show extracted stories */}
                {expandedId === entry.id && (
                  <div className="mt-3 pt-3 border-t border-zinc-800 space-y-2">
                    <p className="text-xs text-zinc-500 font-medium">Raw Content:</p>
                    <p className="text-xs text-zinc-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                      {entry.raw_content}
                    </p>

                    {entry.extracted_stories.length > 0 && (
                      <>
                        <p className="text-xs text-zinc-500 font-medium mt-3">Extracted Stories:</p>
                        {entry.extracted_stories.map((story, i) => (
                          <div key={i} className="rounded-lg bg-zinc-900/50 p-3 space-y-1">
                            <p className="text-sm text-zinc-200">{story.summary}</p>
                            <div className="flex gap-2 text-xs">
                              <span className="text-violet-400">{story.theme}</span>
                              <span className="text-zinc-600">·</span>
                              <span className="text-zinc-500">{story.emotion}</span>
                            </div>
                            {story.key_quote && (
                              <p className="text-xs text-zinc-400 italic">&ldquo;{story.key_quote}&rdquo;</p>
                            )}
                            {story.usable_hook && (
                              <p className="text-xs text-amber-400/80">Hook: {story.usable_hook}</p>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
