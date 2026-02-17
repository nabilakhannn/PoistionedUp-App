"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { collectionsApi, CollectionSummary } from "../../lib/api";

export default function KnowledgeBase() {
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [creating, setCreating] = useState(false);

  const loadCollections = () => {
    collectionsApi
      .list()
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
    loadCollections();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await collectionsApi.create({
        name: newName.trim(),
        description: newDescription.trim(),
        creator_url: newUrl.trim() || undefined,
      });
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
    <main className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Knowledge Base</h1>
          <p className="text-gray-600 mt-1">
            Organize content by creator. Analyze their voice. Mimic their style.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
        >
          + New Collection
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Create collection form */}
      {showCreate && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Create Collection</h2>
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Creator name (e.g., Alex Hormozi)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="Creator URL or YouTube channel (optional)"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-3">
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {creating ? "Creating..." : "Create"}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50 transition"
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
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
              <div className="h-3 bg-gray-200 rounded w-full mb-2" />
              <div className="h-3 bg-gray-200 rounded w-2/3 mb-4" />
              <div className="flex gap-4">
                <div className="h-3 bg-gray-200 rounded w-20" />
                <div className="h-3 bg-gray-200 rounded w-24" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && collections.length === 0 && (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">&#128218;</div>
          <h2 className="text-xl font-semibold mb-2">No collections yet</h2>
          <p className="text-gray-500 mb-4">
            Create a collection for each creator whose style you want to study and mimic.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
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
              className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition group"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-lg font-semibold group-hover:text-blue-600 transition">
                  {col.name}
                </h3>
                {col.voice_dna_ready && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
                    Voice DNA
                  </span>
                )}
              </div>
              {col.description && (
                <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                  {col.description}
                </p>
              )}
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{col.resource_count} resources</span>
                <span>
                  Updated {new Date(col.updated_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
