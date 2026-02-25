"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { personalBrandsApi, BrandResearchSession } from "@/lib/api/brand";
import { scheduleApi } from "@/lib/api/schedule";

const STAGE_LABELS: Record<string, string> = {
  niche_analysis: "Niche Analysis",
  audience_research: "Audience Research",
  competitive_intel: "Competitive Intelligence",
  content_landscape: "Content Landscape",
  voice_positioning: "Voice & Positioning",
  content_strategy: "Content Strategy",
  content_ideas: "Content Ideas",
};

const STAGE_ICONS: Record<string, string> = {
  niche_analysis: "1",
  audience_research: "2",
  competitive_intel: "3",
  content_landscape: "4",
  voice_positioning: "5",
  content_strategy: "6",
  content_ideas: "7",
};

const STAGES = [
  "niche_analysis",
  "audience_research",
  "competitive_intel",
  "content_landscape",
  "voice_positioning",
  "content_strategy",
  "content_ideas",
];

interface ResearchPanelProps {
  brandId: string;
  brandName: string;
  brandDescription: string;
  onResearchApplied: () => void;
}

export function ResearchPanel({
  brandId,
  brandName,
  brandDescription,
  onResearchApplied,
}: ResearchPanelProps) {
  const [session, setSession] = useState<BrandResearchSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [industry, setIndustry] = useState("");
  const [description, setDescription] = useState(brandDescription || "");
  const [expandedStage, setExpandedStage] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [appliedFields, setAppliedFields] = useState<Record<string, string> | null>(null);
  const [scheduling, setScheduling] = useState(false);
  const [scheduledCount, setScheduledCount] = useState<number | null>(null);
  const [skipping, setSkipping] = useState(false);
  const router = useRouter();

  // Load existing sessions on mount
  const loadExisting = useCallback(async () => {
    try {
      const data = await personalBrandsApi.listResearch(brandId);
      if (data.sessions.length > 0) {
        setSession(data.sessions[0]);
      }
    } catch {
      // No existing sessions
    }
  }, [brandId]);

  // Start research
  const handleStart = async () => {
    if (!industry.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const sess = await personalBrandsApi.startResearch(brandId, {
        industry: industry.trim(),
        name: brandName,
        description: description.trim(),
      });
      setSession(sess);
    } catch (err: any) {
      setError(err.message || "Failed to start research");
    } finally {
      setLoading(false);
    }
  };

  // Run next stage or all stages
  const handleRun = async (runAll: boolean = false) => {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await personalBrandsApi.runResearchStage(
        brandId,
        session.id,
        runAll,
      );
      setSession(updated);
    } catch (err: any) {
      setError(err.message || "Research stage failed");
      // Refresh session to get latest state
      try {
        const refreshed = await personalBrandsApi.getResearch(brandId, session.id);
        setSession(refreshed);
      } catch {
        // ignore
      }
    } finally {
      setLoading(false);
    }
  };

  // Apply research to profile
  const handleApply = async () => {
    if (!session || session.status !== "completed") return;
    setApplying(true);
    try {
      const result = await personalBrandsApi.applyResearch(brandId, session.id);
      setAppliedFields(result.prefilled_fields);
      onResearchApplied();
    } catch (err: any) {
      setError(err.message || "Failed to apply research");
    } finally {
      setApplying(false);
    }
  };

  // Skip a failed stage
  const handleSkip = async () => {
    if (!session) return;
    setSkipping(true);
    setError(null);
    try {
      const updated = await personalBrandsApi.skipResearchStage(brandId, session.id);
      setSession(updated);
    } catch (err: any) {
      setError(err.message || "Failed to skip stage");
    } finally {
      setSkipping(false);
    }
  };

  // Auto-schedule content ideas from research
  const handleAutoSchedule = async (scheduleDates: boolean = false) => {
    if (!session) return;
    setScheduling(true);
    setError(null);
    try {
      const result = await scheduleApi.createFromResearch(session.id, scheduleDates);
      setScheduledCount(result.created);
    } catch (err: any) {
      setError(err.message || "Failed to create schedule items");
    } finally {
      setScheduling(false);
    }
  };

  const completedCount = session?.stages_completed?.length ?? 0;
  const totalStages = STAGES.length;
  const progressPct = totalStages > 0 ? Math.round((completedCount / totalStages) * 100) : 0;

  // If no session yet, show the start form
  if (!session) {
    return (
      <div className="bg-gradient-to-br from-violet-950/40 to-zinc-900 border border-violet-800/30 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-violet-600/20 flex items-center justify-center text-xl">
            🔬
          </div>
          <div>
            <h3 className="text-lg font-bold text-zinc-100">AI Brand Research</h3>
            <p className="text-xs text-zinc-400">
              Let AI research your niche, audience, competitors, and more
            </p>
          </div>
        </div>

        <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
          Provide your industry and a brief description. Our AI will run 7 research
          stages — niche analysis, audience research, competitive intelligence, content
          landscape, voice positioning, content strategy, and content ideas — then
          pre-fill your brand profile with the findings.
        </p>

        <div className="space-y-3 mb-4">
          <div>
            <label className="text-xs font-medium text-zinc-400 block mb-1">
              Industry / Niche *
            </label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. Personal branding for tech professionals"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-zinc-400 block mb-1">
              What do you do? (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe what you do and who you help..."
              rows={2}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-violet-500 resize-none"
            />
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-400 mb-3">{error}</p>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleStart}
            disabled={!industry.trim() || loading}
            className="flex-1 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-bold hover:bg-violet-500 disabled:opacity-40 transition"
          >
            {loading ? "Starting..." : "Start AI Research"}
          </button>
          <button
            onClick={loadExisting}
            className="px-4 py-2.5 rounded-lg bg-zinc-800 text-zinc-400 text-sm hover:text-zinc-200 transition"
          >
            Load Previous
          </button>
        </div>
      </div>
    );
  }

  // Session in progress or completed
  return (
    <div className="bg-gradient-to-br from-violet-950/40 to-zinc-900 border border-violet-800/30 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-zinc-800/50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600/20 flex items-center justify-center text-xl">
              🔬
            </div>
            <div>
              <h3 className="text-lg font-bold text-zinc-100">Brand Research Pipeline</h3>
              <p className="text-xs text-zinc-500">
                {session.seed_input.industry}
              </p>
            </div>
          </div>
          <StatusBadge status={session.status} />
        </div>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">
              Progress
            </span>
            <span className="text-xs text-zinc-400 font-mono">
              {completedCount}/{totalStages} stages
            </span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-600 to-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stages list */}
      <div className="divide-y divide-zinc-800/50">
        {STAGES.map((stage) => {
          const isCompleted = session.stages_completed?.includes(stage);
          const isCurrent = session.current_stage === stage && session.status === "running";
          const isExpanded = expandedStage === stage;
          const stageResult = session.results?.[stage];

          return (
            <div key={stage} className="px-6 py-3">
              <button
                onClick={() => setExpandedStage(isExpanded ? null : stage)}
                className="w-full text-left flex items-center gap-3"
                disabled={!isCompleted && !isCurrent}
              >
                {/* Stage number circle */}
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition ${
                    isCompleted
                      ? "bg-green-500/20 text-green-400 border border-green-500/30"
                      : isCurrent
                        ? "bg-violet-500/20 text-violet-400 border border-violet-500/30 animate-pulse"
                        : "bg-zinc-800 text-zinc-600 border border-zinc-700"
                  }`}
                >
                  {isCompleted ? "✓" : STAGE_ICONS[stage]}
                </div>

                <div className="flex-1 min-w-0">
                  <h4
                    className={`text-sm font-medium truncate ${
                      isCompleted
                        ? "text-zinc-200"
                        : isCurrent
                          ? "text-violet-300"
                          : "text-zinc-500"
                    }`}
                  >
                    {STAGE_LABELS[stage]}
                  </h4>
                </div>

                {isCompleted && stageResult && (
                  <span className="text-[10px] text-zinc-500">
                    {isExpanded ? "▲" : "▼"}
                  </span>
                )}
              </button>

              {/* Expanded result preview */}
              {isExpanded && stageResult && (
                <div className="mt-3 ml-11 bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <StageResultPreview stage={stage} result={stageResult} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Actions footer */}
      <div className="px-6 py-4 border-t border-zinc-800/50 bg-zinc-900/50">
        {error && (
          <p className="text-xs text-red-400 mb-3">{error}</p>
        )}

        {session.status === "failed" && session.error && (
          <div className="mb-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400 font-bold mb-1">Stage failed</p>
            <p className="text-[10px] text-zinc-400">{session.error}</p>
          </div>
        )}

        {appliedFields && (
          <div className="mb-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <p className="text-xs text-green-400 font-bold mb-1">
              Research applied! {Object.keys(appliedFields).length} fields pre-filled.
            </p>
            <p className="text-[10px] text-zinc-400">
              Review and refine in the brand strategist.
            </p>
          </div>
        )}

        {scheduledCount !== null && (
          <div className="mb-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-xs text-blue-400 font-bold mb-1">
              {scheduledCount} content ideas added to your schedule!
            </p>
            <button
              onClick={() => router.push("/schedule")}
              className="text-[10px] text-blue-400 underline hover:text-blue-300 transition"
            >
              View schedule
            </button>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {/* Running / Pending — show Run Next + Run All */}
          {session.status !== "completed" && session.status !== "failed" && (
            <>
              <button
                onClick={() => handleRun(false)}
                disabled={loading}
                className="flex-1 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-bold hover:bg-violet-500 disabled:opacity-40 transition"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running {STAGE_LABELS[session.current_stage]}...
                  </span>
                ) : (
                  `Run Next: ${STAGE_LABELS[session.current_stage] || "Stage"}`
                )}
              </button>
              <button
                onClick={() => handleRun(true)}
                disabled={loading}
                className="px-4 py-2.5 rounded-lg bg-zinc-800 text-zinc-300 text-sm font-medium hover:bg-zinc-700 disabled:opacity-40 transition"
              >
                Run All
              </button>
            </>
          )}

          {/* Failed — show Retry + Skip */}
          {session.status === "failed" && (
            <>
              <button
                onClick={() => handleRun(false)}
                disabled={loading}
                className="flex-1 px-4 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-bold hover:bg-violet-500 disabled:opacity-40 transition"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Retrying...
                  </span>
                ) : (
                  "Retry Failed Stage"
                )}
              </button>
              <button
                onClick={handleSkip}
                disabled={skipping || loading}
                className="px-4 py-2.5 rounded-lg bg-amber-600/20 text-amber-400 text-sm font-medium border border-amber-600/30 hover:bg-amber-600/30 disabled:opacity-40 transition"
              >
                {skipping ? "Skipping..." : "Skip & Continue"}
              </button>
            </>
          )}

          {/* Completed — show Apply + Auto-Schedule */}
          {session.status === "completed" && !appliedFields && (
            <button
              onClick={handleApply}
              disabled={applying}
              className="flex-1 px-4 py-2.5 rounded-lg bg-green-600 text-white text-sm font-bold hover:bg-green-500 disabled:opacity-40 transition"
            >
              {applying ? "Applying..." : "Apply Research to Brand Profile"}
            </button>
          )}

          {session.status === "completed" && session.results?.content_ideas && scheduledCount === null && (
            <button
              onClick={() => handleAutoSchedule(false)}
              disabled={scheduling}
              className="px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-bold hover:bg-blue-500 disabled:opacity-40 transition"
            >
              {scheduling ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Scheduling...
                </span>
              ) : (
                "Auto-Schedule Ideas"
              )}
            </button>
          )}

          {(session.status === "completed" || session.status === "failed") && (
            <button
              onClick={() => { setSession(null); setAppliedFields(null); setError(null); setScheduledCount(null); }}
              className="px-4 py-2.5 rounded-lg bg-zinc-800 text-zinc-400 text-sm hover:text-zinc-200 transition"
            >
              New Research
            </button>
          )}
        </div>
      </div>
    </div>
  );
}


function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    pending: { bg: "bg-zinc-500/20", text: "text-zinc-400", label: "READY" },
    running: { bg: "bg-violet-500/20", text: "text-violet-400", label: "RUNNING" },
    completed: { bg: "bg-green-500/20", text: "text-green-400", label: "COMPLETE" },
    failed: { bg: "bg-red-500/20", text: "text-red-400", label: "FAILED" },
    cancelled: { bg: "bg-zinc-500/20", text: "text-zinc-500", label: "CANCELLED" },
  };
  const s = styles[status] || styles.pending;
  return (
    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${s.bg} ${s.text}`}>
      {status === "running" && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse mr-1.5" />
      )}
      {s.label}
    </span>
  );
}


function StageResultPreview({ stage, result }: { stage: string; result: any }) {
  if (!result) return <p className="text-xs text-zinc-500">No results</p>;

  switch (stage) {
    case "niche_analysis":
      return (
        <div className="space-y-2 text-xs">
          <p className="text-zinc-300">{result.industry_overview}</p>
          <p className="text-zinc-400"><strong className="text-zinc-300">Recommended Niche:</strong> {result.recommended_niche}</p>
          <p className="text-zinc-500 text-[11px]">{result.recommended_niche_reasoning}</p>
          {result.sub_niches?.map((n: any, i: number) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-violet-400 font-mono text-[10px]">{n.opportunity_score}/10</span>
              <span className="text-zinc-300">{n.name}</span>
            </div>
          ))}
        </div>
      );

    case "audience_research":
      return (
        <div className="space-y-2 text-xs">
          {result.primary_audience && (
            <p className="text-zinc-300">
              Age: {result.primary_audience.age_range} | Income: {result.primary_audience.income_level}
            </p>
          )}
          <div>
            <p className="text-zinc-400 font-bold mb-1">Pain Points:</p>
            {result.pain_points?.slice(0, 5).map((p: any, i: number) => (
              <p key={i} className="text-zinc-300 ml-2">- {p.pain_point} <span className="text-zinc-500">({p.severity}/10)</span></p>
            ))}
          </div>
        </div>
      );

    case "competitive_intel":
      return (
        <div className="space-y-2 text-xs">
          <p className="text-zinc-400">{result.competitive_landscape}</p>
          {result.competitors?.slice(0, 5).map((c: any, i: number) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-blue-400 font-bold">{c.name}</span>
              <span className="text-zinc-500">({c.platform})</span>
            </div>
          ))}
          {result.market_gaps?.length > 0 && (
            <div className="mt-2">
              <p className="text-zinc-400 font-bold">Gaps:</p>
              {result.market_gaps.slice(0, 3).map((g: any, i: number) => (
                <p key={i} className="text-zinc-300 ml-2">- {g.gap}</p>
              ))}
            </div>
          )}
        </div>
      );

    case "voice_positioning":
      return (
        <div className="space-y-2 text-xs">
          <p className="text-zinc-300"><strong>Positioning:</strong> {result.positioning_statement}</p>
          <p className="text-zinc-300"><strong>IT Factor:</strong> {result.it_factor}</p>
          {result.voice_options?.map((v: any, i: number) => (
            <div key={i} className={`p-2 rounded-lg border ${v.name === result.recommended_voice ? "border-violet-500/30 bg-violet-500/10" : "border-zinc-700 bg-zinc-800"}`}>
              <p className="font-bold text-zinc-200">{v.name} {v.name === result.recommended_voice && <span className="text-violet-400 text-[10px]">RECOMMENDED</span>}</p>
              <p className="text-zinc-400">{v.description}</p>
              <p className="text-zinc-500 text-[10px]">Tone: {v.tone_words?.join(", ")}</p>
            </div>
          ))}
        </div>
      );

    case "content_strategy":
      return (
        <div className="space-y-2 text-xs">
          {result.content_pillars?.map((p: any, i: number) => (
            <div key={i} className="p-2 bg-zinc-800 rounded-lg border border-zinc-700">
              <p className="font-bold text-zinc-200">{p.name} <span className="text-zinc-500">({p.content_ratio}%)</span></p>
              <p className="text-zinc-400">{p.description}</p>
            </div>
          ))}
        </div>
      );

    case "content_ideas":
      return (
        <div className="space-y-2 text-xs">
          {result.quick_wins && (
            <div className="p-2 bg-green-500/10 border border-green-500/20 rounded-lg mb-2">
              <p className="font-bold text-green-400 text-[10px] mb-1">QUICK WINS</p>
              {result.quick_wins.map((w: string, i: number) => (
                <p key={i} className="text-zinc-300">{i + 1}. {w}</p>
              ))}
            </div>
          )}
          {result.content_ideas?.slice(0, 5).map((idea: any, i: number) => (
            <div key={i}>
              <p className="font-bold text-zinc-200">{idea.title}</p>
              <p className="text-zinc-500">{idea.format} | {idea.platform} | {idea.estimated_engagement}</p>
            </div>
          ))}
        </div>
      );

    default:
      return (
        <pre className="text-[10px] text-zinc-400 whitespace-pre-wrap">
          {JSON.stringify(result, null, 2).slice(0, 1000)}
        </pre>
      );
  }
}
