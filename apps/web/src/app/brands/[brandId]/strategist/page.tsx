"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { trackEvent } from "@/lib/posthog";
import { useBrand } from "@/lib/brand-context";
import {
  strategistApi,
  StrategistResponseItem,
  FieldCompleteness,
  StratOption,
} from "@/lib/api/strategist";
import { brandApi, PickerItem, pickerApi } from "@/lib/api";
import ResourcePicker from "@/components/resource-picker";
import {
  ResponseRenderer,
  FeedbackButtons,
} from "./components/response-renderers";
import { CompletenessSidebar } from "./components/completeness-sidebar";
import { CustomInstructionsPanel } from "./components/custom-instructions";

// ── Types ────────────────────────────────────────────────

interface ChatTurn {
  role: "user" | "assistant";
  content: string; // Raw text for user, JSON string for assistant
  parsed?: StrategistResponseItem[]; // Parsed structured responses (assistant only)
}

// ── Helpers ──────────────────────────────────────────────

/**
 * Parse a raw assistant message content string into structured responses.
 * Mirrors the backend parse_strategist_response logic.
 */
function parseAssistantContent(content: string): StrategistResponseItem[] {
  let text = content.trim();

  // Strip markdown code fences
  if (text.startsWith("```")) {
    const firstNl = text.indexOf("\n");
    if (firstNl > 0) text = text.slice(firstNl + 1);
    if (text.endsWith("```")) text = text.slice(0, -3).trim();
  }

  // Try direct JSON parse
  try {
    const data = JSON.parse(text);
    return extractResponses(data);
  } catch {
    // fall through
  }

  // Try finding JSON block in mixed text
  const jsonBlock = findJsonBlock(text);
  if (jsonBlock) {
    try {
      const data = JSON.parse(jsonBlock);
      return extractResponses(data);
    } catch {
      // fall through
    }
  }

  // Plain text fallback
  return [{ type: "message", message: content.trim() } as StrategistResponseItem];
}

function extractResponses(data: any): StrategistResponseItem[] {
  if (data && typeof data === "object" && "responses" in data && Array.isArray(data.responses)) {
    const valid = data.responses.filter((i: any) => i && typeof i === "object" && "type" in i);
    if (valid.length > 0) return valid;
  }
  if (data && typeof data === "object" && "type" in data) {
    return [data];
  }
  if (Array.isArray(data)) {
    const valid = data.filter((i: any) => i && typeof i === "object" && "type" in i);
    if (valid.length > 0) return valid;
  }
  // Legacy format
  if (data && typeof data === "object" && "reply" in data) {
    return [{ type: "message", message: data.reply } as StrategistResponseItem];
  }
  if (data && typeof data === "object" && "message" in data) {
    return [{ type: "message", message: data.message } as StrategistResponseItem];
  }
  return [{ type: "message", message: JSON.stringify(data) } as StrategistResponseItem];
}

function findJsonBlock(text: string): string | null {
  for (const [startChar, endChar] of [["{", "}"], ["[", "]"]]) {
    const startIdx = text.indexOf(startChar);
    if (startIdx === -1) continue;
    const endIdx = text.lastIndexOf(endChar);
    if (endIdx > startIdx) {
      const candidate = text.slice(startIdx, endIdx + 1);
      try {
        JSON.parse(candidate);
        return candidate;
      } catch {
        // not valid JSON
      }
    }
  }
  return null;
}

/**
 * Reconstruct ChatTurn[] from the raw messages array returned by the backend.
 */
function reconstructTurnsFromHistory(
  messages: { role: string; content: string }[]
): ChatTurn[] {
  return messages.map((msg) => {
    if (msg.role === "user") {
      return { role: "user" as const, content: msg.content };
    }
    // Assistant: parse content into structured responses
    const parsed = parseAssistantContent(msg.content);
    return {
      role: "assistant" as const,
      content: msg.content,
      parsed,
    };
  });
}

// ── Page ─────────────────────────────────────────────────

