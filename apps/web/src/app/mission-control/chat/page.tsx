"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { MC_SUB_NAV } from "../constants";
import {
  gatewayApi,
  GatewayAgent,
  GatewayMessageResponse,
} from "@/lib/api/gateway";
import {
  missionControlApi,
  Agent,
} from "@/lib/api/mission-control";

/* ── Types ─────────────────────────────────────────────── */

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  agentId: string;
  timestamp: string;
  sessionId?: string;
  status?: "sent" | "delivered" | "error";
}

interface AgentWithGateway {
  id: string;
  name: string;
  avatarEmoji: string;
  model: string | null;
  status: string;
  isDefault: boolean;
  gatewayStatus: string;
  channels: string[];
}

/* ── Helpers ───────────────────────────────────────────── */

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const AGENT_AVATARS: Record<string, string> = {
  jumbo: "\u{1F418}",
  "trend-analyzer": "\u{1F50D}",
  copywriter: "\u{270D}\u{FE0F}",
  "visual-designer": "\u{1F3A8}",
  distributor: "\u{1F4E1}",
  analytics: "\u{1F4CA}",
};

const MODEL_BADGE: Record<string, string> = {
  "gpt-4o": "bg-green-500/15 text-green-400 border-green-500/20",
  "gpt-4o-mini": "bg-blue-500/15 text-blue-400 border-blue-500/20",
  "claude-sonnet": "bg-purple-500/15 text-purple-400 border-purple-500/20",
};

/* ── Page ──────────────────────────────────────────────── */

