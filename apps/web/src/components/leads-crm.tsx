"use client";

/**
 * Leads CRM — Slice 95
 *
 * Table-first view (Apollo/Clay pattern) with Kanban toggle.
 * Bulk actions, enrichment progress, empty state, lead detail panel.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Lead,
  LeadStatus,
  SequenceMessage,
  leadsApi,
  BatchEnrichItem,
} from "@/lib/api/leads";

interface Props {
  brandId: string;
}

const STATUS_ORDER: LeadStatus[] = ["cold", "warm", "hot", "customer"];
const STATUS_LABELS: Record<LeadStatus, { label: string; emoji: string; color: string }> = {
  cold: { label: "Cold", emoji: "❄️", color: "text-blue-400" },
  warm: { label: "Warm", emoji: "🔥", color: "text-amber-400" },
  hot: { label: "Hot", emoji: "⚡", color: "text-orange-400" },
  customer: { label: "Customer", emoji: "✅", color: "text-green-400" },
  disqualified: { label: "Archived", emoji: "🗄️", color: "text-muted-foreground" },
};

function BantDots({ score }: { score: number }) {
  return (
    <span className="flex gap-0.5">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${i < score ? "bg-primary" : "bg-muted"}`}
        />
      ))}
    </span>
  );
}

// ── Lead detail panel ──────────────────────────────────────────────────────

function LeadDetailPanel({
  lead,
  onClose,
  onUpdated,
}: {
  lead: Lead;
  onClose: () => void;
  onUpdated: (l: Lead) => void;
}) {
  const [activeTab, setActiveTab] = useState<"profile" | "transcript" | "outreach">("profile");
  const [transcript, setTranscript] = useState(lead.transcript || "");
  const [icebreaker, setIcebreaker] = useState(lead.icebreaker || "");
  const [enriching, setEnriching] = useState(false);
  const [generatingOutreach, setGeneratingOutreach] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  };

  const handleReEnrich = async () => {
    setEnriching(true);
    try {
      const updated = await leadsApi.enrich(lead.id);
      onUpdated(updated);
    } catch (err) {
      console.error("Enrich failed:", err);
    } finally {
      setEnriching(false);
    }
  };

  const handleSaveTranscript = async () => {
    setSaving(true);
    try {
      const updated = await leadsApi.update(lead.id, { transcript });
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateOutreach = async () => {
    setGeneratingOutreach(true);
    // Save transcript first
    try {
      await leadsApi.update(lead.id, { transcript });
    } catch { /* ignore */ }
    try {
      const updated = await leadsApi.generateOutreach(lead.id);
      onUpdated(updated);
      setActiveTab("outreach");
      setIcebreaker(updated.icebreaker || "");
    } catch (err) {
      console.error("Outreach gen failed:", err);
    } finally {
      setGeneratingOutreach(false);
    }
  };

  const handleIcebreakerBlur = async () => {
    if (icebreaker === lead.icebreaker) return;
    try {
      const updated = await leadsApi.update(lead.id, { icebreaker });
      onUpdated(updated);
    } catch { /* ignore */ }
  };

  const handleToggleSent = async (idx: number) => {
    const seq: SequenceMessage[] = (lead.sequence || []).map((m, i) => {
      if (i !== idx) return m;
      return {
        ...m,
        sent_at: m.sent_at ? null : new Date().toISOString(),
      };
    });
    try {
      const updated = await leadsApi.update(lead.id, { sequence: seq });
      onUpdated(updated);
    } catch { /* ignore */ }
  };

  const enrichment = lead.enrichment || {};

  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-card border-l border-border shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border">
        <div>
          <h3 className="font-semibold text-sm text-foreground">{lead.full_name}</h3>
          <p className="text-xs text-muted-foreground">{[lead.title, lead.company].filter(Boolean).join(" · ")}</p>
          <div className="flex items-center gap-2 mt-1">
            <BantDots score={lead.bant_score} />
            <span className="text-[10px] text-muted-foreground">BANT {lead.bant_score}/4</span>
            {lead.linkedin_url ? (
              <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer"
                className="text-[10px] text-blue-400 hover:underline">LinkedIn →</a>
            ) : (
              <span className="text-[10px] text-muted-foreground/40">No LinkedIn</span>
            )}
          </div>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-lg">✕</button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        {(["profile", "transcript", "outreach"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`flex-1 px-3 py-2 text-xs font-medium border-b-2 transition capitalize ${
              activeTab === t
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "profile" ? "🔍 Profile" : t === "transcript" ? "📝 Transcript" : "✉️ Outreach"}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* ── Profile tab ───────────────────────────────────── */}
        {activeTab === "profile" && (
          <>
            {/* BANT breakdown */}
            <div className="rounded-lg border border-border bg-muted/20 p-3">
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-2">BANT Score</div>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                {[
                  { key: "Budget", desc: "Funding/revenue signals" },
                  { key: "Authority", desc: "Decision-maker title" },
                  { key: "Need", desc: "Public pain points" },
                  { key: "Timing", desc: "Recent trigger event" },
                ].map((b, i) => (
                  <div key={b.key} className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${i < lead.bant_score ? "bg-primary" : "bg-muted"}`} />
                    <span className="text-foreground font-medium">{b.key}</span>
                    <span className="text-muted-foreground text-[10px]">{b.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 7 enrichment fields grouped by source */}
            {[
              {
                source: "🔗 LinkedIn Personal",
                fields: [
                  { label: "Professional Topics", key: "professional_topics" },
                  { label: "Recent Achievements", key: "recent_achievements" },
                ],
              },
              {
                source: "🏢 Company LinkedIn",
                fields: [
                  { label: "Hiring Signals", key: "hiring_signals" },
                  { label: "Pain Points", key: "pain_points" },
                ],
              },
              {
                source: "🌐 Website",
                fields: [
                  { label: "Company Changes", key: "company_changes" },
                  { label: "Industries Served", key: "industries_served" },
                  { label: "Growth Signals", key: "growth_signals" },
                ],
              },
            ].map((group) => (
              <div key={group.source}>
                <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">{group.source}</div>
                <div className="space-y-1.5">
                  {group.fields.map((field) => {
                    const items = ((enrichment as unknown) as Record<string, string[]>)[field.key] || [];
                    return (
                      <div key={field.key}>
                        <div className="text-[10px] text-muted-foreground">{field.label}</div>
                        {items.length > 0 ? (
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {items.map((item, i) => (
                              <span key={i} className="inline-block text-[10px] bg-muted/50 rounded px-1.5 py-0.5 text-foreground">
                                {item}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-[10px] text-muted-foreground/40">—</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {lead.last_enriched_at && (
              <p className="text-[10px] text-muted-foreground/50">
                Last enriched: {new Date(lead.last_enriched_at).toLocaleDateString()}
              </p>
            )}

            <button
              onClick={handleReEnrich}
              disabled={enriching}
              className="w-full text-xs py-2 border border-border rounded-lg hover:bg-muted/50 transition disabled:opacity-50"
            >
              {enriching ? "Enriching..." : "✦ Re-enrich"}
            </button>
          </>
        )}

        {/* ── Transcript tab ────────────────────────────────── */}
        {activeTab === "transcript" && (
          <>
            <div>
              <div className="text-xs font-medium text-foreground mb-1">Call / Meeting Notes</div>
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder="Paste call transcript, meeting notes, or any context about this lead. The AI reads this when generating outreach."
                rows={10}
                className="w-full text-xs bg-background border border-border rounded-lg p-3 resize-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSaveTranscript}
                disabled={saving}
                className="flex-1 text-xs py-2 border border-border rounded-lg hover:bg-muted/50 transition disabled:opacity-50"
              >
                {saving ? "Saving..." : "💾 Save Notes"}
              </button>
              <button
                onClick={handleGenerateOutreach}
                disabled={generatingOutreach}
                className="flex-1 text-xs py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
              >
                {generatingOutreach ? "Generating..." : "✨ Generate Outreach"}
              </button>
            </div>
          </>
        )}

        {/* ── Outreach tab ──────────────────────────────────── */}
        {activeTab === "outreach" && (
          <>
            {/* Icebreaker — editable */}
            <div>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Icebreaker</div>
              <textarea
                value={icebreaker}
                onChange={(e) => setIcebreaker(e.target.value)}
                onBlur={handleIcebreakerBlur}
                placeholder="AI will generate a personalised icebreaker after enrichment + outreach generation."
                rows={3}
                className="w-full text-xs bg-background border border-border rounded-lg p-3 resize-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground placeholder:text-muted-foreground/50"
              />
              <p className="text-[10px] text-muted-foreground/50 mt-0.5">Edit and save on click away</p>
            </div>

            {/* LinkedIn DM */}
            {lead.outreach_draft?.linkedin_dm && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase">💼 LinkedIn DM</div>
                  <button
                    onClick={() => copyToClipboard(lead.outreach_draft.linkedin_dm!, "linkedin_dm")}
                    className="text-[10px] text-primary hover:underline"
                  >
                    {copiedKey === "linkedin_dm" ? "Copied!" : "Copy"}
                  </button>
                </div>
                <div className="text-xs bg-muted/30 rounded-lg p-3 whitespace-pre-wrap text-foreground">
                  {lead.outreach_draft.linkedin_dm}
                </div>
              </div>
            )}

            {/* Cold email */}
            {lead.outreach_draft?.cold_email?.body && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase">📧 Cold Email</div>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `Subject: ${lead.outreach_draft.cold_email!.subject}\n\n${lead.outreach_draft.cold_email!.body}`,
                        "email"
                      )
                    }
                    className="text-[10px] text-primary hover:underline"
                  >
                    {copiedKey === "email" ? "Copied!" : "Copy"}
                  </button>
                </div>
                <div className="text-xs bg-muted/30 rounded-lg p-3 space-y-2">
                  <div className="font-medium text-foreground">
                    Subject: {lead.outreach_draft.cold_email.subject}
                  </div>
                  <div className="whitespace-pre-wrap text-foreground">
                    {lead.outreach_draft.cold_email.body}
                  </div>
                </div>
              </div>
            )}

            {/* Sequence */}
            {lead.sequence && lead.sequence.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-2">3-Message Sequence</div>
                <div className="space-y-2">
                  {lead.sequence.map((msg, idx) => (
                    <div key={idx} className="rounded-lg border border-border p-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-semibold text-foreground">{msg.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-muted-foreground capitalize">{msg.channel}</span>
                          <button
                            onClick={() => copyToClipboard(msg.message, `seq-${idx}`)}
                            className="text-[10px] text-primary hover:underline"
                          >
                            {copiedKey === `seq-${idx}` ? "Copied!" : "Copy"}
                          </button>
                        </div>
                      </div>
                      <p className="text-[10px] text-muted-foreground whitespace-pre-wrap line-clamp-3">
                        {msg.message || "—"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(!lead.outreach_draft?.linkedin_dm && !lead.outreach_draft?.cold_email?.body) && (
              <div className="text-center py-6">
                <p className="text-xs text-muted-foreground mb-3">No outreach generated yet.</p>
                <button
                  onClick={handleGenerateOutreach}
                  disabled={generatingOutreach}
                  className="text-xs px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
                >
                  {generatingOutreach ? "Generating..." : "✨ Generate Outreach"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function LeadsCRM({ brandId }: Props) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [filterStatus, setFilterStatus] = useState<LeadStatus | "all">("all");
  const [filterBant, setFilterBant] = useState<number | "any">("any");
  const [searchQuery, setSearchQuery] = useState("");
  const [enrichingIds, setEnrichingIds] = useState<Set<string>>(new Set());

  // Dialogs
  const [showPasteDialog, setShowPasteDialog] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [bulkEnriching, setBulkEnriching] = useState(false);
  const [bulkGeneratingOutreach, setBulkGeneratingOutreach] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLeads = useCallback(async () => {
    try {
      const data = await leadsApi.list(brandId);
      setLeads(data);
    } catch (err) {
      console.error("Failed to load leads:", err);
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { loadLeads(); }, [loadLeads]);

  const updateLead = (updated: Lead) => {
    setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    if (selectedLead?.id === updated.id) setSelectedLead(updated);
  };

  const handleStatusMove = async (lead: Lead, direction: "prev" | "next") => {
    const idx = STATUS_ORDER.indexOf(lead.status);
    const newIdx = direction === "next" ? idx + 1 : idx - 1;
    if (newIdx < 0 || newIdx >= STATUS_ORDER.length) return;
    try {
      const updated = await leadsApi.update(lead.id, { status: STATUS_ORDER[newIdx] });
      updateLead(updated);
    } catch { /* ignore */ }
  };

  const handleArchive = async (id: string) => {
    try {
      const updated = await leadsApi.update(id, { status: "disqualified" });
      updateLead(updated);
      setSelectedIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await leadsApi.remove(id);
      setLeads((prev) => prev.filter((l) => l.id !== id));
      setSelectedIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
      if (selectedLead?.id === id) setSelectedLead(null);
    } catch { /* ignore */ }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const newLeads = await leadsApi.generate(brandId, 10);
      setLeads((prev) => {
        const existingIds = new Set(prev.map((l) => l.id));
        const fresh = newLeads.filter((l) => !existingIds.has(l.id));
        return [...fresh, ...prev];
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Generation failed";
      setError(msg.includes("ICP") || msg.includes("422") ? "Complete your ICP in Settings → Brand Profile first." : msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleEnrichSingle = async (leadId: string) => {
    setEnrichingIds((prev) => new Set(prev).add(leadId));
    try {
      const updated = await leadsApi.enrich(leadId);
      updateLead(updated);
    } catch { /* ignore */ }
    finally {
      setEnrichingIds((prev) => { const s = new Set(prev); s.delete(leadId); return s; });
    }
  };

  const handleBulkEnrich = async () => {
    if (selectedIds.size === 0) return;
    setBulkEnriching(true);
    for (const id of selectedIds) {
      setEnrichingIds((prev) => new Set(prev).add(id));
      try {
        const updated = await leadsApi.enrich(id);
        updateLead(updated);
      } catch { /* ignore */ }
      finally {
        setEnrichingIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
      }
    }
    setBulkEnriching(false);
    setSelectedIds(new Set());
  };

  const handleBulkGenerateOutreach = async () => {
    if (selectedIds.size === 0) return;
    setBulkGeneratingOutreach(true);
    for (const id of selectedIds) {
      try {
        const updated = await leadsApi.generateOutreach(id);
        updateLead(updated);
      } catch { /* ignore */ }
    }
    setBulkGeneratingOutreach(false);
    setSelectedIds(new Set());
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await leadsApi.exportXlsx(brandId);
    } catch { /* ignore */ }
    finally { setExporting(false); }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const selectAll = () => {
    const visible = filteredLeads.map((l) => l.id);
    setSelectedIds(new Set(visible));
  };

  const clearSelection = () => setSelectedIds(new Set());

  // Filter + search
  const filteredLeads = leads.filter((l) => {
    if (!showArchived && l.status === "disqualified") return false;
    if (filterStatus !== "all" && l.status !== filterStatus) return false;
    if (filterBant !== "any" && l.bant_score < filterBant) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        l.full_name.toLowerCase().includes(q) ||
        (l.company || "").toLowerCase().includes(q) ||
        (l.title || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const activeLeads = filteredLeads.filter((l) => l.status !== "disqualified");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* ── Toolbar ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition"
        >
          {generating ? (
            <><span className="animate-spin inline-block">⟳</span> Generating...</>
          ) : "✨ Generate from ICP"}
        </button>

        <button
          onClick={() => setShowPasteDialog(true)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50 transition"
        >
          📋 Paste List
        </button>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50 transition"
        >
          ➕ Add Lead
        </button>

        <button
          onClick={handleExport}
          disabled={exporting || leads.length === 0}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50 disabled:opacity-40 transition"
        >
          {exporting ? "Exporting..." : "⬇ Export .xlsx"}
        </button>

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => setViewMode("table")}
            className={`p-1.5 rounded text-sm transition ${viewMode === "table" ? "bg-primary text-primary-foreground" : "hover:bg-muted/50 text-muted-foreground"}`}
            title="Table view"
          >
            ≡
          </button>
          <button
            onClick={() => setViewMode("kanban")}
            className={`p-1.5 rounded text-sm transition ${viewMode === "kanban" ? "bg-primary text-primary-foreground" : "hover:bg-muted/50 text-muted-foreground"}`}
            title="Kanban view"
          >
            ⊞
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          {error}
          <button onClick={() => setError(null)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 text-xs">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as LeadStatus | "all")}
          className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground"
        >
          <option value="all">All Status</option>
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s].emoji} {STATUS_LABELS[s].label}</option>
          ))}
        </select>

        <select
          value={filterBant === "any" ? "any" : String(filterBant)}
          onChange={(e) => setFilterBant(e.target.value === "any" ? "any" : Number(e.target.value))}
          className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground"
        >
          <option value="any">Any BANT</option>
          <option value="3">BANT 3+</option>
          <option value="2">BANT 2+</option>
          <option value="1">BANT 1+</option>
        </select>

        <input
          type="text"
          placeholder="🔍 Search leads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="bg-background border border-border rounded px-2 py-1 text-xs text-foreground placeholder:text-muted-foreground/50 min-w-[140px]"
        />

        <span className="text-muted-foreground/60 text-[10px] ml-auto">
          {activeLeads.length} lead{activeLeads.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-lg px-3 py-2">
          <span className="text-xs font-medium text-foreground">
            ☑ Selected: {selectedIds.size}
          </span>
          <button
            onClick={handleBulkEnrich}
            disabled={bulkEnriching}
            className="text-xs px-2 py-1 bg-primary text-primary-foreground rounded hover:opacity-90 disabled:opacity-50"
          >
            {bulkEnriching ? "Enriching..." : "✦ Enrich All"}
          </button>
          <button
            onClick={handleBulkGenerateOutreach}
            disabled={bulkGeneratingOutreach}
            className="text-xs px-2 py-1 border border-border rounded hover:bg-muted/50 disabled:opacity-50"
          >
            {bulkGeneratingOutreach ? "Generating..." : "→ Outreach"}
          </button>
          <button
            onClick={handleExport}
            className="text-xs px-2 py-1 border border-border rounded hover:bg-muted/50"
          >
            ⬇ Export
          </button>
          <button
            onClick={clearSelection}
            className="text-xs text-muted-foreground hover:text-foreground ml-auto"
          >
            Clear
          </button>
        </div>
      )}

      {/* Empty state */}
      {filteredLeads.filter((l) => l.status !== "disqualified").length === 0 && !loading && (
        <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center">
          <div className="text-2xl mb-2">👥</div>
          <h3 className="text-sm font-semibold text-foreground mb-1">Your Lead List is Empty</h3>
          <p className="text-xs text-muted-foreground mb-4">Three ways to get started:</p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button onClick={handleGenerate} disabled={generating}
              className="text-xs px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50">
              ✨ Generate from ICP
              <div className="text-[10px] opacity-70 mt-0.5">AI finds leads that match your brand ICP</div>
            </button>
            <button onClick={() => setShowPasteDialog(true)}
              className="text-xs px-3 py-2 border border-border rounded-lg hover:bg-muted/50">
              📋 Paste a List
              <div className="text-[10px] opacity-70 mt-0.5">Import LinkedIn URLs or &quot;Name, Company&quot;</div>
            </button>
            <button onClick={() => setShowAddModal(true)}
              className="text-xs px-3 py-2 border border-border rounded-lg hover:bg-muted/50">
              ➕ Add Manually
              <div className="text-[10px] opacity-70 mt-0.5">Enter a single lead&apos;s details</div>
            </button>
          </div>
        </div>
      )}

      {/* ── TABLE VIEW ──────────────────────────────────────────────────── */}
      {viewMode === "table" && filteredLeads.filter((l) => l.status !== "disqualified" || showArchived).length > 0 && (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-card border-b border-border">
                <th className="p-2 w-8">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === activeLeads.length && activeLeads.length > 0}
                    onChange={(e) => e.target.checked ? selectAll() : clearSelection()}
                    className="w-3 h-3"
                  />
                </th>
                <th className="p-2 text-left text-muted-foreground font-medium">Name</th>
                <th className="p-2 text-left text-muted-foreground font-medium">Company</th>
                <th className="p-2 text-left text-muted-foreground font-medium">BANT</th>
                <th className="p-2 text-left text-muted-foreground font-medium">Status</th>
                <th className="p-2 text-left text-muted-foreground font-medium">Icebreaker</th>
                <th className="p-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {filteredLeads
                .filter((l) => l.status !== "disqualified" || showArchived)
                .map((lead) => (
                  <tr
                    key={lead.id}
                    className={`border-b border-border/50 hover:bg-muted/20 group cursor-pointer transition ${
                      lead.status === "disqualified" ? "opacity-50" : ""
                    } ${selectedIds.has(lead.id) ? "bg-primary/5" : ""}`}
                  >
                    <td className="p-2" onClick={(e) => { e.stopPropagation(); toggleSelect(lead.id); }}>
                      <input type="checkbox" checked={selectedIds.has(lead.id)} readOnly className="w-3 h-3" />
                    </td>
                    <td className="p-2" onClick={() => setSelectedLead(lead)}>
                      <div className="font-medium text-foreground">{lead.full_name}</div>
                      <div className="text-muted-foreground">{lead.title}</div>
                    </td>
                    <td className="p-2 text-muted-foreground" onClick={() => setSelectedLead(lead)}>
                      {lead.company || "—"}
                    </td>
                    <td className="p-2" onClick={() => setSelectedLead(lead)}>
                      <BantDots score={lead.bant_score} />
                    </td>
                    <td className="p-2" onClick={() => setSelectedLead(lead)}>
                      <span className={`text-[10px] ${STATUS_LABELS[lead.status]?.color || "text-muted-foreground"}`}>
                        {STATUS_LABELS[lead.status]?.emoji} {STATUS_LABELS[lead.status]?.label}
                      </span>
                    </td>
                    <td className="p-2 max-w-[160px]" onClick={() => setSelectedLead(lead)}>
                      <p className="text-muted-foreground line-clamp-2 text-[10px]">
                        {lead.icebreaker || "—"}
                      </p>
                    </td>
                    <td className="p-2">
                      {/* Hover actions */}
                      <div className="hidden group-hover:flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleEnrichSingle(lead.id); }}
                          disabled={enrichingIds.has(lead.id)}
                          title="Enrich"
                          className="text-[10px] px-1.5 py-0.5 border border-border rounded hover:bg-muted/50 disabled:opacity-50"
                        >
                          {enrichingIds.has(lead.id) ? "⟳" : "✦"}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleStatusMove(lead, "next"); }}
                          disabled={STATUS_ORDER.indexOf(lead.status) >= STATUS_ORDER.length - 1}
                          title="Move forward"
                          className="text-[10px] px-1.5 py-0.5 border border-border rounded hover:bg-muted/50 disabled:opacity-30"
                        >
                          →
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleArchive(lead.id); }}
                          title="Archive"
                          className="text-[10px] px-1.5 py-0.5 border border-border rounded hover:bg-muted/50 text-muted-foreground"
                        >
                          🗄
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── KANBAN VIEW ─────────────────────────────────────────────────── */}
      {viewMode === "kanban" && (
        <div className="grid grid-cols-4 gap-3">
          {STATUS_ORDER.map((status) => {
            const colLeads = filteredLeads.filter((l) => l.status === status);
            const cfg = STATUS_LABELS[status];
            return (
              <div key={status} className="rounded-xl border border-border bg-card/30 p-3 min-h-[200px]">
                <div className={`text-xs font-semibold mb-3 ${cfg.color}`}>
                  {cfg.emoji} {cfg.label} ({colLeads.length})
                </div>
                <div className="space-y-2">
                  {colLeads.map((lead) => (
                    <div
                      key={lead.id}
                      onClick={() => setSelectedLead(lead)}
                      className="rounded-lg border border-border/60 bg-card p-2.5 cursor-pointer hover:border-primary/50 transition"
                    >
                      <div className="font-medium text-xs text-foreground">{lead.full_name}</div>
                      <div className="text-[10px] text-muted-foreground">{lead.company}</div>
                      <div className="flex items-center justify-between mt-1.5">
                        <BantDots score={lead.bant_score} />
                        <div className="flex gap-0.5">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusMove(lead, "prev"); }}
                            disabled={STATUS_ORDER.indexOf(lead.status) === 0}
                            className="text-[10px] px-1 border border-border rounded hover:bg-muted/50 disabled:opacity-20"
                          >
                            ←
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusMove(lead, "next"); }}
                            disabled={STATUS_ORDER.indexOf(lead.status) >= STATUS_ORDER.length - 1}
                            className="text-[10px] px-1 border border-border rounded hover:bg-muted/50 disabled:opacity-20"
                          >
                            →
                          </button>
                        </div>
                      </div>
                      {lead.icebreaker && (
                        <p className="text-[10px] text-muted-foreground line-clamp-2 mt-1.5">
                          {lead.icebreaker}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Archived toggle */}
      <button
        onClick={() => setShowArchived((v) => !v)}
        className="text-xs text-muted-foreground hover:text-foreground transition"
      >
        {showArchived ? "Hide Archived" : "Show Archived"} ({leads.filter((l) => l.status === "disqualified").length})
      </button>

      {/* ── DIALOGS ──────────────────────────────────────────────────────── */}

      {showPasteDialog && (
        <PasteDialog brandId={brandId} onClose={() => setShowPasteDialog(false)} onAdded={(newLeads) => {
          setLeads((prev) => {
            const ids = new Set(prev.map((l) => l.id));
            return [...newLeads.filter((l) => !ids.has(l.id)), ...prev];
          });
        }} />
      )}

      {showAddModal && (
        <AddLeadModal brandId={brandId} onClose={() => setShowAddModal(false)} onAdded={(lead) => {
          setLeads((prev) => [lead, ...prev]);
        }} />
      )}

      {/* Lead detail panel */}
      {selectedLead && (
        <LeadDetailPanel
          lead={selectedLead}
          onClose={() => setSelectedLead(null)}
          onUpdated={updateLead}
        />
      )}
    </div>
  );
}

// ── Paste dialog ───────────────────────────────────────────────────────────

function PasteDialog({
  brandId,
  onClose,
  onAdded,
}: {
  brandId: string;
  onClose: () => void;
  onAdded: (leads: Lead[]) => void;
}) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEnrich = async () => {
    const lines = text.split("\n").filter((l) => l.trim()).slice(0, 3);
    if (lines.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const items: BatchEnrichItem[] = lines.map((line) => {
        const parts = line.split(",").map((p) => p.trim());
        return {
          full_name: parts[0] || line.trim(),
          company: parts[1] || undefined,
          linkedin_url: line.startsWith("http") ? line.trim() : undefined,
        };
      });
      const result = await leadsApi.batchEnrich(brandId, items);
      onAdded(result);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Batch enrich failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl p-5 w-full max-w-md space-y-3">
        <h3 className="text-sm font-semibold text-foreground">📋 Paste Lead List</h3>
        <p className="text-xs text-muted-foreground">
          One entry per line: &quot;Name&quot; or &quot;Name, Company&quot; or LinkedIn URL.
          Max 3 per batch (to stay within processing limits).
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={"Jane Smith, Acme Corp\nJohn Doe\nhttps://linkedin.com/in/janedoe"}
          rows={5}
          className="w-full text-xs bg-background border border-border rounded-lg p-3 resize-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
        />
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50">
            Cancel
          </button>
          <button
            onClick={handleEnrich}
            disabled={loading || !text.trim()}
            className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Enriching..." : "✦ Enrich & Add"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Add Lead modal ─────────────────────────────────────────────────────────

function AddLeadModal({
  brandId,
  onClose,
  onAdded,
}: {
  brandId: string;
  onClose: () => void;
  onAdded: (lead: Lead) => void;
}) {
  const [form, setForm] = useState({
    full_name: "",
    title: "",
    company: "",
    email: "",
    linkedin_url: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!form.full_name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const lead = await leadsApi.create({ brand_id: brandId, ...form });
      onAdded(lead);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add lead");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl p-5 w-full max-w-md space-y-3">
        <h3 className="text-sm font-semibold text-foreground">➕ Add Lead</h3>
        {[
          { key: "full_name", label: "Full Name *", placeholder: "Jane Smith" },
          { key: "title", label: "Job Title", placeholder: "VP Marketing" },
          { key: "company", label: "Company", placeholder: "Acme Corp" },
          { key: "email", label: "Email", placeholder: "jane@acme.com" },
          { key: "linkedin_url", label: "LinkedIn URL", placeholder: "https://linkedin.com/in/..." },
        ].map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="text-[10px] text-muted-foreground">{label}</label>
            <input
              value={form[key as keyof typeof form]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              className="w-full mt-0.5 text-xs bg-background border border-border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary text-foreground placeholder:text-muted-foreground/50"
            />
          </div>
        ))}
        <div>
          <label className="text-[10px] text-muted-foreground">Notes</label>
          <textarea
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            placeholder="Any initial context..."
            rows={2}
            className="w-full mt-0.5 text-xs bg-background border border-border rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
          />
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="text-xs px-3 py-1.5 border border-border rounded-lg hover:bg-muted/50">Cancel</button>
          <button
            onClick={handleSave}
            disabled={loading || !form.full_name.trim()}
            className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Saving..." : "Save Lead"}
          </button>
        </div>
      </div>
    </div>
  );
}
