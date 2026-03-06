"use client";

import { useEffect, useState, useCallback } from "react";
import { connectorsApi, Connector, ConnectorService } from "@/lib/api/connectors";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { knowledgeDocsApi, KnowledgeDoc, DocType } from "@/lib/api/knowledge-docs";
import { useBrand } from "@/lib/brand-context";

type Section = "connectors" | "pipeline" | "knowledge" | "system";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "connectors", label: "Connectors" },
  { id: "pipeline", label: "Pipeline" },
  { id: "knowledge", label: "Knowledge Base" },
  { id: "system", label: "System" },
];

export function BrandSettingsTab({ brandId }: { brandId: string }) {
  const { currentBrand } = useBrand();
  const [section, setSection] = useState<Section>("connectors");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [pipeline, setPipeline] = useState<PipelineSettings | null>(null);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);

  // Pipeline form state
  const [enabled, setEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    const [c, p, d] = await Promise.all([
      connectorsApi.list().catch(() => []),
      pipelineSettingsApi.get().catch(() => null),
      knowledgeDocsApi.list().catch(() => []),
    ]);
    setConnectors(c);
    setPipeline(p);
    if (p) { setEnabled(p.enabled); }
    setDocs(d);
    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleSavePipeline = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await pipelineSettingsApi.update({ enabled });
      setMsg("Saved!");
      setTimeout(() => setMsg(null), 2000);
    } catch { setMsg("Failed to save"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      {/* Section selector */}
      <div className="flex gap-1.5 flex-wrap">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSection(s.id)}
            className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
              section === s.id
                ? "bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/25"
                : "text-zinc-500 hover:text-zinc-300 bg-white/[0.03] ring-1 ring-white/[0.05]"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="glass-card py-8 text-center text-xs text-zinc-500">Loading...</div>
      ) : (
        <>
          {/* Connectors */}
          {section === "connectors" && (
            <div className="space-y-3">
              <p className="text-xs text-zinc-500">Connect your social accounts for auto-publishing.</p>
              {connectors.length === 0 ? (
                <div className="glass-card py-6 text-center">
                  <p className="text-sm text-zinc-500">No connectors configured yet.</p>
                  <p className="text-xs text-zinc-600 mt-1">
                    Visit the <a href="/mission-control/settings" className="text-violet-400 hover:text-violet-300">full settings page</a> to add connectors.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {connectors.map((c) => (
                    <div key={c.id} className="glass-card py-3 px-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-zinc-200 capitalize">{c.service}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                          c.is_active ? "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20" : "bg-zinc-500/10 text-zinc-500 ring-1 ring-zinc-500/20"
                        }`}>
                          {c.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Pipeline */}
          {section === "pipeline" && (
            <div className="glass-card space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-200">Autonomous Pipeline</span>
                <button
                  onClick={() => setEnabled(!enabled)}
                  className={`relative w-10 h-5 rounded-full transition-colors ${enabled ? "bg-emerald-500" : "bg-zinc-700"}`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? "translate-x-5" : ""}`} />
                </button>
              </div>
              {pipeline && (
                <p className="text-xs text-zinc-500">
                  Budget: ${pipeline.monthly_budget_usd}/mo · Interval: {pipeline.interval_hours}h
                </p>
              )}
              <div className="flex items-center gap-3">
                <button onClick={handleSavePipeline} disabled={saving} className="glass-button-primary text-sm">
                  {saving ? "Saving..." : "Save"}
                </button>
                {msg && <span className="text-xs text-zinc-400">{msg}</span>}
              </div>
            </div>
          )}

          {/* Knowledge */}
          {section === "knowledge" && (
            <div className="space-y-3">
              <p className="text-xs text-zinc-500">Training docs, SOPs, and reference materials for your agents.</p>
              {docs.length === 0 ? (
                <div className="glass-card py-6 text-center">
                  <p className="text-sm text-zinc-500">No knowledge docs yet. Train your agents in the Team tab.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {docs.map((d) => (
                    <div key={d.id} className="glass-card py-3 px-4 flex items-center justify-between">
                      <div>
                        <span className="text-sm text-zinc-200">{d.title}</span>
                        <span className="text-[10px] text-zinc-600 ml-2">{d.doc_type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* System */}
          {section === "system" && (
            <div className="space-y-4">
              <div className="glass-card">
                <h3 className="text-sm font-medium text-zinc-200 mb-2">Brand ID</h3>
                <code className="text-xs text-zinc-500 font-mono">{brandId}</code>
              </div>
              {currentBrand && (
                <div className="glass-card">
                  <h3 className="text-sm font-medium text-zinc-200 mb-2">Brand Name</h3>
                  <p className="text-xs text-zinc-400">{currentBrand.name}</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