export default function AgentChatPage() {
  const [agents, setAgents] = useState<AgentWithGateway[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({});
  const [sessions, setSessions] = useState<Record<string, string>>({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [gatewayOnline, setGatewayOnline] = useState(false);
  const [mockMode, setMockMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* ── Load agents from gateway + mission control ───── */

  const loadAgents = useCallback(async () => {
    try {
      const [gatewayAgents, mcAgents] = await Promise.all([
        gatewayApi.agents().catch(() => [] as GatewayAgent[]),
        missionControlApi.listAgents().catch(() => [] as Agent[]),
      ]);

      // Check gateway health
      const health = await gatewayApi.health().catch(() => ({ connected: false }) as Partial<import("@/lib/api/gateway").GatewayHealth>);
      setGatewayOnline(health.connected === true);
      setMockMode(health.mock_mode === true);

      // Merge gateway + MC agent data
      const agentMap = new Map<string, AgentWithGateway>();

      // Start with gateway agents
      for (const ga of gatewayAgents) {
        agentMap.set(ga.id, {
          id: ga.id,
          name: ga.name,
          avatarEmoji: AGENT_AVATARS[ga.id] || "\u{1F916}",
          model: ga.model,
          status: ga.status,
          isDefault: ga.is_default,
          gatewayStatus: ga.status,
          channels: ga.channels,
        });
      }

      // Enrich with MC data (names, status from MC perspective)
      for (const mca of mcAgents) {
        const existing = agentMap.get(mca.id);
        if (existing) {
          existing.name = mca.name;
          existing.avatarEmoji = mca.avatar_emoji || existing.avatarEmoji;
        } else {
          agentMap.set(mca.id, {
            id: mca.id,
            name: mca.name,
            avatarEmoji: mca.avatar_emoji || AGENT_AVATARS[mca.id] || "\u{1F916}",
            model: mca.model_name,
            status: mca.status,
            isDefault: mca.id === "jumbo",
            gatewayStatus: "unknown",
            channels: [],
          });
        }
      }

      const sorted = Array.from(agentMap.values()).sort((a, b) => {
        if (a.isDefault && !b.isDefault) return -1;
        if (!a.isDefault && b.isDefault) return 1;
        return a.name.localeCompare(b.name);
      });

      setAgents(sorted);

      // Auto-select Jumbo (orchestrator) if nothing selected
      if (!selectedAgent && sorted.length > 0) {
        const defaultAgent = sorted.find((a) => a.isDefault) || sorted[0];
        setSelectedAgent(defaultAgent.id);
      }

      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load agents";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedAgent]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  /* ── Scroll to bottom on new messages ────────────── */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  /* ── Focus input when agent changes ─────────────── */

  useEffect(() => {
    if (selectedAgent) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [selectedAgent]);

  /* ── Send message ────────────────────────────────── */

  const sendMessage = async () => {
    if (!input.trim() || !selectedAgent || sending) return;

    const userMsg: ChatMessage = {
      id: generateId(),
      role: "user",
      content: input.trim(),
      agentId: selectedAgent,
      timestamp: new Date().toISOString(),
      status: "sent",
    };

    // Add user message immediately
    setMessages((prev) => ({
      ...prev,
      [selectedAgent]: [...(prev[selectedAgent] || []), userMsg],
    }));
    setInput("");
    setSending(true);

    try {
      const sessionId = sessions[selectedAgent];
      const resp: GatewayMessageResponse = await gatewayApi.sendMessage(
        selectedAgent,
        userMsg.content,
        sessionId,
      );

      // Store session ID for conversation continuity
      if (resp.session_id) {
        setSessions((prev) => ({ ...prev, [selectedAgent]: resp.session_id! }));
      }

      // Add agent response
      const agentMsg: ChatMessage = {
        id: generateId(),
        role: "agent",
        content: resp.response || "Message delivered. Waiting for agent response...",
        agentId: selectedAgent,
        timestamp: new Date().toISOString(),
        sessionId: resp.session_id,
        status: "delivered",
      };

      setMessages((prev) => ({
        ...prev,
        [selectedAgent]: [...(prev[selectedAgent] || []), agentMsg],
      }));
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to send message";
      const errorResponse: ChatMessage = {
        id: generateId(),
        role: "agent",
        content: `Error: ${errMsg}`,
        agentId: selectedAgent,
        timestamp: new Date().toISOString(),
        status: "error",
      };

      setMessages((prev) => ({
        ...prev,
        [selectedAgent]: [...(prev[selectedAgent] || []), errorResponse],
      }));
    } finally {
      setSending(false);
    }
  };

  /* ── Current conversation ───────────────────────── */

  const currentMessages = selectedAgent ? messages[selectedAgent] || [] : [];
  const currentAgent = agents.find((a) => a.id === selectedAgent);
  const currentSession = selectedAgent ? sessions[selectedAgent] : undefined;

  /* ── Loading ─────────────────────────────────────── */

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-violet-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading Agent Chat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <span className="text-lg">{currentAgent?.avatarEmoji || "\u{1F4AC}"}</span>
          <h1 className="text-sm font-bold text-foreground tracking-wider uppercase">
            Agent Chat
          </h1>
          {currentAgent && (
            <span className="text-xs text-muted-foreground">
              {currentAgent.name}
            </span>
          )}
          {gatewayOnline ? (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-green-500/15 text-green-400 border-green-500/20">
              {mockMode ? "DEMO MODE" : "GATEWAY ONLINE"}
            </span>
          ) : (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-red-500/15 text-red-400 border-red-500/20">
              GATEWAY OFFLINE
            </span>
          )}
          {mockMode && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold border bg-violet-500/15 text-violet-400 border-violet-500/20">
              DEMO
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {currentSession && (
            <span className="text-[9px] text-muted-foreground font-mono">
              Session: {currentSession.slice(0, 12)}...
            </span>
          )}
          {selectedAgent && currentMessages.length > 0 && (
            <button
              onClick={() => {
                setMessages((prev) => ({ ...prev, [selectedAgent!]: [] }));
                setSessions((prev) => {
                  const next = { ...prev };
                  delete next[selectedAgent!];
                  return next;
                });
              }}
              className="px-3 py-1.5 rounded-lg text-[10px] font-bold text-zinc-400 border border-zinc-600 hover:bg-zinc-800 transition"
            >
              New Chat
            </button>
          )}
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="h-10 border-b border-border bg-card/50 flex items-center px-5 gap-1 overflow-x-auto">
        {MC_SUB_NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
              item.href === "/mission-control/chat"
                ? "bg-violet-500/15 text-violet-400 border border-violet-500/20"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Main content: agent sidebar + chat panel */}
      <div className="flex-1 flex overflow-hidden">

        {/* Agent sidebar */}
        <div className="w-64 border-r border-border bg-card/30 flex flex-col">
          <div className="px-4 py-3 border-b border-border/50">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Agents</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {agents.map((agent) => {
              const isSelected = agent.id === selectedAgent;
              const hasMessages = (messages[agent.id] || []).length > 0;
              const lastMsg = (messages[agent.id] || []).at(-1);

              return (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent.id)}
                  className={`w-full text-left px-4 py-3 border-b border-border/30 transition hover:bg-accent/30 ${
                    isSelected ? "bg-accent/40 border-l-2 border-l-violet-500" : ""
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-lg">{agent.avatarEmoji}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-foreground truncate">{agent.name}</span>
                        {agent.isDefault && (
                          <span className="text-[8px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold">LEAD</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {agent.model && (
                          <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-bold border ${
                            MODEL_BADGE[agent.model] || "bg-zinc-500/15 text-zinc-400 border-zinc-500/20"
                          }`}>
                            {agent.model}
                          </span>
                        )}
                        <span className={`inline-block w-1.5 h-1.5 rounded-full ${
                          agent.gatewayStatus === "active" ? "bg-green-400" :
                          agent.gatewayStatus === "idle" ? "bg-zinc-400" :
                          "bg-zinc-600"
                        }`} />
                      </div>
                      {hasMessages && lastMsg && (
                        <p className="text-[10px] text-muted-foreground truncate mt-1">
                          {lastMsg.role === "user" ? "You: " : ""}{lastMsg.content.slice(0, 40)}
                          {lastMsg.content.length > 40 ? "..." : ""}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}

            {agents.length === 0 && (
              <div className="px-4 py-8 text-center">
                <p className="text-2xl mb-2">{"\u{1F916}"}</p>
                <p className="text-xs text-muted-foreground">No agents available</p>
                <p className="text-[10px] text-muted-foreground mt-1">Check gateway connection</p>
              </div>
            )}
          </div>
        </div>

        {/* Chat panel */}
        <div className="flex-1 flex flex-col">
          {selectedAgent ? (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {/* Welcome message */}
                {currentMessages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <span className="text-5xl mb-4">{currentAgent?.avatarEmoji || "\u{1F916}"}</span>
                    <h2 className="text-lg font-bold text-foreground mb-1">
                      Chat with {currentAgent?.name || "Agent"}
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-md">
                      Send a message to interact with this agent via the OpenClaw gateway.
                      {currentAgent?.isDefault && " As the orchestrator, Jumbo can delegate tasks to other agents."}
                    </p>
                    {!gatewayOnline && (
                      <div className="mt-4 px-4 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <p className="text-xs text-amber-400">
                          Gateway is offline. Messages will fail until the VPS gateway is running.
                        </p>
                      </div>
                    )}
                    <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-lg">
                      {currentAgent?.isDefault ? (
                        <>
                          <QuickPrompt label="Check agent status" onClick={() => { setInput("What's the current status of all agents?"); }} />
                          <QuickPrompt label="Research AI trends" onClick={() => { setInput("Research the latest AI trends for personal branding in 2026"); }} />
                          <QuickPrompt label="Create content brief" onClick={() => { setInput("Create a content brief for a LinkedIn post about authentic leadership"); }} />
                          <QuickPrompt label="Weekly review" onClick={() => { setInput("Run a weekly performance review across all agents"); }} />
                        </>
                      ) : (
                        <>
                          <QuickPrompt label="What can you do?" onClick={() => { setInput("What are your capabilities and how can you help?"); }} />
                          <QuickPrompt label="Current tasks" onClick={() => { setInput("What tasks are you currently working on?"); }} />
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Message bubbles */}
                {currentMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`max-w-[80%] ${
                      msg.role === "user"
                        ? "bg-violet-600 text-white rounded-2xl rounded-br-md px-4 py-3"
                        : "space-y-0"
                    }`}>
                      {msg.role === "agent" && (
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm">{currentAgent?.avatarEmoji || "\u{1F916}"}</span>
                          <span className="text-[10px] font-bold text-muted-foreground uppercase">
                            {currentAgent?.name || msg.agentId}
                          </span>
                          <span className="text-[9px] text-muted-foreground">
                            {timeAgo(msg.timestamp)}
                          </span>
                        </div>
                      )}

                      {msg.role === "user" ? (
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <div className={`rounded-2xl rounded-bl-md px-4 py-3 text-sm whitespace-pre-wrap ${
                          msg.status === "error"
                            ? "bg-red-500/10 border border-red-500/20 text-red-400"
                            : "bg-card border border-border text-foreground"
                        }`}>
                          {msg.content}
                        </div>
                      )}

                      {msg.role === "user" && (
                        <p className="text-[9px] text-violet-200/60 text-right mt-1">
                          {timeAgo(msg.timestamp)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {/* Typing indicator */}
                {sending && (
                  <div className="flex justify-start">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm">{currentAgent?.avatarEmoji || "\u{1F916}"}</span>
                        <span className="text-[10px] font-bold text-muted-foreground uppercase">
                          {currentAgent?.name}
                        </span>
                      </div>
                      <div className="bg-card border border-border px-4 py-3 rounded-2xl rounded-bl-md text-sm text-muted-foreground">
                        <span className="inline-flex gap-1">
                          <span className="animate-bounce">{"\u00B7"}</span>
                          <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>{"\u00B7"}</span>
                          <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>{"\u00B7"}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input area */}
              <div className="border-t border-border px-4 py-3 bg-card">
                {error && (
                  <div className="mb-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                    <p className="text-[10px] text-red-400">{error}</p>
                  </div>
                )}
                <div className="flex items-end gap-2">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder={`Message ${currentAgent?.name || "agent"}... (Enter to send, Shift+Enter for newline)`}
                    rows={1}
                    className="flex-1 bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-violet-500/50 max-h-32"
                    style={{ minHeight: "40px" }}
                    disabled={sending}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || sending}
                    className={`px-4 py-2.5 rounded-xl text-sm font-bold transition ${
                      input.trim() && !sending
                        ? "bg-violet-600 text-white hover:bg-violet-500"
                        : "bg-muted text-muted-foreground cursor-not-allowed"
                    }`}
                  >
                    {sending ? (
                      <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin inline-block" />
                    ) : (
                      "Send"
                    )}
                  </button>
                </div>
                <div className="flex items-center justify-between mt-1.5 px-1">
                  <div className="flex items-center gap-3">
                    <span className="text-[9px] text-muted-foreground">
                      {input.length > 0 && `${input.length.toLocaleString()} chars`}
                    </span>
                  </div>
                  <span className="text-[9px] text-muted-foreground">
                    via OpenClaw Gateway
                    {currentAgent?.channels.length ? ` + ${currentAgent.channels.join(", ")}` : ""}
                  </span>
                </div>
              </div>
            </>
          ) : (
            /* No agent selected */
            <div className="flex-1 flex items-center justify-center text-center">
              <div>
                <span className="text-5xl">{"\u{1F4AC}"}</span>
                <h2 className="text-lg font-bold text-foreground mt-4 mb-1">Select an Agent</h2>
                <p className="text-sm text-muted-foreground">
                  Choose an agent from the sidebar to start a conversation.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ────────────────────────────────────── */

function QuickPrompt({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-2 rounded-lg text-xs font-medium bg-card border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition"
    >
      {label}
    </button>
  );
}
