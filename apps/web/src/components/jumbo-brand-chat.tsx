"use client";

import { useState, useRef, useEffect } from "react";
import { brandChatApi, QUICK_ACTIONS, type QuickActionId } from "@/lib/api/brand-chat";

interface Message {
  role: "user" | "jumbo";
  content: string;
}

interface JumboBrandChatProps {
  brandId: string;
  clientName?: string;
}

export function JumboBrandChat({ brandId, clientName }: JumboBrandChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data = await brandChatApi.send(brandId, text.trim());
      setMessages((prev) => [
        ...prev,
        { role: "jumbo", content: data.response },
      ]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Jumbo encountered an error. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          role: "jumbo",
          content: `Sorry, something went wrong: ${errMsg}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleQuickAction(id: QuickActionId) {
    const action = QUICK_ACTIONS.find((a) => a.id === id);
    if (action) sendMessage(action.prompt);
  }

  async function copyToClipboard(text: string, idx: number) {
    await navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.id}
            onClick={() => handleQuickAction(action.id)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-sm font-medium hover:bg-indigo-500/20 hover:border-indigo-500/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>{action.emoji}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {/* Chat History */}
      {messages.length > 0 && (
        <div className="flex flex-col gap-3 max-h-[600px] overflow-y-auto pr-1">
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
                    <span className="text-xs text-indigo-400 font-medium">
                      ⚡ Jumbo
                      {clientName ? ` — ${clientName}` : ""}
                    </span>
                  </div>
                  <div className="bg-[#161b27] border border-indigo-500/20 rounded-xl rounded-tl-sm p-4">
                    <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans leading-relaxed">
                      {msg.content}
                    </pre>
                    <div className="mt-3 flex justify-end">
                      <button
                        onClick={() => copyToClipboard(msg.content, idx)}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-gray-200 text-xs transition-all"
                      >
                        {copiedIdx === idx ? (
                          <>
                            <span>✓</span>
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <span>⎘</span>
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
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
                  <span className="ml-1 text-gray-400">Jumbo is generating...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
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
          placeholder={
            clientName
              ? `Ask Jumbo to generate anything for ${clientName}...`
              : "Ask Jumbo to generate anything from this research..."
          }
          maxLength={5000}
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
    </div>
  );
}
