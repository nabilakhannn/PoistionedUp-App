"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { trackEvent } from "@/lib/posthog";
import {
  contentChatApi,
  ContentChatMessage,
  ContentChatListItem,
  personalBrandsApi,
} from "@/lib/api";
import { useBrand } from "@/lib/brand-context";
import { OBJECTIVES, CONTENT_TYPES, PLATFORMS, TONES, LENGTHS } from "../constants";
import { parseContentSections, wordCount, renderMarkdown, copyToClipboard } from "./components/canvas-utils";
import { CanvasSection } from "./components/canvas-section";

/* ────────────────────────────────────────────────────────────
   Main Component
   ──────────────────────────────────────────────────────────── */

export default function ContentCanvasPage() {
  const searchParams = useSearchParams();
  const { brandId } = useBrand();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Chat state
  const [messages, setMessages] = useState<ContentChatMessage[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  // Settings state — validate query params against known values to prevent injection
  const validIds = (items: readonly { id: string }[]) => items.map((i) => i.id);
  const safeParam = (key: string, allowed: string[], fallback: string) => {
    const val = searchParams.get(key);
    return val && allowed.includes(val) ? val : fallback;
  };

  const [settingsOpen, setSettingsOpen] = useState(true);
  const [objective, setObjective] = useState(safeParam("objective", validIds(OBJECTIVES), "personal_branding"));
  const [contentType, setContentType] = useState(safeParam("type", validIds(CONTENT_TYPES), "educational"));
  const [platforms, setPlatforms] = useState<string[]>(() => {
    const raw = searchParams.get("platforms")?.split(",") || [];
    const allowed = validIds(PLATFORMS);
    const filtered = raw.filter((p) => allowed.includes(p));
    return filtered.length > 0 ? filtered : ["youtube"];
  });
  const [tone, setTone] = useState(safeParam("tone", validIds(TONES), "conversational"));
  const [contentLength, setContentLength] = useState("auto");
  const [selectedPillars, setSelectedPillars] = useState<string[]>([]);
  const [brandPillars, setBrandPillars] = useState<string[]>([]);
  const [customPillar, setCustomPillar] = useState("");

  // Chat history
  const [chatList, setChatList] = useState<ContentChatListItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(true);

  // Canvas state
  const [canvasContent, setCanvasContent] = useState<string>("");
  const [canvasSections, setCanvasSections] = useState<{ title: string; body: string }[]>([]);
  const [copiedKey, setCopiedKey] = useState("");

  // Mobile panel state
  const [activePanel, setActivePanel] = useState<"chat" | "canvas">("chat");

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load chat history
  useEffect(() => {
    contentChatApi.listChats(brandId || undefined).then(setChatList).catch(() => {});
  }, [brandId, chatId]);

  // Load brand pillars
  useEffect(() => {
    if (!brandId) return;
    personalBrandsApi
      .get(brandId)
      .then((brand: any) => {
        const pj = brand?.profile_json || {};
        const pillars = pj?.foundation?.content_pillars || pj?.content_pillars || [];
        if (pillars.length > 0) {
          setBrandPillars(pillars);
          setSelectedPillars(pillars);
        }
      })
      .catch(() => {});
  }, [brandId]);

  // Auto-extract content to canvas from latest assistant message
  useEffect(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    if (lastAssistant && lastAssistant.content.length > 100) {
      // Check if it looks like content (has headers, numbered lists, or is long enough)
      const hasStructure =
        /^#{1,3}\s/m.test(lastAssistant.content) ||
        /^\d+\.\s/m.test(lastAssistant.content) ||
        lastAssistant.content.length > 300;
      if (hasStructure) {
        setCanvasContent(lastAssistant.content);
        setCanvasSections(parseContentSections(lastAssistant.content));
      }
    }
  }, [messages]);

  // Toggle platform
  const togglePlatform = (id: string) => {
    setPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  // Total word count
  const totalWords = useMemo(() => wordCount(canvasContent), [canvasContent]);

  // Send message
  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;

    const userMessage = input.trim();
    setInput("");
    setSending(true);
    setError("");

    // Optimistic update
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    try {
      const settings = {
        objective,
        content_type: contentType,
        platforms,
        tone,
        content_length: contentLength,
        content_pillars: selectedPillars,
      };

      const response = await contentChatApi.sendMessage({
        message: userMessage,
        chat_id: chatId || undefined,
        brand_id: brandId || undefined,
        settings: chatId ? undefined : settings,
      });

      setChatId(response.chat_id);
      setMessages(response.messages);
      setSettingsOpen(false);

      trackEvent("content_chat_message_sent", {
        chat_id: response.chat_id,
        brand_id: brandId || "",
      });
    } catch (err: any) {
      setError(err.message || "Failed to send message");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  }, [input, sending, chatId, brandId, objective, contentType, platforms, tone, contentLength, selectedPillars]);

  // Pin a specific message to canvas
  const pinToCanvas = (content: string) => {
    setCanvasContent(content);
    setCanvasSections(parseContentSections(content));
    setActivePanel("canvas");
    trackEvent("content_pinned_to_canvas");
  };

  // Edit canvas section
  const editCanvasSection = (index: number, newBody: string) => {
    const updated = [...canvasSections];
    updated[index] = { ...updated[index], body: newBody };
    setCanvasSections(updated);
    // Rebuild full content
    const rebuilt = updated
      .map((s) => (s.title ? `## ${s.title}\n\n${s.body}` : s.body))
      .join("\n\n");
    setCanvasContent(rebuilt);
  };

  // Copy all canvas content
  const handleCopyAll = () => {
    const fullText = canvasSections
      .map((s) => (s.title ? `## ${s.title}\n\n${s.body}` : s.body))
      .join("\n\n");
    copyToClipboard(fullText, setCopiedKey, "all");
  };

  // Load existing chat
  const loadChat = async (id: string) => {
    try {
      const chat = await contentChatApi.getChat(id);
      setChatId(id);
      setMessages(chat.messages);
      setHistoryOpen(false);

      if (chat.settings) {
        if (chat.settings.objective) setObjective(chat.settings.objective);
        if (chat.settings.content_type) setContentType(chat.settings.content_type);
        if (chat.settings.platforms) setPlatforms(chat.settings.platforms);
        if (chat.settings.tone) setTone(chat.settings.tone);
        if (chat.settings.content_length) setContentLength(chat.settings.content_length);
        if (chat.settings.content_pillars) setSelectedPillars(chat.settings.content_pillars);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load chat");
    }
  };

  // Start new chat
  const startNewChat = () => {
    setChatId(null);
    setMessages([]);
    setCanvasContent("");
    setCanvasSections([]);
    setSettingsOpen(true);
    setError("");
  };

  // Delete chat
  const deleteChat = async (id: string) => {
    try {
      await contentChatApi.deleteChat(id);
      setChatList((prev) => prev.filter((c) => c.chat_id !== id));
      if (chatId === id) startNewChat();
    } catch (err: any) {
      setError(err.message || "Failed to delete chat");
    }
  };

  // Handle enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-4px)] bg-zinc-950">
      {/* ════════════════════════════════════════════════════════
         LEFT SIDEBAR: History + Settings
         ════════════════════════════════════════════════════════ */}
      <aside className="w-64 border-r border-zinc-800 flex-col shrink-0 hidden lg:flex bg-zinc-950">
        {/* New Chat */}
        <div className="p-3 border-b border-zinc-800">
          <button
            onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Content
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* ── Settings ── */}
          <div className="p-3 border-b border-zinc-800">
            <button
              onClick={() => setSettingsOpen(!settingsOpen)}
              className="flex items-center justify-between w-full text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2"
            >
              <span>Settings</span>
              <svg
                className={`w-3.5 h-3.5 transition-transform ${settingsOpen ? "rotate-180" : ""}`}
                fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {settingsOpen && (
              <div className="space-y-3">
                {/* Objective */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Goal</label>
                  <div className="space-y-0.5">
                    {OBJECTIVES.map((o) => (
                      <button
                        key={o.id}
                        onClick={() => setObjective(o.id)}
                        className={`w-full flex items-center gap-2 text-left px-2 py-1.5 rounded text-xs transition ${
                          objective === o.id
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "text-zinc-400 hover:bg-zinc-800/80 hover:text-zinc-300"
                        }`}
                      >
                        <span>{o.icon}</span>
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Platform */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Platform</label>
                  <div className="flex flex-wrap gap-1">
                    {PLATFORMS.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => togglePlatform(p.id)}
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition ${
                          platforms.includes(p.id)
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        <span className="text-[10px]">{p.icon}</span>
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Style */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Style</label>
                  <div className="flex flex-wrap gap-1">
                    {CONTENT_TYPES.map((ct) => (
                      <button
                        key={ct.id}
                        onClick={() => setContentType(ct.id)}
                        className={`px-2 py-1 rounded text-xs transition ${
                          contentType === ct.id
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        {ct.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tone */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Tone</label>
                  <div className="flex flex-wrap gap-1">
                    {TONES.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setTone(t.id)}
                        className={`px-2 py-1 rounded text-xs transition ${
                          tone === t.id
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Length */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Length</label>
                  <div className="flex flex-wrap gap-1">
                    {LENGTHS.map((l) => (
                      <button
                        key={l.id}
                        onClick={() => setContentLength(l.id)}
                        className={`px-2 py-1 rounded text-xs transition ${
                          contentLength === l.id
                            ? "bg-blue-600/20 text-blue-400 font-medium"
                            : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        {l.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Pillars */}
                <div>
                  <label className="text-[10px] text-zinc-500 font-medium uppercase tracking-wide block mb-1">Pillars</label>
                  <div className="flex flex-wrap gap-1 mb-1.5">
                    {[...new Set([...brandPillars, ...selectedPillars])].map((pillar) => {
                      const isSelected = selectedPillars.includes(pillar);
                      return (
                        <button
                          key={pillar}
                          onClick={() => {
                            setSelectedPillars((prev) =>
                              prev.includes(pillar)
                                ? prev.filter((p) => p !== pillar)
                                : [...prev, pillar]
                            );
                          }}
                          className={`px-2 py-0.5 rounded text-xs transition ${
                            isSelected
                              ? "bg-emerald-500/20 text-emerald-400 font-medium"
                              : "bg-zinc-800/80 text-zinc-600 line-through"
                          }`}
                        >
                          {pillar}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex gap-1">
                    <input
                      type="text"
                      value={customPillar}
                      onChange={(e) => setCustomPillar(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && customPillar.trim()) {
                          e.preventDefault();
                          const t = customPillar.trim();
                          if (!selectedPillars.includes(t)) {
                            setSelectedPillars((prev) => [...prev, t]);
                          }
                          setCustomPillar("");
                        }
                      }}
                      placeholder="Add pillar..."
                      className="flex-1 bg-zinc-800/80 border border-zinc-700 text-zinc-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-zinc-600 min-w-0"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── Chat History ── */}
          <div className="p-3">
            <button
              onClick={() => setHistoryOpen(!historyOpen)}
              className="flex items-center justify-between w-full text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2"
            >
              <span>Chats</span>
              <svg
                className={`w-3.5 h-3.5 transition-transform ${historyOpen ? "rotate-180" : ""}`}
                fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>

            {historyOpen && (
              <div className="space-y-0.5">
                {chatList.length === 0 && (
                  <p className="text-xs text-zinc-600 py-2">No chats yet</p>
                )}
                {chatList.map((c) => (
                  <div
                    key={c.chat_id}
                    className={`group flex items-center gap-1.5 px-2 py-1.5 rounded cursor-pointer transition ${
                      chatId === c.chat_id
                        ? "bg-blue-600/20 text-blue-400"
                        : "hover:bg-zinc-800/80 text-zinc-400"
                    }`}
                  >
                    <button
                      onClick={() => loadChat(c.chat_id)}
                      className="flex-1 text-left min-w-0"
                    >
                      <div className="text-xs truncate">
                        {c.title || c.preview || "Untitled"}
                      </div>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteChat(c.chat_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition p-0.5 shrink-0"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Back */}
        <div className="p-3 border-t border-zinc-800">
          <Link
            href="/content"
            className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Back to Content
          </Link>
        </div>
      </aside>

      {/* ════════════════════════════════════════════════════════
         MAIN WORKSPACE: Chat + Canvas
         ════════════════════════════════════════════════════════ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* ── Top Bar ── */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile sidebar toggle */}
            <button
              onClick={() => setSettingsOpen(!settingsOpen)}
              className="lg:hidden p-1.5 text-zinc-500 hover:text-zinc-300 transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
            <h1 className="text-sm font-semibold text-zinc-200">Content Studio</h1>

            {/* Active settings pills */}
            <div className="hidden md:flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-400">
                {OBJECTIVES.find((o) => o.id === objective)?.icon} {OBJECTIVES.find((o) => o.id === objective)?.label}
              </span>
              {platforms.map((pid) => (
                <span key={pid} className="px-2 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-400">
                  {PLATFORMS.find((p) => p.id === pid)?.icon} {PLATFORMS.find((p) => p.id === pid)?.label}
                </span>
              ))}
              <span className="px-2 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-400">
                {TONES.find((t) => t.id === tone)?.label}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mobile panel toggle */}
            <div className="flex md:hidden bg-zinc-800 rounded-lg p-0.5">
              <button
                onClick={() => setActivePanel("chat")}
                className={`px-3 py-1 text-xs rounded-md transition ${
                  activePanel === "chat"
                    ? "bg-zinc-700 text-zinc-200"
                    : "text-zinc-500"
                }`}
              >
                Chat
              </button>
              <button
                onClick={() => setActivePanel("canvas")}
                className={`px-3 py-1 text-xs rounded-md transition ${
                  activePanel === "canvas"
                    ? "bg-zinc-700 text-zinc-200"
                    : "text-zinc-500"
                }`}
              >
                Canvas
              </button>
            </div>

            <Link
              href="/content/new"
              className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
              Automation
            </Link>
          </div>
        </div>

        {/* ── Split: Chat | Canvas ── */}
        <div className="flex-1 flex min-h-0">
          {/* ════ CHAT PANEL ════ */}
          <div
            className={`flex flex-col border-r border-zinc-800 ${
              activePanel === "chat" ? "flex" : "hidden md:flex"
            } md:w-[55%] lg:w-[50%] w-full`}
          >
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.length === 0 && !chatId && (
                <div className="flex flex-col items-center justify-center h-full text-center px-4">
                  <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-3">
                    <svg className="w-7 h-7 text-blue-500" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                    </svg>
                  </div>
                  <h2 className="text-lg font-semibold text-zinc-100 mb-1.5">Content Studio</h2>
                  <p className="text-sm text-zinc-500 max-w-sm leading-relaxed mb-4">
                    Tell me what you want to create. I'll research, write, and refine it.
                    Your content appears on the canvas to the right.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {[
                      "Write a YouTube script about...",
                      "Create 5 LinkedIn posts about...",
                      "Research hooks for...",
                      "Write a Twitter thread about...",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => {
                          setInput(suggestion);
                          textareaRef.current?.focus();
                        }}
                        className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:border-zinc-700 transition"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className="group relative max-w-[90%]">
                    <div
                      className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-zinc-900 border border-zinc-800 text-zinc-200"
                      }`}
                    >
                      {msg.role === "assistant" ? (
                        <div
                          className="prose prose-invert prose-sm max-w-none
                            prose-headings:text-zinc-100 prose-headings:font-semibold prose-headings:mt-2 prose-headings:mb-1
                            prose-p:text-zinc-300 prose-p:leading-relaxed prose-p:my-1
                            prose-strong:text-zinc-100
                            prose-ul:text-zinc-300 prose-ol:text-zinc-300
                            prose-li:text-zinc-300 prose-li:my-0
                            prose-code:text-blue-400 prose-code:bg-zinc-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded"
                          dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                        />
                      ) : (
                        <span className="whitespace-pre-wrap">{msg.content}</span>
                      )}
                    </div>

                    {/* Pin to canvas button for assistant messages */}
                    {msg.role === "assistant" && msg.content.length > 50 && (
                      <button
                        onClick={() => pinToCanvas(msg.content)}
                        className="absolute -right-1 -top-1 opacity-0 group-hover:opacity-100 p-1.5 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-400 hover:text-blue-400 hover:border-blue-500/40 transition shadow-lg"
                        title="Pin to canvas"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="bg-zinc-900 border border-zinc-800 rounded-2xl px-3.5 py-2.5">
                    <div className="flex items-center gap-2 text-zinc-500 text-sm">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                      <span className="text-xs">Writing...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Error */}
            {error && (
              <div className="mx-4 mb-2 bg-red-500/10 border border-red-500/20 rounded-lg p-2.5 text-red-400 text-xs">
                {error}
              </div>
            )}

            {/* Input */}
            <div className="px-4 py-3 border-t border-zinc-800">
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Write a YouTube script about personal branding..."
                  className="flex-1 bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-xl px-3.5 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition placeholder:text-zinc-600 min-h-[44px] max-h-[150px]"
                  rows={1}
                  style={{ height: "auto", minHeight: "44px" }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = Math.min(target.scrollHeight, 150) + "px";
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || sending}
                  className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                </button>
              </div>
              <p className="text-[10px] text-zinc-600 mt-1 text-center">
                Enter to send, Shift+Enter for new line
              </p>
            </div>
          </div>

          {/* ════ CANVAS PANEL ════ */}
          <div
            className={`flex flex-col bg-zinc-950 ${
              activePanel === "canvas" ? "flex" : "hidden md:flex"
            } md:w-[45%] lg:w-[50%] w-full`}
          >
            {canvasSections.length > 0 ? (
              <>
                {/* Canvas header */}
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 shrink-0">
                  <div className="flex items-center gap-3">
                    <h2 className="text-sm font-semibold text-zinc-200">Canvas</h2>
                    <span className="text-[10px] text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                      {totalWords} words
                    </span>
                    <span className="text-[10px] text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                      {canvasSections.length} sections
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleCopyAll}
                      className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-800 text-zinc-300 rounded-lg text-xs hover:bg-zinc-700 transition"
                    >
                      {copiedKey === "all" ? (
                        <>
                          <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                          Copied!
                        </>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                          </svg>
                          Copy All
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setCanvasContent("");
                        setCanvasSections([]);
                      }}
                      className="p-1 text-zinc-500 hover:text-zinc-300 transition"
                      title="Clear canvas"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Canvas body */}
                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
                  {/* Format/platform indicator */}
                  <div className="flex items-center gap-2 mb-2">
                    {platforms.map((pid) => {
                      const p = PLATFORMS.find((pl) => pl.id === pid);
                      return (
                        <span
                          key={pid}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20"
                        >
                          {p?.icon} {p?.label} format
                        </span>
                      );
                    })}
                  </div>

                  {canvasSections.map((section, i) => (
                    <CanvasSection
                      key={i}
                      index={i}
                      title={section.title}
                      body={section.body}
                      onEdit={editCanvasSection}
                      copiedKey={copiedKey}
                      onCopy={(text, key) => copyToClipboard(text, setCopiedKey, key)}
                    />
                  ))}
                </div>
              </>
            ) : (
              /* Empty canvas state */
              <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
                <div className="w-20 h-20 rounded-2xl bg-zinc-900 border border-zinc-800/50 border-dashed flex items-center justify-center mb-4">
                  <svg className="w-8 h-8 text-zinc-700" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-zinc-300 mb-1">Your content canvas</h3>
                <p className="text-xs text-zinc-500 max-w-xs leading-relaxed">
                  Start chatting with the AI on the left. Generated content will automatically
                  appear here for editing, copying, and exporting.
                </p>
                <div className="flex items-center gap-4 mt-6 text-[10px] text-zinc-600">
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
                    </svg>
                    Click to edit
                  </div>
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                    </svg>
                    Copy sections
                  </div>
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                    </svg>
                    Pin from chat
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
