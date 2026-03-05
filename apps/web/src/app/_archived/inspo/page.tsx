"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { inspoApi, InspoBoardSummary } from "../../lib/api";
import { useBrand } from "../../lib/brand-context";
import { trackEvent } from "@/lib/posthog";

export default function InspoBoards() {
  const { brandId } = useBrand();
  const [boards, setBoards] = useState<InspoBoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create board form state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  // Delete confirmation
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadBoards = () => {
    setLoading(true);
    inspoApi
      .listBoards(brandId || undefined)
      .then((data) => {
        setBoards(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadBoards();
  }, [brandId]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await inspoApi.createBoard({
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        brand_id: brandId || undefined,
      });
      trackEvent("inspo_board_created", { brand_id: brandId || "" });
      setNewName("");
      setNewDescription("");
      setShowCreate(false);
      loadBoards();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (boardId: string) => {
    try {
      await inspoApi.deleteBoard(boardId);
      trackEvent("inspo_board_deleted", { board_id: boardId });
      setDeleting(null);
      loadBoards();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-5xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Inspo Boards</h1>
            <p className="text-muted-foreground mt-1">
              Collect inspiration from anywhere. Tag sources. Tell the AI what to learn from each one.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
          >
            + New Board
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

        {/* Create board form */}
        {showCreate && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <h3 className="font-semibold mb-4 text-card-foreground">Create New Board</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Board name (e.g., Hook Ideas, Competitor Analysis)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent"
                autoFocus
              />
              <textarea
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                rows={2}
                className="w-full bg-accent border border-border rounded-lg px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-transparent resize-none"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleCreate}
                  disabled={creating || !newName.trim()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Board"}
                </button>
                <button
                  onClick={() => {
                    setShowCreate(false);
                    setNewName("");
                    setNewDescription("");
                  }}
                  className="px-4 py-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg text-sm transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Board list */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse">
                <div className="h-5 bg-accent rounded w-3/4 mb-3" />
                <div className="h-3 bg-accent rounded w-full mb-2" />
                <div className="h-3 bg-accent rounded w-2/3 mb-4" />
                <div className="flex justify-between">
                  <div className="h-3 bg-accent rounded w-16" />
                  <div className="h-3 bg-accent rounded w-24" />
                </div>
              </div>
            ))}
          </div>
        ) : boards.length === 0 ? (
          <div className="text-center py-16 bg-card rounded-xl border border-dashed border-border">
            <div className="text-5xl mb-4">💡</div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No boards yet
            </h3>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              Create your first board to start collecting inspiration. Save links, notes, screenshots,
              and videos. Tag each source so the AI knows what to learn from it.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
            >
              + Create Your First Board
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {boards.map((board) => (
              <div
                key={board.id}
                className="bg-card border border-border rounded-xl p-5 hover:border-border transition group relative"
              >
                <Link href={`/inspo/${board.id}`} className="block">
                  <h3 className="font-semibold text-lg mb-1 text-card-foreground group-hover:text-primary transition">
                    {board.name}
                  </h3>
                  {board.description && (
                    <p className="text-muted-foreground text-sm mb-3 line-clamp-2">
                      {board.description}
                    </p>
                  )}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      {board.item_count} {board.item_count === 1 ? "item" : "items"}
                    </span>
                    <span>
                      Updated {new Date(board.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>

                {/* Delete button */}
                {deleting === board.id ? (
                  <div className="absolute top-2 right-2 bg-accent border border-border rounded-lg p-2 shadow-lg z-10">
                    <p className="text-xs text-red-400 mb-2">Delete this board?</p>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleDelete(board.id)}
                        className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-500"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeleting(null)}
                        className="px-2 py-1 bg-muted text-foreground rounded text-xs hover:bg-accent"
                      >
                        No
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      setDeleting(board.id);
                    }}
                    className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition text-sm"
                    title="Delete board"
                  >
                    🗑
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Forward link */}
        <div className="mt-8 text-center">
          <Link
            href="/content"
            className="text-primary hover:text-primary/80 text-sm font-medium transition"
          >
            Next: Create Content →
          </Link>
        </div>
      </div>
    </main>
  );
}
