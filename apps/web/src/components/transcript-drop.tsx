"use client";

import { useState } from "react";
import { accountManagerApi, type AccountManagerSession } from "@/lib/api/account-manager";
import { intakeApi } from "@/lib/api/intake";
import AccountManagerPanel from "./account-manager-panel";

interface Props {
  brandId: string;
  onSessionCreated?: (session: AccountManagerSession) => void;
}

type InputTab = "paste" | "upload" | "intake" | "mcp";

export default function TranscriptDrop({ brandId, onSessionCreated }: Props) {
  const [tab, setTab] = useState<InputTab>("paste");
  const [transcript, setTranscript] = useState("");
  const [callDate, setCallDate] = useState("");
  const [intakeFormId, setIntakeFormId] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<AccountManagerSession | null>(null);

  // Intake form
  const [intakeForm, setIntakeForm] = useState<{ id: string; share_url: string } | null>(null);
  const [creatingIntake, setCreatingIntake] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);

  const apiKey = "••••••••••••••••"; // placeholder — user copies from Settings

  const handleAnalyze = async () => {
    if (!transcript.trim()) { setError("Transcript is required."); return; }
    setError(null);
    setAnalyzing(true);
    try {
      const result = await accountManagerApi.analyze({
        brand_id: brandId,
        transcript,
        call_date: callDate || undefined,
        intake_form_id: intakeFormId || undefined,
      });
      setSession(result);
      onSessionCreated?.(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  const createIntakeForm = async () => {
    setCreatingIntake(true);
    try {
      const form = await intakeApi.create(brandId);
      setIntakeForm(form);
      setIntakeFormId(form.id);
    } catch { /* silent */ }
    finally { setCreatingIntake(false); }
  };

  const copyText = async (text: string, setCopied: (v: boolean) => void) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (session) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setSession(null)}
            className="text-xs text-slate-500 hover:text-slate-300"
          >
            ← New Analysis
          </button>
        </div>
        <AccountManagerPanel
          session={session}
          onUpdate={updated => setSession(updated)}
        />
      </div>
    );
  }

  return (
    <div className="bg-[#0d1117] border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex border-b border-white/10">
        {(["paste", "upload", "intake", "mcp"] as InputTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-3 text-xs font-medium transition-colors capitalize ${
              tab === t
                ? "text-indigo-400 border-b-2 border-indigo-500 bg-indigo-950/20"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t === "paste" ? "📝 Paste" : t === "upload" ? "📁 Upload" : t === "intake" ? "📋 Intake" : "🔌 MCP"}
          </button>
        ))}
      </div>

      <div className="p-5 space-y-4">
        {error && (
          <div className="px-3 py-2 bg-red-900/30 border border-red-500/30 text-red-400 rounded-lg text-xs">{error}</div>
        )}

        {/* Paste tab */}
        {tab === "paste" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-500 mb-2">Call transcript</label>
              <textarea
                value={transcript}
                onChange={e => setTranscript(e.target.value)}
                rows={10}
                placeholder="Paste your call transcript here. Can be from Zoom, Otter.ai, Loom, or any recording service..."
                className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 resize-none focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-2">Call date (optional)</label>
              <input
                type="date"
                value={callDate}
                onChange={e => setCallDate(e.target.value)}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        )}

        {/* Upload tab */}
        {tab === "upload" && (
          <div className="space-y-4">
            <label className="block border-2 border-dashed border-white/10 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-500/50 transition-colors">
              <span className="text-4xl block mb-3">📁</span>
              <p className="text-slate-400 text-sm">Drop a transcript file or click to browse</p>
              <p className="text-slate-600 text-xs mt-1">.txt, .md, .docx supported</p>
              <input
                type="file"
                accept=".txt,.md,.docx"
                className="hidden"
                onChange={async e => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const text = await file.text();
                  setTranscript(text);
                  setTab("paste");
                }}
              />
            </label>
          </div>
        )}

        {/* Intake form tab */}
        {tab === "intake" && (
          <div className="space-y-4">
            <p className="text-slate-400 text-sm">
              If your client filled in an intake form, link it here so the Account Manager can read it alongside the transcript.
            </p>
            {intakeForm ? (
              <div className="p-4 bg-green-900/20 border border-green-500/30 rounded-xl">
                <p className="text-green-400 text-xs font-medium mb-2">✓ Intake form linked</p>
                <p className="text-slate-500 text-xs">Form ID: {intakeForm.id.slice(0, 8)}...</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-2">Or paste an existing form ID</label>
                  <input
                    value={intakeFormId}
                    onChange={e => setIntakeFormId(e.target.value)}
                    placeholder="UUID of intake form..."
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="text-center text-xs text-slate-600">or</div>
                <button
                  onClick={createIntakeForm}
                  disabled={creatingIntake}
                  className="w-full py-3 border border-white/10 text-slate-400 hover:text-slate-200 rounded-xl text-sm"
                >
                  {creatingIntake ? "Creating..." : "Create new intake form →"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* MCP tab */}
        {tab === "mcp" && (
          <div className="space-y-4">
            <p className="text-slate-300 text-sm font-medium">Connect from Claude.ai</p>
            <div className="space-y-3">
              <Step n={1} label="Copy your API key" />
              <CopyBox value={apiKey} label="API Key" />
              <Step n={2} label="Add this to Claude.ai → Settings → Integrations → Custom" />
              <CopyBox value="https://api-iota-puce.vercel.app/mcp" label="MCP URL" />
              <div className="pt-2 border-t border-white/10">
                <p className="text-xs text-slate-500 mb-2">Or use the REST endpoint directly:</p>
                <div className="bg-black/50 rounded-xl p-3 font-mono text-xs text-slate-400 overflow-x-auto">
                  <span className="text-green-400">curl</span> -X POST https://api-iota-puce.vercel.app/agent-api/transcript/analyze \{"\n"}
                  {"  "}-H <span className="text-yellow-300">&quot;X-Agent-Key: YOUR_KEY&quot;</span> \{"\n"}
                  {"  "}-H <span className="text-yellow-300">&quot;X-User-Id: YOUR_USER_ID&quot;</span> \{"\n"}
                  {"  "}-d <span className="text-yellow-300">&apos;&#123;&quot;brand_id&quot;: &quot;...&quot;, &quot;transcript&quot;: &quot;...&quot;&#125;&apos;</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analyze button */}
        {(tab === "paste" || tab === "upload") && (
          <button
            onClick={handleAnalyze}
            disabled={analyzing || !transcript.trim()}
            className="w-full py-4 rounded-xl text-white font-semibold disabled:opacity-40 transition-all"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
          >
            {analyzing ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing call...
              </span>
            ) : "Analyze Call →"}
          </button>
        )}
      </div>
    </div>
  );
}

function Step({ n, label }: { n: number; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center shrink-0">{n}</span>
      <span className="text-slate-400 text-sm">{label}</span>
    </div>
  );
}

function CopyBox({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center gap-2 p-3 bg-white/5 rounded-xl">
      <span className="flex-1 text-slate-300 text-xs font-mono truncate">{value}</span>
      <button
        onClick={async () => {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        }}
        className="text-xs text-indigo-400 hover:text-indigo-300 shrink-0"
      >
        {copied ? "✓" : "Copy"}
      </button>
    </div>
  );
}
