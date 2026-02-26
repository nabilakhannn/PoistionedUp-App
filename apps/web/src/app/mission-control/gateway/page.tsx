"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  gatewayApi,
  GatewayStatus,
  GatewayHealth,
  GatewayAgent,
  ChecklistItem,
} from "@/lib/api/gateway";

/* ── Helpers ───────────────────────────────────────────── */

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const STATUS_ICON: Record<string, string> = {
  healthy: "pulse",
  unhealthy: "alert",
  unreachable: "off",
  timeout: "off",
  error: "alert",
  not_configured: "setup",
};

const CHECKLIST_STYLE: Record<string, { icon: string; color: string }> = {
  pass: { icon: "check", color: "text-green-400" },
  fail: { icon: "x", color: "text-red-400" },
  warn: { icon: "warn", color: "text-amber-400" },
  skip: { icon: "skip", color: "text-zinc-500" },
};

const AGENT_MODEL_COLORS: Record<string, string> = {
  "gpt-4o": "bg-green-500/15 text-green-400 border-green-500/20",
  "gpt-4o-mini": "bg-blue-500/15 text-blue-400 border-blue-500/20",
  "claude-sonnet": "bg-purple-500/15 text-purple-400 border-purple-500/20",
};

/* ── Page ──────────────────────────────────────────────── */

