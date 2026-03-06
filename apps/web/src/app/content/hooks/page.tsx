"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { hooksApi, Hook, HookType, HOOK_TYPE_LABELS } from "@/lib/api/hooks";

const HOOK_TYPES: (HookType | "all")[] = ["all", "anxiety", "benefit", "story", "competitor", "belief", "curiosity", "custom"];

export default function ContentHooksPage() {
  const { currentBrand } = useBrand();
  const [hooks, setHooks] = useState<Hook[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<HookType | "all">("all");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [newHookText, setNewHookText] = useState("");
  const [newHookType, setNewHookType] = useState<HookType>("custom");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHooks = async () => {
    if (!currentBrand?.id) return;
    setLoading(true);
    try {
      const res = await hooksApi.list({ brand_id: currentBrand.id, limit: 200 });
      setHooks(Array.isArray(res) ? res : (res as any).hooks ?? []);
    } catch {
      setError("Failed to load hooks");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadHooks(); }, [currentBrand?.id]);

  const filtered = filterType === "all" ? hooks : hooks.filter((h) => h.hook_type === filterType);

  const handleCreate = async () => {
    if (!newHookText.trim() || !currentBrand?.id) return;
    setSaving(true);
    try {
      await hooksApi.create({ brand_id: currentBrand.id, hook_text: newHookText.trim(), hook_type: newHookType, source: "manual" });
      setNewHookText("");
      setAddOpen(false);
      await loadHooks();
    } catch { setError("Failed to create hook"); }
    finally { setSaving(false); }
  };

  const handleUpdate = async (id: string) => {
    if (!editText.trim()) return;
    setSaving(true);
    try {
      await hooksApi.update(id, { hook_text: editText.trim() });
      setEditingId(null);
      await loadHooks();
    } catch { setError("Failed to update hook"); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    try {
      await hooksApi.delete(id);
      await loadHooks();
    } catch { setError("Failed to delete hook"); }
  };

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400">Select a brand to manage hooks.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-4xl mx-auto px-5 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/content" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">← Content</Link>
            <h1 className="text-xl font-bold text-zinc-100 mt-1">Hook Library</h1>
            <p className="text-xs text-zinc-500 mt-0.5">{hooks.length} hooks · Auto-populated from approved posts.</p>
          </div>
          <button onClick={() => setAddOpen(!addOpen)} className="glass-button text-sm">
            + Add Hook
          </button>
        </div>

        {error && (
          <div className="glass-card ring-red-500/20 bg-red-500/5 py-2 px-4 text-xs text-red-400">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">Dismiss</button>
          </div>
        )}

        {addOpen && (
          <div className="glass-card space-y-3">
            <textarea
              value={newHookText}
              onChange={(e) => setNewHookText(e.target.value)}
              placeholder="Write your hook..."
              className="glass-input h-20 resize-none"
            />
            <div className="flex items-center gap-3">
              <select
                value={newHookType}
                onChange={(e) => setNewHookType(e.target.value as HookType)}
                className="glass-input w-40"
              >
                {(Object.entries(HOOK_TYPE_LABELS)).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
              <button onClick={handleCreate} disabled={saving || !newHookText.trim()} className="glass-button-primary text-sm">
                {saving ? "Saving..." : "Save"}
              </button>
              <button onClick={() => setAddOpen(false)} className="glass-button text-sm">Cancel</button>
            </div>
          </div>
        )}

        {/* Filter */}
        <div className="flex gap-1.5 flex-wrap">
          {HOOK_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
                filterType === t
                  ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                  : "text-zinc-500 hover:text-zinc-300 bg-white/[0.03] ring-1 ring-white/[0.05]"
              }`}
            >
              {t === "all" ? "All" : HOOK_TYPE_LABELS[t]?.label || t}
            </button>
          ))}
        </div>

        {/* Hooks list */}
        {loading ? (
          <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="glass-card py-8 text-center">
            <p className="text-sm text-zinc-500">No hooks yet. Approve some posts or add one manually.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((h) => (
              <div key={h.id} className="glass-card py-3 px-4 group">
                {editingId === h.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      className="glass-input h-16 resize-none text-sm"
                    />
                    <div className="flex gap-2">
                      <button onClick={() => handleUpdate(h.id)} disabled={saving} className="glass-button-primary text-xs">Save</button>
                      <button onClick={() => setEditingId(null)} className="glass-button text-xs">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <p className="flex-1 text-sm text-zinc-300 leading-relaxed">{h.hook_text}</p>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="glass-badge text-[9px]">{HOOK_TYPE_LABELS[h.hook_type]?.label || h.hook_type}</span>
                      {h.times_used > 0 && (
                        <span className="text-[9px] text-zinc-600">{h.times_used}x</span>
                      )}
                      <button
                        onClick={() => { setEditingId(h.id); setEditText(h.hook_text); }}
                        className="opacity-40 group-hover:opacity-100 text-xs text-zinc-500 hover:text-zinc-300 transition-all"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(h.id)}
                        className="opacity-40 group-hover:opacity-100 text-xs text-zinc-500 hover:text-red-400 transition-all"
                      >
                        Del
                      </button>
                    </div>
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
