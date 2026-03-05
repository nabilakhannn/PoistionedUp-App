"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { clientResearchApi, type ClientDossier, type RefreshSection, type FalseBelief } from "@/lib/api/client-research";
import { JumboBrandChat } from "@/components/jumbo-brand-chat";

interface Props {
  brandId: string;
  dossier: ClientDossier;
  clientName: string;
  intakeShareUrl?: string;
  onLaunch?: () => void;
}

export default function BrandIntelligenceReport({ brandId, dossier: initialDossier, clientName, intakeShareUrl, onLaunch }: Props) {
  const router = useRouter();
  const [dossier, setDossier] = useState(initialDossier);
  const [refreshing, setRefreshing] = useState<RefreshSection | null>(null);
  const [copied, setCopied] = useState(false);
  const [showNextSteps, setShowNextSteps] = useState(false);

  const refresh = async (section: RefreshSection) => {
    setRefreshing(section);
    try {
      const result = await clientResearchApi.refresh(brandId, section);
      setDossier(prev => ({ ...prev, ...result }));
    } catch (e) {
      console.error("Refresh failed:", e);
    } finally {
      setRefreshing(null);
    }
  };

  const copyIntakeLink = async () => {
    const url = intakeShareUrl
      ? `${window.location.origin}${intakeShareUrl}`
      : window.location.origin;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleWritePost = (hook: string) => {
    router.push(`/content?angle=${encodeURIComponent(hook)}&brand_id=${brandId}`);
  };

  if (showNextSteps) {
    return (
      <NextStepsScreen
        clientName={clientName}
        brandId={brandId}
        angles={dossier.first_week_angles || []}
        intakeShareUrl={intakeShareUrl}
        onWritePost={handleWritePost}
        onGoToDashboard={() => onLaunch?.()}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Intelligence modules grid — RADAR-style dark cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Content Pillars */}
        <IntelCard
          icon="📌"
          title="Content Pillars"
          onRefresh={() => refresh("first_week_angles")}
          loading={refreshing === "first_week_angles"}
        >
          <div className="flex flex-wrap gap-2">
            {(dossier.content_pillars || []).map(p => (
              <span key={p} className="px-3 py-1 bg-indigo-900/40 text-indigo-300 rounded-full text-xs font-medium">{p}</span>
            ))}
          </div>
        </IntelCard>

        {/* Voice */}
        <IntelCard
          icon="🎙"
          title="Voice DNA"
          onRefresh={() => refresh("first_week_angles")}
          loading={refreshing === "first_week_angles"}
        >
          <div className="flex flex-wrap gap-2">
            {(dossier.voice_adjectives || []).map(v => (
              <span key={v} className="px-3 py-1 bg-purple-900/40 text-purple-300 rounded-full text-xs font-medium">{v}</span>
            ))}
          </div>
          {dossier.ica_summary && (
            <p className="text-slate-400 text-xs mt-3">
              <span className="text-slate-500">ICA:</span> {dossier.ica_summary}
            </p>
          )}
        </IntelCard>

        {/* Hormozi Framework */}
        <IntelCard
          icon="💊"
          title="Offer Framework (Hormozi)"
          onRefresh={() => refresh("hormozi")}
          loading={refreshing === "hormozi"}
          wide
        >
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(dossier.hormozi || {}).map(([key, val]) => {
              if (key === "risk_reversals" || !val) return null;
              return (
                <div key={key}>
                  <div className="text-xs text-slate-500 capitalize mb-1">{key.replace(/_/g, " ")}</div>
                  <div className="text-xs text-slate-300">{String(val).slice(0, 120)}</div>
                </div>
              );
            })}
          </div>
          {(dossier.hormozi?.risk_reversals?.length ?? 0) > 0 && (
            <div className="mt-3 pt-3 border-t border-white/10">
              <div className="text-xs text-slate-500 mb-2">Risk Reversals</div>
              <div className="flex flex-wrap gap-2">
                {(dossier.hormozi?.risk_reversals || []).map(r => (
                  <span key={r} className="px-2 py-1 bg-green-900/30 text-green-400 rounded text-xs">{r}</span>
                ))}
              </div>
            </div>
          )}
        </IntelCard>

        {/* Competitor Gap */}
        <IntelCard
          icon="🥊"
          title="Competitor Gap"
          onRefresh={() => refresh("competitors")}
          loading={refreshing === "competitors"}
        >
          {dossier.competitor_gap && (
            <p className="text-yellow-300 text-sm font-medium leading-relaxed">&quot;{dossier.competitor_gap}&quot;</p>
          )}
          <div className="mt-3 space-y-2">
            {(dossier.competitors || []).slice(0, 3).map(c => (
              <div key={c.name} className="text-xs">
                <span className="text-slate-400 font-medium">{c.name}:</span>{" "}
                <span className="text-slate-500">{c.gap}</span>
              </div>
            ))}
          </div>
        </IntelCard>

        {/* Transformation — Section 2 */}
        {(dossier.transformation?.zero_state || dossier.transformation?.dream_state) && (
          <IntelCard
            icon="🔄"
            title="Transformation (ZERO → DREAM)"
            onRefresh={() => refresh("transformation")}
            loading={refreshing === "transformation"}
            wide
            collapsible
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-red-400 font-semibold uppercase tracking-wider mb-2">ZERO STATE — Before</div>
                <p className="text-slate-400 text-xs leading-relaxed line-clamp-6">{dossier.transformation?.zero_state}</p>
              </div>
              <div>
                <div className="text-xs text-green-400 font-semibold uppercase tracking-wider mb-2">DREAM STATE — After</div>
                <p className="text-slate-400 text-xs leading-relaxed line-clamp-6">{dossier.transformation?.dream_state}</p>
              </div>
            </div>
            {dossier.transformation?.journey && (
              <div className="mt-3 pt-3 border-t border-white/10">
                <div className="text-xs text-indigo-400 font-semibold uppercase tracking-wider mb-2">The Journey</div>
                <p className="text-slate-400 text-xs leading-relaxed">{dossier.transformation.journey}</p>
              </div>
            )}
          </IntelCard>
        )}

        {/* New Opportunity — Section 3 */}
        {((dossier.uvps?.length ?? 0) > 0 || dossier.tagline) && (
          <IntelCard
            icon="🚀"
            title="New Opportunity (UVPs + Positioning)"
            onRefresh={() => refresh("uvps")}
            loading={refreshing === "uvps"}
            collapsible
          >
            {dossier.tagline && (
              <div className="mb-3 px-3 py-2 bg-indigo-950/40 border border-indigo-500/30 rounded-lg">
                <p className="text-indigo-300 text-sm font-semibold">"{dossier.tagline}"</p>
                {dossier.niche_statement && (
                  <p className="text-slate-400 text-xs mt-1">{dossier.niche_statement}</p>
                )}
              </div>
            )}
            <div className="space-y-2">
              {(dossier.uvps || []).map((uvp, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-indigo-400 text-xs font-bold shrink-0">UVP {i + 1}</span>
                  <p className="text-slate-400 text-xs leading-relaxed">{uvp}</p>
                </div>
              ))}
            </div>
          </IntelCard>
        )}

        {/* Metaphors — Section 4 */}
        {(dossier.metaphors?.length ?? 0) > 0 && (
          <IntelCard
            icon="💡"
            title="Metaphors & Analogies"
            onRefresh={() => refresh("metaphors")}
            loading={refreshing === "metaphors"}
            collapsible
          >
            <div className="space-y-2">
              {(dossier.metaphors || []).map((m, i) => (
                <div key={i} className="flex items-start gap-2 p-2.5 bg-white/5 rounded-lg">
                  <span className="text-yellow-500 text-sm shrink-0">💬</span>
                  <p className="text-slate-300 text-xs leading-relaxed">{m}</p>
                </div>
              ))}
            </div>
          </IntelCard>
        )}

        {/* Your Story — Section 6 */}
        {dossier.your_story?.background && (
          <IntelCard
            icon="📖"
            title="Your Story"
            onRefresh={() => refresh("your_story")}
            loading={refreshing === "your_story"}
            wide
            collapsible
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {dossier.your_story.background && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Origin</div>
                  <p className="text-slate-400 text-xs leading-relaxed line-clamp-4">{dossier.your_story.background}</p>
                </div>
              )}
              {dossier.your_story.growth_achievements && (
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Achievements</div>
                  <p className="text-slate-400 text-xs leading-relaxed line-clamp-4">{dossier.your_story.growth_achievements}</p>
                </div>
              )}
              {dossier.your_story.mission && (
                <div className="md:col-span-2">
                  <div className="text-xs text-purple-400 uppercase tracking-wider mb-1">Mission</div>
                  <p className="text-slate-300 text-xs leading-relaxed">{dossier.your_story.mission}</p>
                </div>
              )}
            </div>
          </IntelCard>
        )}

        {/* Belief Framework — Section 7 */}
        {dossier.belief_framework?.belief_statement && (
          <IntelCard
            icon="🧠"
            title="Belief Framework"
            onRefresh={() => refresh("belief_framework")}
            loading={refreshing === "belief_framework"}
            wide
            collapsible
          >
            <div className="mb-3 px-3 py-2.5 bg-purple-950/30 border border-purple-500/30 rounded-lg">
              <div className="text-xs text-purple-400 uppercase tracking-wider mb-1">Core Belief</div>
              <p className="text-purple-200 text-sm font-medium">"{dossier.belief_framework.belief_statement}"</p>
            </div>
            <div className="space-y-3">
              {(dossier.belief_framework.false_beliefs || []).map((fb: FalseBelief, i: number) => (
                <div key={i} className="p-3 bg-white/5 rounded-xl">
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-red-400 text-xs shrink-0 mt-0.5">✗</span>
                    <p className="text-slate-400 text-xs italic">"{fb.belief}"</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-green-400 text-xs shrink-0 mt-0.5">→</span>
                    <p className="text-slate-300 text-xs">{fb.counter_story}</p>
                  </div>
                </div>
              ))}
            </div>
          </IntelCard>
        )}

        {/* Power Words + Market Gap */}
        {((dossier.power_words?.length ?? 0) > 0 || dossier.market_gap) && (
          <IntelCard
            icon="⚡"
            title="Power Words & Market Gap"
            onRefresh={() => refresh("power_words")}
            loading={refreshing === "power_words"}
            collapsible
          >
            {dossier.market_gap && (
              <div className="mb-3 px-3 py-2 bg-yellow-950/30 border border-yellow-500/30 rounded-lg">
                <div className="text-xs text-yellow-500 uppercase tracking-wider mb-1">Market Gap</div>
                <p className="text-yellow-200 text-xs leading-relaxed">{dossier.market_gap}</p>
              </div>
            )}
            {(dossier.power_words?.length ?? 0) > 0 && (
              <div className="mb-3">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Power Words</div>
                <div className="flex flex-wrap gap-1.5">
                  {(dossier.power_words || []).map(w => (
                    <span key={w} className="px-2 py-1 bg-orange-900/30 text-orange-300 rounded text-xs font-medium">{w}</span>
                  ))}
                </div>
              </div>
            )}
            {(dossier.industry_lingo?.length ?? 0) > 0 && (
              <div>
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Industry Lingo</div>
                <div className="flex flex-wrap gap-1.5">
                  {(dossier.industry_lingo || []).map(l => (
                    <span key={l} className="px-2 py-1 bg-teal-900/30 text-teal-300 rounded text-xs">{l}</span>
                  ))}
                </div>
              </div>
            )}
          </IntelCard>
        )}

        {/* Anxiety List */}
        <IntelCard
          icon="😰"
          title={`Client Anxieties (${(dossier.anxiety_list || []).length})`}
          onRefresh={() => refresh("anxiety_list")}
          loading={refreshing === "anxiety_list"}
          collapsible
        >
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {(dossier.anxiety_list || []).slice(0, 8).map((a, i) => (
              <p key={i} className="text-slate-400 text-xs leading-relaxed">
                <span className="text-slate-600 mr-1">{i + 1}.</span>{a}
              </p>
            ))}
            {(dossier.anxiety_list?.length ?? 0) > 8 && (
              <p className="text-indigo-400 text-xs">+{(dossier.anxiety_list?.length ?? 0) - 8} more...</p>
            )}
          </div>
        </IntelCard>

        {/* Benefit List */}
        <IntelCard
          icon="🌟"
          title={`Client Benefits (${(dossier.benefit_list || []).length})`}
          onRefresh={() => refresh("benefit_list")}
          loading={refreshing === "benefit_list"}
          collapsible
        >
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {(dossier.benefit_list || []).slice(0, 8).map((b, i) => (
              <p key={i} className="text-slate-400 text-xs leading-relaxed">
                <span className="text-green-600 mr-1">{i + 1}.</span>{b}
              </p>
            ))}
            {(dossier.benefit_list?.length ?? 0) > 8 && (
              <p className="text-indigo-400 text-xs">+{(dossier.benefit_list?.length ?? 0) - 8} more...</p>
            )}
          </div>
        </IntelCard>

        {/* Pain Journal */}
        <IntelCard
          icon="📓"
          title="Pain Journal"
          onRefresh={() => refresh("emotional_pain_journal")}
          loading={refreshing === "emotional_pain_journal"}
          collapsible
        >
          <p className="text-slate-400 text-xs leading-relaxed line-clamp-6">
            {dossier.emotional_pain_journal?.slice(0, 400)}...
          </p>
        </IntelCard>

        {/* Win Journal */}
        <IntelCard
          icon="🏆"
          title="Win Journal"
          onRefresh={() => refresh("emotional_win_journal")}
          loading={refreshing === "emotional_win_journal"}
          collapsible
        >
          <p className="text-slate-400 text-xs leading-relaxed line-clamp-6">
            {dossier.emotional_win_journal?.slice(0, 400)}...
          </p>
        </IntelCard>
      </div>

      {/* Content Angles */}
      <div className="bg-[#0d1117] border border-white/10 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            🎯 Content Angles (All Types)
          </h3>
          <RefreshBtn
            onClick={() => refresh("first_week_angles")}
            loading={refreshing === "first_week_angles"}
          />
        </div>
        <div className="space-y-3">
          {(dossier.first_week_angles || []).map((angle, i) => (
            <div key={i} className="flex items-start justify-between gap-4 p-3 bg-white/5 rounded-xl">
              <div className="flex-1">
                <p className="text-white text-sm font-medium">&quot;{angle.hook}&quot;</p>
                <div className="flex gap-3 mt-1.5 text-xs text-slate-500">
                  <span className="capitalize">{angle.angle_type}</span>
                  <span>→ {angle.offer_connection}</span>
                </div>
              </div>
              <button
                onClick={() => handleWritePost(angle.hook)}
                className="shrink-0 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium transition-colors"
              >
                Write Post →
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Ask Jumbo */}
      <div className="bg-[#0d1117] border border-indigo-500/20 rounded-2xl p-5">
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-1">
            ⚡ Ask Jumbo to Generate Anything from This Research
          </h3>
          <p className="text-xs text-slate-500">
            Jumbo has the full 8-section dossier loaded. Click a quick action or type a custom request.
          </p>
        </div>
        <JumboBrandChat brandId={brandId} clientName={clientName} />
      </div>

      {/* Actions */}
      <div className="bg-[#0d1117] border border-white/10 rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Next Steps</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {intakeShareUrl && (
            <button
              onClick={copyIntakeLink}
              className="flex items-center gap-3 p-3 bg-white/5 hover:bg-white/10 rounded-xl transition-colors text-left"
            >
              <span className="text-xl">📋</span>
              <div>
                <div className="text-white text-sm font-medium">
                  {copied ? "Link Copied!" : "Copy Intake Form Link"}
                </div>
                <div className="text-slate-500 text-xs">Send to client before next call</div>
              </div>
            </button>
          )}
          <button
            onClick={() => setShowNextSteps(true)}
            className="flex items-center gap-3 p-3 rounded-xl transition-colors text-left text-white"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
          >
            <span className="text-xl">🚀</span>
            <div>
              <div className="font-semibold text-sm">Launch Content Machine →</div>
              <div className="text-indigo-200 text-xs">See first 5 post angles + schedule</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Next Steps Screen ─────────────────────────────────────────────────────

function NextStepsScreen({
  clientName,
  brandId,
  angles,
  intakeShareUrl,
  onWritePost,
  onGoToDashboard,
}: {
  clientName: string;
  brandId: string;
  angles: ClientDossier["first_week_angles"];
  intakeShareUrl?: string;
  onWritePost: (hook: string) => void;
  onGoToDashboard: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copyLink = async () => {
    if (!intakeShareUrl) return;
    await navigator.clipboard.writeText(`${window.location.origin}${intakeShareUrl}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-[#0d1117] rounded-2xl p-6 space-y-6">
      <div className="text-center">
        <div className="text-4xl mb-3">✅</div>
        <h2 className="text-2xl font-bold text-white">Research Complete.</h2>
        <p className="text-slate-400 mt-1 text-sm">Here&apos;s what happens next for {clientName}:</p>
      </div>

      {/* Content angles */}
      <div>
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          YOUR FIRST CONTENT ANGLES — Each is ready to generate on demand
        </div>
        <div className="space-y-2">
          {(angles || []).map((angle, i) => (
            <div key={i} className="flex items-center justify-between gap-4 p-3 bg-white/5 rounded-xl">
              <p className="text-slate-300 text-sm">{i + 1}. &quot;{angle.hook}&quot;</p>
              <button
                onClick={() => onWritePost(angle.hook)}
                className="shrink-0 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium"
              >
                Write →
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Intake form link */}
      {intakeShareUrl && (
        <div className="p-4 bg-white/5 rounded-xl">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            SEND CLIENT INTAKE FORM
          </div>
          <p className="text-slate-400 text-xs mb-3">Before your next call, have the client fill this in:</p>
          <button
            onClick={copyLink}
            className="w-full py-3 border border-white/20 rounded-xl text-white text-sm font-medium hover:bg-white/10"
          >
            {copied ? "✓ Copied!" : "📋 Copy intake form link"}
          </button>
        </div>
      )}

      <button
        onClick={onGoToDashboard}
        className="w-full py-4 rounded-xl text-white font-semibold"
        style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
      >
        Go to Mission Control →
      </button>
    </div>
  );
}

// ── Intelligence card ─────────────────────────────────────────────────────

function IntelCard({
  icon,
  title,
  children,
  onRefresh,
  loading,
  wide,
  collapsible,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
  onRefresh: () => void;
  loading: boolean;
  wide?: boolean;
  collapsible?: boolean;
}) {
  const [expanded, setExpanded] = useState(!collapsible);
  return (
    <div className={`bg-[#0d1117] border border-white/10 rounded-2xl p-4 ${wide ? "md:col-span-2" : ""}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <span>{icon}</span> {title}
        </h3>
        <div className="flex items-center gap-2">
          {collapsible && (
            <button onClick={() => setExpanded(e => !e)} className="text-xs text-slate-500 hover:text-slate-300">
              {expanded ? "▲" : "▼"}
            </button>
          )}
          <RefreshBtn onClick={onRefresh} loading={loading} />
        </div>
      </div>
      {expanded && children}
    </div>
  );
}

function RefreshBtn({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="text-xs text-slate-500 hover:text-indigo-400 disabled:opacity-40 transition-colors"
      title="Refresh section"
    >
      {loading ? (
        <span className="inline-block w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
      ) : "🔄"}
    </button>
  );
}
