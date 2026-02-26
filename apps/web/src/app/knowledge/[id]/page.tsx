"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { trackEvent } from "@/lib/posthog";
import { useBrand } from "@/lib/brand-context";
import {
  collectionsApi,
  channelApi,
  resourcesApi,
  CollectionDetail,
  CollectionResource,
  CollectionSearchResult,
  VoiceDNA,
  ChannelImportResponse,
  ChannelVideoSummary,
  ResourceDetail,
} from "../../../lib/api";

/* ── YouTube channel URL detection ─────────────────────── */
const YT_CHANNEL_PATTERNS = [
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/@[\w.-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/c\/[\w.-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/channel\/[\w-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/user\/[\w.-]+/,
];

function isYouTubeChannelUrl(url: string): boolean {
  return YT_CHANNEL_PATTERNS.some((p) => p.test(url));
}

/* ── Status icon helper ────────────────────────────────── */
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "processing":
      return (
        <span className="inline-flex items-center gap-1 text-primary text-xs">
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Extracting
        </span>
      );
    case "success":
      return (
        <span className="inline-flex items-center gap-1 text-green-400 text-xs">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Done
        </span>
      );
    case "skipped":
      return (
        <span className="inline-flex items-center gap-1 text-muted-foreground text-xs">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
          Already imported
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 text-red-400 text-xs">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Failed
        </span>
      );
    default:
      return (
        <span className="text-muted-foreground text-xs">Pending</span>
      );
  }
}

/* ── Expandable Transcript Card ────────────────────────── */
function TranscriptCard({ resource }: { resource: CollectionResource }) {
  const [expanded, setExpanded] = useState(false);
  const [fullContent, setFullContent] = useState<string | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);

  const hasPreview = resource.content_preview && resource.content_preview.length > 0;
  const isExtracting = resource.chunk_count === 0 && !hasPreview;

  const loadFullTranscript = async () => {
    if (fullContent !== null) {
      setExpanded(!expanded);
      return;
    }
    setLoadingContent(true);
    setExpanded(true);
    try {
      const detail = await resourcesApi.get(resource.id);
      // Extract just the transcript text (after [TRANSCRIPT] marker if present)
      let text = detail.content_text || "";
      if (text.includes("[TRANSCRIPT]")) {
        text = text.split("[TRANSCRIPT]")[1]?.trim() || text;
      }
      setFullContent(text);
    } catch {
      setFullContent("Failed to load transcript. Try again.");
    } finally {
      setLoadingContent(false);
    }
  };

  return (
    <div className="bg-accent/30 border border-border/50 rounded-xl overflow-hidden hover:border-border transition group">
      {/* Header row */}
      <button
        onClick={loadFullTranscript}
        className="w-full flex items-center gap-3 py-3 px-4 text-left hover:bg-accent/50 transition"
      >
        {/* Icon */}
        <div className="bg-accent rounded-lg p-2 shrink-0">
          {resource.source_url?.includes("youtube.com") || resource.source_url?.includes("youtu.be") ? (
            <svg className="w-4 h-4 text-red-400" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z" />
              <path fill="#fff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          )}
        </div>

        {/* Title + meta */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{resource.title}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
            <span className="bg-accent px-1.5 py-0.5 rounded text-muted-foreground">{resource.type}</span>
            {resource.has_transcript ? (
              <span className="text-green-400 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Transcript ready
              </span>
            ) : isExtracting ? (
              <span className="text-amber-400 flex items-center gap-1">
                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Extracting...
              </span>
            ) : (
              <span>{resource.chunk_count} chunks</span>
            )}
            <span>{new Date(resource.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Expand arrow */}
        <div className="flex items-center gap-2">
          {resource.source_url && (
            <a
              href={resource.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-primary hover:text-primary/80 transition opacity-0 group-hover:opacity-100"
            >
              Open
            </a>
          )}
          <svg
            className={`w-4 h-4 text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Preview (always visible if has_transcript, collapsed) */}
      {!expanded && hasPreview && (
        <div className="px-4 pb-3">
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {resource.content_preview}
          </p>
        </div>
      )}

      {/* Expanded full transcript */}
      {expanded && (
        <div className="border-t border-border/50 bg-card/50">
          {loadingContent ? (
            <div className="p-6 flex items-center justify-center gap-2">
              <svg className="w-4 h-4 animate-spin text-primary" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-sm text-muted-foreground">Loading transcript...</span>
            </div>
          ) : fullContent ? (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Full Transcript
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(fullContent);
                  }}
                  className="text-xs text-primary hover:text-primary/80 transition flex items-center gap-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto rounded-lg bg-accent/50 p-4 text-sm text-foreground leading-relaxed whitespace-pre-wrap scrollbar-thin scrollbar-thumb-border">
                {fullContent}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {fullContent.split(/\s+/).length.toLocaleString()} words
              </p>
            </div>
          ) : (
            <div className="p-6 text-center">
              <p className="text-sm text-muted-foreground">
                {isExtracting
                  ? "Transcript is still being extracted. Refresh in a minute."
                  : "No transcript content available."}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CollectionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { brandId } = useBrand();
  const collectionId = params.id as string;

  const [collection, setCollection] = useState<CollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<CollectionSearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Channel import state
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ChannelImportResponse | null>(null);
  const [maxVideos, setMaxVideos] = useState(20);
  const [showImportSettings, setShowImportSettings] = useState(false);

  // Re-extract state
  const [reExtracting, setReExtracting] = useState(false);
  const [reExtractMsg, setReExtractMsg] = useState("");

  // Manual URL input for channel import
  const [channelUrlInput, setChannelUrlInput] = useState("");
  const [showAddSource, setShowAddSource] = useState(false);

  const loadCollection = useCallback(() => {
    if (!collectionId) return;
    collectionsApi
      .get(collectionId)
      .then((data) => {
        setCollection(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [collectionId]);

  useEffect(() => {
    loadCollection();
  }, [loadCollection]);

  const isChannelUrl = collection?.creator_url
    ? isYouTubeChannelUrl(collection.creator_url)
    : false;

  const handleImportChannel = async (url?: string) => {
    const channelUrl = url || collection?.creator_url;
    if (!channelUrl) return;

    setImporting(true);
    setError("");
    setImportResult(null);

    try {
      const result = await channelApi.importChannel({
        channel_url: channelUrl,
        max_videos: maxVideos,
        extract_transcripts: true,
        collection_id: collectionId,
        brand_id: brandId || undefined,
      });
      setImportResult(result);
      trackEvent("channel_imported", {
        channel_name: result.channel_name,
        total_videos: result.total_videos,
        imported: result.imported,
      });

      // Refresh collection to show new resources
      setTimeout(() => loadCollection(), 2000);
    } catch (e: any) {
      setError(e.message || "Failed to import channel videos");
    } finally {
      setImporting(false);
    }
  };

  const handleReExtract = async () => {
    if (!collectionId) return;
    setReExtracting(true);
    setReExtractMsg("");
    try {
      const result = await channelApi.reExtract(collectionId);
      setReExtractMsg(result.message);
      if (result.queued > 0) {
        // Refresh after a delay to pick up new transcripts
        setTimeout(() => loadCollection(), 5000);
        setTimeout(() => loadCollection(), 15000);
      }
    } catch (e: any) {
      setReExtractMsg(e.message || "Failed to re-extract transcripts");
    } finally {
      setReExtracting(false);
    }
  };

  const handleAddSourceSubmit = () => {
    const url = channelUrlInput.trim();
    if (!url) return;

    if (isYouTubeChannelUrl(url)) {
      handleImportChannel(url);
      setShowAddSource(false);
      setChannelUrlInput("");
    } else {
      setError("Please enter a valid YouTube channel URL (e.g. youtube.com/@creator)");
    }
  };

  const handleAnalyzeVoice = async () => {
    setAnalyzing(true);
    setError("");
    try {
      await collectionsApi.analyzeVoice(collectionId);
      const updated = await collectionsApi.get(collectionId);
      setCollection(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const result = await collectionsApi.search(collectionId, searchQuery);
      setSearchResults(result.results);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this collection? Resources will be kept.")) return;
    try {
      await collectionsApi.delete(collectionId);
      router.push("/knowledge");
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-background text-card-foreground">
        <div className="max-w-4xl mx-auto p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-accent rounded w-40" />
            <div className="h-8 bg-accent rounded w-64" />
            <div className="h-40 bg-card border border-border rounded-xl" />
          </div>
        </div>
      </main>
    );
  }

  if (!collection) {
    return (
      <main className="min-h-screen bg-background text-card-foreground">
        <div className="max-w-4xl mx-auto p-8">
          <p className="text-red-400">Collection not found.</p>
          <Link href="/knowledge" className="text-primary text-sm mt-2 block hover:text-primary/80">
            Back to Knowledge Base
          </Link>
        </div>
      </main>
    );
  }

  const voiceDna = collection.voice_dna;
  const hasVoiceDna = voiceDna && voiceDna.tone;
  const totalChunks = collection.resources.reduce((sum, r) => sum + (r.chunk_count || 0), 0);
  const canAnalyze = totalChunks >= 5;

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-4xl mx-auto p-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
          <Link href="/knowledge" className="hover:text-primary transition">
            Knowledge Base
          </Link>
          <span>/</span>
          <span className="text-foreground">{collection.name}</span>
        </div>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-card-foreground">{collection.name}</h1>
            {collection.description && (
              <p className="text-muted-foreground mt-1">{collection.description}</p>
            )}
            {collection.creator_url && (
              <a
                href={collection.creator_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:text-primary/80 mt-1 block transition"
              >
                {collection.creator_url}
              </a>
            )}
          </div>
          <button
            onClick={handleDelete}
            className="text-sm text-muted-foreground hover:text-red-400 transition"
          >
            Delete
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
            {error}
            <button onClick={() => setError("")} className="ml-3 text-red-400 hover:text-red-200">
              Dismiss
            </button>
          </div>
        )}

        {/* ── Add Sources Section (NotebookLM-style) ──────── */}
        <section className="bg-card border border-border rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-card-foreground">Sources</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Add a YouTube channel to automatically extract all video transcripts
              </p>
            </div>
            <button
              onClick={() => setShowAddSource(!showAddSource)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add Source
            </button>
          </div>

          {/* Quick import if creator_url is a YouTube channel */}
          {isChannelUrl && !importResult && collection.resources.length === 0 && (
            <div className="bg-gradient-to-r from-red-950/30 to-card border border-red-500/20 rounded-xl p-5 mb-4">
              <div className="flex items-start gap-4">
                <div className="bg-red-600 rounded-lg p-2.5 shrink-0">
                  <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z" />
                    <path fill="#fff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-card-foreground">
                    YouTube Channel Detected
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Import videos from this channel and extract transcripts automatically. Works like NotebookLM but for video content.
                  </p>
                  <div className="flex items-center gap-3 mt-3">
                    <button
                      onClick={() => setShowImportSettings(!showImportSettings)}
                      className="text-xs text-muted-foreground hover:text-foreground transition"
                    >
                      {showImportSettings ? "Hide settings" : "Settings"}
                    </button>
                    <button
                      onClick={() => handleImportChannel()}
                      disabled={importing}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-500 disabled:opacity-50 transition flex items-center gap-2"
                    >
                      {importing ? (
                        <>
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Importing...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          Import All Videos
                        </>
                      )}
                    </button>
                  </div>
                  {showImportSettings && (
                    <div className="mt-3 flex items-center gap-3">
                      <label className="text-xs text-muted-foreground">Max videos:</label>
                      <select
                        value={maxVideos}
                        onChange={(e) => setMaxVideos(Number(e.target.value))}
                        className="bg-accent border border-border rounded px-2 py-1 text-xs text-foreground"
                      >
                        <option value={10}>10</option>
                        <option value={20}>20</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                        <option value={200}>200</option>
                        <option value={500}>All (up to 500)</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Manual add source form */}
          {showAddSource && (
            <div className="bg-accent/50 border border-border rounded-lg p-4 mb-4">
              <label className="text-sm font-medium text-foreground block mb-2">
                YouTube Channel URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={channelUrlInput}
                  onChange={(e) => setChannelUrlInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddSourceSubmit()}
                  placeholder="https://www.youtube.com/@creator"
                  className="flex-1 px-3 py-2 bg-accent border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <button
                  onClick={handleAddSourceSubmit}
                  disabled={importing || !channelUrlInput.trim()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
                >
                  {importing ? "Importing..." : "Import"}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Paste a YouTube channel URL to import all videos and extract their transcripts
              </p>

              {/* Import settings */}
              <div className="flex items-center gap-3 mt-3">
                <label className="text-xs text-muted-foreground">Max videos:</label>
                <select
                  value={maxVideos}
                  onChange={(e) => setMaxVideos(Number(e.target.value))}
                  className="bg-accent border border-border rounded px-2 py-1 text-xs text-foreground"
                >
                  <option value={10}>10</option>
                  <option value={20}>20 (default)</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>All (up to 500)</option>
                </select>
              </div>
            </div>
          )}

          {/* Import in progress */}
          {importing && (
            <div className="bg-accent/50 border border-border rounded-lg p-6 text-center">
              <svg className="w-8 h-8 animate-spin mx-auto text-primary mb-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-sm text-foreground">Discovering videos from channel...</p>
              <p className="text-xs text-muted-foreground mt-1">
                This may take a moment. Transcripts will extract in the background.
              </p>
            </div>
          )}

          {/* Import result */}
          {importResult && (
            <div className="space-y-3">
              {/* Summary banner */}
              <div className="bg-green-950/30 border border-green-500/20 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-semibold text-green-300">
                    {importResult.channel_name}
                  </span>
                </div>
                <p className="text-sm text-foreground">{importResult.message}</p>
                <div className="flex gap-4 mt-2 text-xs">
                  <span className="text-green-400">{importResult.imported} imported</span>
                  {importResult.skipped > 0 && (
                    <span className="text-muted-foreground">{importResult.skipped} already existed</span>
                  )}
                  {importResult.failed > 0 && (
                    <span className="text-red-400">{importResult.failed} failed</span>
                  )}
                  <span className="text-muted-foreground">{importResult.total_videos} total on channel</span>
                </div>
              </div>

              {/* Video list */}
              <div className="bg-accent/30 border border-border rounded-lg divide-y divide-border">
                <div className="px-4 py-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Imported Videos
                  </span>
                  <button
                    onClick={() => {
                      setImportResult(null);
                      loadCollection();
                    }}
                    className="text-xs text-primary hover:text-primary/80 transition"
                  >
                    Refresh Resources
                  </button>
                </div>
                {importResult.videos.slice(0, 50).map((video) => (
                  <div
                    key={video.video_id}
                    className="px-4 py-3 flex items-center justify-between hover:bg-accent/50 transition"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground truncate">{video.title}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        {video.views_str && <span>{video.views_str} views</span>}
                        {video.duration_str && <span>{video.duration_str}</span>}
                      </div>
                    </div>
                    <StatusIcon status={video.status} />
                  </div>
                ))}
                {importResult.videos.length > 50 && (
                  <div className="px-4 py-2 text-center text-xs text-muted-foreground">
                    + {importResult.videos.length - 50} more videos
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Existing resources as sources with expandable transcripts */}
          {!importResult && collection.resources.length > 0 && (
            <div className="space-y-2">
              {collection.resources.map((res) => (
                <TranscriptCard key={res.id} resource={res} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!importResult && !importing && collection.resources.length === 0 && !isChannelUrl && (
            <div className="text-center py-8">
              <div className="text-3xl mb-3">📡</div>
              <p className="text-muted-foreground text-sm mb-2">No sources added yet</p>
              <p className="text-muted-foreground text-xs max-w-sm mx-auto">
                Add a YouTube channel URL to import all videos and extract their transcripts automatically
              </p>
            </div>
          )}

          {/* Re-import + Re-extract buttons (when resources already exist) */}
          {collection.resources.length > 0 && !importResult && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  {collection.resources.length} source{collection.resources.length !== 1 ? "s" : ""} loaded
                  {collection.resources.filter(r => !r.has_transcript).length > 0 && (
                    <> &middot; {collection.resources.filter(r => !r.has_transcript).length} pending transcripts</>
                  )}
                </span>
                <div className="flex items-center gap-3">
                  {collection.resources.some(r => !r.has_transcript) && (
                    <button
                      onClick={handleReExtract}
                      disabled={reExtracting}
                      className="text-xs text-amber-400 hover:text-amber-300 transition flex items-center gap-1 disabled:opacity-50"
                    >
                      {reExtracting ? (
                        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      )}
                      {reExtracting ? "Re-extracting..." : "Re-extract Transcripts"}
                    </button>
                  )}
                  {(isChannelUrl || collection.creator_url) && (
                    <button
                      onClick={() => handleImportChannel()}
                      disabled={importing}
                      className="text-xs text-primary hover:text-primary/80 transition flex items-center gap-1"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Sync new videos
                    </button>
                  )}
                </div>
              </div>
              {reExtractMsg && (
                <p className="text-xs text-amber-400/80 mt-2">{reExtractMsg}</p>
              )}
            </div>
          )}
        </section>

        {/* Voice DNA Section */}
        <section className="bg-card border border-border rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-card-foreground">Voice DNA</h2>
            <button
              onClick={handleAnalyzeVoice}
              disabled={analyzing || !canAnalyze}
              title={!canAnalyze ? `Need at least 5 content chunks (currently ${totalChunks})` : undefined}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {analyzing
                ? "Analyzing..."
                : hasVoiceDna
                ? "Re-analyze"
                : "Analyze Voice"}
            </button>
          </div>

          {hasVoiceDna ? (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                {voiceDna.tone && (
                  <div className="bg-accent/50 border border-border rounded-lg p-3">
                    <span className="text-xs font-medium text-muted-foreground">Tone</span>
                    <p className="text-foreground mt-0.5">{voiceDna.tone}</p>
                  </div>
                )}
                {voiceDna.sentence_style && (
                  <div className="bg-accent/50 border border-border rounded-lg p-3">
                    <span className="text-xs font-medium text-muted-foreground">Sentence Style</span>
                    <p className="text-foreground mt-0.5">{voiceDna.sentence_style}</p>
                  </div>
                )}
                {voiceDna.vocabulary_level && (
                  <div className="bg-accent/50 border border-border rounded-lg p-3">
                    <span className="text-xs font-medium text-muted-foreground">Vocabulary</span>
                    <p className="text-foreground mt-0.5">{voiceDna.vocabulary_level}</p>
                  </div>
                )}
                {voiceDna.content_structure && (
                  <div className="bg-accent/50 border border-border rounded-lg p-3">
                    <span className="text-xs font-medium text-muted-foreground">Structure</span>
                    <p className="text-foreground mt-0.5">{voiceDna.content_structure}</p>
                  </div>
                )}
              </div>

              {voiceDna.hook_patterns.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Hook Patterns</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {voiceDna.hook_patterns.map((p, i) => (
                      <span key={i} className="bg-sky-500/15 text-sky-300 border border-sky-500/20 px-2.5 py-1 rounded-full text-xs">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {voiceDna.signature_phrases.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Signature Phrases</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {voiceDna.signature_phrases.map((p, i) => (
                      <span key={i} className="bg-purple-500/15 text-purple-300 border border-purple-500/20 px-2.5 py-1 rounded-full text-xs">
                        &ldquo;{p}&rdquo;
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {voiceDna.personality_traits.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Personality</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {voiceDna.personality_traits.map((t, i) => (
                      <span key={i} className="bg-green-500/15 text-green-300 border border-green-500/20 px-2.5 py-1 rounded-full text-xs">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {voiceDna.sample_hooks.length > 0 && (
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Sample Hooks</span>
                  <ul className="mt-1 space-y-1">
                    {voiceDna.sample_hooks.slice(0, 5).map((h, i) => (
                      <li key={i} className="text-foreground italic pl-3 border-l-2 border-indigo-500">
                        &ldquo;{h}&rdquo;
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                Analyzed from {voiceDna.analysis_chunk_count} content samples
              </p>
            </div>
          ) : (
            <div className="text-sm">
              {!canAnalyze ? (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-amber-300">
                  <p className="font-medium">Not enough content yet</p>
                  <p className="mt-1 text-amber-400/80">
                    Voice DNA analysis needs at least 5 content chunks to detect writing
                    patterns. This collection has {totalChunks} chunk{totalChunks !== 1 ? "s" : ""} across{" "}
                    {collection.resources.length} resource{collection.resources.length !== 1 ? "s" : ""}.
                    Add more resources with text content, then come back to analyze.
                  </p>
                </div>
              ) : (
                <p className="text-muted-foreground">
                  Voice DNA is ready to analyze. Click &ldquo;Analyze Voice&rdquo; to
                  extract this creator&apos;s writing style profile from{" "}
                  {totalChunks} content chunks.
                </p>
              )}
            </div>
          )}
        </section>

        {/* Search Section */}
        <section className="bg-card border border-border rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-card-foreground">Search This Collection</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask anything about this creator's content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 px-3 py-2 bg-accent border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              onClick={handleSearch}
              disabled={searching || !searchQuery.trim()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
            >
              {searching ? "Searching..." : "Search"}
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="mt-4 space-y-3">
              {searchResults.map((r, i) => (
                <div key={i} className="bg-accent/50 border border-border rounded-lg p-3 text-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-foreground">{r.resource_title}</span>
                    <span className="text-xs text-muted-foreground">
                      {(r.similarity * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-muted-foreground text-xs whitespace-pre-wrap line-clamp-4">
                    {r.chunk_text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
