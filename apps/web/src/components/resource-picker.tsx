"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { pickerApi, PickerItem } from "@/lib/api";

/* ── Props ───────────────────────────────────────────────────── */

interface ResourcePickerProps {
  isOpen: boolean;
  onClose: () => void;
  /** Called when the user selects an item. Parent should set attachment state. */
  onSelect: (item: PickerItem) => void;
  brandId?: string;
}

/* ── Tab definitions ─────────────────────────────────────────── */

type TabKey = "all" | "knowledge" | "inspo";

const TABS: { key: TabKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "knowledge", label: "Knowledge" },
  { key: "inspo", label: "Inspo" },
];

/* ── Component ───────────────────────────────────────────────── */

export default function ResourcePicker({
  isOpen,
  onClose,
  onSelect,
  brandId,
}: ResourcePickerProps) {
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("all");
  const [results, setResults] = useState<PickerItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Focus the search input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      // Reset state on open
      setQuery("");
      setResults([]);
      setSearched(false);
      setActiveTab("all");
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  const doSearch = useCallback(
    async (searchQuery: string, tab: TabKey) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setSearched(false);
        return;
      }
      setLoading(true);
      setSearched(true);
      try {
        const sourceFilter: "all" | "knowledge" | "inspo" = tab;
        const data = await pickerApi.search({
          q: searchQuery,
          source: sourceFilter,
          brand_id: brandId,
        });
        setResults(data.items);
      } catch (err) {
        console.error("[ResourcePicker] search error:", err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [brandId]
  );

  // Debounced search on query or tab change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(query, activeTab);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, activeTab, doSearch]);

  const handleSelect = (item: PickerItem) => {
    onSelect(item);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-xl mx-4 max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-5 pt-5 pb-3">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-800">
              Attach Resource
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition p-1"
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

          {/* Search input */}
          <div className="relative">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search knowledge resources and inspo items..."
              className="w-full border border-gray-300 rounded-lg pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-3">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                  activeTab === tab.key
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-500 hover:bg-gray-100"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto px-5 pb-5 min-h-[200px]">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <span className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="ml-2 text-sm text-gray-400">Searching...</span>
            </div>
          )}

          {!loading && !searched && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-10 h-10 text-gray-300 mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <p className="text-sm text-gray-400">
                Type to search your Knowledge and Inspo items
              </p>
              <p className="text-xs text-gray-300 mt-1">
                Selected items will be injected as context for the AI
              </p>
            </div>
          )}

          {!loading && searched && results.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-sm text-gray-400">
                No results found for &ldquo;{query}&rdquo;
              </p>
              <p className="text-xs text-gray-300 mt-1">
                Try different keywords or switch tabs
              </p>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-2">
              {results.map((item) => (
                <button
                  key={`${item.source}-${item.id}`}
                  onClick={() => handleSelect(item)}
                  className="w-full text-left border border-gray-200 rounded-xl px-4 py-3 hover:border-blue-300 hover:bg-blue-50/50 transition group"
                >
                  <div className="flex items-start gap-3">
                    {/* Type badge */}
                    <div
                      className={`mt-0.5 flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                        item.source === "knowledge"
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-purple-100 text-purple-700"
                      }`}
                    >
                      {item.source === "knowledge" ? "K" : "I"}
                    </div>

                    <div className="flex-1 min-w-0">
                      {/* Title row */}
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800 truncate">
                          {item.title}
                        </span>
                        {item.is_gold && (
                          <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded font-medium flex-shrink-0">
                            Gold
                          </span>
                        )}
                        {item.is_starred && (
                          <span className="text-yellow-500 flex-shrink-0">
                            ★
                          </span>
                        )}
                      </div>

                      {/* Description */}
                      {item.content_preview && (
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {item.content_preview}
                        </p>
                      )}

                      {/* Metadata row */}
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        {item.source_tag && (
                          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                            {item.source_tag}
                          </span>
                        )}
                        {item.source_url && (
                          <span className="text-xs text-blue-400 truncate max-w-[200px]">
                            {item.source_url}
                          </span>
                        )}
                        {item.tags.length > 0 && (
                          <div className="flex gap-1">
                            {item.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                            {item.tags.length > 3 && (
                              <span className="text-xs text-gray-400">
                                +{item.tags.length - 3}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Intent note (inspo only) */}
                      {item.intent_note && (
                        <p className="text-xs text-purple-500 mt-1 italic line-clamp-1">
                          Intent: {item.intent_note}
                        </p>
                      )}
                    </div>

                    {/* Select indicator */}
                    <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition self-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="w-5 h-5 text-blue-500"
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
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
