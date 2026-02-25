"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { brandApi, ChatMessage, ChatSummary } from "../../../../lib/api";

/* ── Brand building stages ────────────────────────────────── */

interface BrandStage {
  key: string;
  label: string;
  shortDesc: string;
  chatPath: string;
}

const STAGES: BrandStage[] = [
  {
    key: "foundation",
    label: "Foundation",
    shortDesc: "Beliefs, IT factor, stories",
    chatPath: "/brand/chat/foundation",
  },
  {
    key: "ica",
    label: "Ideal Client",
    shortDesc: "Who you serve & their pains",
    chatPath: "/brand/chat/ica",
  },
  {
    key: "offer",
    label: "Your Offer",
    shortDesc: "What you sell & why it works",
    chatPath: "/brand/chat/offer",
  },
  {
    key: "brand",
    label: "Brand Statement",
    shortDesc: "Positioning & content pillars",
    chatPath: "/brand/chat/brand",
  },
  {
    key: "authority",
    label: "Authority Building",
    shortDesc: "Credentials, proof & media",
    chatPath: "/brand/chat/authority",
  },
  {
    key: "messaging",
    label: "Messaging",
    shortDesc: "Key phrases & talking points",
    chatPath: "/brand/chat/messaging",
  },
  {
    key: "positioning",
    label: "Positioning",
    shortDesc: "Market position & category",
    chatPath: "/brand/chat/positioning",
  },
  {
    key: "competitors",
    label: "Competitors",
    shortDesc: "Differentiation & white space",
    chatPath: "/brand/chat/competitors",
  },
];

const MODULE_LABELS: Record<string, string> = {
  foundation: "Foundation",
  ica: "Ideal Client Avatar",
  offer: "Your Offer",
  brand: "Brand Statement",
  authority: "Authority Building",
  messaging: "Messaging",
  positioning: "Positioning",
  competitors: "Competitors",
};

