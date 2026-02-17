"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  collectionsApi,
  CollectionDetail,
  CollectionSearchResult,
  VoiceDNA,
} from "../../../lib/api";

export default function CollectionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const collectionId = params.id as string;

  const [collection, setCollection] = useState<CollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<CollectionSearchResult[]>(
    []
  );
  const [searching, setSearching] = useState(false);

  useEffect(() => {
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

  const handleAnalyzeVoice = async () => {
    setAnalyzing(true);
    setError("");
    try {
      const result = await collectionsApi.analyzeVoice(collectionId);
      // Refresh collection to show new voice DNA
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
      <main className="max-w-4xl mx-auto p-8">
        <p className="text-gray-500">Loading collection...</p>
      </main>
    );
  }

  if (!collection) {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <p className="text-red-600">Collection not found.</p>
        <Link href="/knowledge" className="text-blue-600 text-sm mt-2 block">
          Back to Knowledge Base
        </Link>
      </main>
    );
  }

  const voiceDna = collection.voice_dna;
  const hasVoiceDna = voiceDna && voiceDna.tone;

  return (
    <main className="max-w-4xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
        <Link href="/knowledge" className="hover:text-blue-600">
          Knowledge Base
        </Link>
        <span>/</span>
        <span className="text-gray-900">{collection.name}</span>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">{collection.name}</h1>
          {collection.description && (
            <p className="text-gray-600 mt-1">{collection.description}</p>
          )}
          {collection.creator_url && (
            <a
              href={collection.creator_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline mt-1 block"
            >
              {collection.creator_url}
            </a>
          )}
        </div>
        <button
          onClick={handleDelete}
          className="text-sm text-red-500 hover:text-red-700 transition"
        >
          Delete
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Voice DNA Section */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Voice DNA</h2>
          <button
            onClick={handleAnalyzeVoice}
            disabled={analyzing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {analyzing
              ? "Analyzing..."
              : hasVoiceDna
              ? "Re-analyze"
              : "Analyze Voice"}
          </button>
        </div>

        {hasVoiceDna ? (
          <div className="space-y-3 text-sm">
            <div>
              <span className="font-medium text-gray-700">Tone:</span>{" "}
              <span className="text-gray-600">{voiceDna.tone}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">
                Sentence Style:
              </span>{" "}
              <span className="text-gray-600">{voiceDna.sentence_style}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Vocabulary:</span>{" "}
              <span className="text-gray-600">{voiceDna.vocabulary_level}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Structure:</span>{" "}
              <span className="text-gray-600">
                {voiceDna.content_structure}
              </span>
            </div>
            {voiceDna.hook_patterns.length > 0 && (
              <div>
                <span className="font-medium text-gray-700">
                  Hook Patterns:
                </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {voiceDna.hook_patterns.map((p, i) => (
                    <span
                      key={i}
                      className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {voiceDna.signature_phrases.length > 0 && (
              <div>
                <span className="font-medium text-gray-700">
                  Signature Phrases:
                </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {voiceDna.signature_phrases.map((p, i) => (
                    <span
                      key={i}
                      className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-xs"
                    >
                      &ldquo;{p}&rdquo;
                    </span>
                  ))}
                </div>
              </div>
            )}
            {voiceDna.personality_traits.length > 0 && (
              <div>
                <span className="font-medium text-gray-700">Personality:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {voiceDna.personality_traits.map((t, i) => (
                    <span
                      key={i}
                      className="bg-green-50 text-green-700 px-2 py-0.5 rounded text-xs"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {voiceDna.sample_hooks.length > 0 && (
              <div>
                <span className="font-medium text-gray-700">
                  Sample Hooks:
                </span>
                <ul className="mt-1 space-y-1">
                  {voiceDna.sample_hooks.slice(0, 5).map((h, i) => (
                    <li key={i} className="text-gray-600 italic">
                      &ldquo;{h}&rdquo;
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-gray-400 mt-2">
              Analyzed from {voiceDna.analysis_chunk_count} content samples
            </p>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">
            No Voice DNA yet. Add at least 3 resources with content, then click
            &ldquo;Analyze Voice&rdquo; to extract this creator&apos;s writing
            style profile.
          </p>
        )}
      </section>

      {/* Search Section */}
      <section className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">
          Search This Collection
        </h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search within this creator's content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            {searchResults.map((r, i) => (
              <div
                key={i}
                className="border border-gray-100 rounded p-3 text-sm"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-gray-700">
                    {r.resource_title}
                  </span>
                  <span className="text-xs text-gray-400">
                    {(r.similarity * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="text-gray-600 text-xs whitespace-pre-wrap line-clamp-4">
                  {r.chunk_text}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Resources Section */}
      <section className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">
            Resources ({collection.resources.length})
          </h2>
        </div>

        {collection.resources.length === 0 ? (
          <p className="text-gray-500 text-sm">
            No resources in this collection yet. Add resources via the API or
            assign existing resources.
          </p>
        ) : (
          <div className="space-y-2">
            {collection.resources.map((res) => (
              <div
                key={res.id}
                className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
              >
                <div>
                  <span className="text-sm font-medium">{res.title}</span>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                    <span className="bg-gray-100 px-1.5 py-0.5 rounded">
                      {res.type}
                    </span>
                    <span>{res.chunk_count} chunks</span>
                    <span>
                      {new Date(res.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                {res.source_url && (
                  <a
                    href={res.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-500 hover:underline"
                  >
                    Source
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
