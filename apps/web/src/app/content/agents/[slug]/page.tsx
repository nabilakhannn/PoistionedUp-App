"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  marketplaceApi,
  WorkflowInfo,
  WorkflowRunResult,
} from "@/lib/api/marketplace";
import { DynamicFormBuilder } from "@/components/dynamic-form-builder";
import { GenerationHistory } from "@/components/generation-history";

export default function WorkflowExecutionPage() {
  const params = useParams();
  const slug = params.slug as string;
  const { currentBrand } = useBrand();

  const [workflow, setWorkflow] = useState<WorkflowInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<WorkflowRunResult | null>(null);
  const [error, setError] = useState("");
  const [viewingOutput, setViewingOutput] = useState<string | null>(null);

  // Multi-step state
  const [currentStep, setCurrentStep] = useState(0);
  const [stepOutputs, setStepOutputs] = useState<string[]>([]);
  const [formInputs, setFormInputs] = useState<Record<string, string>>({});
  const [copiedSingle, setCopiedSingle] = useState(false);
  const [copiedAll, setCopiedAll] = useState(false);

  const loadWorkflow = useCallback(async () => {
    setLoading(true);
    try {
      const data = await marketplaceApi.getRegistry();
      const wf = data.workflows[slug];
      if (wf) {
        setWorkflow(wf);
      } else {
        setError("Workflow not found");
      }
    } catch {
      setError("Failed to load workflow");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  const handleRun = async (inputs: Record<string, string>) => {
    if (!currentBrand?.id || !workflow) return;
    setRunning(true);
    setError("");
    setResult(null);
    setFormInputs(inputs);

    try {
      if (workflow.multi_step) {
        // Run step 0
        setCurrentStep(0);
        setStepOutputs([]);
        const stepResult = await marketplaceApi.runWorkflow(slug, {
          brand_id: currentBrand.id,
          inputs,
          step_index: 0,
          previous_outputs: [],
        });
        if (stepResult.status === "completed" && stepResult.content) {
          setStepOutputs([stepResult.content]);
          setCurrentStep(1);
          setResult(stepResult);
        } else {
          setError(stepResult.error || "Step 1 failed");
          setResult(stepResult);
        }
      } else {
        // Single-step
        const res = await marketplaceApi.runWorkflow(slug, {
          brand_id: currentBrand.id,
          inputs,
        });
        setResult(res);
        if (res.status === "failed") {
          setError(res.error || "Generation failed");
        }
      }
    } catch {
      setError("Generation failed — please try again.");
    } finally {
      setRunning(false);
    }
  };

  const handleNextStep = async () => {
    if (!currentBrand?.id || !workflow) return;
    setRunning(true);
    setError("");

    try {
      const stepResult = await marketplaceApi.runWorkflow(slug, {
        brand_id: currentBrand.id,
        inputs: formInputs,
        step_index: currentStep,
        previous_outputs: stepOutputs,
      });

      if (stepResult.status === "completed" && stepResult.content) {
        const newOutputs = [...stepOutputs, stepResult.content];
        setStepOutputs(newOutputs);
        setCurrentStep(currentStep + 1);
        setResult(stepResult);
      } else {
        setError(stepResult.error || `Step ${currentStep + 1} failed`);
      }
    } catch {
      setError("Step failed — please try again.");
    } finally {
      setRunning(false);
    }
  };

  const handleRegenStep = async (stepIdx: number) => {
    if (!currentBrand?.id || !workflow) return;
    setRunning(true);
    setError("");

    try {
      const prevOutputs = stepOutputs.slice(0, stepIdx);
      const stepResult = await marketplaceApi.runWorkflow(slug, {
        brand_id: currentBrand.id,
        inputs: formInputs,
        step_index: stepIdx,
        previous_outputs: prevOutputs,
      });

      if (stepResult.status === "completed" && stepResult.content) {
        const newOutputs = [...prevOutputs, stepResult.content];
        setStepOutputs(newOutputs);
        setCurrentStep(stepIdx + 1);
        setResult(stepResult);
      } else {
        setError(stepResult.error || "Re-generation failed");
      }
    } catch {
      setError("Re-generation failed");
    } finally {
      setRunning(false);
    }
  };

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Select a brand first.</p>
          <Link href="/brand" className="glass-button-primary text-sm">
            Go to Brand →
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="max-w-5xl mx-auto px-5 py-8">
          <div className="h-3 w-40 rounded bg-zinc-800/50 animate-pulse mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-4">
              <div className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-6 space-y-3 animate-pulse">
                <div className="h-5 w-48 rounded bg-zinc-800/50" />
                <div className="h-3 w-full rounded bg-zinc-800/40" />
                <div className="h-3 w-2/3 rounded bg-zinc-800/40" />
              </div>
              <div className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-6 space-y-3 animate-pulse">
                <div className="h-8 w-full rounded bg-zinc-800/40" />
                <div className="h-20 w-full rounded bg-zinc-800/40" />
                <div className="h-10 w-full rounded bg-zinc-800/50" />
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="rounded-2xl ring-1 ring-white/[0.05] bg-white/[0.03] p-6 py-16 animate-pulse text-center">
                <div className="h-4 w-64 mx-auto rounded bg-zinc-800/40" />
                <div className="h-3 w-48 mx-auto rounded bg-zinc-800/40 mt-3" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Workflow not found.</p>
          <Link
            href="/content/agents"
            className="glass-button-primary text-sm"
          >
            Back to Marketplace →
          </Link>
        </div>
      </div>
    );
  }

  const isMultiStep = workflow.multi_step && workflow.steps.length > 0;
  const allStepsDone =
    isMultiStep && stepOutputs.length >= workflow.steps.length;

  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-5 py-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-zinc-500 mb-6">
          <Link
            href="/content/agents"
            className="hover:text-zinc-300 transition"
          >
            AI Agents
          </Link>
          <span>/</span>
          <span className="text-zinc-300">{workflow.name}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column: form + step wizard */}
          <div className="lg:col-span-1 space-y-4">
            {/* Workflow header */}
            <div className="glass-card space-y-2">
              <div className="flex items-center justify-between">
                <h1 className="text-lg font-bold text-zinc-100">
                  {workflow.name}
                </h1>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">
                  Active
                </span>
              </div>
              <p className="text-xs text-zinc-500">{workflow.description}</p>
              <div className="flex gap-1 flex-wrap">
                {workflow.enhancements.map((e) => (
                  <span
                    key={e}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400"
                  >
                    +{e.replace("_", " ")}
                  </span>
                ))}
              </div>
              {workflow.estimated_tokens > 0 && (
                <p className="text-[10px] text-zinc-600">
                  ~{workflow.estimated_tokens.toLocaleString()} tokens
                </p>
              )}
            </div>

            {/* Multi-step progress */}
            {isMultiStep && (
              <div className="glass-card space-y-2">
                <p className="text-xs text-zinc-400 font-medium">
                  Progress
                </p>
                {workflow.steps.map((step, i) => {
                  const done = i < stepOutputs.length;
                  const active = i === currentStep;
                  return (
                    <div
                      key={i}
                      className={`flex items-center gap-2 text-xs py-1 ${
                        done
                          ? "text-green-400"
                          : active
                            ? "text-violet-400"
                            : "text-zinc-600"
                      }`}
                    >
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                          done
                            ? "bg-green-500/20"
                            : active
                              ? "bg-violet-500/20"
                              : "bg-zinc-800/50"
                        }`}
                      >
                        {done ? "✓" : i + 1}
                      </span>
                      <span>{step.name}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Input form (show when no result yet or single-step) */}
            {!result && (
              <div className="glass-card">
                <DynamicFormBuilder
                  fields={workflow.inputs}
                  onSubmit={handleRun}
                  loading={running}
                  submitLabel={
                    isMultiStep
                      ? `Start Step 1: ${workflow.steps[0]?.name}`
                      : "Generate"
                  }
                />
              </div>
            )}

            {/* Next step button for multi-step */}
            {isMultiStep && !allStepsDone && stepOutputs.length > 0 && (
              <button
                onClick={handleNextStep}
                disabled={running}
                className="w-full glass-button-primary disabled:opacity-50"
              >
                {running
                  ? "Generating..."
                  : `Continue → Step ${currentStep + 1}: ${workflow.steps[currentStep]?.name}`}
              </button>
            )}

            {/* Start over button */}
            {result && (
              <button
                onClick={() => {
                  setResult(null);
                  setStepOutputs([]);
                  setCurrentStep(0);
                  setError("");
                }}
                className="w-full py-2 glass-button text-xs"
              >
                Start New Generation
              </button>
            )}

            {/* History */}
            <div className="glass-card">
              <GenerationHistory
                brandId={currentBrand.id}
                workflowSlug={slug}
                onViewOutput={(output) => setViewingOutput(output)}
              />
            </div>
          </div>

          {/* Right column: output */}
          <div className="lg:col-span-2 space-y-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2.5 rounded-lg text-sm flex items-center gap-3">
                <span className="flex-1">{error}</span>
                {error === "Failed to load workflow" && (
                  <button
                    onClick={() => { setError(""); loadWorkflow(); }}
                    className="underline shrink-0"
                  >
                    Retry
                  </button>
                )}
                <button
                  onClick={() => setError("")}
                  className="text-red-400/60 hover:text-red-400 shrink-0"
                >
                  ✕
                </button>
              </div>
            )}

            {running && !result && (
              <div className="glass-card text-center py-12">
                <div className="inline-block w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-sm text-zinc-400">
                  {isMultiStep
                    ? `Running Step ${currentStep + 1}: ${workflow.steps[currentStep]?.name}...`
                    : "Generating with your brand intelligence..."}
                </p>
                <p className="text-[10px] text-zinc-600 mt-1">
                  Injecting: {workflow.enhancements.join(", ")}
                </p>
              </div>
            )}

            {/* Multi-step outputs */}
            {isMultiStep &&
              stepOutputs.map((output, i) => (
                <div key={i} className="glass-card space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-zinc-400 font-medium">
                      Step {i + 1}: {workflow.steps[i]?.name}
                    </p>
                    <button
                      onClick={() => handleRegenStep(i)}
                      disabled={running}
                      className="text-[10px] px-2 py-1 rounded border border-zinc-700/50 text-zinc-400 hover:text-zinc-200 transition disabled:opacity-50"
                    >
                      Re-generate
                    </button>
                  </div>
                  <div className="text-sm text-zinc-200 whitespace-pre-wrap max-h-[400px] overflow-y-auto leading-relaxed">
                    {output}
                  </div>
                </div>
              ))}

            {/* Single-step output */}
            {!isMultiStep && result?.content && (
              <div className="glass-card space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-zinc-400 font-medium">
                    Output
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-zinc-600">
                      {result.model_used} ·{" "}
                      {(result.duration_ms / 1000).toFixed(1)}s
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(result.content || "");
                        setCopiedSingle(true);
                        setTimeout(() => setCopiedSingle(false), 2000);
                      }}
                      className="text-[10px] px-2 py-1 rounded border border-zinc-700/50 text-zinc-400 hover:text-zinc-200 transition"
                    >
                      {copiedSingle ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
                <div className="text-sm text-zinc-200 whitespace-pre-wrap max-h-[600px] overflow-y-auto leading-relaxed">
                  {result.content}
                </div>
              </div>
            )}

            {/* All steps done */}
            {allStepsDone && (
              <div className="glass-card border-green-500/20 text-center py-6">
                <p className="text-sm text-green-400 font-medium">
                  All {workflow.steps.length} steps completed!
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  Your full {workflow.name} is ready above.
                </p>
                <button
                  onClick={() => {
                    const full = stepOutputs
                      .map(
                        (o, i) =>
                          `## Step ${i + 1}: ${workflow.steps[i]?.name}\n\n${o}`,
                      )
                      .join("\n\n---\n\n");
                    navigator.clipboard.writeText(full);
                    setCopiedAll(true);
                    setTimeout(() => setCopiedAll(false), 2000);
                  }}
                  className="mt-3 px-4 py-2 glass-button-primary text-xs"
                >
                  {copiedAll ? "Copied All!" : "Copy All Steps"}
                </button>
              </div>
            )}

            {/* Viewing historical output */}
            {viewingOutput && (
              <div className="glass-card space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-zinc-400 font-medium">
                    Historical Output
                  </p>
                  <button
                    onClick={() => setViewingOutput(null)}
                    className="text-[10px] text-zinc-500 hover:text-zinc-300"
                  >
                    Close
                  </button>
                </div>
                <div className="text-sm text-zinc-200 whitespace-pre-wrap max-h-[600px] overflow-y-auto leading-relaxed">
                  {viewingOutput}
                </div>
              </div>
            )}

            {/* Empty state */}
            {!running && !result && !viewingOutput && stepOutputs.length === 0 && (
              <div className="glass-card text-center py-16">
                <p className="text-zinc-500 text-sm">
                  Fill the form and click Generate to get started.
                </p>
                <p className="text-zinc-600 text-xs mt-1">
                  Your brand dossier, stories, and hooks will be automatically
                  injected.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
