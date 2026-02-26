"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { trackEvent } from "@/lib/posthog";
import { researchApi } from "@/lib/api";
import { useBrand } from "@/lib/brand-context";

import { Platform, FeedCard, PLATFORMS, SORT_OPTIONS, SEARCH_SUGGESTIONS } from "./constants";
import { transformToFeedCards } from "./utils";
import { FeedCardComponent } from "./components/feed-card";
import { SkeletonCard } from "./components/skeleton-card";

/* ────────────────────────────────────────────────────────
   Main Page Component
   ──────────────────────────────────────────────────────── */

export default function ResearchFeedPage() {
  const { brandId } = useBrand();
  const searchInputRef = useRef<HTMLInputElement>(null);

  // State
  const [query, setQuery] = useState("");
  const [activePlatform, setActivePlatform] = useState<Platform>("all");
  const [sortBy, setSortBy] = useState("relevance");
  const [showSortDropdown, setShowSortDropdown] = useState(false);
  const [cards, setCards] = useState<FeedCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastSearched, setLastSearched] = useState("");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Saved search topics (persisted in state for now)
  const [savedTopics, setSavedTopics] = useState<string[]>([]);
  const [showTopicInput, setShowTopicInput] = useState(false);
  const [newTopic, setNewTopic] = useState("");

  // Search handler
  const handleSearch = useCallback(async (searchQuery?: string) => {
    const q = (searchQuery || query).trim();
    if (!q) return;

    setLoading(true);
    setError("");
    setLastSearched(q);

    try {
      // Build platform sources
      const sources: Record<string, boolean> = {};
      if (activePlatform === "all") {
        sources.reddit = true;
        sources.youtube = true;
        sources.linkedin = true;
        sources.tiktok = true;
        sources.web = true;
      } else {
        sources[activePlatform] = true;
      }

      const response = await researchApi.feed(q, sources, 12);
      const feedCards = transformToFeedCards(response);
      setCards(feedCards);
      setLastUpdated(new Date().toLocaleTimeString());

      trackEvent("research_feed_searched", {
        query: q,
        platform: activePlatform,
        result_count: feedCards.length,
        brand_id: brandId || "",
      });
    } catch (err: any) {
      setError(err.message || "Search failed. Please try again.");
      setCards([]);
    } finally {
      setLoading(false);
    }
  }, [query, activePlatform, brandId]);

  // Handle enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  // Platform tab switch triggers new search if we have a query
  useEffect(() => {
    if (lastSearched) {
      handleSearch(lastSearched);
    }
  }, [activePlatform]); // eslint-disable-line react-hooks/exhaustive-deps

  // Add saved topic
  const addTopic = () => {
    const t = newTopic.trim();
    if (t && !savedTopics.includes(t)) {
      setSavedTopics((prev) => [...prev, t]);
      setNewTopic("");
      setShowTopicInput(false);
    }
  };

  // Remove saved topic
  const removeTopic = (topic: string) => {
    setSavedTopics((prev) => prev.filter((t) => t !== topic));
  };

  // Filter cards based on sort
  const sortedCards = [...cards].sort((a, b) => {
    if (sortBy === "views") {
      const aViews = parseInt(a.views.replace(/[^0-9]/g, "")) || 0;
      const bViews = parseInt(b.views.replace(/[^0-9]/g, "")) || 0;
      return bViews - aViews;
    }
    return 0; // relevance = original order
  });

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      {/* ── Header Bar ── */}
      <div className="border-b border-border bg-card/50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
                  <svg className="w-5 h-5 text-black" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h1 className="text-xl font-bold text-card-foreground tracking-tight">Research Feed</h1>
              </div>

              {lastUpdated && (
                <span className="text-xs text-muted-foreground hidden sm:inline">
                  Last Updated: {lastUpdated}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {/* Saved topics pill */}
              <button
                onClick={() => setShowTopicInput(!showTopicInput)}
                className="flex items-center gap-2 px-3 py-2 bg-accent border border-border rounded-lg text-xs text-foreground hover:border-border transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
                </svg>
                Manage Topics
              </button>

              {/* Refresh button */}
              <button
                onClick={() => handleSearch(lastSearched || query)}
                disabled={loading || (!query.trim() && !lastSearched)}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className={`w-2 h-2 rounded-full ${loading ? "bg-amber-400 animate-pulse" : "bg-emerald-300"}`} />
                {loading ? "Searching..." : "Refresh Feed"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* ── Platform Tabs ── */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center bg-card/80 border border-border rounded-xl p-1.5 gap-1">
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                onClick={() => setActivePlatform(p.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activePlatform === p.id
                    ? "bg-accent text-card-foreground shadow-lg shadow-black/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${
                  activePlatform === p.id ? p.dotColor : "bg-muted-foreground"
                }`} />
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Filter Row: Saved Topics + Sort ── */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 flex-wrap flex-1">
            {/* Saved topic chips */}
            {savedTopics.map((topic) => (
              <button
                key={topic}
                onClick={() => {
                  setQuery(topic);
                  handleSearch(topic);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition group"
              >
                {topic.toUpperCase()}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeTopic(topic);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-emerald-300 hover:text-red-400 transition ml-0.5"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </button>
            ))}

            {/* Add topic button/input */}
            {showTopicInput ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTopic())}
                  placeholder="Add a tracked topic..."
                  className="bg-accent border border-border rounded-full px-3 py-1.5 text-xs text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500 w-40"
                  autoFocus
                />
                <button
                  onClick={addTopic}
                  disabled={!newTopic.trim()}
                  className="px-2.5 py-1.5 bg-emerald-600 text-white rounded-full text-xs hover:bg-emerald-700 disabled:opacity-40 transition"
                >
                  Add
                </button>
                <button
                  onClick={() => { setShowTopicInput(false); setNewTopic(""); }}
                  className="text-muted-foreground hover:text-foreground p-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : savedTopics.length === 0 ? (
              <button
                onClick={() => setShowTopicInput(true)}
                className="text-xs text-muted-foreground hover:text-muted-foreground transition"
              >
                + Add tracked topic
              </button>
            ) : null}
          </div>

          {/* Sort dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowSortDropdown(!showSortDropdown)}
              className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition"
            >
              <span className="text-muted-foreground">Sort:</span>
              <span className="font-medium text-foreground">
                {SORT_OPTIONS.find((s) => s.id === sortBy)?.label || "Relevance"}
              </span>
              <svg className={`w-3.5 h-3.5 transition-transform ${showSortDropdown ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>
            {showSortDropdown && (
              <div className="absolute right-0 top-full mt-1 bg-accent border border-border rounded-lg shadow-xl z-30 py-1 min-w-[120px]">
                {SORT_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    onClick={() => { setSortBy(opt.id); setShowSortDropdown(false); }}
                    className={`w-full text-left px-3 py-2 text-xs transition ${
                      sortBy === opt.id
                        ? "bg-primary/20 text-primary font-medium"
                        : "text-foreground hover:bg-muted"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Search Bar ── */}
        <div className="mb-8">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search posts by keyword, creator, or topic..."
              className="w-full bg-card border border-border rounded-xl pl-12 pr-4 py-3.5 text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring/50 transition"
            />
            {query && (
              <button
                onClick={() => { setQuery(""); setCards([]); setLastSearched(""); }}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ── Results Grid ── */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : cards.length > 0 ? (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs text-muted-foreground">
                {sortedCards.length} result{sortedCards.length !== 1 ? "s" : ""} for &quot;{lastSearched}&quot;
                {activePlatform !== "all" && ` on ${PLATFORMS.find(p => p.id === activePlatform)?.label}`}
              </p>
              <p className="text-xs text-muted-foreground">
                {sortedCards.length} signals found
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedCards.map((card) => (
                <FeedCardComponent key={card.id} card={card} />
              ))}
            </div>
          </>
        ) : lastSearched ? (
          <div className="text-center py-20">
            <svg className="mx-auto h-12 w-12 text-muted mb-4" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <h3 className="text-lg font-medium text-foreground mb-1">No results found</h3>
            <p className="text-muted-foreground text-sm">
              Try a different search term or switch platforms.
            </p>
          </div>
        ) : (
          /* Empty state */
          <div className="text-center py-20">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-card-foreground mb-3">Research the competition</h2>
            <p className="text-muted-foreground text-sm max-w-md mx-auto leading-relaxed mb-8">
              Search across Reddit, LinkedIn, YouTube, and TikTok to find what&apos;s
              trending in your niche. Track topics and creators to stay ahead.
            </p>
            <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
              {SEARCH_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setQuery(suggestion);
                    handleSearch(suggestion);
                  }}
                  className="px-4 py-2 bg-card border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-border transition"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