export default function StrategistPage() {
  const params = useParams();
  const brandId = params.brandId as string;
  const { selectBrand } = useBrand();

  // Chat state
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [chatId, setChatId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Completeness
  const [completeness, setCompleteness] = useState<FieldCompleteness | null>(
    null
  );
  const [completenessLoading, setCompletenessLoading] = useState(true);

  // Sidebar visibility (mobile)
  const [showSidebar, setShowSidebar] = useState(false);

  // Attachment state
  const [attachedText, setAttachedText] = useState("");
  const [attachedLabel, setAttachedLabel] = useState("");
  const [attachSourceType, setAttachSourceType] = useState("");
  const [attachedLink, setAttachedLink] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedPickerItem, setAttachedPickerItem] =
    useState<PickerItem | null>(null);
  const [attachUploading, setAttachUploading] = useState(false);
  const [showLinkInput, setShowLinkInput] = useState(false);
  const [linkInputValue, setLinkInputValue] = useState("");
  const [showPicker, setShowPicker] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Voice state
  const [isListening, setIsListening] = useState(false);
  const [micSupported, setMicSupported] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  // Pending interactive response (the last options/refinement from AI)
  const [pendingInteraction, setPendingInteraction] =
    useState<StrategistResponseItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Select brand on mount ──────────────────────────────

  useEffect(() => {
    if (brandId) {
      selectBrand(brandId);
    }
  }, [brandId, selectBrand]);

  // ── Load chat & completeness ───────────────────────────

  const loadCompleteness = useCallback(async () => {
    try {
      const data = await strategistApi.getCompleteness(brandId);
      setCompleteness(data);
    } catch (e) {
      console.error("[strategist] Failed to load completeness:", e);
    } finally {
      setCompletenessLoading(false);
    }
  }, [brandId]);

  const initChat = useCallback(async () => {
    setLoading(true);
    try {
      const data = await strategistApi.resume(brandId);
      setChatId(data.chat_id);
      setCompleteness(data.completeness);
      setCompletenessLoading(false);

      // If full history is available, reconstruct ALL turns
      if (data.history && data.history.length > 0) {
        const allTurns = reconstructTurnsFromHistory(data.history);
        setTurns(allTurns);

        // Find the last assistant turn and check for interactive responses
        const lastAssistant = [...allTurns].reverse().find((t) => t.role === "assistant");
        if (lastAssistant?.parsed) {
          const lastResponse = lastAssistant.parsed[lastAssistant.parsed.length - 1];
          if (
            lastResponse &&
            (lastResponse.type === "options" || lastResponse.type === "refinement")
          ) {
            setPendingInteraction(lastResponse);
          }
        }
      } else if (data.responses && data.responses.length > 0) {
        // Fallback: only the latest assistant response (legacy behavior)
        const assistantTurn: ChatTurn = {
          role: "assistant",
          content: JSON.stringify(data.responses),
          parsed: data.responses,
        };
        setTurns([assistantTurn]);

        const lastResponse = data.responses[data.responses.length - 1];
        if (
          lastResponse.type === "options" ||
          lastResponse.type === "refinement"
        ) {
          setPendingInteraction(lastResponse);
        }
      }
    } catch (e: any) {
      console.error("[strategist] Failed to init chat:", e);
      setError(e.message || "Failed to load strategist chat");
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => {
    initChat();
  }, [initChat]);

  // ── Web Speech API ─────────────────────────────────────

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setMicSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: any) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setInput(transcript);
    };

    recognition.onerror = (event: any) => {
      console.warn("[voice] Speech recognition error:", event.error);
      if (event.error === "not-allowed") {
        setError("Microphone access denied. Allow mic access in browser settings.");
      }
      setIsListening(false);
    };

    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    return () => recognition.abort();
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setError("");
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // ── Auto-scroll ────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, sending]);

  // ── File/Link/Picker handlers ──────────────────────────

  const removeAttachment = () => {
    setAttachedFile(null);
    setAttachedLink(null);
    setAttachedLabel("");
    setAttachedText("");
    setAttachSourceType("");
    setAttachedPickerItem(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("File too large. Maximum size is 10 MB.");
      return;
    }
    setAttachUploading(true);
    setError("");
    try {
      const result = await brandApi.uploadChatFile(file);
      setAttachedFile(file);
      setAttachedLink(null);
      setAttachedLabel(file.name);
      setAttachedText(result.text);
      setAttachSourceType(result.source_type);
      if (result.truncated) {
        setError("File was large, only the first portion was extracted.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to process file.");
      removeAttachment();
    } finally {
      setAttachUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleLinkSubmit = async () => {
    const url = linkInputValue.trim();
    if (!url) return;
    setAttachUploading(true);
    setError("");
    setShowLinkInput(false);
    try {
      const result = await brandApi.extractLink(url);
      setAttachedLink(url);
      setAttachedFile(null);
      setAttachedLabel(url);
      setAttachedText(result.text);
      setAttachSourceType(result.source_type);
      setLinkInputValue("");
    } catch (err: any) {
      setError(err.message || "Failed to extract content from link.");
      removeAttachment();
    } finally {
      setAttachUploading(false);
    }
  };

  const handlePickerSelect = async (item: PickerItem) => {
    setAttachedFile(null);
    setAttachedLink(item.source_url || null);
    setAttachedPickerItem(item);
    setAttachedLabel(item.title);
    setAttachSourceType(item.source);
    setShowPicker(false);
    try {
      const fullContent = await pickerApi.getContent(item.source, item.id);
      setAttachedText(fullContent.formatted_context);
    } catch {
      setAttachedText(item.content_preview || "");
      setError("Could not load full content. Preview text will be used.");
    }
  };

  // ── Send Message ───────────────────────────────────────

  const sendMessage = async (overrideText?: string) => {
    const text = overrideText || input.trim();
    if (!text || sending) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    const fileCtx = attachedText || undefined;
    const displayBadge = attachedLabel
      ? attachSourceType === "knowledge"
        ? `\n\n📗 ${attachedLabel}`
        : attachSourceType === "inspo"
        ? `\n\n💡 ${attachedLabel}`
        : attachedLink
        ? `\n\n🔗 ${attachedLink}`
        : attachedFile
        ? `\n\n📎 ${attachedFile.name}`
        : ""
      : "";

    setInput("");
    setSending(true);
    setError("");
    setPendingInteraction(null);

    const userTurn: ChatTurn = {
      role: "user",
      content: text + displayBadge,
    };
    setTurns((prev) => [...prev, userTurn]);
    removeAttachment();

    try {
      const response = await strategistApi.chat({
        brand_id: brandId,
        message: text,
        file_context: fileCtx,
      });

      setChatId(response.chat_id);
      setCompleteness(response.completeness);

      const assistantTurn: ChatTurn = {
        role: "assistant",
        content: JSON.stringify(response.responses),
        parsed: response.responses,
      };
      setTurns((prev) => [...prev, assistantTurn]);

      // Check for interactive responses
      const lastResp =
        response.responses[response.responses.length - 1];
      if (
        lastResp &&
        (lastResp.type === "options" || lastResp.type === "refinement")
      ) {
        setPendingInteraction(lastResp);
      }

      trackEvent("strategist_message", {
        brand_id: brandId,
        response_types: response.responses.map((r) => r.type),
        overall_percent: response.completeness?.overall_percent,
      });
    } catch (e: any) {
      setError(e.message || "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  // ── Option/Refinement handlers ─────────────────────────

  const handleSelectOption = (option: StratOption) => {
    sendMessage(`I choose Option ${option.id}: ${option.label}`);
  };

  const handleCustomWrite = () => {
    // Focus the input and let user type
    setPendingInteraction(null);
  };

  const handleSkip = () => {
    sendMessage("Skip this question for now.");
  };

  const handleConfirmRefinement = () => {
    sendMessage("Keep this. Save it.");
  };

  const handleEditRefinement = (text: string) => {
    sendMessage(`Here is my edited version: ${text}`);
  };

  // ── New Chat ───────────────────────────────────────────

  const handleNewChat = async () => {
    try {
      setLoading(true);
      const data = await strategistApi.startNew(brandId);
      setChatId(data.chat_id);
      setCompleteness(data.completeness);
      setPendingInteraction(null);

      // Reconstruct turns from history if available
      if (data.history && data.history.length > 0) {
        const allTurns = reconstructTurnsFromHistory(data.history);
        setTurns(allTurns);

        const lastAssistant = [...allTurns].reverse().find((t) => t.role === "assistant");
        if (lastAssistant?.parsed) {
          const lastResponse = lastAssistant.parsed[lastAssistant.parsed.length - 1];
          if (
            lastResponse &&
            (lastResponse.type === "options" || lastResponse.type === "refinement")
          ) {
            setPendingInteraction(lastResponse);
          }
        }
      } else if (data.responses && data.responses.length > 0) {
        const assistantTurn: ChatTurn = {
          role: "assistant",
          content: JSON.stringify(data.responses),
          parsed: data.responses,
        };
        setTurns([assistantTurn]);

        const lastResponse = data.responses[data.responses.length - 1];
        if (
          lastResponse.type === "options" ||
          lastResponse.type === "refinement"
        ) {
          setPendingInteraction(lastResponse);
        }
      } else {
        setTurns([]);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Key handling ───────────────────────────────────────

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Render ─────────────────────────────────────────────

  if (loading) {
    return (
      <main className="flex h-screen bg-background">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-muted-foreground">Loading your brand strategist...</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex h-screen bg-background">
      {/* ── Right sidebar: completeness (desktop) ───────── */}
      <div
        className={`w-64 border-l border-border bg-card overflow-y-auto order-last ${
          showSidebar ? "block" : "hidden lg:block"
        }`}
      >
        <div className="px-4 py-5 space-y-4">
          <CompletenessSidebar
            completeness={completeness}
            loading={completenessLoading}
          />
          <CustomInstructionsPanel brandId={brandId} />
        </div>
      </div>

      {/* ── Main chat area ────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-border px-6 py-3 flex items-center justify-between bg-card">
          <div className="flex items-center gap-3">
            <Link
              href={`/brands/${brandId}`}
              className="text-muted-foreground hover:text-foreground transition"
              title="Back to brand dashboard"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </Link>
            <div>
              <h1 className="text-base font-semibold text-card-foreground">
                Brand Strategist
              </h1>
              <p className="text-xs text-muted-foreground">
                Building your personal brand DNA
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Completeness badge */}
            {completeness && (
              <div className="hidden sm:flex items-center gap-2">
                <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      completeness.overall_percent >= 100
                        ? "bg-green-500"
                        : completeness.overall_percent >= 50
                        ? "bg-primary"
                        : "bg-muted-foreground"
                    }`}
                    style={{
                      width: `${Math.min(completeness.overall_percent, 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs text-muted-foreground">
                  {completeness.overall_percent}%
                </span>
              </div>
            )}

            {/* Mobile sidebar toggle */}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="lg:hidden px-3 py-1.5 border border-border text-muted-foreground rounded-lg text-xs font-medium hover:bg-accent transition"
            >
              {showSidebar ? "Hide progress" : "Progress"}
            </button>

            {/* New chat */}
            <button
              onClick={handleNewChat}
              className="px-3 py-1.5 border border-border text-muted-foreground rounded-lg text-xs font-medium hover:bg-accent hover:text-foreground transition flex items-center gap-1.5"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New
            </button>
          </div>
        </div>

        {/* ── Messages ────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-6">
          {turns.map((turn, turnIdx) => {
            const isUser = turn.role === "user";
            const isLastAssistant =
              !isUser && turnIdx === turns.length - 1;

            return (
              <div
                key={turnIdx}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[75%] ${
                    isUser
                      ? "bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-3"
                      : "space-y-4"
                  }`}
                >
                  {isUser ? (
                    <UserBubble content={turn.content} />
                  ) : (
                    <div className="space-y-3">
                      {(turn.parsed || []).map((resp, respIdx) => {
                        const parsedItems = turn.parsed || [];
                        const isLastResp =
                          isLastAssistant &&
                          respIdx === parsedItems.length - 1;
                        const isInteractive =
                          isLastResp &&
                          !sending &&
                          (resp.type === "options" ||
                            resp.type === "refinement");

                        return (
                          <div
                            key={respIdx}
                            className="group bg-card border border-border rounded-2xl rounded-bl-md px-4 py-4"
                          >
                            <ResponseRenderer
                              response={resp}
                              onSelectOption={handleSelectOption}
                              onCustomWrite={handleCustomWrite}
                              onSkip={handleSkip}
                              onConfirmRefinement={handleConfirmRefinement}
                              onEditRefinement={handleEditRefinement}
                              interactive={isInteractive}
                              disabled={sending}
                            />
                          </div>
                        );
                      })}
                      {/* Feedback buttons: once per turn, after all responses */}
                      {brandId && !isLastAssistant && (
                        <div className="group flex justify-start pl-2">
                          <FeedbackButtons
                            brandId={brandId}
                            chatId={chatId || undefined}
                            messageIndex={turnIdx}
                            originalResponse={
                              (turn.parsed || [])
                                .map((r) => r.message || "")
                                .join(" ")
                                .slice(0, 2000) || turn.content.slice(0, 2000)
                            }
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Sending indicator */}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-card border border-border px-4 py-3 rounded-2xl rounded-bl-md text-sm text-muted-foreground">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">·</span>
                  <span
                    className="animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  >
                    ·
                  </span>
                  <span
                    className="animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  >
                    ·
                  </span>
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Error ───────────────────────────────────────── */}
        {error && (
          <div className="px-6 py-2 text-red-400 text-sm bg-red-500/10 border-t border-red-500/20">
            {error}
          </div>
        )}

        {/* ── Input area ──────────────────────────────────── */}
        <div className="border-t border-border px-4 sm:px-6 py-4 bg-card">
          {/* Attachment preview */}
          {(attachedFile || attachedLink || attachedText) && (
            <AttachmentPreview
              label={attachedLabel}
              sourceType={attachSourceType}
              textLength={attachedText.length}
              onRemove={removeAttachment}
              pickerItem={attachedPickerItem}
            />
          )}
          {attachUploading && (
            <div className="flex items-center gap-2 mb-2 text-xs text-primary">
              <span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              {attachedLink ? "Extracting content..." : "Reading file..."}
            </div>
          )}

          {/* Link input bar */}
          {showLinkInput && (
            <div className="flex gap-2 mb-2">
              <input
                type="url"
                value={linkInputValue}
                onChange={(e) => setLinkInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleLinkSubmit();
                  }
                  if (e.key === "Escape") {
                    setShowLinkInput(false);
                    setLinkInputValue("");
                  }
                }}
                placeholder="Paste a URL (YouTube, website, Reddit, etc.)"
                className="flex-1 bg-muted border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                autoFocus
              />
              <button
                onClick={handleLinkSubmit}
                disabled={!linkInputValue.trim()}
                className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
              >
                Extract
              </button>
              <button
                onClick={() => {
                  setShowLinkInput(false);
                  setLinkInputValue("");
                }}
                className="px-2 py-2 text-muted-foreground hover:text-foreground transition"
              >
                ✕
              </button>
            </div>
          )}

          <div className="flex gap-2 items-end">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg,.gif,.webp"
              className="hidden"
              onChange={handleFileSelect}
            />

            {/* File button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={attachUploading || sending}
              title="Attach a file or image"
              className="w-9 h-9 rounded-lg flex items-center justify-center bg-muted text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50 transition flex-shrink-0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                />
              </svg>
            </button>

            {/* Link button */}
            <button
              onClick={() => setShowLinkInput(!showLinkInput)}
              disabled={attachUploading || sending}
              title="Attach a link"
              className={`w-9 h-9 rounded-lg flex items-center justify-center disabled:opacity-50 transition flex-shrink-0 ${
                showLinkInput
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                />
              </svg>
            </button>

            {/* Picker button */}
            <button
              onClick={() => setShowPicker(true)}
              disabled={attachUploading || sending}
              title="Attach from Knowledge or Inspo"
              className="w-9 h-9 rounded-lg flex items-center justify-center bg-muted text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50 transition flex-shrink-0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </button>

            {/* Text input */}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                pendingInteraction?.type === "options"
                  ? "Write your own answer or select an option above..."
                  : "Type your message..."
              }
              rows={2}
              className="flex-1 bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent placeholder:text-muted-foreground"
            />

            {/* Mic button */}
            {micSupported && (
              <button
                onClick={toggleListening}
                title={isListening ? "Stop recording" : "Speak"}
                className={`w-9 h-9 rounded-lg flex items-center justify-center transition flex-shrink-0 ${
                  isListening
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="w-4 h-4"
                >
                  {isListening ? (
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  ) : (
                    <path d="M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 0014 0h-2zm-4 7.93A7.001 7.001 0 0017 12h-2a5 5 0 01-10 0H3a7.001 7.001 0 006 6.93V22h2v-3.07z" />
                  )}
                </svg>
              </button>
            )}

            {/* Send button */}
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || sending}
              className="px-4 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition flex-shrink-0"
            >
              Send
            </button>
          </div>

          {isListening && (
            <div className="flex items-center gap-2 mt-2 text-xs text-red-400">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Listening... speak your answer, then hit Send
            </div>
          )}
        </div>
      </div>

      {/* Resource Picker Modal */}
      {showPicker && (
        <ResourcePicker
          isOpen={showPicker}
          brandId={brandId}
          onSelect={handlePickerSelect}
          onClose={() => setShowPicker(false)}
        />
      )}
    </main>
  );
}

// ── User Bubble ──────────────────────────────────────────

function UserBubble({ content }: { content: string }) {
  // Check for attachment badges
  const parts = content.split(/\n\n(📎|🔗|📗|💡) /);
  if (parts.length > 1) {
    const text = parts[0];
    const icon = parts[1];
    const label = parts[2] || "";
    const colorClass =
      icon === "📗"
        ? "bg-emerald-500/20 text-emerald-200"
        : icon === "💡"
        ? "bg-purple-500/20 text-purple-200"
        : "bg-primary/20 text-primary";

    return (
      <div className="text-sm leading-relaxed">
        <div>{text}</div>
        {label && (
          <div
            className={`flex items-center gap-1.5 mt-2 px-2 py-1 rounded text-xs ${colorClass}`}
          >
            <span>{icon}</span>
            <span className="truncate">{label}</span>
          </div>
        )}
      </div>
    );
  }

  return <div className="text-sm leading-relaxed">{content}</div>;
}

// ── Attachment Preview ───────────────────────────────────

function AttachmentPreview({
  label,
  sourceType,
  textLength,
  onRemove,
  pickerItem,
}: {
  label: string;
  sourceType: string;
  textLength: number;
  onRemove: () => void;
  pickerItem: PickerItem | null;
}) {
  const isKnowledge = sourceType === "knowledge";
  const isInspo = sourceType === "inspo";

  return (
    <div
      className={`flex items-center gap-2 mb-2 px-3 py-2 rounded-lg text-sm ${
        isKnowledge
          ? "bg-emerald-500/10 border border-emerald-500/20"
          : isInspo
          ? "bg-purple-500/10 border border-purple-500/20"
          : "bg-primary/10 border border-primary/20"
      }`}
    >
      <span className="text-xs">
        {isKnowledge ? "📗" : isInspo ? "💡" : "📎"}
      </span>
      <span
        className={`truncate flex-1 text-xs ${
          isKnowledge
            ? "text-emerald-400"
            : isInspo
            ? "text-purple-400"
            : "text-primary"
        }`}
      >
        {label}
      </span>
      {pickerItem?.is_gold && (
        <span className="text-yellow-400 text-xs bg-yellow-500/10 px-1.5 py-0.5 rounded">
          Gold
        </span>
      )}
      <span className="text-muted-foreground text-xs">
        {textLength > 0 ? `${Math.round(textLength / 1000)}k chars` : "..."}
      </span>
      <button
        onClick={onRemove}
        className="text-muted-foreground hover:text-red-400 transition"
        title="Remove"
      >
        ✕
      </button>
    </div>
  );
}