export default function GatewayPage() {
  const [status, setStatus] = useState<GatewayStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const data = await gatewayApi.status();
      setStatus(data);
      setError(null);
      setLastRefresh(new Date());
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to check gateway status";
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(), 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  /* ── Loading ────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Checking gateway connection...</p>
        </div>
      </div>
    );
  }

  const health = status?.health;
  const agents = status?.agents || [];
  const sessions = status?.sessions || [];
  const checklist = status?.checklist || [];
  const config = status?.config;
  const isConnected = health?.connected === true;
  const isHealthy = health?.status === "healthy";
  const isMockMode = status?.mock_mode === true || health?.mock_mode === true;
  const passCount = checklist.filter((c) => c.status === "pass").length;

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <span className="text-cyan-400 text-lg">
            {isHealthy ? (
              <span className="inline-block w-3 h-3 rounded-full bg-green-400 animate-pulse" />
            ) : isConnected ? (
              <span className="inline-block w-3 h-3 rounded-full bg-amber-400" />
            ) : (
              <span className="inline-block w-3 h-3 rounded-full bg-red-400" />
            )}
          </span>
          <h1 className="text-sm font-bold text-foreground tracking-wider uppercase">
            Gateway Status
          </h1>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
            isHealthy
              ? "bg-green-500/15 text-green-400 border-green-500/20"
              : isConnected
              ? "bg-amber-500/15 text-amber-400 border-amber-500/20"
              : "bg-red-500/15 text-red-400 border-red-500/20"
          }`}>
            {isHealthy ? "ONLINE" : isConnected ? "DEGRADED" : "OFFLINE"}
          </span>
          {isMockMode && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-violet-500/15 text-violet-400 border-violet-500/20">
              DEMO MODE
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition flex items-center gap-1.5 ${
              refreshing
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 cursor-wait"
                : "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/25"
            }`}
          >
            {refreshing ? (
              <span className="w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <span>&#8635;</span>
            )}
            {refreshing ? "Checking..." : "Refresh"}
          </button>
          {lastRefresh && (
            <span className="text-[9px] text-muted-foreground">
              {timeAgo(lastRefresh.toISOString())}
            </span>
          )}
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="h-10 border-b border-border bg-card/50 flex items-center px-5 gap-1">
        <Link href="/mission-control" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Dashboard
        </Link>
        <Link href="/mission-control/analytics" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Analytics
        </Link>
        <Link href="/mission-control/orchestrator" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Orchestrator
        </Link>
        <Link href="/mission-control/gateway" className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
          Gateway
        </Link>
        <Link href="/mission-control/chat" className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition">
          Chat
        </Link>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">

          {/* Error banner */}
          {error && (
            <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-3">
              <span className="text-red-400 text-sm">&#9888;</span>
              <p className="text-xs text-red-400 flex-1">{error}</p>
              <button onClick={() => loadData(true)} className="text-[10px] text-red-400 underline">
                Retry
              </button>
            </div>
          )}

          {/* ── Connection Card ─────────────────────────── */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50">
              <h2 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Connection
              </h2>
            </div>
            <div className="px-5 py-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                  label="Status"
                  value={isHealthy ? "Healthy" : isConnected ? "Degraded" : "Offline"}
                  color={isHealthy ? "green" : isConnected ? "amber" : "red"}
                />
                <StatCard
                  label="Latency"
                  value={health?.latency_ms ? `${health.latency_ms}ms` : "—"}
                  color={
                    health?.latency_ms
                      ? health.latency_ms < 200
                        ? "green"
                        : health.latency_ms < 1000
                        ? "amber"
                        : "red"
                      : "zinc"
                  }
                />
                <StatCard
                  label="Agents"
                  value={String(agents.length)}
                  color={agents.length > 0 ? "cyan" : "zinc"}
                />
                <StatCard
                  label="Sessions"
                  value={String(sessions.length)}
                  color={sessions.length > 0 ? "purple" : "zinc"}
                />
              </div>

              {health?.gateway_url && (
                <div className="mt-4 flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">URL:</span>
                  <code className="text-[11px] text-foreground font-mono bg-accent px-2 py-0.5 rounded">
                    {health.gateway_url}
                  </code>
                  {health.version && health.version !== "unknown" && (
                    <span className="text-[10px] text-muted-foreground ml-2">v{health.version}</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Deployment Checklist ─────────────────────── */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50 flex items-center justify-between">
              <h2 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                Deployment Checklist
              </h2>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                passCount === checklist.length
                  ? "bg-green-500/15 text-green-400"
                  : passCount >= checklist.length / 2
                  ? "bg-amber-500/15 text-amber-400"
                  : "bg-red-500/15 text-red-400"
              }`}>
                {passCount}/{checklist.length} PASSED
              </span>
            </div>
            <div className="divide-y divide-border/50">
              {checklist.map((item) => (
                <ChecklistRow key={item.id} item={item} />
              ))}
              {checklist.length === 0 && (
                <div className="px-5 py-6 text-center text-xs text-muted-foreground">
                  Unable to build checklist. Configure OPENCLAW_GATEWAY_URL to start.
                </div>
              )}
            </div>
          </div>

          {/* ── Agent Roster (from Gateway) ──────────────── */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50">
              <h2 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-400" />
                Agent Roster
              </h2>
            </div>
            <div className="divide-y divide-border/50">
              {agents.map((agent) => (
                <AgentRow key={agent.id} agent={agent} />
              ))}
              {agents.length === 0 && (
                <div className="px-5 py-6 text-center text-xs text-muted-foreground">
                  No agents detected. Deploy OpenClaw to your VPS to see agents here.
                </div>
              )}
            </div>
          </div>

          {/* ── Active Sessions ──────────────────────────── */}
          {sessions.length > 0 && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="px-5 py-4 border-b border-border/50">
                <h2 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  Active Sessions
                </h2>
              </div>
              <div className="divide-y divide-border/50">
                {sessions.map((session) => (
                  <div key={session.id} className="px-5 py-3 flex items-center gap-3">
                    <code className="text-[10px] text-muted-foreground font-mono">{session.id.slice(0, 12)}...</code>
                    {session.agent_id && (
                      <span className="text-[10px] text-foreground font-medium">{session.agent_id}</span>
                    )}
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                      session.status === "active" ? "bg-green-500/15 text-green-400" : "bg-zinc-500/15 text-zinc-400"
                    }`}>
                      {session.status}
                    </span>
                    <span className="flex-1" />
                    {session.message_count !== null && (
                      <span className="text-[10px] text-muted-foreground">{session.message_count} msgs</span>
                    )}
                    {session.last_activity && (
                      <span className="text-[10px] text-muted-foreground">{timeAgo(session.last_activity)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Quick Deploy Guide ───────────────────────── */}
          {!isConnected && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="px-5 py-4 border-b border-border/50">
                <h2 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-400" />
                  Quick Deploy Guide
                </h2>
              </div>
              <div className="px-5 py-5 space-y-4">
                <DeployStep
                  step={1}
                  title="SSH into your VPS"
                  code="ssh root@YOUR_VPS_IP"
                />
                <DeployStep
                  step={2}
                  title="Run the setup script"
                  code="bash setup-vps.sh"
                />
                <DeployStep
                  step={3}
                  title="Edit the .env file with your keys"
                  code="nano /opt/openclaw/.env"
                />
                <DeployStep
                  step={4}
                  title="Clone repo and build"
                  code={`git clone YOUR_REPO /opt/openclaw/app\ncd /opt/openclaw/app\ncp /opt/openclaw/.env deploy/.env\ndocker compose -f deploy/docker-compose.yml up -d --build`}
                />
                <DeployStep
                  step={5}
                  title="Set up SSH tunnel (for local testing)"
                  code="ssh -N -L 18789:127.0.0.1:18789 root@YOUR_VPS_IP"
                />
                <DeployStep
                  step={6}
                  title="Add to your backend .env"
                  code={`OPENCLAW_GATEWAY_URL=http://localhost:18789\nOPENCLAW_GATEWAY_TOKEN=your-generated-token`}
                />

                <div className="pt-3 border-t border-border/50">
                  <p className="text-[10px] text-muted-foreground">
                    After setting the env vars, refresh this page to verify the connection.
                    For HTTPS access, enable the Caddy profile:
                  </p>
                  <code className="text-[10px] text-cyan-400 font-mono block mt-1">
                    docker compose -f deploy/docker-compose.yml --profile https up -d
                  </code>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────────── */

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: "green" | "amber" | "red" | "cyan" | "purple" | "zinc";
}) {
  const colorMap: Record<string, string> = {
    green: "text-green-400",
    amber: "text-amber-400",
    red: "text-red-400",
    cyan: "text-cyan-400",
    purple: "text-purple-400",
    zinc: "text-zinc-500",
  };
  return (
    <div className="text-center px-3 py-3 rounded-lg bg-accent/50 border border-border">
      <div className={`text-xl font-bold font-mono ${colorMap[color]}`}>{value}</div>
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider mt-0.5">{label}</div>
    </div>
  );
}

function ChecklistRow({ item }: { item: ChecklistItem }) {
  const style = CHECKLIST_STYLE[item.status] || CHECKLIST_STYLE.skip;
  return (
    <div className="px-5 py-3 flex items-center gap-3">
      <span className={`text-sm ${style.color}`}>
        {item.status === "pass" ? "\u2713" : item.status === "fail" ? "\u2717" : item.status === "warn" ? "!" : "\u2014"}
      </span>
      <span className="text-xs text-foreground font-medium flex-1">{item.label}</span>
      <span className="text-[10px] text-muted-foreground">{item.detail}</span>
    </div>
  );
}

function AgentRow({ agent }: { agent: GatewayAgent }) {
  const modelStyle = AGENT_MODEL_COLORS[agent.model || ""] || "bg-zinc-500/15 text-zinc-400 border-zinc-500/20";
  const agentEmojis: Record<string, string> = {
    jumbo: "\uD83C\uDFAF",
    "trend-analyzer": "\uD83D\uDD0D",
    copywriter: "\u270D\uFE0F",
    "visual-designer": "\uD83C\uDFA8",
    distributor: "\uD83D\uDE80",
    analytics: "\uD83D\uDCCA",
  };
  const emoji = agentEmojis[agent.id] || "\uD83E\uDD16";

  return (
    <div className="px-5 py-3 flex items-center gap-3 hover:bg-accent/20 transition">
      <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-base border border-border flex-shrink-0">
        {emoji}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-foreground">{agent.name}</span>
          {agent.is_default && (
            <span className="text-[8px] px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 font-bold">
              DEFAULT
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {agent.model && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold ${modelStyle}`}>
              {agent.model}
            </span>
          )}
          {agent.channels.length > 0 && (
            <span className="text-[9px] text-muted-foreground">
              {agent.channels.join(", ")}
            </span>
          )}
        </div>
      </div>
      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
        agent.status === "active" || agent.status === "ready"
          ? "bg-green-500/15 text-green-400"
          : agent.status === "working"
          ? "bg-blue-500/15 text-blue-400"
          : agent.status === "error"
          ? "bg-red-500/15 text-red-400"
          : "bg-zinc-500/15 text-zinc-400"
      }`}>
        {agent.status.toUpperCase()}
      </span>
    </div>
  );
}

function DeployStep({
  step,
  title,
  code,
}: {
  step: number;
  title: string;
  code: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
          {step}
        </span>
        <span className="text-xs font-medium text-foreground">{title}</span>
      </div>
      <pre className="text-[11px] text-cyan-400/80 font-mono bg-zinc-900 border border-border rounded-lg px-3 py-2 overflow-x-auto whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  );
}
