"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { playbooksApi, Playbook } from "@/lib/api/playbooks";
import { MC_SUB_NAV } from "../constants";

const AGENT_EMOJIS: Record<string, string> = {
  copywriter: "✍️",
  "qa-reviewer": "✔️",
  "trend-analyzer": "🔍",
  "competitor-analyst": "🎯",
  "visual-designer": "🎨",
  distributor: "📤",
  analytics: "📊",
  jumbo: "🧠",
};

export default function PlaybooksPage() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [proposing, setProposing] = useState<string | null>(null);
  const [proposeText, setProposeText] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPlaybooks = useCallback(async (autoSeedIfEmpty = false) => {
    try {
      const data = await playbooksApi.list();
      if (data.length === 0 && autoSeedIfEmpty) {
        // First load — auto-seed default playbooks for this user
        await playbooksApi.seed();
        const seeded = await playbooksApi.list();
        setPlaybooks(seeded);
      } else {
        setPlaybooks(data);
      }
    } catch {
      // Table may not have rows yet — try seeding once
      if (autoSeedIfEmpty) {
        try {
          await playbooksApi.seed();
          const seeded = await playbooksApi.list();
          setPlaybooks(seeded);
        } catch {
          setError("Failed to load playbooks");
        }
      } else {
        setError("Failed to load playbooks");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlaybooks(true); // auto-seed on first load
  }, [loadPlaybooks]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await playbooksApi.seed();
      await loadPlaybooks();
    } catch {
      setError("Failed to seed playbooks");
    } finally {
      setSeeding(false);
    }
  };

  const handlePropose = async (agentId: string) => {
    const newMd = proposeText[agentId];
    if (!newMd?.trim()) return;
    setSaving(agentId);
    try {
      await playbooksApi.proposeEdit(agentId, newMd);
      await loadPlaybooks();
      setProposing(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to propose edit");
    } finally {
      setSaving(null);
    }
  };

  const handleApply = async (agentId: string) => {
    if (!confirm(`Apply pending edit for ${agentId}? This activates the new playbook immediately.`)) return;
    setApplying(agentId);
    try {
      await playbooksApi.applyEdit(agentId);
      await loadPlaybooks();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to apply edit");
    } finally {
      setApplying(null);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Sub-nav */}
      <div className="flex items-center gap-1 flex-wrap">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/playbooks"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agent Playbooks</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Each agent&apos;s rules and SOPs. Agents read their playbook before every task.
          </p>
        </div>
        {playbooks.length === 0 && !loading && (
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {seeding ? "Seeding..." : "Seed Default Playbooks"}
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
          <button className="ml-2 underline" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="text-muted-foreground text-sm">Loading playbooks...</div>
      ) : playbooks.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground text-sm">
          No playbooks yet. Click &quot;Seed Default Playbooks&quot; to create them.
        </div>
      ) : (
        <div className="grid gap-4">
          {playbooks.map((pb) => (
            <div key={pb.agent_id} className="rounded-lg border border-border bg-card overflow-hidden">
              {/* Card header */}
              <button
                className="w-full px-5 py-4 flex items-center justify-between hover:bg-accent/50 transition text-left"
                onClick={() => setExpanded(expanded === pb.agent_id ? null : pb.agent_id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{AGENT_EMOJIS[pb.agent_id] || "🤖"}</span>
                  <div>
                    <div className="font-semibold text-sm">{pb.agent_name}</div>
                    <div className="text-xs text-muted-foreground">v{pb.version} · Updated {new Date(pb.updated_at).toLocaleDateString()}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {pb.pending_edit_md && (
                    <span className="px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      Pending Edit
                    </span>
                  )}
                  <span className="text-muted-foreground text-xs">{expanded === pb.agent_id ? "▲" : "▼"}</span>
                </div>
              </button>

              {/* Expanded content */}
              {expanded === pb.agent_id && (
                <div className="px-5 pb-5 space-y-4 border-t border-border">
                  {/* Active playbook */}
                  <div>
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mt-4 mb-2">Active Playbook</div>
                    <pre className="text-xs text-foreground bg-muted/30 rounded p-3 whitespace-pre-wrap font-mono leading-relaxed overflow-auto max-h-64">
                      {pb.playbook_md || "(empty)"}
                    </pre>
                  </div>

                  {/* Pending edit (if any) */}
                  {pb.pending_edit_md && (
                    <div>
                      <div className="text-xs font-medium text-amber-400 uppercase tracking-wide mb-2">Pending Edit</div>
                      <pre className="text-xs text-foreground bg-amber-500/10 border border-amber-500/20 rounded p-3 whitespace-pre-wrap font-mono leading-relaxed overflow-auto max-h-48">
                        {pb.pending_edit_md}
                      </pre>
                      <button
                        onClick={() => handleApply(pb.agent_id)}
                        disabled={applying === pb.agent_id}
                        className="mt-2 px-3 py-1.5 bg-amber-500 text-black rounded text-xs font-medium disabled:opacity-50"
                      >
                        {applying === pb.agent_id ? "Applying..." : "Apply Edit"}
                      </button>
                    </div>
                  )}

                  {/* Propose edit toggle */}
                  {proposing === pb.agent_id ? (
                    <div>
                      <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Propose New Playbook</div>
                      <textarea
                        className="w-full h-48 bg-muted/30 border border-border rounded p-3 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary"
                        value={proposeText[pb.agent_id] ?? pb.playbook_md}
                        onChange={(e) => setProposeText(prev => ({ ...prev, [pb.agent_id]: e.target.value }))}
                        placeholder="Edit playbook markdown here..."
                      />
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => handlePropose(pb.agent_id)}
                          disabled={saving === pb.agent_id}
                          className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
                        >
                          {saving === pb.agent_id ? "Saving..." : "Save as Pending"}
                        </button>
                        <button
                          onClick={() => setProposing(null)}
                          className="px-3 py-1.5 border border-border rounded text-xs text-muted-foreground hover:text-foreground"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setProposeText(prev => ({ ...prev, [pb.agent_id]: pb.playbook_md }));
                        setProposing(pb.agent_id);
                      }}
                      className="px-3 py-1.5 border border-border rounded text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition"
                    >
                      Propose Edit
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
