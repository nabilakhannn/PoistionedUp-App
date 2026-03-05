"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { trackEvent } from "@/lib/posthog";
import { collectionsApi, CollectionSummary } from "../../lib/api";
import { useBrand } from "@/lib/brand-context";

const YT_CHANNEL_PATTERNS = [
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/@[\w.-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/c\/[\w.-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/channel\/[\w-]+/,
  /(?:https?:\/\/)?(?:www\.)?youtube\.com\/user\/[\w.-]+/,
];

function isYouTubeChannelUrl(url: string): boolean {
  return YT_CHANNEL_PATTERNS.some((p) => p.test(url));
}

export default function KnowledgeBase() {
  const router = useRouter();
  const { brandId, loading: brandLoading } = useBrand();
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [creating, setCreating] = useState(false);
  const isChannel = isYouTubeChannelUrl(newUrl);

  const loadCollections = () => {
    collectionsApi
      .list(brandId || undefined)
      .then((data) => {
        setCollections(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    if (brandLoading) return;
    loadCollections();
  }, [brandId, brandLoading]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const created = await collectionsApi.create({
        name: newName.trim(),
        description: newDescription.trim(),
        creator_url: newUrl.trim() || undefined,
        brand_id: brandId || undefined,
      });
      trackEvent("collection_created", {
        brand_id: brandId || "",
        is_youtube_channel: isChannel,
      });

      // If it is a YouTube channel, redirect straight to the detail page
      // so the channel import UI can take over
      if (isChannel && created.id) {
        router.push(`/knowledge/${created.id}`);
        return;
      }

      setNewName("");
      setNewDescription("");
      setNewUrl("");
      setShowCreate(false);
      loadCollections();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-5xl mx-auto p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Knowledge Base</h1>
            <p className="text-muted-foreground mt-1">
              Organize content by creator. Analyze their voice. Mimic their style.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
          >
            + New Collection
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

        {/* Create collection form */}
        {showCreate && (
          <div className="bg-card border border-border rounded-xl p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4 text-card-foreground">Create Collection</h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Creator name (e.g., Alex Hormozi)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-2 bg-accent border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full px-3 py-2 bg-accent border border-border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <div>
                <input
                  type="text"
                  placeholder="YouTube channel URL (e.g. youtube.com/@creator)"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className={`w-full px-3 py-2 bg-accent border rounded-lg text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring ${
                    isChannel ? "border-red-500/50" : "border-border"
                  }`}
                />
                {isChannel && (
                  <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z" />
                      <path fill="#fff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                    </svg>
                    YouTube channel detected. Videos will be auto-imported after creation.
                  </p>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleCreate}
                  disabled={creating || !newName.trim()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition"
                >
                  {creating
                    ? "Creating..."
                    : isChannel
                    ? "Create & Import Videos"
                    : "Create"}
                </button>
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg text-sm transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-5 animate-pulse">
                <div className="h-5 bg-accent rounded w-3/4 mb-3" />
                <div className="h-3 bg-accent rounded w-full mb-2" />
                <div className="h-3 bg-accent rounded w-2/3 mb-4" />
                <div className="flex gap-4">
                  <div className="h-3 bg-accent rounded w-20" />
                  <div className="h-3 bg-accent rounded w-24" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && collections.length === 0 && (
          <div className="text-center py-16">
            <div className="text-4xl mb-4">📚</div>
            <h2 className="text-xl font-semibold mb-2 text-foreground">No collections yet</h2>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              Create a collection for each creator whose style you want to study and mimic.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition"
            >
              Create your first collection
            </button>
          </div>
        )}

        {/* Collection grid */}
        {!loading && collections.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {collections.map((col) => (
              <Link
                key={col.id}
                href={`/knowledge/${col.id}`}
                className="bg-card border border-border rounded-xl p-5 hover:border-border transition group"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary transition">
                    {col.name}
                  </h3>
                  {col.voice_dna_ready && (
                    <span className="text-xs bg-green-500/20 text-green-300 border border-green-500/30 px-2 py-0.5 rounded-full font-medium">
                      Voice DNA
                    </span>
                  )}
                </div>
                {col.description && (
                  <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                    {col.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{col.resource_count} resources</span>
                  <span>
                    Updated {new Date(col.updated_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
