"use client";

/**
 * Newsletter Engine — Slice 95
 *
 * Generates a weekly newsletter draft from the latest research brief.
 * Draft is displayed in an editable textarea for review + copy.
 */

import { useCallback, useEffect, useState } from "react";
import { newsletterApi, NewsletterDraft } from "@/lib/api/newsletter";

interface Props {
  brandId: string;
}

export default function NewsletterEngine({ brandId }: Props) {
  const [draft, setDraft] = useState<NewsletterDraft | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDraft = useCallback(async () => {
    try {
      const d = await newsletterApi.getDraft(brandId);
      setDraft(d);
      setContent(d?.content || "");
    } catch {
      // No draft exists — that's fine
    } finally {
      setLoading(false);
    }
  }, [brandId]);

  useEffect(() => { loadDraft(); }, [loadDraft]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const result = await newsletterApi.generate(brandId);
      setDraft(result);
      setContent(result.content);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Generation failed";
      if (msg.includes("research brief") || msg.includes("422")) {
        setError("No research brief found. Run the pipeline first to generate research, then come back.");
      } else {
        setError(msg);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">📧 Newsletter Engine</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Jumbo writes a 400-600 word weekly email based on what was researched this week.
            Review, edit, and copy to send.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition ml-4 shrink-0"
        >
          {generating ? (
            <><span className="animate-spin inline-block">⟳</span> Generating...</>
          ) : "✨ Generate"}
        </button>
      </div>

      {error && (
        <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {content ? (
        <div className="rounded-xl border border-border bg-card/50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20">
            <div className="text-[10px] text-muted-foreground">
              {draft?.created_at
                ? `Generated ${new Date(draft.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`
                : "Draft"}
            </div>
            <button
              onClick={handleCopy}
              className="text-xs text-primary hover:underline"
            >
              {copied ? "✓ Copied!" : "📋 Copy to Clipboard"}
            </button>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={18}
            className="w-full text-xs bg-transparent p-4 resize-none focus:outline-none text-foreground font-mono leading-relaxed"
            placeholder="Your newsletter draft will appear here..."
          />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border bg-card/30 px-6 py-10 text-center">
          <div className="text-2xl mb-2">📧</div>
          <p className="text-sm font-medium text-foreground mb-1">No newsletter yet</p>
          <p className="text-xs text-muted-foreground mb-4">
            Run the pipeline first to generate a research brief, then click Generate.
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="text-xs px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {generating ? "Generating..." : "✨ Generate Newsletter"}
          </button>
        </div>
      )}
    </div>
  );
}
