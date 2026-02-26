"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { trackEvent } from "@/lib/posthog";
import { brandApi, ChatMessage, ChatSummary, PickerItem, pickerApi } from "../../../../../lib/api";
import { useBrand } from "@/lib/brand-context";
import ResourcePicker from "@/components/resource-picker";

/* ── Brand building stages ────────────────────────────────── */

interface BrandStage {
  key: string;
  label: string;
  shortDesc: string;
}

const STAGES: BrandStage[] = [
  {
    key: "foundation",
    label: "Foundation",
    shortDesc: "Beliefs, IT factor, stories",
  },
  {
    key: "ica",
    label: "Ideal Client",
    shortDesc: "Who you serve & their pains",
  },
  {
    key: "offer",
    label: "Your Offer",
    shortDesc: "What you sell & why it works",
  },
  {
    key: "brand",
    label: "Brand Statement",
    shortDesc: "Positioning & content pillars",
  },
  {
    key: "authority",
    label: "Authority Building",
    shortDesc: "Credentials, proof & media",
  },
  {
    key: "messaging",
    label: "Messaging",
    shortDesc: "Key phrases & talking points",
  },
  {
    key: "positioning",
    label: "Positioning",
    shortDesc: "Market position & category",
  },
  {
    key: "competitors",
    label: "Competitors",
    shortDesc: "Differentiation & white space",
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
  const brandId = params.brandId as string;
  const module = params.module as string;
  const label = MODULE_LABELS[module] || module;

  const { selectBrand } = useBrand();

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
  const [showPicker, setShowPicker] = useState(false);
  const [attachedPickerItem, setAttachedPickerItem] = useState<PickerItem | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Select brand on mount
  useEffect(() => {
    if (brandId) {
      selectBrand(brandId);
    }
  }, [brandId, selectBrand]);

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
        setError(
          "Microphone access denied. Please allow mic access in your browser settings."
        );
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
    setAttachedPickerItem(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /* ── Resource picker handler ────────────────────────────────── */
  const handlePickerSelect = async (item: PickerItem) => {
    setAttachedFile(null);
    setAttachedLink(item.source_url || null);
    setAttachedPickerItem(item);
    setAttachedLabel(item.title);
    setAttachSourceType(item.source);
    setShowPicker(false);

    // Fetch full content from the backend (search results only have previews)
    try {
      const fullContent = await pickerApi.getContent(item.source, item.id);
      setAttachedText(fullContent.formatted_context);
    } catch (err: any) {
      console.error("[handlePickerSelect] Failed to fetch full content:", err);
      // Fall back to the preview text
      setAttachedText(item.content_preview || "");
      setError("Could not load full content. Preview text will be used.");
    }
  };

  // Load existing chat history + chat list (scoped to brand)
  useEffect(() => {
    brandApi
      .getChatHistory(module, undefined, brandId)
      .then((data) => {
        if (data.chat_id) {
          setChatId(data.chat_id);
          setMessages(data.messages);
          setExtracted(data.extracted);
        }
      })
      .catch((e) => setError(e.message));

    loadChatList();
  }, [module, brandId]);

  const loadChatList = () => {
    brandApi
      .listChats(module, brandId)
      .then((data) => setChatList(data.chats))
      .catch(() => {});
  };

  const handleNewChat = async () => {
    try {
      const data = await brandApi.startNewChat(module, brandId);
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
      const data = await brandApi.getChatHistory(module, targetChatId, brandId);
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
      if (targetChatId === chatId) {
        const data = await brandApi.getChatHistory(module, undefined, brandId);
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

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    const userMsg = input.trim();
    const fileCtx = attachedText || undefined;
    const fileLabel = attachedLabel || undefined;

    // Determine attachment type for correct badge storage
    let attType: "file" | "link" | "knowledge" | "inspo" | undefined;
    if (attachSourceType === "knowledge") attType = "knowledge";
    else if (attachSourceType === "inspo") attType = "inspo";
    else if (attachedLink) attType = "link";
    else if (attachedFile) attType = "file";

    setInput("");
    setSending(true);
    setError("");

    let badge = "";
    if (attachSourceType === "knowledge") {
      badge = `\n\n📗 ${attachedLabel}`;
    } else if (attachSourceType === "inspo") {
      badge = `\n\n💡 ${attachedLabel}`;
    } else if (attachedLink) {
      badge = `\n\n🔗 ${attachedLink}`;
    } else if (attachedFile) {
      badge = `\n\n📎 ${attachedFile.name}`;
    }
    const displayMsg = userMsg + badge;
    setMessages((prev) => [...prev, { role: "user", content: displayMsg }]);

    removeAttachment();

    try {
      const response = await brandApi.sendChat(
        module,
        userMsg,
        fileCtx,
        fileLabel,
        brandId,
        attType
      );
      setChatId(response.chat_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ]);
      setExtracted(response.extracted_so_far);
      setProgress(response.progress);
      trackEvent("brand_chat_message", {
        module,
        brand_id: brandId,
        has_attachment: !!attType,
        attachment_type: attType || "",
      });
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
      await brandApi.completeChat(module, brandId);
      trackEvent("brand_module_completed", { module, brand_id: brandId });
      router.push(`/brands/${brandId}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const currentStageIndex = STAGES.findIndex((s) => s.key === module);

  return (
    <main className="flex h-screen">
      {/* Left sidebar: Brand building stages */}
      <div className="w-56 border-r border-gray-200 bg-white flex flex-col hidden md:flex">
        <div className="px-4 pt-4 pb-2">
          <Link
            href={`/brands/${brandId}`}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <span>←</span> Brand Dashboard
          </Link>
          <h2 className="text-sm font-bold text-gray-800 mt-3 mb-1">
            Build Your Brand
          </h2>
          <p className="text-xs text-gray-400 leading-tight">
            Complete each stage to define your personal brand
          </p>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-1">
          {STAGES.map((stage, i) => {
            const isCurrent = stage.key === module;
            const isPast = i < currentStageIndex;
            const chatPath = `/brands/${brandId}/chat/${stage.key}`;

            return (
              <Link
                key={stage.key}
                href={chatPath}
                className={`block rounded-lg px-3 py-2.5 transition-all ${
                  isCurrent
                    ? "bg-primary/10 border border-primary/30"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      isCurrent
                        ? "bg-primary text-primary-foreground"
                        : isPast
                        ? "bg-green-500 text-white"
                        : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {isPast ? "✓" : i + 1}
                  </div>
                  <div className="min-w-0">
                    <div
                      className={`text-sm font-medium truncate ${
                        isCurrent ? "text-primary" : "text-gray-700"
                      }`}
                    >
                      {stage.label}
                    </div>
                    <div className="text-xs text-gray-400 truncate">
                      {stage.shortDesc}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400 space-y-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            Completed
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary inline-block" />
            In progress
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-gray-200 inline-block" />
            Not started
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-3 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="md:hidden flex items-center gap-1.5 text-xs text-gray-400">
              <span className="font-medium text-gray-700">
                Step {currentStageIndex + 1}/{STAGES.length}
              </span>
              ·
            </div>
            <div>
              <h1 className="text-lg font-semibold">{label}</h1>
              <p className="text-xs text-gray-400">
                Chat with AI to build your {label.toLowerCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-gray-500">
              {Math.round(progress * 100)}%
            </div>
            <button
              onClick={() => setShowExtracted(!showExtracted)}
              className="px-3 py-1.5 border border-gray-300 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50 transition lg:hidden"
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
        <div className="border-b border-gray-100 px-6 py-2 bg-gray-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowChatList(!showChatList)}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 transition"
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
                  d="M19 9l-7 7-7-7"
                />
              </svg>
              {chatList.length > 0
                ? `${chatList.length} chat${chatList.length !== 1 ? "s" : ""}`
                : "No chats yet"}
            </button>
            {chatId && (
              <span className="text-xs text-gray-400">
                ·{" "}
                {chatList.find((c) => c.chat_id === chatId)?.title ||
                  `Chat ${
                    chatList.findIndex((c) => c.chat_id === chatId) + 1 || ""
                  }`}
              </span>
            )}
          </div>
          <button
            onClick={handleNewChat}
            className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1 transition"
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
            New Chat
          </button>
        </div>

        {/* Chat list dropdown */}
        {showChatList && chatList.length > 0 && (
          <div className="border-b border-gray-200 bg-white px-6 py-3 max-h-48 overflow-y-auto">
            <div className="space-y-1">
              {chatList.map((chat, idx) => (
                <div
                  key={chat.chat_id}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition ${
                    chat.chat_id === chatId
                      ? "bg-primary/10 border border-primary/30"
                      : "hover:bg-gray-50"
                  }`}
                  onClick={() => handleSwitchChat(chat.chat_id)}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        chat.status === "active"
                          ? "bg-green-400"
                          : chat.status === "completed"
                          ? "bg-primary"
                          : "bg-gray-300"
                      }`}
                    />
                    <span className="truncate text-gray-700">
                      {chat.title || `Chat ${chatList.length - idx}`}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {chat.message_count} msg
                      {chat.message_count !== 1 ? "s" : ""}
                    </span>
                    {chat.status === "completed" && (
                      <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded flex-shrink-0">
                        saved
                      </span>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteChat(chat.chat_id);
                    }}
                    className="text-gray-300 hover:text-red-500 transition ml-2 flex-shrink-0"
                    title="Delete this chat"
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-white">
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
                    ? "bg-primary text-primary-foreground rounded-br-md"
                    : "bg-gray-50 text-gray-800 rounded-bl-md border border-gray-100"
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
              <div className="bg-gray-50 border border-gray-100 px-4 py-3 rounded-2xl rounded-bl-md text-sm text-gray-400">
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

        {error && (
          <div className="px-6 py-2 text-red-600 text-sm bg-red-50">
            {error}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 px-6 py-4 bg-white">
          {/* Attachment preview */}
          {(attachedFile || attachedLink || attachedText) && (
            <div className={`flex items-center gap-2 mb-2 px-3 py-2 rounded-lg text-sm ${
              attachSourceType === "knowledge"
                ? "bg-emerald-50 border border-emerald-200"
                : attachSourceType === "inspo"
                ? "bg-purple-50 border border-purple-200"
                : "bg-primary/10 border border-primary/20"
            }`}>
              {attachSourceType === "knowledge" ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-emerald-500 flex-shrink-0"
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
              ) : attachSourceType === "inspo" ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-purple-500 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              ) : attachedLink ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-primary flex-shrink-0"
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
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-4 h-4 text-primary flex-shrink-0"
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
              )}
              <span className={`truncate flex-1 ${
                attachSourceType === "knowledge"
                  ? "text-emerald-700"
                  : attachSourceType === "inspo"
                  ? "text-purple-700"
                  : "text-primary"
              }`}>
                {attachedLabel}
              </span>
              {attachSourceType === "knowledge" && (
                <span className="text-emerald-600 text-xs flex-shrink-0 bg-emerald-100 px-1.5 py-0.5 rounded font-medium">
                  Knowledge
                </span>
              )}
              {attachSourceType === "inspo" && (
                <span className="text-purple-600 text-xs flex-shrink-0 bg-purple-100 px-1.5 py-0.5 rounded font-medium">
                  Inspo
                </span>
              )}
              {attachSourceType && attachSourceType !== "knowledge" && attachSourceType !== "inspo" && (
                <span className="text-primary text-xs flex-shrink-0 bg-primary/10 px-1.5 py-0.5 rounded">
                  {attachSourceType.replace(/_/g, " ")}
                </span>
              )}
              {attachedPickerItem?.is_gold && (
                <span className="text-yellow-700 text-xs flex-shrink-0 bg-yellow-100 px-1.5 py-0.5 rounded font-medium">
                  Gold
                </span>
              )}
              {attachedPickerItem?.is_starred && (
                <span className="text-purple-600 text-xs flex-shrink-0 bg-purple-100 px-1.5 py-0.5 rounded font-medium">
                  Starred
                </span>
              )}
              {attachedPickerItem?.source_tag && (
                <span className="text-gray-500 text-xs flex-shrink-0 bg-gray-100 px-1.5 py-0.5 rounded">
                  {attachedPickerItem.source_tag}
                </span>
              )}
              <span className="text-gray-400 text-xs flex-shrink-0">
                {attachedText.length > 0
                  ? `${Math.round(attachedText.length / 1000)}k chars`
                  : "processing..."}
              </span>
              <button
                onClick={removeAttachment}
                className="text-primary hover:text-red-500 transition flex-shrink-0"
                title="Remove attachment"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}
          {attachUploading && (
            <div className="flex items-center gap-2 mb-2 text-xs text-primary">
              <span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              {attachedLink
                ? "Extracting content from link..."
                : "Reading file..."}
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
                className="flex-1 border border-primary/30 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
                className="px-2 py-2 text-gray-400 hover:text-gray-600 transition"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}

          <div className="flex gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg,.gif,.webp"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={attachUploading || sending}
              title="Attach a file or image"
              className="self-end w-10 h-10 rounded-full flex items-center justify-center transition-all bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 disabled:opacity-50"
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
                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                />
              </svg>
            </button>
            <button
              onClick={() => setShowLinkInput(!showLinkInput)}
              disabled={attachUploading || sending}
              title="Attach a link (YouTube, website, Reddit, etc.)"
              className={`self-end w-10 h-10 rounded-full flex items-center justify-center transition-all disabled:opacity-50 ${
                showLinkInput
                  ? "bg-primary/10 text-primary"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700"
              }`}
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
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                />
              </svg>
            </button>
            <button
              onClick={() => setShowPicker(true)}
              disabled={attachUploading || sending}
              title="Attach from Knowledge or Inspo"
              className="self-end w-10 h-10 rounded-full flex items-center justify-center transition-all bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700 disabled:opacity-50"
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
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                attachedFile || attachedLink || attachedPickerItem
                  ? `Add a note about ${attachedLabel}...`
                  : "Type your answer..."
              }
              rows={2}
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
            />
            {micSupported && (
              <button
                onClick={toggleListening}
                title={isListening ? "Stop recording" : "Speak your answer"}
                className={`self-end w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                  isListening
                    ? "bg-red-500 text-white animate-pulse"
                    : "bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700"
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
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition self-end"
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

      {/* Right sidebar: extracted data */}
      <div
        className={`w-72 border-l border-gray-200 bg-gray-50 overflow-y-auto ${
          showExtracted ? "block" : "hidden lg:block"
        }`}
      >
        <div className="px-4 py-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">
            Extracted Profile Data
          </h2>
          <p className="text-xs text-gray-400 mb-3">
            Fields auto-fill as you chat
          </p>

          <div className="w-full bg-gray-200 rounded-full h-1.5 mb-4">
            <div
              className="bg-primary h-1.5 rounded-full transition-all"
              style={{ width: `${progress * 100}%` }}
            />
          </div>

          {Object.keys(extracted).length === 0 ? (
            <p className="text-xs text-gray-400 italic">
              Answer questions and your profile will build itself here.
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(extracted).map(([key, value]) => (
                <div key={key} className="text-sm">
                  <div className="font-medium text-gray-500 text-xs uppercase tracking-wide mb-0.5">
                    {key.replace(/[._]/g, " ")}
                  </div>
                  <div className="text-gray-800 bg-white rounded px-2 py-1.5 border border-gray-200 text-xs leading-relaxed">
                    {typeof value === "object"
                      ? Array.isArray(value)
                        ? value.map((v, i) => (
                            <div key={i} className="flex items-start gap-1">
                              <span className="text-gray-400">•</span>
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

/* ── Render user messages with file attachment badge ──────── */

function UserMessage({ content }: { content: string }) {
  const fileParts = content.split(/\n\n📎 /);
  const linkParts = content.split(/\n\n🔗 /);
  const knowledgeParts = content.split(/\n\n📗 /);
  const inspoParts = content.split(/\n\n💡 /);

  if (fileParts.length > 1) {
    return (
      <div>
        <div>{fileParts[0]}</div>
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-primary/20 rounded text-xs text-primary">
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
              d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
            />
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
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-primary/20 rounded text-xs text-primary">
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
              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
            />
          </svg>
          {linkParts[1]}
        </div>
      </div>
    );
  }
  if (knowledgeParts.length > 1) {
    return (
      <div>
        <div>{knowledgeParts[0]}</div>
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-emerald-500/20 rounded text-xs text-emerald-100">
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
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
          {knowledgeParts[1]}
        </div>
      </div>
    );
  }
  if (inspoParts.length > 1) {
    return (
      <div>
        <div>{inspoParts[0]}</div>
        <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-100">
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          {inspoParts[1]}
        </div>
      </div>
    );
  }
  return <>{content}</>;
}

/* ── Format AI messages with bullets/paragraphs ──────────── */

function FormattedMessage({ content }: { content: string }) {
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

    if (!trimmed) {
      flushParagraph();
      return;
    }

    const bulletMatch = trimmed.match(/^[-•*]\s+(.+)/);
    if (bulletMatch) {
      flushParagraph();
      elements.push(
        <div key={`b-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-primary font-bold mt-0.5 text-xs">•</span>
          <span>{bulletMatch[1]}</span>
        </div>
      );
      return;
    }

    const numMatch = trimmed.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      flushParagraph();
      elements.push(
        <div key={`n-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-primary font-semibold text-xs min-w-[1rem]">
            {numMatch[1]}.
          </span>
          <span>{numMatch[2]}</span>
        </div>
      );
      return;
    }

    currentParagraph.push(trimmed);
  });

  flushParagraph();

  return <div>{elements}</div>;
}
