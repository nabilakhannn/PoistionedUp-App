"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  inspoApi,
  InspoBoardDetail,
  InspoItemDetail,
} from "../../../lib/api";
import { trackEvent } from "@/lib/posthog";

const CONTENT_TYPE_ICONS: Record<string, string> = {
  text: "📝",
  link: "🔗",
  image: "🖼️",
  video: "🎬",
  voice_note: "🎤",
};

const CONTENT_TYPE_LABELS: Record<string, string> = {
  text: "Text Note",
  link: "Link",
  image: "Image",
  video: "Video",
  voice_note: "Voice Note",
};

export default function BoardDetail() {
  const params = useParams();
  const router = useRouter();
  const boardId = params.boardId as string;

  const [board, setBoard] = useState<InspoBoardDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Add item form state
  const [showAdd, setShowAdd] = useState(false);
  const [contentType, setContentType] = useState<string>("text");
  const [contentText, setContentText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceTag, setSourceTag] = useState("");
  const [intentNote, setIntentNote] = useState("");
  const [tags, setTags] = useState("");
  const [adding, setAdding] = useState(false);

  // Filter state
  const [starredOnly, setStarredOnly] = useState(false);
  const [filterTag, setFilterTag] = useState("");

  // Delete item
  const [deletingItem, setDeletingItem] = useState<string | null>(null);

  // Edit item
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editIntentNote, setEditIntentNote] = useState("");
  const [editSourceTag, setEditSourceTag] = useState("");

  const loadBoard = () => {
    setLoading(true);
    inspoApi
      .getBoard(boardId)
      .then((data) => {
        setBoard(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadBoard();
  }, [boardId]);

  const handleAddItem = async () => {
    if (contentType === "text" && !contentText.trim()) return;
    if (contentType === "link" && !sourceUrl.trim()) return;

    setAdding(true);
    try {
      await inspoApi.createItem(boardId, {
        content_type: contentType,
        content_text: contentText.trim() || undefined,
        source_url: sourceUrl.trim() || undefined,
        source_tag: sourceTag.trim() || undefined,
        intent_note: intentNote.trim() || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      trackEvent("inspo_item_created", {
        board_id: boardId,
        content_type: contentType,
        source_tag: sourceTag,
      });
      // Reset form
      setContentText("");
      setSourceUrl("");
      setSourceTag("");
      setIntentNote("");
      setTags("");
      setShowAdd(false);
      loadBoard();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleToggleStar = async (itemId: string) => {
    try {
      await inspoApi.toggleStar(itemId);
      trackEvent("inspo_item_starred", { item_id: itemId, board_id: boardId });
      loadBoard();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    try {
      await inspoApi.deleteItem(itemId);
      trackEvent("inspo_item_deleted", { item_id: itemId, board_id: boardId });
      setDeletingItem(null);
      loadBoard();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSaveEdit = async (itemId: string) => {
    try {
      await inspoApi.updateItem(itemId, {
        intent_note: editIntentNote || undefined,
        source_tag: editSourceTag || undefined,
      });
      trackEvent("inspo_item_updated", { item_id: itemId, board_id: boardId });
      setEditingItem(null);
      loadBoard();
    } catch (e: any) {
      setError(e.message);
    }
  };

  // Get filtered items
  const getFilteredItems = (): InspoItemDetail[] => {
    if (!board) return [];
    let items = board.items;
    if (starredOnly) {
      items = items.filter((i) => i.is_starred);
    }
    if (filterTag) {
      items = items.filter((i) => i.tags.includes(filterTag));
    }
    return items;
  };

  // Collect all unique tags across items
  const getAllTags = (): string[] => {
    if (!board) return [];
    const tagSet = new Set<string>();
    board.items.forEach((item) => item.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-background text-card-foreground">
        <div className="max-w-5xl mx-auto p-8">
          <div className="text-center py-16 text-muted-foreground">Loading board...</div>
        </div>
      </main>
    );
  }

  if (!board) {
    return (
      <main className="min-h-screen bg-background text-card-foreground">
        <div className="max-w-5xl mx-auto p-8">
          <div className="text-center py-16">
            <h2 className="text-xl font-semibold text-foreground mb-2">Board not found</h2>
            <Link href="/inspo" className="text-primary hover:text-primary/80">
              Back to boards
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const filteredItems = getFilteredItems();
  const allTags = getAllTags();

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-5xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Link
                href="/inspo"
                className="text-muted-foreground hover:text-foreground text-sm transition"
              >
                Boards
              </Link>
              <span className="text-border">/</span>
            </div>
            <h1 className="text-3xl font-bold text-card-foreground">{board.name}</h1>
            {board.description && (
              <p className="text-muted-foreground mt-1">{board.description}</p>
            )}
            <p className="text-muted-foreground text-sm mt-1">
              {board.item_count} {board.item_count === 1 ? "item" : "items"}
            </p>
          </div>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
          >
            + Add Item
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
            {error}
            <button onClick={() => setError("")} className="ml-3 text-red-400 hover:text-red-200">
              dismiss
            </button>
          </div>
        )}

        {/* Add item form */}
        {showAdd && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <h3 className="font-semibold mb-4 text-card-foreground">Add Inspiration</h3>
            <div className="space-y-4">
              {/* Content type selector */}
              <div className="flex gap-2 flex-wrap">
                {["text", "link", "image", "video", "voice_note"].map((type) => (
                  <button
                    key={type}
                    onClick={() => setContentType(type)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition ${
                      contentType === type
                        ? "bg-primary/20 text-primary font-medium border border-primary/30"
                        : "bg-accent text-muted-foreground hover:bg-accent border border-border"
                    }`}
                  >
                    {CONTENT_TYPE_ICONS[type]} {CONTENT_TYPE_LABELS[type]}
                  </button>
                ))}
              </div>

              {/* URL input for links/videos */}
              {(contentType === "link" || contentType === "video") && (
                <input
                  type="url"
                  placeholder="Paste URL (YouTube, Reddit, Twitter, any website...)"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent"
                  autoFocus
                />
              )}

              {/* Text content */}
              <textarea
                placeholder={
                  contentType === "link"
                    ? "Add your own notes about this link (optional, text will be auto-extracted)"
                    : "Write your inspiration, note, or idea..."
                }
                value={contentText}
                onChange={(e) => setContentText(e.target.value)}
                rows={contentType === "text" ? 4 : 2}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent resize-none"
                autoFocus={contentType === "text"}
              />

              {/* Source tag */}
              <input
                type="text"
                placeholder="Source tag (e.g., Alex Hormozi, YouTube)"
                value={sourceTag}
                onChange={(e) => setSourceTag(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent"
              />

              {/* Intent note (critical for AI) */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  What should the AI learn from this?
                </label>
                <textarea
                  placeholder="e.g., Study the hook pattern. First 3 seconds use a bold claim then contradiction. Use this rhythm in my hooks."
                  value={intentNote}
                  onChange={(e) => setIntentNote(e.target.value)}
                  rows={2}
                  className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent resize-none"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  This tells the AI what to derive when this item is attached to a chat or pipeline step.
                </p>
              </div>

              {/* Tags */}
              <input
                type="text"
                placeholder="Tags (comma-separated, e.g., hooks, retention, intro)"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent"
              />

              <div className="flex gap-2">
                <button
                  onClick={handleAddItem}
                  disabled={
                    adding ||
                    (contentType === "text" && !contentText.trim()) ||
                    (contentType === "link" && !sourceUrl.trim())
                  }
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition disabled:opacity-50"
                >
                  {adding ? "Adding..." : "Add to Board"}
                </button>
                <button
                  onClick={() => {
                    setShowAdd(false);
                    setContentText("");
                    setSourceUrl("");
                    setSourceTag("");
                    setIntentNote("");
                    setTags("");
                  }}
                  className="px-4 py-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg text-sm transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        {board.items.length > 0 && (
          <div className="flex items-center gap-3 mb-6 flex-wrap">
            <button
              onClick={() => setStarredOnly(!starredOnly)}
              className={`px-3 py-1.5 rounded-lg text-sm transition ${
                starredOnly
                  ? "bg-yellow-500/20 text-yellow-300 font-medium border border-yellow-500/30"
                  : "bg-accent text-muted-foreground hover:bg-accent border border-border"
              }`}
            >
              ⭐ {starredOnly ? "Starred" : "All"}
            </button>

            {allTags.length > 0 && (
              <select
                value={filterTag}
                onChange={(e) => setFilterTag(e.target.value)}
                className="bg-accent border border-border rounded-lg px-3 py-1.5 text-sm text-foreground"
              >
                <option value="">All tags</option>
                {allTags.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
            )}

            {(starredOnly || filterTag) && (
              <button
                onClick={() => {
                  setStarredOnly(false);
                  setFilterTag("");
                }}
                className="text-muted-foreground hover:text-foreground text-sm transition"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Items list */}
        {filteredItems.length === 0 ? (
          <div className="text-center py-16 bg-card rounded-xl border border-dashed border-border">
            <div className="text-5xl mb-4">✨</div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {board.items.length === 0 ? "No items yet" : "No items match filters"}
            </h3>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              {board.items.length === 0
                ? "Add your first inspiration. Paste a link, write a note, or upload a screenshot."
                : "Try removing your filters to see all items."}
            </p>
            {board.items.length === 0 && (
              <button
                onClick={() => setShowAdd(true)}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
              >
                + Add First Item
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="bg-card border border-border rounded-xl p-4 hover:border-border transition group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Type badge + source tag */}
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-xs bg-accent text-muted-foreground px-2 py-0.5 rounded-full">
                        {CONTENT_TYPE_ICONS[item.content_type]}{" "}
                        {CONTENT_TYPE_LABELS[item.content_type]}
                      </span>
                      {item.source_tag && (
                        <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                          {item.source_tag}
                        </span>
                      )}
                      {item.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs bg-accent text-muted-foreground px-2 py-0.5 rounded-full cursor-pointer hover:bg-accent hover:text-foreground transition"
                          onClick={() => setFilterTag(tag)}
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>

                    {/* Source URL */}
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:text-primary/80 text-sm block mb-2 truncate transition"
                      >
                        {item.source_url}
                      </a>
                    )}

                    {/* Content text preview */}
                    {item.content_text && (
                      <p className="text-foreground text-sm mb-2 whitespace-pre-wrap line-clamp-4">
                        {item.content_text}
                      </p>
                    )}

                    {/* Intent note (highlighted) */}
                    {editingItem === item.id ? (
                      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mt-2">
                        <label className="block text-xs font-medium text-amber-400 mb-1">
                          Source Tag
                        </label>
                        <input
                          type="text"
                          value={editSourceTag}
                          onChange={(e) => setEditSourceTag(e.target.value)}
                          className="w-full bg-accent border border-border rounded px-2 py-1 text-sm text-card-foreground mb-2"
                        />
                        <label className="block text-xs font-medium text-amber-400 mb-1">
                          What should the AI learn?
                        </label>
                        <textarea
                          value={editIntentNote}
                          onChange={(e) => setEditIntentNote(e.target.value)}
                          rows={2}
                          className="w-full bg-accent border border-border rounded px-2 py-1 text-sm text-card-foreground resize-none"
                        />
                        <div className="flex gap-2 mt-2">
                          <button
                            onClick={() => handleSaveEdit(item.id)}
                            className="px-3 py-1 bg-amber-600 text-white rounded text-xs hover:bg-amber-500"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingItem(null)}
                            className="px-3 py-1 bg-muted text-foreground rounded text-xs hover:bg-accent"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      item.intent_note && (
                        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 mt-2">
                          <span className="text-xs font-medium text-amber-400 block mb-0.5">
                            AI should learn:
                          </span>
                          <span className="text-sm text-amber-300">
                            {item.intent_note}
                          </span>
                        </div>
                      )
                    )}

                    {/* Timestamp */}
                    <p className="text-xs text-muted-foreground mt-2">
                      Added {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 ml-3 shrink-0">
                    <button
                      onClick={() => handleToggleStar(item.id)}
                      className={`p-1.5 rounded transition ${
                        item.is_starred
                          ? "text-yellow-400"
                          : "text-muted-foreground hover:text-yellow-400 opacity-0 group-hover:opacity-100"
                      }`}
                      title={item.is_starred ? "Unstar" : "Star"}
                    >
                      ⭐
                    </button>

                    <button
                      onClick={() => {
                        setEditingItem(item.id);
                        setEditIntentNote(item.intent_note || "");
                        setEditSourceTag(item.source_tag || "");
                      }}
                      className="p-1.5 rounded text-muted-foreground hover:text-primary opacity-0 group-hover:opacity-100 transition"
                      title="Edit intent note"
                    >
                      ✏️
                    </button>

                    {deletingItem === item.id ? (
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleDeleteItem(item.id)}
                          className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-500"
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => setDeletingItem(null)}
                          className="px-2 py-1 bg-muted text-foreground rounded text-xs hover:bg-accent"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setDeletingItem(item.id)}
                        className="p-1.5 rounded text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition"
                        title="Delete"
                      >
                        🗑
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Back link */}
        <div className="mt-8 text-center">
          <Link
            href="/inspo"
            className="text-muted-foreground hover:text-foreground text-sm transition"
          >
            ← Back to all boards
          </Link>
        </div>
      </div>
    </main>
  );
}
