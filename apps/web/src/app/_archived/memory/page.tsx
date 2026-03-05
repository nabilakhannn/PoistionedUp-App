"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  memoryApi,
  AgentMemorySummary,
  MemorySynthesisResponse,
} from "../../lib/api";
import { useBrand } from "@/lib/brand-context";

const MEMORY_TYPES = [
  { value: "observation", label: "Observations" },
  { value: "preference", label: "Preferences" },
  { value: "lesson", label: "Lessons" },
  { value: "content_pattern", label: "Patterns" },
  { value: "voice_note", label: "Voice Notes" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-300 border border-green-500/30",
  pending_approval: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30",
  dismissed: "bg-muted text-muted-foreground border border-border",
  superseded: "bg-primary/20 text-primary border border-primary/30",
  expired: "bg-red-500/20 text-red-300 border border-red-500/30",
};

const TYPE_COLORS: Record<string, string> = {
  observation: "bg-sky-500/20 text-sky-300 border border-sky-500/30",
  preference: "bg-pink-500/20 text-pink-300 border border-pink-500/30",
  lesson: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  content_pattern: "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30",
  voice_note: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
};

export default function MemoryPage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [memories, setMemories] = useState<AgentMemorySummary[]>([]);
  const [pendingMemories, setPendingMemories] = useState<AgentMemorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"all" | "pending" | "add">("all");
  const [filterType, setFilterType] = useState("");
  const [synthesizing, setSynthesizing] = useState(false);
  const [synthResult, setSynthResult] = useState<MemorySynthesisResponse | null>(null);

  // Add memory form
  const [newType, setNewType] = useState("observation");
  const [newContent, setNewContent] = useState("");
  const [newConfidence, setNewConfidence] = useState(0.5);
  const [newPlatform, setNewPlatform] = useState("");
  const [newCategory, setNewCategory] = useState("");

  async function loadMemories() {
    try {
      setLoading(true);
      setError("");
      const [all, pending] = await Promise.all([
        memoryApi.list(filterType || undefined, "active", undefined, brandId || undefined),
        memoryApi.pending(brandId || undefined),
      ]);
      setMemories(all);
      setPendingMemories(pending);
    } catch (err: any) {
      setError(err.message || "Failed to load memories");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (brandLoading) return;
    loadMemories();
  }, [filterType, brandId, brandLoading]);

  async function handleApprove(id: string) {
    try {
      await memoryApi.approve(id, "approve");
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDismiss(id: string) {
    try {
      await memoryApi.approve(id, "dismiss");
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this memory permanently?")) return;
    try {
      await memoryApi.delete(id);
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleSynthesize() {
    try {
      setSynthesizing(true);
      setSynthResult(null);
      const result = await memoryApi.synthesize(brandId || undefined);
      setSynthResult(result);
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSynthesizing(false);
    }
  }

  async function handleAddMemory(e: React.FormEvent) {
    e.preventDefault();
    if (!newContent.trim()) return;
    try {
      await memoryApi.create({
        memory_type: newType,
        content: newContent,
        confidence: newConfidence,
        platform: newPlatform || undefined,
        category: newCategory || undefined,
        source: "user",
        brand_id: brandId || undefined,
      });
      setNewContent("");
      setNewConfidence(0.5);
      setNewPlatform("");
      setNewCategory("");
      setTab("all");
      loadMemories();
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link href="/" className="text-sm text-primary hover:text-primary/80 transition">
              &larr; Home
            </Link>
            <h1 className="text-2xl font-bold mt-1">Agent Memory</h1>
            <p className="text-sm text-muted-foreground mt-1">
              What the AI has learned about your content, preferences, and patterns
            </p>
          </div>
          <button
            onClick={handleSynthesize}
            disabled={synthesizing}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:opacity-50 text-sm transition"
          >
            {synthesizing ? "Synthesizing..." : "Synthesize Patterns"}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg text-sm">
            {error}
            <button onClick={() => setError("")} className="ml-3 text-red-400 hover:text-red-200">
              Dismiss
            </button>
          </div>
        )}

        {synthResult && (
          <div className="mb-4 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
            <p className="font-medium text-indigo-300">{synthResult.message}</p>
            {synthResult.patterns_detected.length > 0 && (
              <ul className="mt-2 text-sm text-indigo-400">
                {synthResult.patterns_detected.map((p, i) => (
                  <li key={i}>New lesson: {p}</li>
                ))}
              </ul>
            )}
            <button
              onClick={() => setSynthResult(null)}
              className="mt-2 text-xs text-indigo-500 hover:text-indigo-300 transition"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-border">
          {[
            { key: "all" as const, label: `Active Memories (${memories.length})` },
            { key: "pending" as const, label: `Pending Approval (${pendingMemories.length})` },
            { key: "add" as const, label: "Add Memory" },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
                tab === t.key
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── ALL MEMORIES TAB ────────────────────────────── */}
        {tab === "all" && (
          <>
            {/* Type filter */}
            <div className="flex gap-2 mb-4 flex-wrap">
              <button
                onClick={() => setFilterType("")}
                className={`px-3 py-1 text-xs rounded-full transition ${
                  !filterType
                    ? "bg-foreground text-background"
                    : "bg-accent text-muted-foreground hover:bg-accent/80"
                }`}
              >
                All
              </button>
              {MEMORY_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setFilterType(t.value)}
                  className={`px-3 py-1 text-xs rounded-full transition ${
                    filterType === t.value
                      ? "bg-foreground text-background"
                      : `${TYPE_COLORS[t.value]} hover:opacity-80`
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="bg-card border border-border rounded-lg p-4">
                    <div className="h-4 bg-accent rounded w-1/3 mb-2" />
                    <div className="h-3 bg-accent rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : memories.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-4xl mb-3">🧠</div>
                <p className="text-lg mb-2 text-foreground">No memories yet</p>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  Memories are auto-created as the agent learns from your content performance
                  and editing patterns. You can also add memories manually.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {memories.map((m) => (
                  <div
                    key={m.id}
                    className="p-4 bg-card border border-border rounded-lg hover:border-muted-foreground transition"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${TYPE_COLORS[m.memory_type] || "bg-muted text-foreground"}`}>
                            {m.memory_type}
                          </span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[m.status] || "bg-muted text-foreground"}`}>
                            {m.status}
                          </span>
                          {m.platform && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-accent text-muted-foreground">
                              {m.platform}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-foreground">{m.content}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          <span>
                            Confidence:{" "}
                            <span
                              className={`font-medium ${
                                m.confidence >= 0.8
                                  ? "text-green-400"
                                  : m.confidence >= 0.5
                                  ? "text-yellow-400"
                                  : "text-red-400"
                              }`}
                            >
                              {Math.round(m.confidence * 100)}%
                            </span>
                          </span>
                          {m.category && <span>Category: {m.category}</span>}
                          {m.source && <span>Source: {m.source}</span>}
                          {m.last_used_at && (
                            <span>Last used: {new Date(m.last_used_at).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDelete(m.id)}
                        className="ml-3 text-muted-foreground hover:text-red-400 text-sm transition"
                        title="Delete memory"
                      >
                        &times;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── PENDING APPROVAL TAB ─────────────────────── */}
        {tab === "pending" && (
          <>
            {pendingMemories.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-4xl mb-3">✅</div>
                <p className="text-lg mb-2 text-foreground">No pending approvals</p>
                <p className="text-sm text-muted-foreground max-w-md mx-auto">
                  When the agent synthesizes observations into strategic lessons,
                  they appear here for your review.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingMemories.map((m) => (
                  <div
                    key={m.id}
                    className="p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-lg"
                  >
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${TYPE_COLORS[m.memory_type] || "bg-muted text-foreground"}`}>
                        {m.memory_type}
                      </span>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                        Pending Approval
                      </span>
                    </div>
                    <p className="text-sm text-foreground mb-3">{m.content}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
                      <span>Confidence: {Math.round(m.confidence * 100)}%</span>
                      {m.category && <span>Category: {m.category}</span>}
                      {m.platform && <span>Platform: {m.platform}</span>}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(m.id)}
                        className="px-4 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-500 transition"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleDismiss(m.id)}
                        className="px-4 py-1.5 bg-accent text-foreground rounded-lg text-sm hover:bg-accent/80 transition"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── ADD MEMORY TAB ────────────────────────────── */}
        {tab === "add" && (
          <form
            onSubmit={handleAddMemory}
            className="bg-card border border-border p-6 rounded-xl space-y-4"
          >
            <h2 className="text-lg font-semibold text-card-foreground">Add a Memory Manually</h2>
            <p className="text-sm text-muted-foreground">
              Tell the agent something it should remember about your content preferences,
              voice, or strategy.
            </p>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Memory Type</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground focus:ring-2 focus:ring-ring"
              >
                {MEMORY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Content</label>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="e.g., 'I prefer short, punchy hooks under 10 words' or 'Never use rhetorical questions'"
                rows={3}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring resize-none"
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Confidence ({Math.round(newConfidence * 100)}%)
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={newConfidence}
                  onChange={(e) => setNewConfidence(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Platform (optional)</label>
                <select
                  value={newPlatform}
                  onChange={(e) => setNewPlatform(e.target.value)}
                  className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground focus:ring-2 focus:ring-ring"
                >
                  <option value="">All platforms</option>
                  <option value="youtube">YouTube</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="instagram">Instagram</option>
                  <option value="twitter">Twitter</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Category (optional)</label>
                <input
                  type="text"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  placeholder="e.g., hooks, voice, topics"
                  className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>

            <button
              type="submit"
              className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 text-sm font-medium transition"
            >
              Save Memory
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
