"use client";

import { useState, useRef, useEffect } from "react";
import { contentPlanningApi, type PlanItem } from "@/lib/api/content-planning";

interface Message {
  role: "user" | "jumbo";
  content: string;
}

interface ContentPlanChatProps {
  brandId: string;
  onApproved: (planId: string, itemCount: number) => void;
  onClose?: () => void;
}

/** Parse Jumbo's PLAN: section into structured items.
 *  Lenient: accepts | - – — as separators, • * as bullets, case-insensitive. */
function parsePlan(text: string): PlanItem[] | null {
  const match = text.match(/PLAN:?\s*\n((?:\s*[-•*]\s*.+\n?)+)/i);
  if (!match?.[1]) return null;

  const lines = match[1].trim().split("\n").filter((l) => l.trim());
  const items: PlanItem[] = lines.map((line) => {
    const clean = line.replace(/^\s*[-•*]\s*/, "").trim();
    // Split on | or – or — (but not a plain - inside words)
    const parts = clean.split(/\s*[|–—]\s*/);
    return {
      topic: parts[0]?.trim() ?? clean,
      angle: parts[1]?.trim() ?? "",
      format: parts[2]?.trim().toLowerCase() ?? "post",
    };
  });

  return items.length > 0 ? items : null;
}

export function ContentPlanChat({ brandId, onApproved, onClose }: ContentPlanChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(false);
  const [parsedPlan, setParsedPlan] = useState<PlanItem[] | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualItems, setManualItems] = useState<PlanItem[]>([
    { topic: "", angle: "", format: "post" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // On mount: load Jumbo's opening brainstorm message
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await contentPlanningApi.brainstorm(brandId);
        setMessages([{ role: "jumbo", content: data.message }]);
      } catch {
        setMessages([
          {
            role: "jumbo",
            content:
              "I'm having trouble connecting right now. Try refreshing — I'll have some content ideas ready for you.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    })();
  }, [brandId]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const data = await contentPlanningApi.chat(brandId, updatedMessages);
      const jumboMsg: Message = { role: "jumbo", content: data.response };
      setMessages((prev) => [...prev, jumboMsg]);

      // Try to parse a plan from Jumbo's response
      const plan = parsePlan(data.response);
      if (plan) {
        setParsedPlan(plan);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "jumbo",
          content: "Sorry, something went wrong. Try sending your message again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(items: PlanItem[]) {
    const validItems = items.filter((i) => i.topic.trim());
    if (!validItems.length) return;

    setApproving(true);
    setError(null);
    try {
      const data = await contentPlanningApi.approve(brandId, validItems);
      onApproved(data.plan_id, data.item_count);
    } catch {
      setError("Failed to save the plan. Please try again.");
    } finally {
      setApproving(false);
    }
  }

  function addManualItem() {
    setManualItems((prev) => [...prev, { topic: "", angle: "", format: "post" }]);
  }

  function removeManualItem(idx: number) {
    setManualItems((prev) => prev.filter((_, i) => i !== idx));
  }

  function updateManualItem(idx: number, field: keyof PlanItem, value: string) {
    setManualItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item))
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-indigo-500/20 bg-[#0f1420] p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">📋</span>
          <span className="text-sm font-semibold text-gray-200">Plan Content with Jumbo</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xs transition-colors"
          >
            ✕ Close
          </button>
        )}
      </div>

      {/* Chat History */}
      <div className="flex flex-col gap-3 max-h-[400px] overflow-y-auto pr-1">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col gap-1 ${
              msg.role === "user" ? "items-end" : "items-start"
            }`}
          >
            {msg.role === "user" ? (
              <div className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-tr-sm bg-indigo-600 text-white text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="w-full">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs text-indigo-400 font-medium">⚡ Jumbo</span>
                </div>
                <div className="bg-[#161b27] border border-indigo-500/20 rounded-xl rounded-tl-sm p-4">
                  <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans leading-relaxed">
                    {msg.content}
                  </pre>
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-2">
            <div className="bg-[#161b27] border border-indigo-500/20 rounded-xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-2 text-indigo-400 text-sm">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse" style={{ animationDelay: "0.2s" }}>●</span>
                <span className="animate-pulse" style={{ animationDelay: "0.4s" }}>●</span>
                <span className="ml-1 text-gray-400">Jumbo is thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!parsedPlan && (
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            placeholder="Tell Jumbo what you want — topics, how many posts, any angle..."
            maxLength={2000}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-[#161b27] border border-indigo-500/20 text-gray-200 placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500/50 disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      )}

      {/* Parsed Plan — approval cards */}
      {parsedPlan && (
        <div className="flex flex-col gap-3 mt-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-green-400 uppercase tracking-wider">
              Plan Ready ({parsedPlan.length} post{parsedPlan.length !== 1 ? "s" : ""})
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {parsedPlan.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-[#161b27] border border-green-500/20"
              >
                <span className="text-green-400 text-xs font-bold mt-0.5">{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 font-medium leading-snug">{item.topic}</p>
                  {item.angle && (
                    <p className="text-xs text-gray-500 mt-0.5">{item.angle}</p>
                  )}
                </div>
                <span className="text-[10px] text-gray-500 uppercase tracking-wider shrink-0 mt-0.5">
                  {item.format}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={() => handleApprove(parsedPlan)}
              disabled={approving}
              className="flex-1 px-4 py-2.5 rounded-xl bg-green-600 hover:bg-green-500 text-white text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {approving ? "Saving..." : `Approve & Create ${parsedPlan.length} Post${parsedPlan.length !== 1 ? "s" : ""}`}
            </button>
            <button
              onClick={() => {
                setParsedPlan(null);
                setInput("");
              }}
              disabled={approving}
              className="px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 hover:text-gray-200 text-sm transition-all disabled:opacity-50"
            >
              Edit
            </button>
          </div>
        </div>
      )}

      {/* Manual fallback — always available */}
      {!parsedPlan && (
        <div className="border-t border-white/5 pt-3">
          <button
            onClick={() => setManualOpen((v) => !v)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
          >
            <span>{manualOpen ? "▼" : "▶"}</span>
            <span>Enter topics manually instead</span>
          </button>

          {manualOpen && (
            <div className="flex flex-col gap-3 mt-3">
              {manualItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={item.topic}
                    onChange={(e) => updateManualItem(idx, "topic", e.target.value)}
                    placeholder={`Topic ${idx + 1}`}
                    maxLength={300}
                    className="flex-1 px-3 py-2 rounded-lg bg-[#161b27] border border-white/10 text-gray-200 placeholder-gray-600 text-sm focus:outline-none focus:border-indigo-500/40"
                  />
                  <input
                    type="text"
                    value={item.angle}
                    onChange={(e) => updateManualItem(idx, "angle", e.target.value)}
                    placeholder="Angle (optional)"
                    maxLength={200}
                    className="w-36 px-3 py-2 rounded-lg bg-[#161b27] border border-white/10 text-gray-200 placeholder-gray-600 text-sm focus:outline-none focus:border-indigo-500/40"
                  />
                  {manualItems.length > 1 && (
                    <button
                      onClick={() => removeManualItem(idx)}
                      className="text-gray-600 hover:text-red-400 text-sm transition-colors"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}

              <div className="flex items-center gap-2">
                {manualItems.length < 10 && (
                  <button
                    onClick={addManualItem}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    + Add topic
                  </button>
                )}
                <button
                  onClick={() => handleApprove(manualItems)}
                  disabled={approving || !manualItems.some((i) => i.topic.trim())}
                  className="ml-auto px-4 py-2 rounded-xl bg-green-600 hover:bg-green-500 text-white text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {approving ? "Saving..." : "Approve Plan"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-400 text-center">{error}</p>
      )}
    </div>
  );
}
