"use client";

import React, { useState } from "react";
import type {
  OptionsResponse,
  RefinementResponse,
  SaveResponse,
  MessageResponse,
  ContentResponse,
  StratOption,
  StrategistResponseItem,
} from "@/lib/api/strategist";
import { userTrainingApi } from "@/lib/api/training";

// ── Module Labels ────────────────────────────────────────

const MODULE_LABELS: Record<string, string> = {
  foundation: "Foundation",
  authority: "Authority",
  ica: "Ideal Client",
  positioning: "Positioning",
  voice: "Voice & Tone",
  offer: "Offer",
  content_pillars: "Content Pillars",
  competitive: "Competitive",
};

function moduleLabel(mod: string): string {
  return MODULE_LABELS[mod] || mod.replace(/_/g, " ");
}

function fieldLabel(field: string): string {
  return field
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Option Card ──────────────────────────────────────────

interface OptionCardProps {
  option: StratOption;
  selected: boolean;
  onSelect: (option: StratOption) => void;
  disabled: boolean;
}

function OptionCard({ option, selected, onSelect, disabled }: OptionCardProps) {
  return (
    <button
      onClick={() => onSelect(option)}
      disabled={disabled}
      className={`w-full text-left rounded-xl border-2 p-4 transition-all ${
        selected
          ? "border-blue-500 bg-blue-500/10 ring-1 ring-blue-500/30"
          : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-500 hover:bg-zinc-800"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
            selected
              ? "bg-blue-500 text-white"
              : "bg-zinc-700 text-zinc-300"
          }`}
        >
          {option.id}
        </div>
        <div className="min-w-0 flex-1">
          <div
            className={`text-sm font-semibold mb-1 ${
              selected ? "text-blue-400" : "text-zinc-200"
            }`}
          >
            {option.label}
          </div>
          <div className="text-sm text-zinc-400 leading-relaxed">
            {option.text}
          </div>
        </div>
      </div>
    </button>
  );
}

// ── Options Block ────────────────────────────────────────

interface OptionsBlockProps {
  data: OptionsResponse;
  onSelectOption: (option: StratOption) => void;
  onCustomWrite: () => void;
  onSkip: () => void;
  disabled: boolean;
}

export function OptionsBlock({
  data,
  onSelectOption,
  onCustomWrite,
  onSkip,
  disabled,
}: OptionsBlockProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (option: StratOption) => {
    setSelectedId(option.id);
    onSelectOption(option);
  };

  return (
    <div className="space-y-4">
      {/* Module/field badge */}
      {data.module && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
            {moduleLabel(data.module)}
          </span>
          <span className="text-xs text-zinc-500">
            {fieldLabel(data.field)}
          </span>
        </div>
      )}

      {/* Coaching message */}
      <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
        {data.message}
      </div>

      {/* Option cards */}
      {data.options && data.options.length > 0 && (
        <div className="space-y-3">
          {data.options.map((opt) => (
            <OptionCard
              key={opt.id}
              option={opt}
              selected={selectedId === opt.id}
              onSelect={handleSelect}
              disabled={disabled}
            />
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        {data.allow_custom && (
          <button
            onClick={onCustomWrite}
            disabled={disabled}
            className="text-sm text-zinc-400 hover:text-zinc-200 underline underline-offset-2 transition disabled:opacity-50"
          >
            Write my own
          </button>
        )}
        {data.allow_skip && (
          <button
            onClick={onSkip}
            disabled={disabled}
            className="text-sm text-zinc-500 hover:text-zinc-300 underline underline-offset-2 transition disabled:opacity-50"
          >
            Skip for now
          </button>
        )}
      </div>
    </div>
  );
}

// ── Refinement Block ─────────────────────────────────────

interface RefinementBlockProps {
  data: RefinementResponse;
  onConfirm: () => void;
  onEdit: (text: string) => void;
  disabled: boolean;
}

export function RefinementBlock({
  data,
  onConfirm,
  onEdit,
  disabled,
}: RefinementBlockProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(data.refined_text);

  return (
    <div className="space-y-4">
      {/* Module/field badge */}
      {data.module && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
            {moduleLabel(data.module)}
          </span>
          <span className="text-xs text-zinc-500">
            {fieldLabel(data.field)}
          </span>
        </div>
      )}

      {/* Coaching message */}
      <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
        {data.message}
      </div>

      {/* Refined text */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
        <div className="text-xs font-medium text-amber-400 mb-2 uppercase tracking-wide">
          Refined Version
        </div>
        {editing ? (
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={4}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 resize-none focus:outline-none focus:ring-2 focus:ring-amber-500/50"
          />
        ) : (
          <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {data.refined_text}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        {editing ? (
          <>
            <button
              onClick={() => {
                onEdit(editText);
                setEditing(false);
              }}
              disabled={disabled || !editText.trim()}
              className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-500 disabled:opacity-50 transition"
            >
              Submit Edit
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setEditText(data.refined_text);
              }}
              className="px-4 py-2 text-zinc-400 hover:text-zinc-200 text-sm transition"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            {data.actions.includes("confirm") && (
              <button
                onClick={onConfirm}
                disabled={disabled}
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-500 disabled:opacity-50 transition flex items-center gap-2"
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
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Keep this
              </button>
            )}
            {data.actions.includes("edit") && (
              <button
                onClick={() => setEditing(true)}
                disabled={disabled}
                className="px-4 py-2 border border-zinc-600 text-zinc-300 rounded-lg text-sm font-medium hover:bg-zinc-800 disabled:opacity-50 transition"
              >
                Tweak it
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Save Block ───────────────────────────────────────────

interface SaveBlockProps {
  data: SaveResponse;
}

export function SaveBlock({ data }: SaveBlockProps) {
  return (
    <div className="space-y-3">
      {/* Save confirmation badge */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 text-xs font-medium text-green-400 bg-green-500/10 px-2.5 py-1 rounded-full">
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
              d="M5 13l4 4L19 7"
            />
          </svg>
          Saved to {moduleLabel(data.module)}
        </div>
        <span className="text-xs text-zinc-500">{fieldLabel(data.field)}</span>
      </div>

      {/* Message */}
      {data.message && (
        <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
          {data.message}
        </div>
      )}

      {/* Completeness update */}
      {data.completeness && (
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span>{data.completeness.module_name}: {data.completeness.module_percent}%</span>
          <span className="text-zinc-600">|</span>
          <span>Overall: {data.completeness.overall_percent}%</span>
        </div>
      )}
    </div>
  );
}

// ── Message Block ────────────────────────────────────────

interface MessageBlockProps {
  data: MessageResponse;
}

export function MessageBlock({ data }: MessageBlockProps) {
  return (
    <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
      <FormattedText text={data.message} />
    </div>
  );
}

// ── Content Block ────────────────────────────────────────

interface ContentBlockProps {
  data: ContentResponse;
}

export function ContentBlock({ data }: ContentBlockProps) {
  const [copied, setCopied] = useState(false);

  const fullContent = [data.hook, data.body, data.cta]
    .filter(Boolean)
    .join("\n\n");

  const handleCopy = async () => {
    await navigator.clipboard.writeText(fullContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Content type badge */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">
          {data.content_type.replace(/_/g, " ")}
        </span>
        <span className="text-xs text-zinc-500">{data.platform}</span>
        {data.pillar && (
          <>
            <span className="text-zinc-600">|</span>
            <span className="text-xs text-zinc-500">{data.pillar}</span>
          </>
        )}
      </div>

      {/* Coaching message */}
      {data.message && (
        <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
          {data.message}
        </div>
      )}

      {/* Content preview */}
      <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 overflow-hidden">
        {/* Hook */}
        {data.hook && (
          <div className="border-b border-purple-500/10 px-4 py-3">
            <div className="text-xs font-medium text-purple-400 mb-1 uppercase tracking-wide">
              Hook
            </div>
            <div className="text-sm text-zinc-200 font-medium">
              {data.hook}
            </div>
          </div>
        )}

        {/* Body */}
        {data.body && (
          <div className="border-b border-purple-500/10 px-4 py-3">
            <div className="text-xs font-medium text-purple-400 mb-1 uppercase tracking-wide">
              Body
            </div>
            <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
              {data.body}
            </div>
          </div>
        )}

        {/* CTA */}
        {data.cta && (
          <div className="px-4 py-3">
            <div className="text-xs font-medium text-purple-400 mb-1 uppercase tracking-wide">
              CTA
            </div>
            <div className="text-sm text-zinc-200 font-medium">
              {data.cta}
            </div>
          </div>
        )}
      </div>

      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition"
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
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
        {copied ? "Copied!" : "Copy all"}
      </button>
    </div>
  );
}

// ── Main Response Renderer ───────────────────────────────

interface ResponseRendererProps {
  response: StrategistResponseItem;
  onSelectOption?: (option: StratOption) => void;
  onCustomWrite?: () => void;
  onSkip?: () => void;
  onConfirmRefinement?: () => void;
  onEditRefinement?: (text: string) => void;
  interactive: boolean;
  disabled: boolean;
}

export function ResponseRenderer({
  response,
  onSelectOption,
  onCustomWrite,
  onSkip,
  onConfirmRefinement,
  onEditRefinement,
  interactive,
  disabled,
}: ResponseRendererProps) {
  switch (response.type) {
    case "options":
      return interactive ? (
        <OptionsBlock
          data={response}
          onSelectOption={onSelectOption || (() => {})}
          onCustomWrite={onCustomWrite || (() => {})}
          onSkip={onSkip || (() => {})}
          disabled={disabled}
        />
      ) : (
        <div className="space-y-3">
          {response.module && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                {moduleLabel(response.module)}
              </span>
              <span className="text-xs text-zinc-500">
                {fieldLabel(response.field)}
              </span>
            </div>
          )}
          <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {response.message}
          </div>
          {response.options && response.options.length > 0 && (
            <div className="space-y-2">
              {response.options.map((opt) => (
                <div
                  key={opt.id}
                  className="rounded-lg border border-zinc-700 bg-zinc-800/30 p-3 opacity-60"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-bold text-zinc-500">
                      {opt.id}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-zinc-400">
                        {opt.label}
                      </div>
                      <div className="text-xs text-zinc-500">{opt.text}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );

    case "refinement":
      return interactive ? (
        <RefinementBlock
          data={response}
          onConfirm={onConfirmRefinement || (() => {})}
          onEdit={onEditRefinement || (() => {})}
          disabled={disabled}
        />
      ) : (
        <div className="space-y-3">
          <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {response.message}
          </div>
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 opacity-60">
            <div className="text-xs text-amber-400 mb-1">Refined</div>
            <div className="text-sm text-zinc-300">{response.refined_text}</div>
          </div>
        </div>
      );

    case "save":
      return <SaveBlock data={response} />;

    case "message":
      return <MessageBlock data={response} />;

    case "content":
      return <ContentBlock data={response} />;

    default:
      return (
        <div className="text-sm text-zinc-400 italic">
          Unknown response type
        </div>
      );
  }
}

// ── Feedback Buttons ─────────────────────────────────────

interface FeedbackButtonsProps {
  brandId: string;
  chatId?: string;
  messageIndex?: number;
  originalResponse: string;
}

export function FeedbackButtons({
  brandId,
  chatId,
  messageIndex,
  originalResponse,
}: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = async (
    type: "thumbs_up" | "thumbs_down" | "correction" | "voice_mismatch",
    text?: string
  ) => {
    try {
      setSubmitting(true);
      await userTrainingApi.submitFeedback({
        brand_id: brandId,
        chat_id: chatId,
        message_index: messageIndex,
        feedback_type: type,
        feedback_text: text,
        original_response: originalResponse.slice(0, 5000),
      });
      setSubmitted(type);
      setShowCorrection(false);
    } catch (e) {
      console.error("Failed to submit feedback:", e);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-1 text-xs text-zinc-500">
        <span>
          {submitted === "thumbs_up"
            ? "👍"
            : submitted === "thumbs_down"
            ? "👎"
            : submitted === "correction"
            ? "✏️"
            : "🔊"}{" "}
          Thanks for the feedback
        </span>
      </div>
    );
  }

  return (
    <div className="inline-flex flex-col">
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => handleFeedback("thumbs_up")}
          disabled={submitting}
          className="p-1 text-zinc-600 hover:text-green-400 hover:bg-green-400/10 rounded transition-colors"
          title="Good response"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017a2 2 0 01-.632-.103l-2.614-.783V10l4-9h1a2 2 0 012 2v5z" />
          </svg>
        </button>
        <button
          onClick={() => handleFeedback("thumbs_down")}
          disabled={submitting}
          className="p-1 text-zinc-600 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
          title="Bad response"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.632.103l2.614.783V14l-4 9h-1a2 2 0 01-2-2v-5z" />
          </svg>
        </button>
        <button
          onClick={() => setShowCorrection(!showCorrection)}
          disabled={submitting}
          className="p-1 text-zinc-600 hover:text-amber-400 hover:bg-amber-400/10 rounded transition-colors"
          title="Suggest correction"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
      </div>

      {showCorrection && (
        <div className="flex gap-2 mt-1.5">
          <input
            value={correctionText}
            onChange={(e) => setCorrectionText(e.target.value)}
            placeholder="What should be different?"
            className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-200 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-500"
            onKeyDown={(e) => {
              if (e.key === "Enter" && correctionText) {
                handleFeedback("correction", correctionText);
              }
            }}
          />
          <button
            onClick={() => handleFeedback("correction", correctionText)}
            disabled={!correctionText || submitting}
            className="px-2 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs disabled:opacity-50"
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}

// ── Text Formatter (bullets, numbered lists, paragraphs, inline bold) ─

/**
 * Render inline markdown formatting: **bold** and *italic*.
 */
function renderInlineFormatting(text: string, keyPrefix: string): React.ReactNode {
  // Split on **bold** patterns and render inline
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let partIdx = 0;

  while (remaining.length > 0) {
    const boldStart = remaining.indexOf("**");
    if (boldStart === -1) {
      parts.push(remaining);
      break;
    }

    // Text before the bold marker
    if (boldStart > 0) {
      parts.push(remaining.slice(0, boldStart));
    }

    // Find closing **
    const boldEnd = remaining.indexOf("**", boldStart + 2);
    if (boldEnd === -1) {
      // No closing marker, treat as plain text
      parts.push(remaining.slice(boldStart));
      break;
    }

    // The bold text
    const boldText = remaining.slice(boldStart + 2, boldEnd);
    parts.push(
      <strong key={`${keyPrefix}-b-${partIdx}`} className="font-semibold text-zinc-100">
        {boldText}
      </strong>
    );
    partIdx++;
    remaining = remaining.slice(boldEnd + 2);
  }

  return parts.length === 1 && typeof parts[0] === "string" ? parts[0] : <>{parts}</>;
}

function FormattedText({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let currentParagraph: string[] = [];

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      const joined = currentParagraph.join(" ");
      elements.push(
        <p key={`p-${elements.length}`} className="mb-2 last:mb-0">
          {renderInlineFormatting(joined, `p-${elements.length}`)}
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

    // Full-line bold text: **text**
    const boldMatch = trimmed.match(/^\*\*(.+?)\*\*$/);
    if (boldMatch) {
      flushParagraph();
      elements.push(
        <p key={`bold-${i}`} className="mb-2 font-semibold text-zinc-100">
          {boldMatch[1]}
        </p>
      );
      return;
    }

    // Bullet point
    const bulletMatch = trimmed.match(/^[-•*]\s+(.+)/);
    if (bulletMatch) {
      flushParagraph();
      elements.push(
        <div key={`b-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-blue-400 font-bold mt-0.5 text-xs">•</span>
          <span>{renderInlineFormatting(bulletMatch[1], `b-${i}`)}</span>
        </div>
      );
      return;
    }

    // Numbered list
    const numMatch = trimmed.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      flushParagraph();
      elements.push(
        <div key={`n-${i}`} className="flex items-start gap-2 ml-1 mb-1">
          <span className="text-blue-500 font-semibold text-xs min-w-[1rem]">
            {numMatch[1]}.
          </span>
          <span>{renderInlineFormatting(numMatch[2], `n-${i}`)}</span>
        </div>
      );
      return;
    }

    currentParagraph.push(trimmed);
  });

  flushParagraph();

  return <>{elements}</>;
}
