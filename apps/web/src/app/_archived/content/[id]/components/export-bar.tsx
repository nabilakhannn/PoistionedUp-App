"use client";

import { useState, useEffect } from "react";
import { contentApi, scheduleApi, oauthApi } from "@/lib/api";

interface ExportBarProps {
  workflowId: string;
  compact?: boolean;
}

export function ExportBar({ workflowId, compact }: ExportBarProps) {
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [googleLoading, setGoogleLoading] = useState(false);
  const [notionLoading, setNotionLoading] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [googleConnected, setGoogleConnected] = useState<boolean | null>(null);
  const [notionConnected, setNotionConnected] = useState<boolean | null>(null);

  // Check OAuth connection status on mount
  useEffect(() => {
    oauthApi
      .googleStatus()
      .then((s) => setGoogleConnected(s.connected))
      .catch(() => setGoogleConnected(false));
    oauthApi
      .notionStatus()
      .then((s) => setNotionConnected(s.connected))
      .catch(() => setNotionConnected(false));
  }, []);

  const handleCopyClipboard = async () => {
    try {
      const result = await contentApi.exportClipboard(workflowId);
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setExportMsg("Failed to copy");
      setTimeout(() => setExportMsg(""), 3000);
    }
  };

  const handleDownloadMarkdown = async () => {
    setDownloading(true);
    try {
      const md = await contentApi.exportMarkdown(workflowId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `content-${workflowId.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setExportMsg("Download failed");
      setTimeout(() => setExportMsg(""), 3000);
    } finally {
      setDownloading(false);
    }
  };

  /** Extract a human-friendly message from an API error string. */
  const friendlyError = (raw: string, fallback: string): string => {
    // API errors look like 'API 503: {"detail":"..."}' -- pull the detail out
    const detailMatch = raw.match(/"detail"\s*:\s*"([^"]+)"/);
    const detail = detailMatch ? detailMatch[1] : "";

    if (detail.includes("not configured") || raw.includes("503"))
      return "Not configured yet. Ask your admin to add the credentials.";
    if (detail.includes("No content found") || raw.includes("404"))
      return "No finished content to export yet. Complete the pipeline first.";
    return fallback;
  };

  const handleGoogleDocsExport = async () => {
    if (!googleConnected) {
      try {
        const { url } = await oauthApi.googleAuthUrl();
        window.location.href = url;
      } catch (e: any) {
        setExportMsg(friendlyError(e.message, "Google Docs not available"));
        setTimeout(() => setExportMsg(""), 4000);
      }
      return;
    }
    setGoogleLoading(true);
    setExportMsg("");
    try {
      const result = await contentApi.exportGoogleDocs(workflowId);
      window.open(result.url, "_blank");
      setExportMsg("Google Doc created");
      setTimeout(() => setExportMsg(""), 3000);
    } catch (e: any) {
      setExportMsg(friendlyError(e.message, "Google Docs export failed"));
      setTimeout(() => setExportMsg(""), 4000);
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleNotionExport = async () => {
    if (!notionConnected) {
      try {
        const { url } = await oauthApi.notionAuthUrl();
        window.location.href = url;
      } catch (e: any) {
        setExportMsg(friendlyError(e.message, "Notion not available"));
        setTimeout(() => setExportMsg(""), 4000);
      }
      return;
    }
    setNotionLoading(true);
    setExportMsg("");
    try {
      const result = await contentApi.exportNotion(workflowId);
      window.open(result.url, "_blank");
      setExportMsg("Notion page created");
      setTimeout(() => setExportMsg(""), 3000);
    } catch (e: any) {
      setExportMsg(friendlyError(e.message, "Notion export failed"));
      setTimeout(() => setExportMsg(""), 4000);
    } finally {
      setNotionLoading(false);
    }
  };

  const handleImportToSchedule = async () => {
    setImporting(true);
    setImportMsg("");
    try {
      const result = await scheduleApi.importFromWorkflow(workflowId);
      setImportMsg(`Imported ${result.imported} items to schedule`);
      setTimeout(() => setImportMsg(""), 3000);
    } catch (e: any) {
      setImportMsg(friendlyError(e.message, "Import failed"));
      setTimeout(() => setImportMsg(""), 4000);
    } finally {
      setImporting(false);
    }
  };

  // Compact mode for sidebar
  if (compact) {
    return (
      <div className="space-y-1.5">
        <button
          onClick={handleCopyClipboard}
          className="w-full text-left text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg transition-colors"
        >
          {copied ? "✓ Copied!" : "📋 Copy to clipboard"}
        </button>
        <button
          onClick={handleDownloadMarkdown}
          disabled={downloading}
          className="w-full text-left text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {downloading ? "Downloading..." : "⬇️ Download .md"}
        </button>
        <button
          onClick={handleGoogleDocsExport}
          disabled={googleLoading}
          className="w-full text-left text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {googleLoading
            ? "Creating..."
            : googleConnected
            ? "📄 Google Docs"
            : "📄 Connect Google"}
        </button>
        <button
          onClick={handleNotionExport}
          disabled={notionLoading}
          className="w-full text-left text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {notionLoading
            ? "Creating..."
            : notionConnected
            ? "📝 Notion"
            : "📝 Connect Notion"}
        </button>
        <button
          onClick={handleImportToSchedule}
          disabled={importing}
          className="w-full text-left text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          {importing ? "Importing..." : "📅 Add to Schedule"}
        </button>
        {(importMsg || exportMsg) && (
          <p
            className={`text-xs px-1 ${
              (importMsg || exportMsg || "").includes("failed") ||
              (importMsg || exportMsg || "").includes("not") ||
              (importMsg || exportMsg || "").includes("No ")
                ? "text-amber-400"
                : "text-green-400"
            }`}
          >
            {importMsg || exportMsg}
          </p>
        )}
      </div>
    );
  }

  // Full mode for completed section
  return (
    <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="text-green-400 font-medium text-sm">
            Content approved and ready
          </h3>
          <p className="text-zinc-400 text-xs mt-0.5">
            Generated, edited, tested, and approved.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={handleCopyClipboard}
            className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 text-zinc-300 rounded-lg text-xs font-medium hover:bg-zinc-700 transition"
          >
            {copied ? "Copied!" : "📋 Copy"}
          </button>
          <button
            onClick={handleDownloadMarkdown}
            disabled={downloading}
            className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-500 transition disabled:opacity-50"
          >
            {downloading ? "..." : "⬇️ Download .md"}
          </button>
          <button
            onClick={handleGoogleDocsExport}
            disabled={googleLoading}
            className="px-3 py-1.5 bg-zinc-800 border border-blue-500/30 text-blue-400 rounded-lg text-xs font-medium hover:bg-zinc-700 transition disabled:opacity-50"
            title={
              googleConnected
                ? "Send to Google Docs"
                : "Connect Google account first"
            }
          >
            {googleLoading
              ? "Creating..."
              : googleConnected
              ? "📄 Google Docs"
              : "📄 Connect Google"}
          </button>
          <button
            onClick={handleNotionExport}
            disabled={notionLoading}
            className="px-3 py-1.5 bg-zinc-800 border border-zinc-600 text-zinc-300 rounded-lg text-xs font-medium hover:bg-zinc-700 transition disabled:opacity-50"
            title={
              notionConnected
                ? "Send to Notion"
                : "Connect Notion account first"
            }
          >
            {notionLoading
              ? "Creating..."
              : notionConnected
              ? "📝 Notion"
              : "📝 Connect Notion"}
          </button>
          <button
            onClick={handleImportToSchedule}
            disabled={importing}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-500 transition disabled:opacity-50"
          >
            {importing ? "Importing..." : "📅 Schedule"}
          </button>
        </div>
      </div>
      {importMsg && (
        <p
          className={`text-xs mt-2 ${
            importMsg.includes("failed") ||
            importMsg.includes("not") ||
            importMsg.includes("No ")
              ? "text-amber-400"
              : "text-green-400"
          }`}
        >
          {importMsg}
        </p>
      )}
      {exportMsg && (
        <p
          className={`text-xs mt-2 ${
            exportMsg.includes("failed") ||
            exportMsg.includes("not") ||
            exportMsg.includes("No ")
              ? "text-amber-400"
              : "text-blue-400"
          }`}
        >
          {exportMsg}
        </p>
      )}
    </div>
  );
}
