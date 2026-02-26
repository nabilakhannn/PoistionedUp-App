"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { personalBrandsApi } from "../../../lib/api";
import { useBrand } from "@/lib/brand-context";

type Step = "basics" | "industry" | "launch";

export default function NewBrandPage() {
  const router = useRouter();
  const { selectBrand, refreshBrands } = useBrand();

  // Step state
  const [step, setStep] = useState<Step>("basics");

  // Form data
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [industry, setIndustry] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [autoResearch, setAutoResearch] = useState(true);

  // UI state
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!name.trim()) return;

    setCreating(true);
    setError("");
    try {
      // Step 1: Create the brand
      const brand = await personalBrandsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
      });

      selectBrand(brand.id);
      await refreshBrands();

      // Step 2: If auto-research is enabled and industry is provided, start it
      if (autoResearch && industry.trim()) {
        try {
          const session = await personalBrandsApi.startResearch(brand.id, {
            industry: industry.trim(),
            name: name.trim(),
            description: description.trim(),
            target_audience: targetAudience.trim() || undefined,
          });

          // Run all stages in background (non-blocking)
          personalBrandsApi.runResearchStage(brand.id, session.id, true).catch(() => {
            // Research runs in background — errors are tracked on the session
          });
        } catch {
          // Research start failed, but brand was created successfully
          // User can start research manually from the brand page
        }
      }

      router.push(`/brands/${brand.id}`);
    } catch (e: any) {
      setError(e.message);
      setCreating(false);
    }
  };

  const INDUSTRY_SUGGESTIONS = [
    "Personal branding for tech professionals",
    "Health & wellness coaching",
    "Business consulting",
    "Creative freelancing (design, writing, video)",
    "Real estate",
    "Financial advisory",
    "Education & online courses",
    "SaaS / startup founder",
    "Career coaching",
    "Fitness & nutrition",
  ];

  return (
    <main className="min-h-screen bg-background text-card-foreground">
      <div className="max-w-xl mx-auto p-8">
        <Link
          href="/brands"
          className="text-sm text-primary hover:text-primary/80 flex items-center gap-1 mb-6 transition"
        >
          &larr; Back to brands
        </Link>

        {/* Progress indicator */}
        <div className="flex items-center gap-2 mb-8">
          {(["basics", "industry", "launch"] as const).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition ${
                  step === s
                    ? "bg-primary text-primary-foreground"
                    : (["basics", "industry", "launch"].indexOf(step) > i)
                      ? "bg-green-600 text-white"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {(["basics", "industry", "launch"].indexOf(step) > i) ? "✓" : i + 1}
              </div>
              {i < 2 && (
                <div className={`w-12 h-0.5 ${
                  (["basics", "industry", "launch"].indexOf(step) > i)
                    ? "bg-green-600" : "bg-muted"
                }`} />
              )}
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Step 1: Basics */}
        {step === "basics" && (
          <div>
            <h1 className="text-3xl font-bold mb-2">What should we call your brand?</h1>
            <p className="text-muted-foreground mb-8">
              Just a name to get started. You can always change it later.
            </p>

            <div className="space-y-5">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-foreground mb-1">
                  Brand Name *
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. My Personal Brand"
                  className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  required
                  maxLength={100}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && name.trim()) {
                      e.preventDefault();
                      setStep("industry");
                    }
                  }}
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-foreground mb-1">
                  Brief description (optional)
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What do you do? Who do you help?"
                  rows={2}
                  className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-sm text-card-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  maxLength={500}
                />
              </div>

              <button
                onClick={() => setStep("industry")}
                disabled={!name.trim()}
                className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-lg text-sm font-bold hover:bg-primary/90 disabled:opacity-40 transition"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Industry */}
        {step === "industry" && (
          <div>
            <h1 className="text-3xl font-bold mb-2">What&apos;s your industry?</h1>
            <p className="text-muted-foreground mb-6">
              This helps our AI research your niche, audience, and competitors automatically.
            </p>

            <div className="space-y-5">
              <div>
                <label htmlFor="industry" className="block text-sm font-medium text-foreground mb-1">
                  Industry / Niche *
                </label>
                <input
                  id="industry"
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. Personal branding for tech professionals"
                  className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  maxLength={200}
                  autoFocus
                />

                {/* Quick suggestions */}
                {!industry && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {INDUSTRY_SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        onClick={() => setIndustry(s)}
                        className="px-3 py-1.5 bg-muted border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-border transition"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label htmlFor="audience" className="block text-sm font-medium text-foreground mb-1">
                  Target audience (optional)
                </label>
                <input
                  id="audience"
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. Early-career software engineers wanting to build a personal brand"
                  className="w-full bg-muted border border-border rounded-lg px-4 py-3 text-sm text-card-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  maxLength={300}
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep("basics")}
                  className="px-4 py-3 text-muted-foreground text-sm hover:text-foreground transition"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep("launch")}
                  disabled={!industry.trim()}
                  className="flex-1 px-6 py-3 bg-primary text-primary-foreground rounded-lg text-sm font-bold hover:bg-primary/90 disabled:opacity-40 transition"
                >
                  Continue
                </button>
                <button
                  onClick={() => { setIndustry(""); setStep("launch"); }}
                  className="px-4 py-3 text-muted-foreground text-xs hover:text-foreground transition"
                >
                  Skip
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Launch */}
        {step === "launch" && (
          <div>
            <h1 className="text-3xl font-bold mb-2">Ready to launch</h1>
            <p className="text-muted-foreground mb-8">
              Here&apos;s what we&apos;ll set up for you.
            </p>

            {/* Summary */}
            <div className="bg-card border border-border rounded-xl p-5 mb-6 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Brand name</span>
                <span className="text-sm font-medium text-foreground">{name}</span>
              </div>
              {description && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Description</span>
                  <span className="text-sm text-foreground text-right max-w-[250px] truncate">{description}</span>
                </div>
              )}
              {industry && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Industry</span>
                  <span className="text-sm text-foreground text-right max-w-[250px] truncate">{industry}</span>
                </div>
              )}
              {targetAudience && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Target audience</span>
                  <span className="text-sm text-foreground text-right max-w-[250px] truncate">{targetAudience}</span>
                </div>
              )}
            </div>

            {/* Auto-research toggle */}
            {industry && (
              <div className="bg-violet-950/30 border border-violet-800/30 rounded-xl p-5 mb-6">
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => setAutoResearch(!autoResearch)}
                    className={`mt-0.5 w-10 h-5 rounded-full transition flex-shrink-0 relative ${
                      autoResearch ? "bg-violet-600" : "bg-border"
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${
                        autoResearch ? "left-5" : "left-0.5"
                      }`}
                    />
                  </button>
                  <div>
                    <p className="text-sm font-bold text-foreground">
                      Run AI Research automatically
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      Our AI will research your niche, audience, competitors, content landscape,
                      voice positioning, content strategy, and generate initial content ideas.
                      Results appear on your brand dashboard.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep("industry")}
                className="px-4 py-3 text-muted-foreground text-sm hover:text-foreground transition"
              >
                Back
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg text-sm font-bold hover:bg-green-500 disabled:opacity-40 transition"
              >
                {creating ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating brand{autoResearch && industry ? " & starting research" : ""}...
                  </span>
                ) : (
                  `Create Brand${autoResearch && industry ? " & Start Research" : ""}`
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
