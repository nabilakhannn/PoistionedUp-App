"use client";

/**
 * Agent Command — replaces Intelligence (Slice 100+)
 * 3 tabs:
 *   Agents       — live status of all 8 agents + send task
 *   Deliverables — all agent_deliverables in a searchable board
 *   Journal      — experience journal (transcripts, notes, calls)
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import { gatewayApi, GatewayAgent } from "@/lib/api/gateway";
import { missionControlApi, Deliverable } from "@/lib/api/mission-control";
import { journalApi, JournalEntry, SourceType, SuggestResult } from "@/lib/api/journal";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import AgentTrainingPanel from "@/components/agent-training-panel";

type Tab = "agents" | "deliverables" | "journal";

const TABS: { key: Tab; label: string; emoji: string }[] = [
  { key: "agents", label: "Agents", emoji: "🤖" },
  { key: "deliverables", label: "Deliverables", emoji: "📦" },
  { key: "journal", label: "Journal", emoji: "📒" },
];

const AGENT_EMOJIS: Record<string, string> = {
  jumbo: "🧠",
  copywriter: "✍️",
  "qa-reviewer": "✔️",
  "trend-analyzer": "🔍",
  "competitor-analyst": "🎯",
  "visual-designer": "🎨",
  distributor: "📤",
  analytics: "📊",
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  jumbo: "Lead orchestrator. Directs all agents, reads playbooks, makes strategic decisions.",
  copywriter: "Writes LinkedIn posts, emails, hooks, carousels, and ad copy.",
  "qa-reviewer": "Scores every piece of content across 6 dimensions before it goes live.",
  "trend-analyzer": "Researches trending topics and writes the intel brief each pipeline run.",
  "competitor-analyst": "Monitors competitors daily — threat scores, gaps, and alerts.",
  "visual-designer": "Generates image prompts and directs visual identity for posts.",
  distributor: "Publishes approved content to LinkedIn, Twitter, Instagram.",
  analytics: "Tracks performance and flags what's working vs. what needs to change.",
};

const SOURCE_TYPE_LABELS: Record<SourceType, { label: string; emoji: string }> = {
  call_recording: { label: "Call Recording", emoji: "🎙️" },
  transcript: { label: "Transcript", emoji: "📝" },
  note: { label: "Note", emoji: "📒" },
  case_study: { label: "Case Study", emoji: "📊" },
};

// ── Agents Tab ─────────────────────────────────────────────────

function AgentsTab() {
  const [agents, setAgents] = useState<GatewayAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [sendingTo, setSendingTo] = useState<string | null>(null);
  const [taskInputs, setTaskInputs] = useState<Record<string, string>>({});
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [activityFeed, setActivityFeed] = useState<Array<{
    id: string; agent_id: string; task_type: string; summary: string;
    status: string; created_at: string; emoji: string;
  }>>([]);
  const [activityLoading, setActivityLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    gatewayApi.agents()
      .then((data) => {
        setAgents(data);
        setConnected(data.length > 0);
      })
      .catch(() => setConnected(false))
      .finally(() => setLoading(false));
  }, []);

  // Load real activity feed from agent_ledger (polls every 15s)
  useEffect(() => {
    const load = () => {
      agentBridgeApi.getActivityFeed(20)
        .then((res) => setActivityFeed(res.items))
        .catch(() => {})
        .finally(() => setActivityLoading(false));
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  const handleSendTask = async (agentId: string) => {
    const msg = taskInputs[agentId]?.trim();
    if (!msg) return;
    setSendingTo(agentId);
    try {
      const res = await gatewayApi.sendMessage(agentId, msg);
      setResponses((prev) => ({ ...prev, [agentId]: res.response || "Task delivered." }));
      setTaskInputs((prev) => ({ ...prev, [agentId]: "" }));
    } catch {
      setResponses((prev) => ({ ...prev, [agentId]: "Failed to reach agent. Check gateway connection." }));
    } finally {
      setSendingTo(null);
    }
  };

  const DEFAULT_AGENTS = ["jumbo", "copywriter", "qa-reviewer", "trend-analyzer", "competitor-analyst", "visual-designer", "distributor", "analytics"];
  const displayAgents = agents.length > 0
    ? agents
    : DEFAULT_AGENTS.map((id) => ({ id, name: id, status: "offline" as const }));

  return (
    <div className="space-y-4">
      {/* Connection status */}
      <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${connected ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
        {connected ? `${agents.length} agents connected via OpenClaw gateway` : "Gateway offline — showing cached agent list. Check VPS."}
        <Link href="/mission-control/gateway" className="ml-auto underline">Gateway status →</Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-card/30 p-4 animate-pulse h-28" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {displayAgents.map((agent) => {
            const emoji = AGENT_EMOJIS[agent.id] || "🤖";
            const desc = AGENT_DESCRIPTIONS[agent.id] || "Specialist agent.";
            const isOnline = connected;
            const isSending = sendingTo === agent.id;
            const response = responses[agent.id];
            return (
              <div key={agent.id} className={`rounded-xl border bg-card ${isOnline ? "border-border" : "border-border/50 opacity-70"}`}>
                {/* Agent header */}
                <div className="p-4 space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">{emoji}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-foreground capitalize">{agent.name || agent.id}</p>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${isOnline ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-500"}`}>
                          {isOnline ? "ONLINE" : "OFFLINE"}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{desc}</p>
                    </div>
                    {/* Train button */}
                    <button
                      onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
                      className={`shrink-0 text-[10px] px-2 py-1 rounded-lg border transition ${expandedAgent === agent.id ? "border-indigo-500/50 text-indigo-400 bg-indigo-950/30" : "border-border text-muted-foreground hover:text-foreground hover:border-border"}`}
                    >
                      {expandedAgent === agent.id ? "▲ Close" : "🎓 Train"}
                    </button>
                  </div>

                  {/* Send task input */}
                  {isOnline && (
                    <div className="flex gap-2">
                      <input
                        value={taskInputs[agent.id] || ""}
                        onChange={(e) => setTaskInputs((prev) => ({ ...prev, [agent.id]: e.target.value }))}
                        onKeyDown={(e) => e.key === "Enter" && handleSendTask(agent.id)}
                        placeholder={`Give ${agent.name || agent.id} a task...`}
                        className="flex-1 bg-muted/30 border border-border rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                      <button
                        onClick={() => handleSendTask(agent.id)}
                        disabled={isSending || !taskInputs[agent.id]?.trim()}
                        className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-40"
                      >
                        {isSending ? "..." : "Send"}
                      </button>
                    </div>
                  )}
                  {response && (
                    <p className="text-[10px] text-muted-foreground bg-muted/20 rounded p-2 line-clamp-3 italic">
                      {response}
                    </p>
                  )}
                </div>

                {/* Training panel — expands inline */}
                {expandedAgent === agent.id && (
                  <div className="border-t border-border/50 p-4 bg-[#0d1117]">
                    <AgentTrainingPanel agentId={agent.id} agentName={agent.name || agent.id} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Real Activity Feed from agent_ledger */}
      <div className="rounded-xl border border-border bg-card/50">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Agent Activity Feed</h3>
          <span className="text-[10px] text-muted-foreground">Live · updates every 15s</span>
        </div>
        {activityLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(5)].map((_, i) => <div key={i} className="h-8 rounded bg-muted/20 animate-pulse" />)}
          </div>
        ) : activityFeed.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No agent activity yet. Run the pipeline to see agents in action.
          </div>
        ) : (
          <div className="divide-y divide-border/50 max-h-80 overflow-y-auto">
            {activityFeed.map((item) => (
              <div key={item.id} className="flex items-start gap-3 px-4 py-2.5">
                <span className="text-base shrink-0 mt-0.5">{item.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground capitalize">{item.agent_id}</span>
                    <span className={`text-[9px] px-1 py-0.5 rounded font-mono ${item.status === "done" ? "bg-green-500/15 text-green-400" : item.status === "error" ? "bg-red-500/15 text-red-400" : "bg-zinc-500/15 text-zinc-400"}`}>
                      {item.status}
                    </span>
                    <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                      {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate mt-0.5">{item.summary}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Deliverables Tab ────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  review: "bg-amber-500/20 text-amber-400",
  approved: "bg-green-500/20 text-green-400",
  rejected: "bg-red-500/20 text-red-400",
  published: "bg-blue-500/20 text-blue-400",
  draft: "bg-zinc-500/20 text-zinc-400",
};

const TYPE_EMOJIS: Record<string, string> = {
  content: "📝",
  document: "📄",
  report: "📊",
  image: "🖼️",
  code: "💻",
};

function DeliverablesTab() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await missionControlApi.listDeliverables({});
      setDeliverables(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = deliverables.filter((d) => {
    if (filter !== "all" && d.status !== filter) return false;
    if (search && !d.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const statusCounts = deliverables.reduce<Record<string, number>>((acc, d) => {
    acc[d.status] = (acc[d.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search deliverables..."
          className="bg-muted/30 border border-border rounded px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-48"
        />
        {["all", "review", "approved", "rejected", "published"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded text-xs font-medium capitalize transition ${filter === s ? "bg-primary text-primary-foreground" : "bg-muted/30 text-muted-foreground hover:text-foreground"}`}
          >
            {s === "all" ? `All (${deliverables.length})` : `${s} (${statusCounts[s] || 0})`}
          </button>
        ))}
        <Link href="/deliverables" className="ml-auto text-xs text-primary hover:underline">Full gallery →</Link>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-card border border-border rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
          <div className="text-3xl mb-3">📦</div>
          <p className="text-sm font-medium text-foreground mb-1">No deliverables yet</p>
          <p className="text-xs text-muted-foreground">
            Run the content pipeline and your agents will create deliverables here.
          </p>
          <Link href="/mission-control" className="inline-block mt-3 text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium">
            Go to Command Center →
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((d) => (
            <div key={d.id} className="rounded-xl border border-border bg-card p-4 flex items-start gap-3">
              <span className="text-xl flex-shrink-0">{TYPE_EMOJIS[d.deliverable_type] || "📄"}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-medium text-foreground truncate">{d.title}</p>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono uppercase ${STATUS_COLORS[d.status] || STATUS_COLORS.draft}`}>
                    {d.status}
                  </span>
                  {d.created_by_agent_id && (
                    <span className="text-[10px] text-muted-foreground">
                      by {AGENT_EMOJIS[d.created_by_agent_id] || ""} {d.created_by_agent_id}
                    </span>
                  )}
                </div>
                {d.content && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{d.content}</p>
                )}
              </div>
              <span className="text-[10px] text-muted-foreground flex-shrink-0">
                {new Date(d.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Journal Tab ─────────────────────────────────────────────────

function JournalTab({ brandId }: { brandId: string }) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ title: "", source_type: "note" as SourceType, raw_content: "", tags: "" });
  const [saving, setSaving] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [pinLoading, setPinLoading] = useState<string | null>(null);
  const [suggest, setSuggest] = useState<SuggestResult | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestTopic, setSuggestTopic] = useState("");

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

  const handlePin = async (entryId: string) => {
    setPinLoading(entryId);
    try {
      const updated = await journalApi.pin(entryId);
      setEntries((prev) => prev.map((e) => e.id === entryId ? updated : e));
    } catch {
      // ignore
    } finally {
      setPinLoading(null);
    }
  };

  const handleSuggest = async () => {
    setSuggesting(true);
    setSuggest(null);
    try {
      const result = await journalApi.suggest(brandId, suggestTopic || undefined);
      setSuggest(result);
    } catch {
      // ignore
    } finally {
      setSuggesting(false);
    }
  };

  const suggestedIds = new Set(suggest?.suggested_ids ?? []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Experience Journal</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Paste call transcripts, meeting notes, case studies. Agents rotate through fresh entries automatically.
            <span className="ml-1 text-primary">📌 Pin entries you always want used.</span>
          </p>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
        >
          + Add Entry
        </button>
      </div>

      {/* AI Suggest panel */}
      <div className="rounded-xl border border-border bg-card/50 p-3 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium">🤖 AI Suggest</span>
          <span className="text-[10px] text-muted-foreground">— see which entries Jumbo would use right now</span>
        </div>
        <div className="flex gap-2">
          <input
            value={suggestTopic}
            onChange={(e) => setSuggestTopic(e.target.value)}
            placeholder="Optional: paste a topic or research brief to get relevance-ranked picks"
            className="flex-1 bg-muted/30 border border-border rounded px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={handleSuggest}
            disabled={suggesting}
            className="px-3 py-1.5 bg-primary/10 border border-primary/30 text-primary rounded text-xs font-medium hover:bg-primary/20 transition disabled:opacity-50 shrink-0"
          >
            {suggesting ? "Thinking..." : "Suggest"}
          </button>
        </div>
        {suggest && (
          <div className="text-[11px] text-muted-foreground bg-muted/20 rounded px-3 py-2">
            <span className="text-foreground font-medium">Jumbo would use:</span>{" "}
            {suggest.entries.map((e) => e.title || e.source_type).join(", ")}
            <br />
            <span className="text-muted-foreground/70">{suggest.reasoning}</span>
          </div>
        )}
      </div>

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
                  <option key={type} value={type}>{SOURCE_TYPE_LABELS[type].emoji} {SOURCE_TYPE_LABELS[type].label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Content</label>
            <textarea
              value={form.raw_content}
              onChange={(e) => setForm((f) => ({ ...f, raw_content: e.target.value }))}
              placeholder="Paste transcript, describe what happened, or write your notes..."
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
            <button onClick={handleSave} disabled={saving || !form.raw_content.trim()} className="px-4 py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50">
              {saving ? "Saving..." : "Save Entry"}
            </button>
            <button onClick={() => setAdding(false)} className="px-4 py-2 border border-border rounded text-xs text-muted-foreground hover:text-foreground">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-xs text-muted-foreground">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
          <div className="text-3xl mb-3">📒</div>
          <p className="text-sm font-medium text-foreground mb-1">No entries yet</p>
          <p className="text-xs text-muted-foreground">Add a call transcript or note — Jumbo will write content grounded in your real experiences.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => {
            const typeInfo = SOURCE_TYPE_LABELS[entry.source_type] || { label: entry.source_type, emoji: "📝" };
            const isSuggested = suggestedIds.has(entry.id);
            return (
              <div
                key={entry.id}
                className={`rounded-xl border bg-card p-4 transition ${
                  entry.pinned
                    ? "border-primary/50 bg-primary/5"
                    : isSuggested
                    ? "border-yellow-400/40 bg-yellow-400/5"
                    : "border-border"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-base">{typeInfo.emoji}</span>
                      <span className="text-sm font-medium text-foreground truncate">{entry.title || typeInfo.label}</span>
                      <span className="text-[10px] text-muted-foreground shrink-0">{new Date(entry.created_at).toLocaleDateString()}</span>
                      {/* Usage badge */}
                      {entry.times_used === 0 ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 font-medium shrink-0">✨ Fresh</span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0">Used {entry.times_used}×</span>
                      )}
                      {isSuggested && !entry.pinned && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-400/20 text-yellow-500 font-medium shrink-0">🤖 AI pick</span>
                      )}
                      {entry.pinned && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium shrink-0">📌 Pinned</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 ml-7">{entry.raw_content}</p>
                    {entry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2 ml-7">
                        {entry.tags.map((tag) => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    {/* Pin toggle */}
                    <button
                      onClick={() => handlePin(entry.id)}
                      disabled={pinLoading === entry.id}
                      title={entry.pinned ? "Unpin (remove from always-include list)" : "Pin (always include in pipeline)"}
                      className={`text-[11px] px-2 py-1 rounded border transition ${
                        entry.pinned
                          ? "border-primary/40 text-primary bg-primary/10 hover:bg-primary/20"
                          : "border-border text-muted-foreground hover:border-primary/30 hover:text-primary"
                      } disabled:opacity-50`}
                    >
                      {pinLoading === entry.id ? "..." : entry.pinned ? "📌 Pinned" : "📌 Pin"}
                    </button>
                    <button
                      onClick={() => {
                        setDeleteLoading(entry.id);
                        journalApi.delete(entry.id)
                          .then(() => setEntries((p) => p.filter((e) => e.id !== entry.id)))
                          .finally(() => setDeleteLoading(null));
                      }}
                      disabled={deleteLoading === entry.id}
                      className="text-[10px] text-muted-foreground/50 hover:text-red-400 transition"
                    >
                      {deleteLoading === entry.id ? "..." : "Delete"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────

export default function AgentCommandPage() {
  const [activeTab, setActiveTab] = useState<Tab>("agents");
  const { currentBrand } = useBrand();

  // Deep-link support: /intelligence?tab=journal opens journal directly
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get("tab") as Tab;
    if (tab && (["agents", "deliverables", "journal"] as Tab[]).includes(tab)) {
      setActiveTab(tab);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
              🎬 Studio
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Your production hub — agents, deliverables, and experience journal.
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
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${activeTab === tab.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-6 py-6 max-w-5xl">
        {activeTab === "agents" && <AgentsTab />}
        {activeTab === "deliverables" && <DeliverablesTab />}
        {activeTab === "journal" && (
          currentBrand
            ? <JournalTab brandId={currentBrand.id} />
            : <div className="rounded-xl border border-border bg-card/30 px-6 py-12 text-center">
                <p className="text-sm text-muted-foreground">Select a brand to access your journal.</p>
                <Link href="/brands" className="inline-block mt-3 text-xs text-primary hover:underline">Select brand →</Link>
              </div>
        )}
      </div>
    </div>
  );
}
