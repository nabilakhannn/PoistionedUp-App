"use client";

import { useState } from "react";
import { contentApi, ContentAsset } from "@/lib/api";

interface VersionHistoryProps {
  workflowId: string;
  assets: ContentAsset[];
  onRestore?: () => void;
}

export function VersionHistory({
  workflowId,
  assets,
  onRestore,
}: VersionHistoryProps) {
  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState<Record<string, ContentAsset[]>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  // Only show if there are versioned assets (version > 1)
  const hasVersions = assets.some((a) => a.version > 1);
  if (!hasVersions && !open) return null;

  const loadVersions = async (assetId: string) => {
    if (versions[assetId]) {
      // Toggle: clear to hide
      const copy = { ...versions };
      delete copy[assetId];
      setVersions(copy);
      return;
    }
    setLoadingId(assetId);
    try {
      const vList = await contentApi.getAssetVersions(workflowId, assetId);
      setVersions((prev) => ({ ...prev, [assetId]: vList }));
    } catch {
      // silently fail
    } finally {
      setLoadingId(null);
    }
  };

  const handleRestore = async (assetId: string) => {
    setRestoring(true);
    try {
      await contentApi.restoreAssetVersion(workflowId, assetId);
      if (onRestore) {
        onRestore();
      } else {
        window.location.reload();
      }
    } catch {
      console.error("Failed to restore version");
    } finally {
      setRestoring(false);
    }
  };

  // Group latest assets by type for display
  const latestAssets = assets.filter((a) => a.is_latest !== false);

  return (
    <div className="border border-zinc-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-zinc-800/50 hover:bg-zinc-800 transition text-xs font-medium text-zinc-300"
      >
        <span>Version History ({latestAssets.length} assets)</span>
        <span className="text-zinc-500">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="p-3 space-y-2">
          {latestAssets.length === 0 ? (
            <p className="text-xs text-zinc-500 text-center py-3">
              No assets found.
            </p>
          ) : (
            latestAssets.map((asset) => (
              <div
                key={asset.id}
                className="border border-zinc-800 rounded-lg p-2.5"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded font-medium">
                      {asset.type}
                    </span>
                    <span className="text-xs text-zinc-500">
                      v{asset.version}
                    </span>
                    {asset.version > 1 && (
                      <span className="text-xs bg-blue-500/20 text-blue-400 px-1 py-0.5 rounded">
                        edited
                      </span>
                    )}
                  </div>
                  {asset.version > 1 && (
                    <button
                      onClick={() => loadVersions(asset.id)}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      {loadingId === asset.id
                        ? "Loading..."
                        : versions[asset.id]
                        ? "Hide"
                        : "Show older"}
                    </button>
                  )}
                </div>
                {asset.feedback && (
                  <p className="text-xs text-zinc-500 italic mb-1.5">
                    {asset.feedback}
                  </p>
                )}

                {/* Version list */}
                {versions[asset.id] && (
                  <div className="mt-1.5 pl-2 border-l-2 border-zinc-700 space-y-1">
                    {versions[asset.id].map((v) => (
                      <div
                        key={v.id}
                        className={`flex items-center justify-between p-1.5 rounded text-xs ${
                          v.is_latest
                            ? "bg-blue-500/10"
                            : "bg-zinc-800/50"
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-zinc-300">
                            v{v.version}
                          </span>
                          <span className="text-zinc-600">
                            {new Date(v.created_at).toLocaleString()}
                          </span>
                          {v.is_latest && (
                            <span className="bg-blue-500/20 text-blue-400 px-1 py-0.5 rounded">
                              current
                            </span>
                          )}
                          {v.feedback && (
                            <span className="text-zinc-500 italic truncate max-w-[120px]">
                              {v.feedback}
                            </span>
                          )}
                        </div>
                        {!v.is_latest && (
                          <button
                            onClick={() => handleRestore(v.id)}
                            disabled={restoring}
                            className="text-blue-400 hover:text-blue-300 font-medium disabled:opacity-50"
                          >
                            Restore
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
