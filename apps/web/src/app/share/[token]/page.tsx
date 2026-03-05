"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://api-iota-puce.vercel.app";

interface DeliverableMeta {
  id: string;
  deliverable_type: string;
  title: string;
  version: number;
  created_at: string;
}

export default function SharePage() {
  const params = useParams();
  const token = params?.token as string;

  const [html, setHtml] = useState<string | null>(null);
  const [meta, setMeta] = useState<DeliverableMeta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;

    async function load() {
      try {
        const res = await fetch(`${API_URL}/share/${token}`, {
          headers: { Accept: "text/html,application/json" },
        });

        if (!res.ok) {
          setError("This deliverable is not available or the link has expired.");
          return;
        }

        const contentType = res.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          const data = await res.json();
          // Nurture sequence returns JSON
          if (data.emails) {
            // Render nurture sequence as readable HTML
            const emails = data.emails as {
              subject: string;
              body: string;
              touchpoint?: number;
            }[];
            const nurturHtml = buildNurtureHtml(emails, data.title);
            setHtml(nurturHtml);
            setMeta({ id: token, deliverable_type: "nurture_sequence", title: data.title || "Nurture Sequence", version: 1, created_at: new Date().toISOString() });
          } else {
            setMeta(data);
          }
        } else {
          const htmlContent = await res.text();
          setHtml(htmlContent);
          setMeta({
            id: token,
            deliverable_type: detectType(htmlContent),
            title: extractTitle(htmlContent),
            version: 1,
            created_at: new Date().toISOString(),
          });
        }
      } catch {
        setError("Failed to load deliverable. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token]);

  function detectType(h: string): string {
    if (h.includes("proposal") || h.includes("Proposal")) return "proposal";
    if (h.includes("landing") || h.includes("Landing")) return "landing_page";
    return "document";
  }

  function extractTitle(h: string): string {
    const match = h.match(/<title[^>]*>([^<]+)<\/title>/i);
    return match?.[1] || "Deliverable Preview";
  }

  function buildNurtureHtml(
    emails: { subject: string; body: string; touchpoint?: number }[],
    title: string
  ): string {
    const items = emails
      .map(
        (e, i) => `
      <div class="email-card">
        <div class="tp">Touch ${e.touchpoint ?? i + 1}</div>
        <div class="subject">Subject: ${e.subject}</div>
        <div class="body">${e.body.replace(/\n/g, "<br>")}</div>
      </div>`
      )
      .join("");

    return `<!DOCTYPE html><html><head><title>${title}</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a14;color:#e2e8f0;margin:0;padding:40px 20px;}
  h1{color:#fff;font-size:1.5rem;margin-bottom:24px;}
  .email-card{background:#111827;border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:24px;margin-bottom:16px;}
  .tp{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#6366f1;margin-bottom:8px;}
  .subject{font-size:13px;font-weight:600;color:#a5b4fc;margin-bottom:12px;}
  .body{font-size:13px;color:#94a3b8;line-height:1.7;}
</style></head><body>
<h1>${title}</h1>${items}
</body></html>`;
  }

  function handleDownload() {
    if (!html) return;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${meta?.title || "deliverable"}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a14] flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading deliverable...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a14] flex items-center justify-center px-4">
        <div className="text-center">
          <div className="text-4xl mb-4">🔒</div>
          <h1 className="text-white text-xl font-bold mb-2">Link Not Found</h1>
          <p className="text-slate-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const typeLabel: Record<string, string> = {
    proposal: "Proposal",
    landing_page: "Landing Page",
    nurture_sequence: "Nurture Sequence",
    ad_creative: "Ad Creatives",
    document: "Document",
  };

  return (
    <div className="min-h-screen bg-[#0a0a14] flex flex-col">
      {/* Header bar */}
      <div className="h-14 bg-[#0d1117] border-b border-white/10 flex items-center justify-between px-5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">P</span>
          </div>
          <div>
            <div className="text-white text-sm font-semibold">
              {meta?.title || "Deliverable"}
            </div>
            <div className="text-slate-500 text-xs">
              {meta?.deliverable_type
                ? typeLabel[meta.deliverable_type] || meta.deliverable_type
                : "Preview"}{" "}
              {meta?.version ? `· v${meta.version}` : ""}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {html && (
            <button
              onClick={handleDownload}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-lg font-medium transition-colors"
            >
              Download
            </button>
          )}
          <div className="text-slate-600 text-xs">
            Powered by PositionedUp
          </div>
        </div>
      </div>

      {/* Content */}
      {html ? (
        <iframe
          srcDoc={html}
          sandbox="allow-same-origin"
          className="flex-1 w-full border-0"
          title={meta?.title || "Deliverable Preview"}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500 text-sm">No content to display.</p>
        </div>
      )}
    </div>
  );
}
