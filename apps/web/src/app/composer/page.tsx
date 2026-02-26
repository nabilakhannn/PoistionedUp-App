"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useBrand } from "@/lib/brand-context";
import { trackEvent } from "@/lib/posthog";
import {
  composerApi,
  countLinkedInChars,
  countWords,
  estimateReadTime,
  LINKEDIN_CHAR_LIMIT,
} from "@/lib/api/composer";

// ── Constants ─────────────────────────────────────────

const PLATFORM_CONFIG = {
  linkedin: {
    label: "LinkedIn",
    charLimit: 3000,
    color: "blue",
    placeholder: "Write your LinkedIn post...\n\nTip: Start with a strong hook to stop the scroll.",
  },
  twitter: {
    label: "X (Twitter)",
    charLimit: 280,
    color: "sky",
    placeholder: "Write your tweet...",
  },
} as const;

type Platform = keyof typeof PLATFORM_CONFIG;

// ── LinkedIn Preview Component ────────────────────────

function LinkedInPreview({
  body,
  authorName,
  viewMode,
}: {
  body: string;
  authorName: string;
  viewMode: "mobile" | "desktop";
}) {
  const [expanded, setExpanded] = useState(false);
  const lines = body.split("\n");
  const shouldTruncate = lines.length > 5 || body.length > 300;
  const displayText = !expanded && shouldTruncate ? lines.slice(0, 3).join("\n") : body;

  return (
    <div
      className={`bg-white rounded-lg shadow-sm border border-gray-200 ${
        viewMode === "mobile" ? "max-w-[375px]" : "max-w-[555px]"
      }`}
    >
      {/* Author header */}
      <div className="flex items-start gap-3 p-4 pb-2">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center flex-shrink-0">
          <span className="text-white font-bold text-lg">
            {authorName.charAt(0).toUpperCase()}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 leading-tight">
            {authorName || "Your Name"}
          </p>
          <p className="text-xs text-gray-500 leading-tight mt-0.5">
            Your headline here
          </p>
          <p className="text-xs text-gray-400 leading-tight mt-0.5">Just now</p>
        </div>
      </div>

      {/* Post body */}
      <div className="px-4 pb-2">
        <div className="text-sm text-gray-900 whitespace-pre-wrap leading-relaxed">
          {displayText || (
            <span className="text-gray-400 italic">Start typing to see preview</span>
          )}
          {!expanded && shouldTruncate && (
            <button
              onClick={() => setExpanded(true)}
              className="text-gray-500 hover:text-gray-700 font-medium ml-1"
            >
              ...see more
            </button>
          )}
        </div>
      </div>

      {/* Engagement bar */}
      <div className="px-4 pb-2">
        <div className="flex items-center gap-1 text-xs text-gray-500 py-2">
          <span className="inline-flex items-center gap-0.5">
            <span className="w-4 h-4 rounded-full bg-primary flex items-center justify-center">
              <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
              </svg>
            </span>
          </span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="border-t border-gray-200 px-4 py-2 flex justify-around">
        {["Like", "Comment", "Repost", "Send"].map((action) => (
          <button
            key={action}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-md transition"
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Formatting Toolbar ─────────────────────────────────

function FormattingToolbar({
  onFormat,
}: {
  onFormat: (type: "bold" | "italic" | "list" | "numbered" | "emoji") => void;
}) {
  return (
    <div className="flex items-center gap-1 py-2 px-1 border-b border-border">
      <button
        onClick={() => onFormat("bold")}
        className="px-2.5 py-1.5 text-sm font-bold text-foreground hover:bg-accent rounded transition"
        title="Bold (**text**)"
      >
        B
      </button>
      <button
        onClick={() => onFormat("italic")}
        className="px-2.5 py-1.5 text-sm italic text-foreground hover:bg-accent rounded transition"
        title="Italic"
      >
        I
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={() => onFormat("list")}
        className="px-2.5 py-1.5 text-sm text-foreground hover:bg-accent rounded transition"
        title="Bullet list"
      >
        &bull;
      </button>
      <button
        onClick={() => onFormat("numbered")}
        className="px-2.5 py-1.5 text-sm text-foreground hover:bg-accent rounded transition"
        title="Numbered list"
      >
        1.
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={() => onFormat("emoji")}
        className="px-2 py-1.5 text-sm text-foreground hover:bg-accent rounded transition"
        title="Add emoji"
      >
        :)
      </button>
    </div>
  );
}

// ── Schedule Modal ──────────────────────────────────────

function ScheduleModal({
  onClose,
  onSchedule,
}: {
  onClose: () => void;
  onSchedule: (dateTime: string) => void;
}) {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("09:00");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!date) return;
    const isoDate = new Date(`${date}T${time}`).toISOString();
    onSchedule(isoDate);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-popover border border-border rounded-xl shadow-xl max-w-sm w-full p-6">
        <h3 className="text-lg font-semibold text-card-foreground mb-4">Schedule Post</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-sm text-card-foreground focus:ring-2 focus:ring-ring"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Time</label>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-sm text-card-foreground focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!date}
              className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg disabled:opacity-50 transition"
            >
              Schedule
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── AI Generate Modal ───────────────────────────────────

function AIGenerateModal({
  onClose,
  onGenerated,
  platform,
  brandId,
}: {
  onClose: () => void;
  onGenerated: (text: string) => void;
  platform: Platform;
  brandId?: string;
}) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await composerApi.generateContent(
        `Write a ${platform === "linkedin" ? "LinkedIn" : "Twitter/X"} post about: ${prompt}. Return ONLY the post text, no explanations.`,
        brandId,
        { platform }
      );
      const lastMsg = result.messages?.filter((m) => m.role === "assistant").pop();
      if (lastMsg?.content) {
        onGenerated(lastMsg.content);
        onClose();
      } else {
        setError("No content generated. Try a different prompt.");
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-popover border border-border rounded-xl shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-card-foreground mb-1">AI Generate</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Describe what you want to post about. The AI will use your brand voice.
        </p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          placeholder="e.g., Share 3 lessons I learned about building a personal brand on LinkedIn"
          className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring resize-none mb-4"
          autoFocus
        />
        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="px-4 py-2 text-sm font-medium text-primary-foreground bg-chart-2 hover:bg-chart-2/90 rounded-lg disabled:opacity-50 transition flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating...
              </>
            ) : (
              "Generate"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Composer Page ──────────────────────────────────

export default function ComposerPage() {
  const { brandId, currentBrand } = useBrand();

  // Editor state
  const [platform, setPlatform] = useState<Platform>("linkedin");
  const [body, setBody] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // UI state
  const [viewMode, setViewMode] = useState<"mobile" | "desktop">("mobile");
  const [saving, setSaving] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [error, setError] = useState("");
  const [draftId, setDraftId] = useState<string | null>(null);

  // Computed values
  const config = PLATFORM_CONFIG[platform];
  const charCount = countLinkedInChars(body);
  const words = countWords(body);
  const readTime = estimateReadTime(body);
  const overLimit = charCount > config.charLimit;
  const authorName = currentBrand?.name || "Your Name";

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.max(ta.scrollHeight, 300)}px`;
    }
  }, [body]);

  // Formatting helpers
  const applyFormat = useCallback(
    (type: "bold" | "italic" | "list" | "numbered" | "emoji") => {
      const ta = textareaRef.current;
      if (!ta) return;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const selected = body.slice(start, end);

      let insert = "";
      switch (type) {
        case "bold":
          insert = `**${selected || "bold text"}**`;
          break;
        case "italic":
          insert = `_${selected || "italic text"}_`;
          break;
        case "list":
          insert = selected
            ? selected.split("\n").map((l) => `\u2022 ${l}`).join("\n")
            : "\u2022 ";
          break;
        case "numbered":
          insert = selected
            ? selected.split("\n").map((l, i) => `${i + 1}. ${l}`).join("\n")
            : "1. ";
          break;
        case "emoji":
          insert = selected + "\u{1F4A1}";
          break;
      }

      const newBody = body.slice(0, start) + insert + body.slice(end);
      setBody(newBody);
      setTimeout(() => {
        ta.focus();
        ta.selectionStart = ta.selectionEnd = start + insert.length;
      }, 0);
    },
    [body]
  );

  // Actions
  const handleSaveDraft = async () => {
    if (!body.trim()) return;
    setSaving(true);
    setError("");
    try {
      const draft = { platform, body, images, brand_id: brandId || undefined };
      if (draftId) {
        await composerApi.updateDraft(draftId, draft);
      } else {
        const result = await composerApi.saveDraft(draft);
        setDraftId(result.id);
      }
      setSuccessMsg("Draft saved!");
      trackEvent("composer_draft_saved", { platform });
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSchedule = async (dateTime: string) => {
    if (!body.trim()) return;
    setScheduling(true);
    setError("");
    try {
      await composerApi.schedule(
        { platform, body, images, brand_id: brandId || undefined },
        dateTime
      );
      setSuccessMsg("Post scheduled!");
      trackEvent("composer_scheduled", { platform });
      setBody("");
      setDraftId(null);
      setShowScheduleModal(false);
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setScheduling(false);
    }
  };

  const handleAddToQueue = async () => {
    if (!body.trim()) return;
    setSaving(true);
    setError("");
    try {
      await composerApi.addToQueue({
        platform,
        body,
        images,
        brand_id: brandId || undefined,
      });
      setSuccessMsg("Added to queue!");
      trackEvent("composer_queued", { platform });
      setBody("");
      setDraftId(null);
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleClear = () => {
    if (body.trim() && !confirm("Clear the editor? Unsaved changes will be lost.")) return;
    setBody("");
    setImages([]);
    setDraftId(null);
    setError("");
    setSuccessMsg("");
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(body);
      setSuccessMsg("Copied to clipboard!");
      setTimeout(() => setSuccessMsg(""), 2000);
    } catch {
      setError("Failed to copy");
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-7xl mx-auto p-4 lg:p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-card-foreground">Composer</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Create, preview, and schedule your posts
            </p>
          </div>

          {/* Platform toggle */}
          <div className="flex bg-muted rounded-lg p-0.5">
            {(Object.keys(PLATFORM_CONFIG) as Platform[]).map((p) => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition ${
                  platform === p
                    ? "bg-primary/20 text-primary shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    platform === p ? "bg-primary" : "bg-muted-foreground/40"
                  }`}
                />
                {PLATFORM_CONFIG[p].label}
              </button>
            ))}
          </div>
        </div>

        {/* Success / Error banners */}
        {successMsg && (
          <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-2.5 rounded-lg mb-4 text-sm flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            {successMsg}
          </div>
        )}
        {error && (
          <div className="bg-destructive/10 border border-destructive/30 text-destructive px-4 py-2.5 rounded-lg mb-4 text-sm">
            {error}
            <button onClick={() => setError("")} className="ml-3 text-destructive hover:text-destructive/70">
              Dismiss
            </button>
          </div>
        )}

        {/* Main layout: Editor + Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ── LEFT: Editor ────────────────────────── */}
          <div className="space-y-4">
            {/* Draft label */}
            <div className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full bg-primary`} />
              <span className="text-sm font-medium text-foreground">
                {config.label} {draftId ? "Draft" : "New Post"}
              </span>
              {draftId && (
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                  Saved
                </span>
              )}
            </div>

            {/* Formatting toolbar */}
            <FormattingToolbar onFormat={applyFormat} />

            {/* Text editor */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder={config.placeholder}
                className="w-full min-h-[300px] px-4 py-3 bg-card border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent resize-none leading-relaxed"
                style={{ overflow: "hidden" }}
              />
            </div>

            {/* Character count + stats */}
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-4">
                <span className={overLimit ? "text-destructive font-medium" : "text-muted-foreground"}>
                  {charCount} / {config.charLimit}
                </span>
                <span className="text-border">|</span>
                <span className="text-muted-foreground">{words} words</span>
                {words > 0 && (
                  <>
                    <span className="text-border">|</span>
                    <span className="text-muted-foreground">~{readTime} min read</span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyToClipboard}
                  disabled={!body.trim()}
                  className="px-2.5 py-1 text-muted-foreground hover:text-foreground hover:bg-accent rounded transition disabled:opacity-30"
                  title="Copy to clipboard"
                >
                  Copy
                </button>
                <button
                  onClick={handleClear}
                  disabled={!body.trim()}
                  className="px-2.5 py-1 text-muted-foreground hover:text-destructive hover:bg-accent rounded transition disabled:opacity-30"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* AI Generate + Attachments */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setShowAIModal(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-chart-2/20 text-chart-2 border border-chart-2/30 rounded-lg text-sm font-medium hover:bg-chart-2/30 transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                </svg>
                AI Generate
              </button>
              <button
                className="flex items-center gap-1.5 px-3 py-2 bg-accent text-muted-foreground border border-border rounded-lg text-sm font-medium hover:bg-muted transition"
                title="Coming soon"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5a2.25 2.25 0 0 0 2.25-2.25V5.25a2.25 2.25 0 0 0-2.25-2.25H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                </svg>
                Attach Images
              </button>
              <button
                className="flex items-center gap-1.5 px-3 py-2 bg-accent text-muted-foreground border border-border rounded-lg text-sm font-medium hover:bg-muted transition"
                title="Coming soon"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
                Attach PDF
              </button>
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-border">
              <button
                onClick={handleSaveDraft}
                disabled={saving || !body.trim()}
                className="px-5 py-2.5 text-sm font-medium text-foreground bg-accent border border-border rounded-lg hover:bg-muted disabled:opacity-50 transition"
              >
                {saving ? "Saving..." : "Save Draft"}
              </button>
              <button
                onClick={handleAddToQueue}
                disabled={saving || !body.trim() || overLimit}
                className="px-5 py-2.5 text-sm font-medium text-primary bg-primary/20 border border-primary/30 rounded-lg hover:bg-primary/30 disabled:opacity-50 transition"
              >
                Add to Queue
              </button>
              <button
                onClick={() => setShowScheduleModal(true)}
                disabled={!body.trim() || overLimit}
                className="px-5 py-2.5 text-sm font-medium text-foreground bg-accent border border-border rounded-lg hover:bg-muted disabled:opacity-50 transition"
              >
                Schedule For...
              </button>
            </div>
          </div>

          {/* ── RIGHT: Preview ───────────────────────── */}
          <div className="space-y-4">
            {/* View mode toggle */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Preview</span>
              <div className="flex bg-muted rounded-lg p-0.5">
                <button
                  onClick={() => setViewMode("mobile")}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    viewMode === "mobile"
                      ? "bg-accent text-card-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Mobile
                </button>
                <button
                  onClick={() => setViewMode("desktop")}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                    viewMode === "desktop"
                      ? "bg-accent text-card-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Desktop
                </button>
              </div>
            </div>

            {/* Preview card */}
            <div className="bg-card border border-border rounded-xl p-6 flex justify-center min-h-[400px]">
              <LinkedInPreview
                body={body}
                authorName={authorName}
                viewMode={viewMode}
              />
            </div>

            {/* Writing tips */}
            <div className="bg-card/50 border border-border rounded-xl p-4">
              <h3 className="text-sm font-medium text-foreground mb-2">
                {platform === "linkedin" ? "LinkedIn" : "X"} Tips
              </h3>
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                {platform === "linkedin" ? (
                  <>
                    <li>-- First line is your hook — make it stop the scroll</li>
                    <li>-- Use line breaks for readability (no wall of text)</li>
                    <li>-- Ask a question to drive comments</li>
                    <li>-- 1,200-1,500 chars performs best (you have {config.charLimit})</li>
                    <li>-- Posts with images get 2x engagement</li>
                  </>
                ) : (
                  <>
                    <li>-- Be concise — every word counts at 280 chars</li>
                    <li>-- Use a strong take or hot opinion</li>
                    <li>-- End with a question or CTA</li>
                    <li>-- Tweets with media get 3x engagement</li>
                  </>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Modals */}
        {showScheduleModal && (
          <ScheduleModal
            onClose={() => setShowScheduleModal(false)}
            onSchedule={handleSchedule}
          />
        )}
        {showAIModal && (
          <AIGenerateModal
            onClose={() => setShowAIModal(false)}
            onGenerated={(text) => setBody(text)}
            platform={platform}
            brandId={brandId || undefined}
          />
        )}
      </div>
    </div>
  );
}
