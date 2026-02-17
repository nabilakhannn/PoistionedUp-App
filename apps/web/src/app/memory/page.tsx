"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  memoryApi,
  AgentMemorySummary,
  MemorySynthesisResponse,
} from "../../lib/api";

const MEMORY_TYPES = [
  { value: "observation", label: "Observations", icon: "eye" },
  { value: "preference", label: "Preferences", icon: "heart" },
  { value: "lesson", label: "Lessons", icon: "lightbulb" },
  { value: "content_pattern", label: "Patterns", icon: "puzzle" },
  { value: "voice_note", label: "Voice Notes", icon: "mic" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  pending_approval: "bg-yellow-100 text-yellow-800",
  dismissed: "bg-gray-100 text-gray-500",
  superseded: "bg-blue-100 text-blue-600",
  expired: "bg-red-100 text-red-600",
};

const TYPE_COLORS: Record<string, string> = {
  observation: "bg-sky-100 text-sky-800",
  preference: "bg-pink-100 text-pink-800",
  lesson: "bg-amber-100 text-amber-800",
  content_pattern: "bg-indigo-100 text-indigo-800",
  voice_note: "bg-violet-100 text-violet-800",
};

const CONFIDENCE_BAR: Record<string, string> = {
  high: "bg-green-500",
  medium: "bg-yellow-500",
  low: "bg-red-400",
};

function confidenceLabel(c: number): string {
  if (c >= 0.8) return "high";
  if (c >= 0.5) return "medium";
  return "low";
}

export default function MemoryPage() {
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
        memoryApi.list(filterType || undefined, "active"),
        memoryApi.pending(),
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
    loadMemories();
  }, [filterType]);

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
      const result = await memoryApi.synthesize();
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
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            &larr; Home
          </Link>
          <h1 className="text-2xl font-bold mt-1">Agent Memory</h1>
          <p className="text-sm text-gray-500 mt-1">
            What the AI has learned about your content, preferences, and patterns
          </p>
        </div>
        <button
          onClick={handleSynthesize}
          disabled={synthesizing}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
        >
          {synthesizing ? "Synthesizing..." : "Synthesize Patterns"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {synthResult && (
        <div className="mb-4 p-4 bg-indigo-50 rounded-lg">
          <p className="font-medium text-indigo-900">{synthResult.message}</p>
          {synthResult.patterns_detected.length > 0 && (
            <ul className="mt-2 text-sm text-indigo-700">
              {synthResult.patterns_detected.map((p, i) => (
                <li key={i}>New lesson: {p}</li>
              ))}
            </ul>
          )}
          <button
            onClick={() => setSynthResult(null)}
            className="mt-2 text-xs text-indigo-500 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        {[
          { key: "all" as const, label: `Active Memories (${memories.length})` },
          { key: "pending" as const, label: `Pending Approval (${pendingMemories.length})` },
          { key: "add" as const, label: "Add Memory" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t.key
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
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
              className={`px-3 py-1 text-xs rounded-full ${
                !filterType ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              All
            </button>
            {MEMORY_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setFilterType(t.value)}
                className={`px-3 py-1 text-xs rounded-full ${
                  filterType === t.value
                    ? "bg-gray-900 text-white"
                    : `${TYPE_COLORS[t.value]} hover:opacity-80`
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="text-gray-400 text-center py-8">Loading memories...</p>
          ) : memories.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg mb-2">No memories yet</p>
              <p className="text-sm">
                Memories are auto-created as the agent learns from your content performance
                and editing patterns. You can also add memories manually.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {memories.map((m) => (
                <div
                  key={m.id}
                  className="p-4 bg-white rounded-lg border shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${TYPE_COLORS[m.memory_type] || "bg-gray-100"}`}>
                          {m.memory_type}
                        </span>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[m.status] || "bg-gray-100"}`}>
                          {m.status}
                        </span>
                        {m.platform && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                            {m.platform}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900">{m.content}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        <span>
                          Confidence:{" "}
                          <span className={`font-medium ${
                            m.confidence >= 0.8 ? "text-green-600" :
                            m.confidence >= 0.5 ? "text-yellow-600" : "text-red-500"
                          }`}>
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
                      className="ml-3 text-gray-300 hover:text-red-500 text-sm"
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
            <div className="text-center py-12 text-gray-400">
              <p className="text-lg mb-2">No pending approvals</p>
              <p className="text-sm">
                When the agent synthesizes observations into strategic lessons,
                they appear here for your review.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingMemories.map((m) => (
                <div
                  key={m.id}
                  className="p-4 bg-yellow-50 rounded-lg border border-yellow-200"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${TYPE_COLORS[m.memory_type] || "bg-gray-100"}`}>
                      {m.memory_type}
                    </span>
                    <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800">
                      Pending Approval
                    </span>
                  </div>
                  <p className="text-sm text-gray-900 mb-3">{m.content}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                    <span>Confidence: {Math.round(m.confidence * 100)}%</span>
                    {m.category && <span>Category: {m.category}</span>}
                    {m.platform && <span>Platform: {m.platform}</span>}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApprove(m.id)}
                      className="px-4 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleDismiss(m.id)}
                      className="px-4 py-1.5 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
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
        <form onSubmit={handleAddMemory} className="bg-white p-6 rounded-lg border shadow-sm space-y-4">
          <h2 className="text-lg font-semibold">Add a Memory Manually</h2>
          <p className="text-sm text-gray-500">
            Tell the agent something it should remember about your content preferences,
            voice, or strategy.
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Memory Type</label>
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              {MEMORY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="e.g., 'I prefer short, punchy hooks under 10 words' or 'Never use rhetorical questions'"
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confidence ({Math.round(newConfidence * 100)}%)
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={newConfidence}
                onChange={(e) => setNewConfidence(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Platform (optional)</label>
              <select
                value={newPlatform}
                onChange={(e) => setNewPlatform(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Category (optional)</label>
              <input
                type="text"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="e.g., hooks, voice, topics"
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
          >
            Save Memory
          </button>
        </form>
      )}
    </main>
  );
}
