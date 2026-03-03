"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { connectorsApi, Connector, ConnectorService } from "@/lib/api/connectors";
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
    description: "Post to LinkedIn automatically via Make.com or Zapier. Paste your automation webhook URL below — we send your content there and it posts via LinkedIn's official API.",
    fields: [
      {
        key: "session_cookie",
        label: "Make.com / Zapier Webhook URL",
        placeholder: "https://hook.make.com/...",
        type: "text",
      },
    ],
  },
  {
    service: "twitter",
    label: "Twitter / X",
    icon: "X",
    description: "Connect Twitter/X with OAuth 1.0a keys to enable automatic tweet posting. Get your keys from developer.twitter.com → Your App → Keys and Tokens.",
    fields: [
      {
        key: "api_key",
        label: "API Key (Consumer Key)",
        placeholder: "abc123...",
        type: "password",
      },
      {
        key: "api_secret",
        label: "API Secret (Consumer Secret)",
        placeholder: "xyz789...",
        type: "password",
      },
      {
        key: "access_token",
        label: "Access Token",
        placeholder: "1234567890-abc...",
        type: "password",
      },
      {
        key: "access_token_secret",
        label: "Access Token Secret",
        placeholder: "def456...",
        type: "password",
      },
    ],
  },
  {
    service: "instagram",
    label: "Instagram",
    icon: "IG",
    description: "Connect Instagram via Graph API to post to business accounts.",
    fields: [
      {
        key: "access_token",
        label: "Access Token",
        placeholder: "EAA...",
        type: "password",
      },
      {
        key: "page_id",
        label: "Page ID",
        placeholder: "123456789",
      },
    ],
  },
  {
    service: "webhook",
    label: "Custom Webhook",
    icon: "⚡",
    description: "Send content to any external system via a webhook URL.",
    fields: [
      {
        key: "url",
        label: "Webhook URL",
        placeholder: "https://your-service.com/webhook",
      },
      {
        key: "secret",
        label: "Secret (optional)",
        placeholder: "your-signing-secret",
        type: "password",
      },
    ],
  },
];

const STATUS_BADGE: Record<string, { label: string; color: string; dot: string }> = {
  ok: { label: "Connected", color: "text-green-400", dot: "bg-green-400" },
  error: { label: "Error", color: "text-red-400", dot: "bg-red-400" },
  untested: { label: "Untested", color: "text-amber-400", dot: "bg-amber-400" },
};

const SETTINGS_TABS = [
  { key: "connectors", label: "Connectors" },
  { key: "playbooks", label: "Playbooks", href: "/mission-control/playbooks" },
  { key: "history", label: "History", href: "/mission-control/ledger" },
  { key: "system", label: "System", href: "/mission-control/gateway" },
] as const;

type SettingsTab = typeof SETTINGS_TABS[number]["key"];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("connectors");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<ConnectorService | null>(null);
  const [formValues, setFormValues] = useState<Record<string, Record<string, string>>>({});
  const [testing, setTesting] = useState<ConnectorService | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { status: string; message: string }>>({});
  const [removing, setRemoving] = useState<ConnectorService | null>(null);
  const [saving, setSaving] = useState<ConnectorService | null>(null);
  const [saveError, setSaveError] = useState<Record<string, string>>({});

  const loadConnectors = useCallback(async () => {
    try {
      const data = await connectorsApi.list();
      setConnectors(data);
    } catch {
      console.error("Failed to load connectors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConnectors();
  }, [loadConnectors]);

  const getConnector = (service: ConnectorService) =>
    connectors.find((c) => c.service === service);

  const handleSave = async (service: ConnectorService) => {
    const creds = formValues[service];
    if (!creds) return;
    setSaving(service);
    setSaveError(prev => ({ ...prev, [service]: "" }));
    try {
      await connectorsApi.save(service, creds);
      await loadConnectors();
      setConnecting(null);
    } catch (e: unknown) {
      setSaveError(prev => ({ ...prev, [service]: e instanceof Error ? e.message : "Save failed" }));
    } finally {
      setSaving(null);
    }
  };

  const handleTest = async (service: ConnectorService) => {
    setTesting(service);
    try {
      const result = await connectorsApi.test(service);
      setTestResult(prev => ({ ...prev, [service]: result }));
      await loadConnectors();
    } catch (e: unknown) {
      setTestResult(prev => ({ ...prev, [service]: { status: "error", message: e instanceof Error ? e.message : "Test failed" } }));
    } finally {
      setTesting(null);
    }
  };

  const handleRemove = async (service: ConnectorService) => {
    if (!confirm(`Remove ${service} connector? This cannot be undone.`)) return;
    setRemoving(service);
    try {
      await connectorsApi.remove(service);
      await loadConnectors();
      setTestResult(prev => { const n = { ...prev }; delete n[service]; return n; });
    } catch {
      console.error("Failed to remove connector");
    } finally {
      setRemoving(null);
    }
  };

  const setField = (service: ConnectorService, key: string, value: string) => {
    setFormValues(prev => ({
      ...prev,
      [service]: { ...(prev[service] || {}), [key]: value },
    }));
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Top MC Sub-nav */}
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

      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your connections, agent playbooks, history, and system configuration.
          </p>
        </div>

        {/* Settings sub-tabs */}
        <div className="flex items-center gap-1 border-b border-border pb-0 -mb-2">
          {SETTINGS_TABS.map((tab) => (
            tab.key === "connectors" ? (
              <button
                key={tab.key}
                onClick={() => setActiveTab("connectors")}
                data-settings-tab={tab.label}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  activeTab === "connectors"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ) : (
              <Link
                key={tab.key}
                href={"href" in tab ? tab.href : "#"}
                data-settings-tab={tab.label}
                className="px-4 py-2 text-sm font-medium border-b-2 border-transparent text-muted-foreground hover:text-foreground transition"
              >
                {tab.label}
              </Link>
            )
          ))}
        </div>

      {activeTab === "connectors" && (loading ? (
        <div className="text-muted-foreground text-sm">Loading...</div>
      ) : (
        <div className="grid gap-4">
          {CONNECTOR_CONFIGS.map((config) => {
            const existing = getConnector(config.service);
            const st = existing
              ? STATUS_BADGE[existing.last_test_status || "untested"]
              : null;
            const isConnecting = connecting === config.service;
            const tr = testResult[config.service];

            return (
              <div key={config.service} className="rounded-lg border border-border bg-card overflow-hidden">
                {/* Card header */}
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

                {/* Test result inline */}
                {tr && (
                  <div className={`px-5 pb-3 text-xs ${tr.status === "ok" ? "text-green-400" : "text-red-400"}`}>
                    {tr.status === "ok" ? "✓" : "✗"} {tr.message}
                  </div>
                )}

                {/* Connect form */}
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
                        onClick={() => handleSave(config.service)}
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

                {/* Last tested info */}
                {existing?.last_tested_at && (
                  <div className="px-5 pb-3 text-xs text-muted-foreground">
                    Last tested: {new Date(existing.last_tested_at).toLocaleString()}
                    {existing.last_test_error && (
                      <span className="text-red-400 ml-2">— {existing.last_test_error}</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
      </div>
    </div>
  );
}