export default function BrandChatPage() {
  const params = useParams();
  const router = useRouter();
  const module = params.module as string;
  const label = MODULE_LABELS[module] || module;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [extracted, setExtracted] = useState<Record<string, any>>({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [chatId, setChatId] = useState<string | null>(null);
  const [showExtracted, setShowExtracted] = useState(false);

  /* ── Chat list state ──────────────────────────────────────── */
  const [chatList, setChatList] = useState<ChatSummary[]>([]);
  const [showChatList, setShowChatList] = useState(false);

  /* ── Voice input state ──────────────────────────────────── */
  const [isListening, setIsListening] = useState(false);
  const [micSupported, setMicSupported] = useState(true);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  /* ── File/link attachment state ───────────────────────────── */
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedLink, setAttachedLink] = useState<string | null>(null);
  const [attachedLabel, setAttachedLabel] = useState("");
  const [attachedText, setAttachedText] = useState("");
  const [attachSourceType, setAttachSourceType] = useState("");
  const [attachUploading, setAttachUploading] = useState(false);
  const [showLinkInput, setShowLinkInput] = useState(false);
  const [linkInputValue, setLinkInputValue] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* ── Initialise Web Speech API ─────────────────────────── */
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
        setError("Microphone access denied. Please allow mic access in your browser settings.");
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
    };
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

  /* ── File/link attachment handlers ────────────────────────── */
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (10 MB)
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
        setError("File was large, so only the first portion was extracted.");
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
      if (result.truncated) {
        setError("Content was long, so only the first portion was extracted.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to extract content from link.");
      removeAttachment();
    } finally {
      setAttachUploading(false);
    }
  };

  const removeAttachment = () => {
    setAttachedFile(null);
    setAttachedLink(null);
    setAttachedLabel("");
    setAttachedText("");
    setAttachSourceType("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Load existing chat history + chat list
  useEffect(() => {
    // Load the most recent active chat
    brandApi
      .getChatHistory(module)
      .then((data) => {
        if (data.chat_id) {
          setChatId(data.chat_id);
          setMessages(data.messages);
          setExtracted(data.extracted);
        }
      })
      .catch((e) => setError(e.message));

    // Load all chats for this module
    loadChatList();
  }, [module]);

  const loadChatList = () => {
    brandApi
      .listChats(module)
      .then((data) => setChatList(data.chats))
      .catch(() => {}); // silent fail — list is non-critical
  };

  const handleNewChat = async () => {
    try {
      const data = await brandApi.startNewChat(module);
      if (data.chat_id) {
        setChatId(data.chat_id);
        setMessages(data.messages);
        setExtracted(data.extracted);
        setProgress(0);
        setError("");
        loadChatList();
        setShowChatList(false);
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSwitchChat = async (targetChatId: string) => {
    try {
      const data = await brandApi.getChatHistory(module, targetChatId);
      if (data.chat_id) {
        setChatId(data.chat_id);
        setMessages(data.messages);
        setExtracted(data.extracted);
        setProgress(0);
        setError("");
        setShowChatList(false);
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDeleteChat = async (targetChatId: string) => {
    try {
      await brandApi.deleteChat(targetChatId);
      // If we deleted the current chat, load the latest one
      if (targetChatId === chatId) {
        const data = await brandApi.getChatHistory(module);
        if (data.chat_id) {
          setChatId(data.chat_id);
          setMessages(data.messages);
          setExtracted(data.extracted);
        } else {
          setChatId(null);
          setMessages([]);
          setExtracted({});
        }
        setProgress(0);
      }
      loadChatList();
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;

    // Stop mic if still listening
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    const userMsg = input.trim();
    const fileCtx = attachedText || undefined;
    const label = attachedLabel || undefined;

    setInput("");
    setSending(true);
    setError("");

    // Build display badge
    let badge = "";
    if (attachedLink) {
      badge = `\n\n🔗 ${attachedLink}`;
    } else if (attachedFile) {
      badge = `\n\n📎 ${attachedFile.name}`;
    }
    const displayMsg = userMsg + badge;
    setMessages((prev) => [...prev, { role: "user", content: displayMsg }]);

    // Clear attachment after sending
    removeAttachment();

    try {
      const response = await brandApi.sendChat(module, userMsg, fileCtx, label);
      setChatId(response.chat_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ]);
      setExtracted(response.extracted_so_far);
      setProgress(response.progress);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleComplete = async () => {
    try {
      await brandApi.completeChat(module);
      const editPaths: Record<string, string> = {
        foundation: "/brand/foundation",
        ica: "/brand/ica",
        offer: "/brand/offer",
        brand: "/brand/strategy",
      };
      router.push(editPaths[module] || "/brand");
    } catch (e: any) {
      setError(e.message);
    }
  };

  const currentStageIndex = STAGES.findIndex((s) => s.key === module);

  return (
    <main className="flex h-screen">
      {/* Left sidebar: Brand building stages */}
      <div className="w-56 border-r border-zinc-800 bg-zinc-900 flex flex-col hidden md:flex">
        <div className="px-4 pt-4 pb-2">
          <Link
            href="/brand"
            className="text-xs text-blue-400 hover:underline flex items-center gap-1"
          >
            <span>←</span> Brand Dashboard
          </Link>
          <h2 className="text-sm font-bold text-zinc-200 mt-3 mb-1">
            Build Your Brand
          </h2>
          <p className="text-xs text-zinc-500 leading-tight">
            Complete each stage to define your personal brand
          </p>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-1">
          {STAGES.map((stage, i) => {
            const isCurrent = stage.key === module;
            const isPast = i < currentStageIndex;

            return (
              <Link
                key={stage.key}
                href={stage.chatPath}
                className={`block rounded-lg px-3 py-2.5 transition-all ${
                  isCurrent
                    ? "bg-blue-600/20 border border-blue-500/30"
                    : "hover:bg-zinc-800"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {/* Step indicator */}
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      isCurrent
                        ? "bg-blue-600 text-white"
                        : isPast
                        ? "bg-green-500 text-white"
                        : "bg-zinc-700 text-zinc-400"
                    }`}
                  >
                    {isPast ? "✓" : i + 1}
                  </div>
                  <div className="min-w-0">
                    <div
                      className={`text-sm font-medium truncate ${
                        isCurrent ? "text-blue-400" : "text-zinc-300"
                      }`}
                    >
                      {stage.label}
                    </div>
                    <div className="text-xs text-zinc-500 truncate">
                      {stage.shortDesc}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Stage legend */}
        <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500 space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            Completed
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" />
            In progress
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-zinc-700 inline-block" />
            Not started
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between bg-zinc-900">
          <div className="flex items-center gap-3">
            {/* Mobile: stage indicator */}
            <div className="md:hidden flex items-center gap-1.5 text-xs text-zinc-500">
              <span className="font-medium text-zinc-300">
                Step {currentStageIndex + 1}/4
              </span>
              ·
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-100">{label}</h1>
              <p className="text-xs text-zinc-500">
                Chat with AI to build your {label.toLowerCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-zinc-400">
              {Math.round(progress * 100)}%
            </div>
            <button
              onClick={() => setShowExtracted(!showExtracted)}
              className="px-3 py-1.5 border border-zinc-700 text-zinc-400 rounded-lg text-xs font-medium hover:bg-zinc-800 transition lg:hidden"
            >
              {showExtracted ? "Hide data" : "View data"}
            </button>
            <button
              onClick={handleComplete}
              disabled={messages.length < 4}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Done, review form
            </button>
          </div>
        </div>

        {/* Chat switcher bar */}
        <div className="border-b border-zinc-800 px-6 py-2 bg-zinc-900/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowChatList(!showChatList)}
              className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              {chatList.length > 0
                ? `${chatList.length} chat${chatList.length !== 1 ? "s" : ""}`
                : "No chats yet"}
            </button>
            {chatId && (
              <span className="text-xs text-zinc-500">
                · {chatList.find((c) => c.chat_id === chatId)?.title ||
                  `Chat ${chatList.findIndex((c) => c.chat_id === chatId) + 1 || ""}`}
              </span>
            )}
          </div>
          <button
            onClick={handleNewChat}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Chat list dropdown */}
        {showChatList && chatList.length > 0 && (
          <div className="border-b border-zinc-800 bg-zinc-900 px-6 py-3 max-h-48 overflow-y-auto">
            <div className="space-y-1">
              {chatList.map((chat, idx) => (
                <div
                  key={chat.chat_id}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition ${
                    chat.chat_id === chatId
                      ? "bg-blue-600/20 border border-blue-500/30"
                      : "hover:bg-zinc-800"
                  }`}
                  onClick={() => handleSwitchChat(chat.chat_id)}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        chat.status === "active"
                          ? "bg-green-400"
                          : chat.status === "completed"
                          ? "bg-blue-400"
                          : "bg-zinc-600"
                      }`}
                    />
                    <span className="truncate text-zinc-300">
                      {chat.title || `Chat ${chatList.length - idx}`}
                    </span>
                    <span className="text-xs text-zinc-500 flex-shrink-0">
                      {chat.message_count} msg{chat.message_count !== 1 ? "s" : ""}
                    </span>
                    {chat.status === "completed" && (
                      <span className="text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded flex-shrink-0">
                        saved
                      </span>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteChat(chat.chat_id);
                    }}
                    className="text-zinc-600 hover:text-red-400 transition ml-2 flex-shrink-0"
                    title="Delete this chat"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-zinc-950">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-md"
                    : "bg-zinc-800 text-zinc-200 rounded-bl-md border border-zinc-700"
                }`}
              >
                {msg.role === "assistant" ? (
                  <FormattedMessage content={msg.content} />
                ) : (
                  <UserMessage content={msg.content} />
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-zinc-800 border border-zinc-700 px-4 py-3 rounded-2xl rounded-bl-md text-sm text-zinc-400">
                <span className="inline-flex gap-1">
                  <span className="animate-bounce">·</span>
                  <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>·</span>
                  <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>·</span>
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div className="px-6 py-2 text-red-400 text-sm bg-red-500/10">
            {error}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-zinc-800 px-6 py-4 bg-zinc-900">
          {/* Attachment preview (file or link) */}
          {(attachedFile || attachedLink) && (
            <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm">
              {attachedLink ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              )}
              <span className="text-blue-300 truncate flex-1">{attachedLabel}</span>
              {attachSourceType && (
                <span className="text-blue-400 text-xs flex-shrink-0 bg-blue-500/20 px-1.5 py-0.5 rounded">
                  {attachSourceType.replace(/_/g, " ")}
                </span>
              )}
              <span className="text-blue-400 text-xs flex-shrink-0">
                {attachedText.length > 0
                  ? `${Math.round(attachedText.length / 1000)}k chars`
                  : "processing..."}
              </span>
              <button
                onClick={removeAttachment}
                className="text-blue-400 hover:text-red-500 transition flex-shrink-0"
                title="Remove attachment"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
          {attachUploading && (
            <div className="flex items-center gap-2 mb-2 text-xs text-blue-500">
              <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              {attachedLink ? "Extracting content from link..." : "Reading file..."}
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
                className="flex-1 border border-zinc-700 bg-zinc-800 text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-zinc-500"
                autoFocus
              />
              <button
                onClick={handleLinkSubmit}
                disabled={!linkInputValue.trim()}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                Extract
              </button>
              <button
                onClick={() => { setShowLinkInput(false); setLinkInputValue(""); }}
                className="px-2 py-2 text-zinc-500 hover:text-zinc-300 transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          <div className="flex gap-3">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg,.gif,.webp"
              className="hidden"
              onChange={handleFileSelect}
            />
            {/* Attach file button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={attachUploading || sending}
              title="Attach a file or image"
              className="self-end w-10 h-10 rounded-full flex items-center justify-center transition-all bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 disabled:opacity-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            {/* Attach link button */}
            <button
              onClick={() => setShowLinkInput(!showLinkInput)}
              disabled={attachUploading || sending}
              title="Attach a link (YouTube, website, Reddit, etc.)"
              className={`self-end w-10 h-10 rounded-full flex items-center justify-center transition-all disabled:opacity-50 ${
                showLinkInput
                  ? "bg-blue-500/20 text-blue-400"
                  : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                attachedFile || attachedLink
                  ? `Add a note about ${attachedLabel}...`
                  : "Type your answer..."
              }
              rows={2}
              className="flex-1 border border-zinc-700 bg-zinc-800 text-zinc-100 rounded-lg px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder:text-zinc-500"
            />
            {/* Mic button */}
            {micSupported && (
              <button
                onClick={toggleListening}
                title={isListening ? "Stop recording" : "Speak your answer"}
                className={`self-end w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                  isListening
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                }`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="w-5 h-5"
                >
                  {isListening ? (
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  ) : (
                    <path d="M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3zm5-3a5 5 0 01-10 0H5a7 7 0 0014 0h-2zm-4 7.93A7.001 7.001 0 0017 12h-2a5 5 0 01-10 0H3a7.001 7.001 0 006 6.93V22h2v-3.07z" />
                  )}
                </svg>
              </button>
            )}
            <button
              onClick={sendMessage}
              disabled={!input.trim() || sending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition self-end"
            >
              Send
            </button>
          </div>
          {isListening && (
            <div className="flex items-center gap-2 mt-2 text-xs text-red-500">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Listening... speak your answer, then hit Send
            </div>
          )}
        </div>
      </div>

      {/* Right sidebar: extracted data (desktop always, mobile toggle) */}
      <div
        className={`w-72 border-l border-zinc-800 bg-zinc-900 overflow-y-auto ${
          showExtracted ? "block" : "hidden lg:block"
        }`}
      >
        <div className="px-4 py-4">
          <h2 className="text-sm font-semibold text-zinc-200 mb-1">
            Extracted Profile Data
          </h2>
          <p className="text-xs text-zinc-500 mb-3">
            Fields auto-fill as you chat
          </p>

          {/* Progress bar */}
          <div className="w-full bg-zinc-800 rounded-full h-1.5 mb-4">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all"
              style={{ width: `${progress * 100}%` }}
            />
          </div>

          {/* Extracted fields */}
          {Object.keys(extracted).length === 0 ? (
            <p className="text-xs text-zinc-500 italic">
              Answer questions and your profile will build itself here.
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(extracted).map(([key, value]) => (
                <div key={key} className="text-sm">
                  <div className="font-medium text-zinc-500 text-xs uppercase tracking-wide mb-0.5">
                    {key.replace(/[._]/g, " ")}
                  </div>
                  <div className="text-zinc-200 bg-zinc-800 rounded px-2 py-1.5 border border-zinc-700 text-xs leading-relaxed">
                    {typeof value === "object"
                      ? Array.isArray(value)
                        ? value.map((v, i) => (
                            <div key={i} className="flex items-start gap-1">
                              <span className="text-zinc-500">•</span>
                              <span>{String(v)}</span>
                            </div>
                          ))
                        : JSON.stringify(value, null, 2)
                      : String(value)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

/* ── Render user messages with file attachment badge ──────── */

function UserMessage({ content }: { content: string }) {
  // Check if message contains a file or link attachment indicator
  const fileParts = content.split(/\n\n📎 /);
  const linkParts = content.split(/\n\n🔗 /);

  if (fileParts.length > 1) {
    return (
      <div>
        <div>{fileParts[0]}</div>
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-blue-500/20 rounded text-xs text-blue-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
          </svg>
          {fileParts[1]}
        </div>
      </div>
    );
  }
  if (linkParts.length > 1) {
    return (
      <div>
        <div>{linkParts[0]}</div>
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-blue-500/20 rounded text-xs text-blue-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          {linkParts[1]}
        </div>
      </div>
    );
  }
  return <>{content}</>;
}

/* ── Format AI messages with bullets/paragraphs ──────────── */

function FormattedMessage({ content }: { content: string }) {
  // Split into lines and render bullets, numbered lists, and paragraphs nicely
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let currentParagraph: string[] = [];

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      elements.push(
        <p key={`p-${elements.length}`} className="mb-2 last:mb-0">
          {currentParagraph.join(" ")}
        </p>
      );
      currentParagraph = [];
    }
  };

  lines.forEach((line, i) => {
    const trimmed = line.trim();

    // Empty line = paragraph break
    if (!trimmed) {
      flushParagraph();
      return;
    }

    // Bullet point: "- ", "• ", "* "
    const bulletMatch = trimmed.match(/^[-•*]\s+(.+)/);
    if (bulletMatch) {
      flushParagraph();
      elements.push(
        <div key={`b-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-blue-300 font-bold mt-0.5 text-xs">•</span>
          <span>{bulletMatch[1]}</span>
        </div>
      );
      return;
    }

    // Numbered list: "1. ", "2. " etc
    const numMatch = trimmed.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      flushParagraph();
      elements.push(
        <div key={`n-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-blue-400 font-semibold text-xs min-w-[1rem]">
            {numMatch[1]}.
          </span>
          <span>{numMatch[2]}</span>
        </div>
      );
      return;
    }

    // Regular text: accumulate into paragraph
    currentParagraph.push(trimmed);
  });

  flushParagraph();

  return <div>{elements}</div>;
}
