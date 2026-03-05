"use client";

/**
 * Hook Library — Slice 102 (Fix F)
 * User-visible, editable hook library. Agents pull from this before writing.
 * Auto-populated when a post is approved (opening line saved as hook).
 */

import { useEffect, useState, useCallback } from "react";
import { useBrand } from "@/lib/brand-context";
import { hooksApi, Hook, HookType, HOOK_TYPE_LABELS } from "@/lib/api/hooks";

const HOOK_TYPES = Object.keys(HOOK_TYPE_LABELS) as HookType[];

export default function HookLibraryPage() {
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

  const load = useCallback(async () => {
    try {
      const data = await hooksApi.list({
        brand_id: currentBrand?.id,
        hook_type: filterType === "all" ? undefined : filterType,
      });
      setHooks(data);
    } catch {
      setError("Failed to load hooks");
    } finally {
      setLoading(false);
    }
  }, [currentBrand?.id, filterType]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    const text = newHookText.trim();
    if (!text) return;
    setSaving(true);
    try {
      await hooksApi.create({
        brand_id: currentBrand?.id,
        hook_text: text,
        hook_type: newHookType,
        source: "manual",
      });
      setNewHookText("");
      setNewHookType("custom");
      setAddOpen(false);
      await load();
    } catch {
      setError("Failed to add hook");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (hookId: string) => {
    const text = editText.trim();
    if (!text) return;
    setSaving(true);
    try {
      await hooksApi.update(hookId, { hook_text: text });
      setEditingId(null);
      await load();
    } catch {
      setError("Failed to save edit");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (hookId: string) => {
    if (!confirm("Delete this hook?")) return;
    try {
      await hooksApi.delete(hookId);
      await load();
    } catch {
      setError("Failed to delete hook");
    }
  };

  const filtered = filterType === "all" ? hooks : hooks.filter((h) => h.hook_type === filterType);

  // Group by type for the grid view
  const grouped: Record<string, Hook[]> = {};
  for (const h of filtered) {
    const t = h.hook_type;
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(h);
  }

  if (!currentBrand) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="rounded-xl border border-border bg-card/30 px-8 py-12 text-center max-w-sm">
          <div className="text-3xl mb-3">🪝</div>
          <p className="text-sm font-medium text-foreground mb-1">No brand selected</p>
          <p className="text-xs text-muted-foreground mb-4">
            Select a brand from the sidebar to access your hook library.
          </p>
          <a href="/brands" className="text-xs text-primary hover:underline">Manage brands →</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <div className="flex items-center gap-2">
          <span className="text-amber-400 text-lg">🪝</span>
          <h1 className="text-sm font-bold text-foreground tracking-wider uppercase">Hook Library</h1>
          {currentBrand && (
            <span className="text-xs text-muted-foreground">— {currentBrand.name}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">{hooks.length} hooks total</span>
          <button
            onClick={() => setAddOpen(true)}
            className="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:bg-primary/90 transition"
          >
            + Add Hook
          </button>
        </div>
      </div>

      <div className="p-5 max-w-5xl mx-auto space-y-5">
        {/* Context banner */}
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 text-xs text-amber-200/80 flex items-start gap-2">
          <span className="text-amber-400 mt-0.5">💡</span>
          <div>
            <strong className="text-amber-300">Agents use this library before every write.</strong> Add hooks here to train your copywriter.
            Hooks auto-save when you approve posts. The more you add, the more your content sounds like you.
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 text-xs text-red-400 flex items-center gap-2">
            <span>⚠️</span> {error}
            <button onClick={() => setError(null)} className="ml-auto text-muted-foreground hover:text-foreground">✕</button>
          </div>
        )}

        {/* Add Hook form */}
        {addOpen && (
          <div className="bg-card border border-border rounded-xl p-4 space-y-3">
            <p className="text-sm font-semibold text-foreground">Add New Hook</p>
            <textarea
              value={newHookText}
              onChange={(e) => setNewHookText(e.target.value)}
              placeholder="Enter the hook text — the opening line that stops the scroll..."
              rows={3}
              className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
            <div className="flex items-center gap-3">
              <select
                value={newHookType}
                onChange={(e) => setNewHookType(e.target.value as HookType)}
                className="bg-muted/30 border border-border rounded-lg px-2 py-1.5 text-xs focus:outline-none"
              >
                {HOOK_TYPES.map((t) => (
                  <option key={t} value={t}>{HOOK_TYPE_LABELS[t].label}</option>
                ))}
              </select>
              <span className="text-[10px] text-muted-foreground">{HOOK_TYPE_LABELS[newHookType].description}</span>
              <div className="flex gap-2 ml-auto">
                <button onClick={() => setAddOpen(false)} className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted-foreground hover:text-foreground transition">
                  Cancel
                </button>
                <button onClick={handleAdd} disabled={saving || !newHookText.trim()} className="px-3 py-1.5 text-xs rounded-lg bg-primary text-primary-foreground font-medium disabled:opacity-40 transition">
                  {saving ? "Saving..." : "Save Hook"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1.5 text-xs rounded-lg border transition ${filterType === "all" ? "bg-primary/15 text-primary border-primary/20" : "border-border text-muted-foreground hover:text-foreground"}`}
          >
            All ({hooks.length})
          </button>
          {HOOK_TYPES.map((t) => {
            const count = hooks.filter((h) => h.hook_type === t).length;
            if (count === 0) return null;
            const meta = HOOK_TYPE_LABELS[t];
            return (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`px-3 py-1.5 text-xs rounded-lg border transition ${filterType === t ? `${meta.color} border-current` : "border-border text-muted-foreground hover:text-foreground"}`}
              >
                {meta.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Hook grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-24 rounded-xl border border-border bg-card/30 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <div className="text-4xl mb-3">🪝</div>
            <p className="text-sm font-medium">No hooks yet</p>
            <p className="text-xs mt-1">Add hooks manually or approve a pipeline post to auto-save its opening line.</p>
          </div>
        ) : filterType === "all" ? (
          // Grouped view when showing all
          <div className="space-y-6">
            {Object.entries(grouped).map(([type, typeHooks]) => {
              const meta = HOOK_TYPE_LABELS[type as HookType] || HOOK_TYPE_LABELS.custom;
              return (
                <div key={type}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${meta.color}`}>{meta.label}</span>
                    <span className="text-[10px] text-muted-foreground">{meta.description} · {typeHooks.length} hooks</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {typeHooks.map((hook) => (
                      <HookCard
                        key={hook.id}
                        hook={hook}
                        editing={editingId === hook.id}
                        editText={editText}
                        onStartEdit={() => { setEditingId(hook.id); setEditText(hook.hook_text); }}
                        onCancelEdit={() => setEditingId(null)}
                        onSaveEdit={() => handleEdit(hook.id)}
                        onEditTextChange={setEditText}
                        onDelete={() => handleDelete(hook.id)}
                        saving={saving}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          // Flat grid when filtered by type
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {filtered.map((hook) => (
              <HookCard
                key={hook.id}
                hook={hook}
                editing={editingId === hook.id}
                editText={editText}
                onStartEdit={() => { setEditingId(hook.id); setEditText(hook.hook_text); }}
                onCancelEdit={() => setEditingId(null)}
                onSaveEdit={() => handleEdit(hook.id)}
                onEditTextChange={setEditText}
                onDelete={() => handleDelete(hook.id)}
                saving={saving}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Hook Card ────────────────────────────────────────────────────────────

interface HookCardProps {
  hook: Hook;
  editing: boolean;
  editText: string;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onEditTextChange: (t: string) => void;
  onDelete: () => void;
  saving: boolean;
}

function HookCard({ hook, editing, editText, onStartEdit, onCancelEdit, onSaveEdit, onEditTextChange, onDelete, saving }: HookCardProps) {
  const meta = HOOK_TYPE_LABELS[hook.hook_type as HookType] || HOOK_TYPE_LABELS.custom;
  return (
    <div className="bg-card border border-border rounded-xl p-3 space-y-2 group hover:border-primary/30 transition">
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={editText}
            onChange={(e) => onEditTextChange(e.target.value)}
            rows={3}
            className="w-full bg-muted/30 border border-border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            autoFocus
          />
          <div className="flex gap-1.5 justify-end">
            <button onClick={onCancelEdit} className="px-2.5 py-1 text-[10px] rounded border border-border text-muted-foreground hover:text-foreground transition">
              Cancel
            </button>
            <button onClick={onSaveEdit} disabled={saving} className="px-2.5 py-1 text-[10px] rounded bg-primary text-primary-foreground disabled:opacity-40 transition">
              Save
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm text-foreground leading-snug">{hook.hook_text}</p>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${meta.color}`}>{meta.label}</span>
            {hook.source !== "manual" && (
              <span className="text-[9px] text-muted-foreground bg-muted/20 px-1.5 py-0.5 rounded">{hook.source}</span>
            )}
            {hook.times_used > 0 && (
              <span className="text-[9px] text-muted-foreground">Used {hook.times_used}×</span>
            )}
            <div className="ml-auto flex gap-1 opacity-40 group-hover:opacity-100 transition">
              <button onClick={onStartEdit} className="text-[10px] px-2 py-0.5 rounded border border-border text-muted-foreground hover:text-foreground transition">
                Edit
              </button>
              <button onClick={onDelete} className="text-[10px] px-2 py-0.5 rounded border border-red-500/20 text-red-400/60 hover:text-red-400 transition">
                Del
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
