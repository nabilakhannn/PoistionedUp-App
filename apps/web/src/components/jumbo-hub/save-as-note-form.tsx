"use client";

import { useState } from "react";
import { jumboHubApi } from "@/lib/api/jumbo-hub";

interface SaveAsNoteFormProps {
  brandId: string;
  content: string;
  onClose: () => void;
}

export function SaveAsNoteForm({ brandId, content, onClose }: SaveAsNoteFormProps) {
  const [title, setTitle] = useState(content.slice(0, 60).replace(/\n/g, " ").trim());
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await jumboHubApi.saveAsNote(brandId, content, title);
      setSaved(true);
      setTimeout(onClose, 1500);
    } catch {
      setError("Failed to save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  if (saved) {
    return (
      <div
        data-testid="save-note-success"
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs"
      >
        <span>✓</span> Saved to notes
      </div>
    );
  }

  return (
    <div
      data-testid="save-note-form"
      className="flex flex-col gap-2 p-3 rounded-lg bg-[#161b27] border border-indigo-500/20 mt-2"
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-indigo-400 font-medium">📌 Save as Note</span>
      </div>
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Note title..."
        maxLength={200}
        className="px-3 py-2 rounded-lg bg-[#0f1420] border border-white/10 text-gray-200 placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500/50"
      />
      <div className="flex items-center gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !title.trim()}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all disabled:opacity-40"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          onClick={onClose}
          className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 text-xs transition-all"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
