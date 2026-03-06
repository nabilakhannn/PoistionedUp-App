"use client";

/**
 * Settings Page — Slice 90
 * 4 tabs: Connectors / Pipeline / Knowledge Base / Team & System
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { connectorsApi, Connector, ConnectorService } from "@/lib/api/connectors";
import { pipelineSettingsApi, PipelineSettings } from "@/lib/api/pipeline-settings";
import { knowledgeDocsApi, KnowledgeDoc, DocType, Platform } from "@/lib/api/knowledge-docs";
import { agentBridgeApi } from "@/lib/api/agent-bridge";
import { personalBrandsApi } from "@/lib/api/brand";
import { useBrand } from "@/lib/brand-context";
import { MC_SUB_NAV } from "../constants";

interface ConnectorConfig {
  service: ConnectorService;
  label: string;
  icon: string;
  description: string;
  fields: { key: string; label: string; placeholder: string; type?: string }[];
}

const CONNECTOR_CONFIGS: ConnectorConfig[] = [
  {
    service: "linkedin",
    label: "LinkedIn (via Webhook)",
    icon: "in",
    description: "Post to LinkedIn automatically via Make.com or Zapier webhook URL.",
    fields: [
      { key: "session_cookie", label: "Make.com / Zapier Webhook URL", placeholder: "https://hook.make.com/...", type: "text" },
    ],
  },
  {
    service: "twitter",
    label: "Twitter / X",
    icon: "X",
    description: "Connect Twitter/X with OAuth 1.0a keys. Get from developer.twitter.com.",
    fields: [
      { key: "api_key", label: "API Key (Consumer Key)", placeholder: "abc123...", type: "password" },
      { key: "api_secret", label: "API Secret", placeholder: "xyz789...", type: "password" },
      { key: "access_token", label: "Access Token", placeholder: "1234567890-abc...", type: "password" },
      { key: "access_token_secret", label: "Access Token Secret", placeholder: "def456...", type: "password" },
    ],
  },
  {
    service: "instagram",
    label: "Instagram",
    icon: "IG",
    description: "Connect Instagram via Graph API to post to business accounts.",
    fields: [
      { key: "access_token", label: "Access Token", placeholder: "EAA...", type: "password" },
      { key: "page_id", label: "Page ID", placeholder: "123456789" },
    ],
  },
  {
    service: "webhook",
    label: "Custom Webhook",
    icon: "⚡",
    description: "Send content to any external system via a webhook URL.",
    fields: [
      { key: "url", label: "Webhook URL", placeholder: "https://your-service.com/webhook" },
      { key: "secret", label: "Secret (optional)", placeholder: "your-signing-secret", type: "password" },
    ],
  },
  {
    service: "manus_ai",
    label: "Manus AI (Optional BYOK)",
    icon: "M",
    description: "Bring your own Manus AI key for deep research workflows. Built-in AI handles everything else.",
    fields: [
      { key: "api_key", label: "Manus API Key", placeholder: "manus-...", type: "password" },
    ],
  },
];

const STATUS_BADGE: Record<string, { label: string; color: string; dot: string }> = {
  ok: { label: "Connected", color: "text-green-400", dot: "bg-green-400" },
  error: { label: "Error", color: "text-red-400", dot: "bg-red-400" },
  untested: { label: "Untested", color: "text-amber-400", dot: "bg-amber-400" },
};

const INTERVAL_OPTIONS = [
  { value: 6, label: "Every 6 hours" },
  { value: 12, label: "Every 12 hours" },
  { value: 24, label: "Once a day (recommended)" },
  { value: 48, label: "Every 2 days" },
  { value: 168, label: "Once a week" },
];

const DOC_TYPE_OPTIONS: { value: DocType; label: string }[] = [
  { value: "writing_sop", label: "Writing SOP" },
  { value: "cold_email", label: "Cold Email Template" },
  { value: "framework", label: "Framework" },
  { value: "ad_copy", label: "Ad Copy" },
  { value: "case_study", label: "Case Study" },
  { value: "other", label: "Other" },
];

const PLATFORM_OPTIONS: { value: Platform; label: string }[] = [
  { value: "all", label: "All Platforms" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "youtube", label: "YouTube" },
  { value: "twitter", label: "Twitter / X" },
  { value: "email", label: "Email" },
];

type SettingsTab = "connectors" | "pipeline" | "knowledge" | "team";

const SETTINGS_TABS: { key: SettingsTab; label: string }[] = [
  { key: "connectors", label: "Connectors" },
  { key: "pipeline", label: "Pipeline" },
  { key: "knowledge", label: "Knowledge Base" },
  { key: "team", label: "Team & System" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("connectors");
  const { currentBrand } = useBrand();

  // ── Connector state ───────────────────────────────────────
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [connectorsLoading, setConnectorsLoading] = useState(true);
  const [connecting, setConnecting] = useState<ConnectorService | null>(null);
  const [formValues, setFormValues] = useState<Record<string, Record<string, string>>>({});
  const [testing, setTesting] = useState<ConnectorService | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { status: string; message: string }>>({});
  const [removing, setRemoving] = useState<ConnectorService | null>(null);
  const [saving, setSaving] = useState<ConnectorService | null>(null);
  const [saveError, setSaveError] = useState<Record<string, string>>({});

  // ── Pipeline state ────────────────────────────────────────
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineSaving, setPipelineSaving] = useState(false);
  const [runningNow, setRunningNow] = useState(false);
  const [pipelineMsg, setPipelineMsg] = useState("");

  // ── Knowledge docs state ──────────────────────────────────
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [addingDoc, setAddingDoc] = useState(false);
  const [docForm, setDocForm] = useState({ title: "", content: "", doc_type: "writing_sop" as DocType, platform: "all" as Platform });
  const [savingDoc, setSavingDoc] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);

  // ── Team state ────────────────────────────────────────────
  const [tipText, setTipText] = useState("");
  const [tipAgent, setTipAgent] = useState("all");
  const [savingTip, setSavingTip] = useState(false);
  const [tipMsg, setTipMsg] = useState("");

  // ── Rebuild Profile state (Slice 91b) ─────────────────────
  const [rebuildName, setRebuildName] = useState("");
  const [rebuildUrl, setRebuildUrl] = useState("");
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildMsg, setRebuildMsg] = useState("");

  // ── Connector loaders ─────────────────────────────────────

  const loadConnectors = useCallback(async () => {
    try {
      const data = await connectorsApi.list();
      setConnectors(data);
    } finally {
      setConnectorsLoading(false);
    }
  }, []);

  useEffect(() => { loadConnectors(); }, [loadConnectors]);

  // ── Pipeline loaders ──────────────────────────────────────

  const loadPipeline = useCallback(async () => {
    setPipelineLoading(true);
    try {
      const data = await pipelineSettingsApi.get();
      setPipelineSettings(data);
    } finally {
      setPipelineLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "pipeline") loadPipeline();
  }, [activeTab, loadPipeline]);

  const handlePipelineUpdate = async (updates: { enabled?: boolean; interval_hours?: number }) => {
    setPipelineSaving(true);
    setPipelineMsg("");
    try {
      const data = await pipelineSettingsApi.update(updates);
      setPipelineSettings(data);
      setPipelineMsg("Saved.");
      setTimeout(() => setPipelineMsg(""), 2000);
    } catch {
      setPipelineMsg("Failed to save.");
    } finally {
      setPipelineSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunningNow(true);
    try {
      await pipelineSettingsApi.runNow();
      setPipelineMsg("Run requested — Jumbo will start within 60 seconds.");
      await loadPipeline();
    } catch {
      setPipelineMsg("Failed to trigger run.");
    } finally {
      setRunningNow(false);
    }
  };

  // ── Knowledge doc loaders ─────────────────────────────────

  const loadDocs = useCallback(async () => {
    setDocsLoading(true);
    try {
      const data = await knowledgeDocsApi.list(
        currentBrand ? { brand_id: currentBrand.id } : undefined
      );
      setDocs(data);
    } finally {
      setDocsLoading(false);
    }
  }, [currentBrand]);

  useEffect(() => {
    if (activeTab === "knowledge") loadDocs();
  }, [activeTab, loadDocs]);

  const handleSaveDoc = async () => {
    if (!docForm.title.trim() || !docForm.content.trim()) return;
    setSavingDoc(true);
    try {
      const created = await knowledgeDocsApi.create({
        brand_id: currentBrand?.id,
        title: docForm.title,
        content: docForm.content,
        doc_type: docForm.doc_type,
        platform: docForm.platform,
      });
      setDocs((prev) => [...prev, created]);
      setDocForm({ title: "", content: "", doc_type: "writing_sop", platform: "all" });
      setAddingDoc(false);
    } catch {
      // ignore
    } finally {
      setSavingDoc(false);
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm("Delete this document?")) return;
    setDeletingDoc(id);
    try {
      await knowledgeDocsApi.delete(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } finally {
      setDeletingDoc(null);
    }
  };

  // ── Connector handlers ────────────────────────────────────

  const getConnector = (service: ConnectorService) => connectors.find((c) => c.service === service);

  const handleSaveConnector = async (service: ConnectorService) => {
    const creds = formValues[service];
    if (!creds) return;
    setSaving(service);
    setSaveError((prev) => ({ ...prev, [service]: "" }));
    try {
      await connectorsApi.save(service, creds);
      await loadConnectors();
      setConnecting(null);
    } catch (e: unknown) {
      setSaveError((prev) => ({ ...prev, [service]: e instanceof Error ? e.message : "Save failed" }));
    } finally {
      setSaving(null);
    }
  };

  const handleTest = async (service: ConnectorService) => {
    setTesting(service);
    try {
      const result = await connectorsApi.test(service);
      setTestResult((prev) => ({ ...prev, [service]: result }));
      await loadConnectors();
    } catch (e: unknown) {
      setTestResult((prev) => ({ ...prev, [service]: { status: "error", message: e instanceof Error ? e.message : "Test failed" } }));
    } finally {
      setTesting(null);
    }
  };

  const handleRemove = async (service: ConnectorService) => {
    if (!confirm(`Remove ${service} connector?`)) return;
    setRemoving(service);
    try {
      await connectorsApi.remove(service);
      await loadConnectors();
      setTestResult((prev) => { const n = { ...prev }; delete n[service]; return n; });
    } finally {
      setRemoving(null);
    }
  };

  const setField = (service: ConnectorService, key: string, value: string) => {
    setFormValues((prev) => ({
      ...prev,
      [service]: { ...(prev[service] || {}), [key]: value },
    }));
  };

  // ── Rebuild Profile (Slice 91b) ───────────────────────────

  const handleRebuildProfile = async () => {
    if (!currentBrand || !rebuildName.trim()) return;
    setRebuilding(true);
    setRebuildMsg("");
    try {
      const result = await personalBrandsApi.autoProfile(currentBrand.id, {
        full_name: rebuildName.trim(),
        public_url: rebuildUrl.trim() || undefined,
      });
      if (result.sections_filled.length > 0) {
        setRebuildMsg(
          `✅ Updated ${result.sections_filled.length} section${result.sections_filled.length !== 1 ? "s" : ""}: ${result.sections_filled.join(", ")}.`,
        );
      } else {
        setRebuildMsg("No new data found — profile unchanged.");
      }
      setTimeout(() => setRebuildMsg(""), 6000);
    } catch {
      setRebuildMsg("Failed to rebuild profile. Check your API keys.");
    } finally {
      setRebuilding(false);
    }
  };

  // ── Train agent ───────────────────────────────────────────

  const handleSaveTip = async () => {
    if (!tipText.trim()) return;
    setSavingTip(true);
    setTipMsg("");
    try {
      await agentBridgeApi.submitReport({
        agent_id: tipAgent === "all" ? "jumbo" : tipAgent,
        report_type: "user_input",
        title: "Agent tip from user",
        content: `[TIP for ${tipAgent}]: ${tipText}`,
        tags: ["user_tip"],
        save_to_memory: true,
      });
      setTipText("");
      setTipMsg("Saved! Your agents will use this on the next run.");
      setTimeout(() => setTipMsg(""), 4000);
    } catch {
      setTipMsg("Failed to save tip.");
    } finally {
      setSavingTip(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* MC Sub-nav */}
      <div className="h-12 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              item.href === "/mission-control/settings"
                ? "bg-primary/15 text-primary border border-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      <div className="p-6 space-y-6 max-w-4xl">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage connections, pipeline, knowledge base, and agent training.
          </p>
        </div>

        {/* Settings tabs */}
        <div className="flex items-center gap-1 border-b border-border">
          {SETTINGS_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition -mb-px ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── CONNECTORS TAB ───────────────────────── */}
        {activeTab === "connectors" && (
          connectorsLoading ? (
            <div className="text-sm text-muted-foreground">Loading...</div>
          ) : (
            <div className="grid gap-4">
              {CONNECTOR_CONFIGS.map((config) => {
                const existing = getConnector(config.service);
                const st = existing ? STATUS_BADGE[existing.last_test_status || "untested"] : null;
                const isConnecting = connecting === config.service;
                const tr = testResult[config.service];

                return (
                  <div key={config.service} className="rounded-lg border border-border bg-card overflow-hidden">
                    <div className="px-5 py-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center font-bold text-sm">
                          {config.icon}
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{config.label}</div>
                          <div className="text-xs text-muted-foreground">{config.description}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {existing && st && (
                          <div className="flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${st.dot}`} />
                            <span className={`text-xs ${st.color}`}>{st.label}</span>
                          </div>
                        )}
                        {existing && (
                          <>
                            <button
                              onClick={() => handleTest(config.service)}
                              disabled={testing === config.service}
                              className="px-2.5 py-1 border border-border rounded text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
                            >
                              {testing === config.service ? "Testing..." : "Test"}
                            </button>
                            <button
                              onClick={() => handleRemove(config.service)}
                              disabled={removing === config.service}
                              className="px-2.5 py-1 border border-red-500/30 text-red-400 rounded text-xs hover:bg-red-500/10 disabled:opacity-50"
                            >
                              {removing === config.service ? "Removing..." : "Remove"}
                            </button>
                          </>
                        )}
                        {!existing && (
                          <button
                            onClick={() => setConnecting(isConnecting ? null : config.service)}
                            className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs font-medium"
                          >
                            {isConnecting ? "Cancel" : "Connect"}
                          </button>
                        )}
                        {existing && !isConnecting && (
                          <button
                            onClick={() => setConnecting(isConnecting ? null : config.service)}
                            className="px-3 py-1.5 border border-border rounded text-xs text-muted-foreground hover:text-foreground"
                          >
                            Update
                          </button>
                        )}
                      </div>
                    </div>

                    {tr && (
                      <div className={`px-5 pb-3 text-xs ${tr.status === "ok" ? "text-green-400" : "text-red-400"}`}>
                        {tr.status === "ok" ? "✓" : "✗"} {tr.message}
                      </div>
                    )}

                    {isConnecting && (
                      <div className="border-t border-border px-5 py-4 space-y-3">
                        {config.fields.map((field) => (
                          <div key={field.key}>
                            <label className="block text-xs text-muted-foreground mb-1">{field.label}</label>
                            <input
                              type={field.type || "text"}
                              placeholder={field.placeholder}
                              value={formValues[config.service]?.[field.key] || ""}
                              onChange={(e) => setField(config.service, field.key, e.target.value)}
                              className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>
                        ))}
                        {saveError[config.service] && (
                          <div className="text-xs text-red-400">{saveError[config.service]}</div>
                        )}
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveConnector(config.service)}
                            disabled={saving === config.service}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
                          >
                            {saving === config.service ? "Saving..." : "Save Credentials"}
                          </button>
                          <button
                            onClick={() => setConnecting(null)}
                            className="px-4 py-2 border border-border rounded text-xs text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )
        )}

        {/* ── PIPELINE TAB ─────────────────────────── */}
        {activeTab === "pipeline" && (
          <div className="space-y-4 max-w-xl">
            <div className="rounded-lg border border-border bg-card p-5 space-y-5">
              <div>
                <h2 className="font-semibold text-sm">Automated Pipeline</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Jumbo researches, writes, and QA-reviews a post on your schedule. Posts land in Home Inbox for approval.
                </p>
              </div>

              {pipelineLoading ? (
                <div className="text-sm text-muted-foreground">Loading...</div>
              ) : pipelineSettings ? (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">Pipeline active</div>
                      <div className="text-xs text-muted-foreground">Turn off to pause all automatic runs</div>
                    </div>
                    <button
                      onClick={() => handlePipelineUpdate({ enabled: !pipelineSettings.enabled })}
                      disabled={pipelineSaving}
                      className={`relative w-11 h-6 rounded-full transition-colors ${pipelineSettings.enabled ? "bg-primary" : "bg-muted"}`}
                    >
                      <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-all ${pipelineSettings.enabled ? "left-6" : "left-1"}`} />
                    </button>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">How often should Jumbo run?</label>
                    <select
                      value={pipelineSettings.interval_hours}
                      onChange={(e) => handlePipelineUpdate({ interval_hours: Number(e.target.value) })}
                      disabled={pipelineSaving || !pipelineSettings.enabled}
                      className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
                    >
                      {INTERVAL_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg bg-muted/30 border border-border px-3 py-2.5">
                      <div className="text-xs text-muted-foreground">Last run</div>
                      <div className="text-sm font-medium mt-0.5">
                        {pipelineSettings.last_run_at
                          ? new Date(pipelineSettings.last_run_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                          : "Never"}
                      </div>
                    </div>
                    <div className="rounded-lg bg-muted/30 border border-border px-3 py-2.5">
                      <div className="text-xs text-muted-foreground">Next run</div>
                      <div className="text-sm font-medium mt-0.5">
                        {pipelineSettings.next_run_at && pipelineSettings.enabled
                          ? new Date(pipelineSettings.next_run_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                          : "Paused"}
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-border pt-4">
                    <button
                      onClick={handleRunNow}
                      disabled={runningNow || pipelineSettings.run_now}
                      className="w-full py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50 hover:opacity-90 transition"
                    >
                      {runningNow ? "Requesting..." : pipelineSettings.run_now ? "Run queued..." : "Run Now"}
                    </button>
                    <p className="text-xs text-muted-foreground text-center mt-2">
                      Jumbo will research, write, and QA a post immediately.
                    </p>
                  </div>

                  {pipelineMsg && (
                    <div className={`text-xs text-center ${pipelineMsg.includes("Failed") ? "text-red-400" : "text-green-400"}`}>
                      {pipelineMsg}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-sm text-red-400">Could not load pipeline settings.</div>
              )}
            </div>
          </div>
        )}

        {/* ── KNOWLEDGE BASE TAB ───────────────────── */}
        {activeTab === "knowledge" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Knowledge Base</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  System SOPs (platform writing rules) + your brand docs (templates, case studies).
                  Agents read these before every task.
                </p>
              </div>
              <button
                onClick={() => setAddingDoc(!addingDoc)}
                className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded-lg font-medium hover:opacity-90 transition"
              >
                + Add Document
              </button>
            </div>

            {addingDoc && (
              <div className="rounded-xl border border-primary/30 bg-card p-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Title</label>
                    <input
                      value={docForm.title}
                      onChange={(e) => setDocForm((f) => ({ ...f, title: e.target.value }))}
                      placeholder="e.g. LinkedIn Hook Rules"
                      className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">Type</label>
                      <select
                        value={docForm.doc_type}
                        onChange={(e) => setDocForm((f) => ({ ...f, doc_type: e.target.value as DocType }))}
                        className="w-full bg-muted/30 border border-border rounded px-2 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        {DOC_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-muted-foreground mb-1">Platform</label>
                      <select
                        value={docForm.platform}
                        onChange={(e) => setDocForm((f) => ({ ...f, platform: e.target.value as Platform }))}
                        className="w-full bg-muted/30 border border-border rounded px-2 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        {PLATFORM_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Content</label>
                  <textarea
                    value={docForm.content}
                    onChange={(e) => setDocForm((f) => ({ ...f, content: e.target.value }))}
                    placeholder="Paste your SOP, template, or framework..."
                    rows={5}
                    className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveDoc}
                    disabled={savingDoc || !docForm.title.trim() || !docForm.content.trim()}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
                  >
                    {savingDoc ? "Saving..." : "Save Document"}
                  </button>
                  <button
                    onClick={() => setAddingDoc(false)}
                    className="px-4 py-2 border border-border rounded text-xs text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {docsLoading ? (
              <div className="text-sm text-muted-foreground">Loading documents...</div>
            ) : docs.length === 0 ? (
              <div className="rounded-xl border border-border bg-card/30 px-6 py-10 text-center">
                <div className="text-2xl mb-2">📄</div>
                <p className="text-sm text-muted-foreground">No documents yet. Add a writing SOP or template to train your agents.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((doc) => (
                  <div key={doc.id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {doc.scope === "system" && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">SYSTEM</span>
                          )}
                          <span className="text-sm font-medium text-foreground truncate">{doc.title}</span>
                          <span className="text-[10px] text-muted-foreground shrink-0">
                            {doc.platform !== "all" ? doc.platform.toUpperCase() : "ALL"} · {doc.doc_type.replace("_", " ")}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-2">{doc.content}</p>
                      </div>
                      {doc.scope !== "system" && (
                        <button
                          onClick={() => handleDeleteDoc(doc.id)}
                          disabled={deletingDoc === doc.id}
                          className="text-[10px] text-muted-foreground/50 hover:text-red-400 transition shrink-0"
                        >
                          {deletingDoc === doc.id ? "..." : "Delete"}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── TEAM & SYSTEM TAB ────────────────────── */}
        {activeTab === "team" && (
          <div className="space-y-6 max-w-xl">
            {/* Train Your Agents */}
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <div>
                <h2 className="font-semibold text-sm">Train Your Agents</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Quick 1-2 sentence rules that agents apply forever. No code change needed.
                </p>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">What did you learn?</label>
                  <textarea
                    value={tipText}
                    onChange={(e) => setTipText(e.target.value)}
                    placeholder='e.g. "Never use the word game-changer" or "Always mention ROI in cold emails"'
                    rows={3}
                    className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Which agent?</label>
                  <select
                    value={tipAgent}
                    onChange={(e) => setTipAgent(e.target.value)}
                    className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="all">All Agents</option>
                    <option value="copywriter">Copywriter</option>
                    <option value="trend-analyzer">Researcher</option>
                    <option value="qa-reviewer">QA Reviewer</option>
                    <option value="distributor">Distributor</option>
                    <option value="competitor-analyst">Competitor Analyst</option>
                  </select>
                </div>
                <button
                  onClick={handleSaveTip}
                  disabled={savingTip || !tipText.trim()}
                  className="w-full py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
                >
                  {savingTip ? "Saving..." : "Save to Agent Memory"}
                </button>
                {tipMsg && (
                  <div className={`text-xs text-center ${tipMsg.includes("Failed") ? "text-red-400" : "text-green-400"}`}>
                    {tipMsg}
                  </div>
                )}
              </div>
            </div>

            {/* Rebuild Profile from Web */}
            <div className="rounded-lg border border-border bg-card p-5 space-y-4" data-testid="rebuild-profile">
              <div>
                <h2 className="font-semibold text-sm">Rebuild Profile from Web</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  AI finds your public content (LinkedIn, website, X) and fills empty brand profile fields. Existing data is never overwritten.
                </p>
              </div>
              <div className="space-y-2">
                <input
                  type="text"
                  value={rebuildName}
                  onChange={(e) => setRebuildName(e.target.value)}
                  placeholder="Your full name (e.g. Sarah Chen)"
                  className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <input
                  type="url"
                  value={rebuildUrl}
                  onChange={(e) => setRebuildUrl(e.target.value)}
                  placeholder="Public URL (optional — LinkedIn, website, X)"
                  className="w-full bg-muted/30 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  onClick={handleRebuildProfile}
                  disabled={rebuilding || !rebuildName.trim() || !currentBrand}
                  className="w-full py-2 bg-primary text-primary-foreground rounded text-xs font-medium disabled:opacity-50"
                >
                  {rebuilding ? "Analyzing your content…" : "Rebuild Profile →"}
                </button>
                {rebuildMsg && (
                  <div className={`text-xs text-center ${rebuildMsg.startsWith("✅") ? "text-green-400" : "text-muted-foreground"}`}>
                    {rebuildMsg}
                  </div>
                )}
              </div>
            </div>

            {/* System links */}
            <div className="rounded-lg border border-border bg-card p-5 space-y-2">
              <h2 className="font-semibold text-sm mb-3">System</h2>
              {[
                { href: "/mission-control/playbooks", label: "Agent Playbooks", desc: "View and approve agent self-improvement proposals" },
                { href: "/mission-control/ledger", label: "Audit Ledger", desc: "Append-only tamper-proof log of all agent actions" },
                { href: "/mission-control/gateway", label: "Gateway", desc: "OpenClaw VPS connection status and health" },
                { href: "/mission-control/goals", label: "Agent Goals", desc: "Tell Jumbo what to prioritize this week" },
                { href: "/brands", label: "Manage Brands", desc: "Add, edit, or switch between brands" },
              ].map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-sidebar-accent transition group"
                >
                  <div>
                    <div className="text-sm font-medium text-foreground group-hover:text-primary transition">{link.label}</div>
                    <div className="text-xs text-muted-foreground">{link.desc}</div>
                  </div>
                  <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                  </svg>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
