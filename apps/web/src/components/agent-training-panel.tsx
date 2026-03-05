"use client";

/**
 * AgentTrainingPanel — Gemini-style per-agent knowledge manager.
 *
 * Sections:
 *   Instructions — current plan/goals textarea (doc_type: "instructions")
 *   Knowledge    — card grid: Quick Note, PDF/Doc, URL
 *
 * Each agent stores its own instructions + knowledge docs via agent_scope.
 */

import { useState, useEffect } from "react";
import { knowledgeDocsApi } from "@/lib/api/knowledge-docs";

interface Props {
  agentId: string;
  agentName?: string;
}

interface KnowledgeDoc {
  id: string;
  title: string;
  content: string;
  doc_type: string;
  agent_scope?: string[];
  created_at?: string;
}

const DOC_TYPE_ICONS: Record<string, string> = {
  instructions: "📋",
  framework: "🏗️",
  writing_sop: "✍️",
  cold_email: "📧",
  ad_copy: "🎯",
  case_study: "📊",
  other: "📄",
  url: "🔗",
};

export default function AgentTrainingPanel({ agentId, agentName }: Props) {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [instructions, setInstructions] = useState<KnowledgeDoc | null>(null);
  const [instrText, setInstrText] = useState("");
  const [instrSaving, setInstrSaving] = useState(false);
  const [instrSaved, setInstrSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"note" | "url" | "file" | null>(null);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { loadAll(); }, [agentId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const all = await knowledgeDocsApi.list() as KnowledgeDoc[];
      const mine = all.filter((d) => (d.agent_scope || []).includes(agentId));
      const instr = mine.find((d) => d.doc_type === "instructions") || null;
      setInstructions(instr);
      setInstrText(instr?.content || "");
      setDocs(mine.filter((d) => d.doc_type !== "instructions"));
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  // ── Instructions ────────────────────────────────────────────────────────

  const saveInstructions = async () => {
    if (!instrText.trim()) return;
    setInstrSaving(true);
    try {
      if (instructions) {
        await knowledgeDocsApi.update(instructions.id, {
          content: instrText,
          doc_type: "instructions",
        });
      } else {
        const created = await knowledgeDocsApi.create({
          title: `${agentName || agentId} — Instructions`,
          content: instrText,
          doc_type: "instructions",
          agent_scope: [agentId],
        });
        setInstructions(created as KnowledgeDoc);
      }
      setInstrSaved(true);
      setTimeout(() => setInstrSaved(false), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save instructions");
    } finally {
      setInstrSaving(false);
    }
  };

  // ── Knowledge docs ──────────────────────────────────────────────────────

  const saveNote = async () => {
    if (!noteContent.trim()) { setError("Content is required."); return; }
    const title = noteTitle.trim() || noteContent.trim().split("\n")[0].slice(0, 60) || "Quick Note";
    setSaving(true);
    setError(null);
    try {
      await knowledgeDocsApi.create({
        title,
        content: noteContent,
        doc_type: "framework",
        agent_scope: [agentId],
      });
      setNoteTitle("");
      setNoteContent("");
      setMode(null);
      await loadAll();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save note");
    } finally {
      setSaving(false);
    }
  };

  const saveUrl = async () => {
    if (!urlInput.trim()) { setError("URL is required."); return; }
    setSaving(true);
    setError(null);
    try {
      await knowledgeDocsApi.create({
        title: urlInput.replace(/^https?:\/\/(www\.)?/, "").split("/")[0],
        content: urlInput,
        doc_type: "other",
        agent_scope: [agentId],
      });
      setUrlInput("");
      setMode(null);
      await loadAll();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save URL");
    } finally {
      setSaving(false);
    }
  };

  const handleFileDrop = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { setError("File too large. Max 10MB."); return; }
    setUploading(true);
    setError(null);
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = (reader.result as string).split(",")[1];
      try {
        await knowledgeDocsApi.create({
          title: file.name,
          content: base64,
          doc_type: "other",
          agent_scope: [agentId],
        });
        await loadAll();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const deleteDoc = async (id: string) => {
    try {
      await knowledgeDocsApi.delete(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch { /* silent */ }
  };

  const cancel = () => { setMode(null); setNoteTitle(""); setNoteContent(""); setUrlInput(""); setError(null); };

  return (
    <div className="space-y-4">
      {error && (
        <div className="px-3 py-2 bg-red-900/30 border border-red-500/30 text-red-400 rounded-lg text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-2 hover:text-red-200">×</button>
        </div>
      )}

      {/* ── Instructions ─────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Instructions</span>
          {instrSaved && <span className="text-[10px] text-green-400">Saved ✓</span>}
        </div>
        <textarea
          value={instrText}
          onChange={(e) => setInstrText(e.target.value)}
          rows={5}
          placeholder={`Tell ${agentName || agentId} their current plan, goals, and priorities...\n\nExample: My current plan is to generate 50 qualified leads this week for agency owners in the US. Focus on decision-makers with 5-50 employees. Prioritize LinkedIn outreach.`}
          className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 resize-none focus:outline-none focus:border-indigo-500/60 transition-colors"
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={saveInstructions}
            disabled={instrSaving || !instrText.trim()}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-lg disabled:opacity-40 transition"
          >
            {instrSaving ? "Saving..." : "Save Instructions"}
          </button>
        </div>
      </div>

      {/* ── Knowledge ─────────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Knowledge</span>
          <span className="text-[10px] text-slate-600">{docs.length} doc{docs.length !== 1 ? "s" : ""}</span>
        </div>

        {/* Add buttons */}
        {!mode && (
          <div className="grid grid-cols-3 gap-2 mb-3">
            <button
              onClick={() => setMode("note")}
              className="flex flex-col items-center gap-1.5 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              <span className="text-lg">📝</span>
              <span>Quick Note</span>
            </button>
            <label className="flex flex-col items-center gap-1.5 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer">
              <span className="text-lg">{uploading ? "⏳" : "📄"}</span>
              <span>{uploading ? "Uploading..." : "PDF / Doc"}</span>
              <input type="file" accept=".pdf,.docx,.txt,.md" className="hidden" onChange={handleFileDrop} disabled={uploading} />
            </label>
            <button
              onClick={() => setMode("url")}
              className="flex flex-col items-center gap-1.5 py-3 bg-white/5 hover:bg-white/10 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              <span className="text-lg">🔗</span>
              <span>Add Link</span>
            </button>
          </div>
        )}

        {/* Quick Note form */}
        {mode === "note" && (
          <div className="space-y-2 mb-3">
            <input
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="Title (optional — auto-detected from first line)"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60"
            />
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Paste your framework, SOP, book notes, methodology, case study..."
              rows={5}
              className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 resize-none focus:outline-none focus:border-indigo-500/60"
            />
            <div className="flex gap-2">
              <button onClick={saveNote} disabled={saving} className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-xl disabled:opacity-40">
                {saving ? "Saving..." : "Save"}
              </button>
              <button onClick={cancel} className="px-4 py-1.5 border border-white/10 text-slate-400 text-xs rounded-xl hover:text-slate-200">Cancel</button>
            </div>
          </div>
        )}

        {/* URL form */}
        {mode === "url" && (
          <div className="space-y-2 mb-3">
            <input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://..."
              type="url"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60"
            />
            <div className="flex gap-2">
              <button onClick={saveUrl} disabled={saving} className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-xl disabled:opacity-40">
                {saving ? "Saving..." : "Save Link"}
              </button>
              <button onClick={cancel} className="px-4 py-1.5 border border-white/10 text-slate-400 text-xs rounded-xl hover:text-slate-200">Cancel</button>
            </div>
          </div>
        )}

        {/* Knowledge card grid */}
        {loading ? (
          <div className="grid grid-cols-2 gap-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : docs.length > 0 ? (
          <div className="grid grid-cols-2 gap-2">
            {docs.map((doc) => (
              <div key={doc.id} className="group relative flex flex-col gap-1.5 p-3 bg-white/5 hover:bg-white/8 rounded-xl border border-white/5 hover:border-white/10 transition-colors">
                <button
                  onClick={() => deleteDoc(doc.id)}
                  className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400 text-sm transition-opacity"
                >
                  ×
                </button>
                <span className="text-lg">{DOC_TYPE_ICONS[doc.doc_type] || "📄"}</span>
                <p className="text-slate-300 text-[11px] font-medium leading-tight line-clamp-2 pr-4">{doc.title}</p>
                <span className="text-[9px] text-slate-600 uppercase tracking-wide">{doc.doc_type}</span>
              </div>
            ))}
          </div>
        ) : !mode ? (
          <p className="text-xs text-slate-600 text-center py-3">No knowledge yet. Add your first document above.</p>
        ) : null}
      </div>
    </div>
  );
}
