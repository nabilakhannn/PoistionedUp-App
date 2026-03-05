"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { personalBrandsApi } from "@/lib/api/brand";
import { clientResearchApi, type ClientDossier } from "@/lib/api/client-research";
import { intakeApi } from "@/lib/api/intake";
import BrandIntelligenceReport from "@/components/brand-intelligence-report";

type Step = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
type ContentGoal = "Get new leads" | "Build authority" | "Nurture existing audience";

const RESEARCH_STEPS = [
  "Reading LinkedIn profile and posts...",
  "Analysing writing style and voice...",
  "Scanning website for offer and social proof...",
  "Mapping ideal customer pain points...",
  "Building Hormozi offer framework...",
  "Identifying competitor gaps...",
  "Generating content strategy...",
];

export default function ClientOnboardingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const existingBrandId = searchParams.get("brand_id");

  const [step, setStep] = useState<Step>(existingBrandId ? 2 : 1);
  const [brandId, setBrandId] = useState<string>(existingBrandId || "");
  const [error, setError] = useState<string | null>(null);

  // Step 1
  const [clientName, setClientName] = useState("");

  // Step 2
  const [linkedinUrl, setLinkedinUrl] = useState("");

  // Step 3
  const [websiteUrl, setWebsiteUrl] = useState("");

  // Step 4
  const [offerDescription, setOfferDescription] = useState("");

  // Step 5
  const [bestClients, setBestClients] = useState("");

  // Step 6
  const [contentGoal, setContentGoal] = useState<ContentGoal | null>(null);

  // Step 7 — research progress
  const [researchStepIdx, setResearchStepIdx] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  // Step 8 — results
  const [dossier, setDossier] = useState<ClientDossier | null>(null);
  const [intakeShareUrl, setIntakeShareUrl] = useState<string>("");

  const progress = (step / 8) * 100;

  // ── Step 1: create brand ──────────────────────────────────────────────
  const handleStep1 = async () => {
    if (!clientName.trim()) { setError("Please enter your client's name."); return; }
    setError(null);
    try {
      const brand = await personalBrandsApi.create({
        name: clientName.trim(),
        description: "Client brand",
      });
      setBrandId(brand.id);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create brand");
    }
  };

  // ── Step 7: run research ──────────────────────────────────────────────
  const handleRunResearch = async () => {
    if (!linkedinUrl.trim()) { setError("LinkedIn URL is required."); return; }
    setError(null);
    setStep(7);

    // Animate research steps
    for (let i = 0; i < RESEARCH_STEPS.length; i++) {
      setResearchStepIdx(i);
      await new Promise(r => setTimeout(r, i === 0 ? 500 : 8000));
      setCompletedSteps(prev => [...prev, i]);
    }

    try {
      const result = await clientResearchApi.run(brandId, {
        linkedin_url: linkedinUrl,
        website_url: websiteUrl || undefined,
        offer_description: offerDescription || undefined,
        best_clients: bestClients || undefined,
        content_goal: contentGoal || undefined,
      });
      setDossier(result.dossier);

      // Create intake form
      try {
        const intake = await intakeApi.create(brandId, clientName);
        setIntakeShareUrl(intake.share_url);
      } catch { /* non-fatal */ }

      setStep(8);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Research failed. Please try again.");
      setStep(6);
    }
  };

  // ── Step 6 → trigger research ─────────────────────────────────────────
  const handleGoalSelect = async (goal: ContentGoal) => {
    setContentGoal(goal);
    await handleRunResearch();
  };

  const handleNext = (nextStep: Step) => {
    setError(null);
    setStep(nextStep);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <div className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            ✦ AI BRAND RESEARCHER
          </span>
          <span className="text-sm text-gray-400">Step {step} of 8</span>
        </div>
        <button onClick={() => router.push("/mission-control")} className="text-sm text-gray-400 hover:text-gray-600">
          Save &amp; exit
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-gray-200">
        <div
          className="h-1 transition-all duration-500"
          style={{
            width: `${progress}%`,
            background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
          }}
        />
      </div>

      {/* Content */}
      <div className="flex-1 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-xl">
          {error && (
            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
              {error}
            </div>
          )}

          {/* Step 1 — Client name */}
          {step === 1 && (
            <StepCard
              heading="What's your client's name?"
              guidance="This will create their brand profile in your system."
            >
              <input
                autoFocus
                type="text"
                value={clientName}
                onChange={e => setClientName(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleStep1()}
                placeholder="e.g. Jay Campbell"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-lg focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <ContinueButton onClick={handleStep1} disabled={!clientName.trim()} />
            </StepCard>
          )}

          {/* Step 2 — LinkedIn */}
          {step === 2 && (
            <StepCard
              heading="Drop their LinkedIn URL"
              guidance="I'll read their posts, writing style, and most engaging content to understand their voice."
            >
              <input
                autoFocus
                type="url"
                value={linkedinUrl}
                onChange={e => setLinkedinUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleNext(3)}
                placeholder="https://linkedin.com/in/jaycampbell"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <ContinueButton onClick={() => handleNext(3)} disabled={!linkedinUrl.trim()} />
            </StepCard>
          )}

          {/* Step 3 — Website */}
          {step === 3 && (
            <StepCard
              heading="Their website?"
              guidance="I'll scan it for their offer, testimonials, and brand identity."
            >
              <input
                autoFocus
                type="url"
                value={websiteUrl}
                onChange={e => setWebsiteUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleNext(4)}
                placeholder="https://jaycampbell.com"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
              <div className="flex gap-3 mt-6">
                <BackButton onClick={() => setStep(2)} />
                <ContinueButton onClick={() => handleNext(4)} label="Continue" />
              </div>
              <button onClick={() => handleNext(4)} className="block text-center text-sm text-gray-400 hover:text-gray-600 mt-2">
                Skip
              </button>
            </StepCard>
          )}

          {/* Step 4 — Main offer */}
          {step === 4 && (
            <StepCard
              heading="What's their main offer and price point?"
              guidance="e.g. '6-week testosterone optimization program, $5,000'. Helps me build their Hormozi offer framework."
            >
              <textarea
                autoFocus
                value={offerDescription}
                onChange={e => setOfferDescription(e.target.value)}
                placeholder="Describe their main offer and what it costs..."
                rows={3}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
              />
              <div className="flex gap-3 mt-6">
                <BackButton onClick={() => setStep(3)} />
                <ContinueButton onClick={() => handleNext(5)} label="Continue" />
              </div>
              <button onClick={() => handleNext(5)} className="block text-center text-sm text-gray-400 hover:text-gray-600 mt-2">
                Skip
              </button>
            </StepCard>
          )}

          {/* Step 5 — Best clients */}
          {step === 5 && (
            <StepCard
              heading="Who are their 3 best clients?"
              guidance="A few words each — helps me understand exactly who they serve and what results they get."
            >
              <textarea
                autoFocus
                value={bestClients}
                onChange={e => setBestClients(e.target.value)}
                placeholder="e.g. Mike, 52, CEO who recovered energy and focus; Sarah, 48, entrepreneur who lost 20lbs..."
                rows={3}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
              />
              <div className="flex gap-3 mt-6">
                <BackButton onClick={() => setStep(4)} />
                <ContinueButton onClick={() => handleNext(6)} label="Continue" />
              </div>
              <button onClick={() => handleNext(6)} className="block text-center text-sm text-gray-400 hover:text-gray-600 mt-2">
                Skip
              </button>
            </StepCard>
          )}

          {/* Step 6 — Content goal */}
          {step === 6 && (
            <StepCard
              heading="What's the goal for their content?"
              guidance="This shapes the entire content strategy."
            >
              <div className="space-y-3 mt-2">
                {(["Get new leads", "Build authority", "Nurture existing audience"] as ContentGoal[]).map(goal => (
                  <button
                    key={goal}
                    onClick={() => handleGoalSelect(goal)}
                    className="w-full text-left px-5 py-4 border-2 border-gray-200 rounded-xl hover:border-indigo-400 hover:bg-indigo-50 transition-all font-medium text-gray-800"
                  >
                    {goal}
                  </button>
                ))}
              </div>
              <div className="mt-4">
                <BackButton onClick={() => setStep(5)} />
              </div>
            </StepCard>
          )}

          {/* Step 7 — Research in progress */}
          {step === 7 && (
            <div className="text-center">
              <div className="inline-block mb-6">
                <div className="w-16 h-16 rounded-full bg-indigo-100 flex items-center justify-center mx-auto mb-4">
                  <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">Researching {clientName}...</h2>
                <p className="text-gray-500 mt-1 text-sm">Deep research takes 60-90 seconds. Don't close this tab.</p>
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl p-6 text-left space-y-3 max-w-md mx-auto">
                {RESEARCH_STEPS.map((label, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    {completedSteps.includes(i) ? (
                      <span className="text-green-500 text-lg">✓</span>
                    ) : i === researchStepIdx ? (
                      <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin inline-block" />
                    ) : (
                      <span className="w-4 h-4 rounded-full border-2 border-gray-200 inline-block" />
                    )}
                    <span className={completedSteps.includes(i) ? "text-green-700" : i === researchStepIdx ? "text-indigo-700 font-medium" : "text-gray-400"}>
                      {label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 8 — Results: Brand Intelligence Report */}
          {step === 8 && dossier && (
            <div className="max-w-none">
              <div className="flex items-center gap-3 mb-6">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-green-600 bg-green-50 px-3 py-1.5 rounded-full">
                  ✓ ANALYSIS COMPLETE
                </span>
                <h2 className="text-xl font-bold text-gray-900">{clientName} — Brand Intelligence Report</h2>
              </div>
              <BrandIntelligenceReport
                brandId={brandId}
                dossier={dossier}
                clientName={clientName}
                intakeShareUrl={intakeShareUrl}
                onLaunch={() => router.push(`/mission-control?brand_id=${brandId}`)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StepCard({
  heading,
  guidance,
  children,
}: {
  heading: string;
  guidance?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">{heading}</h1>
      {guidance && <p className="text-gray-500 mb-6 text-sm">{guidance}</p>}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function ContinueButton({
  onClick,
  disabled = false,
  label = "Continue →",
}: {
  onClick: () => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full mt-6 py-3.5 rounded-xl text-white font-semibold disabled:opacity-40 transition-all"
      style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
    >
      {label}
    </button>
  );
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="py-3.5 px-6 rounded-xl border border-gray-200 text-gray-600 font-medium hover:bg-gray-50"
    >
      ← Back
    </button>
  );
}
