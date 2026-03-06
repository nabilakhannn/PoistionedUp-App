"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { useBrand } from "@/lib/brand-context";

const PAGE_HINTS: Record<string, string> = {
  "/dashboard": "You have posts to review. Want a quick summary?",
  "/content": "Ready to create something? I can help plan your next piece.",
  "/brand": "Let's make sure your brand profile is dialed in.",
  "/growth": "Want some outreach ideas for your leads?",
  "/jumbo": "", // hide bubble on full Jumbo page
};

function getPageHint(pathname: string): string {
  for (const [prefix, hint] of Object.entries(PAGE_HINTS)) {
    if (pathname.startsWith(prefix)) return hint;
  }
  return "How can I help?";
}

export function JumboBubble() {
  const pathname = usePathname();
  const { currentBrand } = useBrand();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Hide on auth pages, onboarding, and full Jumbo room
  if (
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/onboarding" ||
    pathname?.startsWith("/jumbo") ||
    pathname?.startsWith("/intelligence")
  ) {
    return null;
  }

  const hint = getPageHint(pathname || "/dashboard");

  const handleSend = async () => {
    if (!message.trim() || loading) return;
    const userMsg = message.trim();
    setMessage("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://api-iota-puce.vercel.app";
      const token = typeof window !== "undefined"
        ? (await (await import("@/lib/supabase/client")).createClient().auth.getSession()).data.session?.access_token
        : null;

      const res = await fetch(`${apiBase}/brand-chat/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          brand_id: currentBrand?.id || "",
          message: userMsg,
          page_context: pathname,
        }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply || data.response || "I'm here to help!" }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Something went wrong. Try again?" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating bubble */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-testid="jumbo-bubble"
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 text-white shadow-lg shadow-violet-500/20 flex items-center justify-center hover:scale-105 transition-transform duration-200"
          aria-label="Chat with Jumbo"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
          </svg>
        </button>
      )}

      {/* Slide-up panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 w-[380px] max-h-[520px] flex flex-col bg-zinc-900/95 backdrop-blur-xl rounded-2xl ring-1 ring-white/[0.08] shadow-2xl animate-slide-up">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                </svg>
              </div>
              <span className="text-sm font-semibold text-zinc-100">Jumbo</span>
              {currentBrand && (
                <span className="text-xs text-zinc-500">· {currentBrand.name}</span>
              )}
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-1 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.06] transition-colors"
              aria-label="Close"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[200px] max-h-[360px]">
            {messages.length === 0 && hint && (
              <div className="text-sm text-zinc-500 italic">{hint}</div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-violet-500/20 text-zinc-200"
                    : "bg-white/[0.04] text-zinc-300"
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white/[0.04] rounded-xl px-3 py-2 text-sm text-zinc-500">
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="px-3 pb-3 pt-2 border-t border-white/[0.06]">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Ask Jumbo anything..."
                className="glass-input flex-1 py-2 text-sm"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!message.trim() || loading}
                className="p-2 rounded-xl bg-violet-500 text-white disabled:opacity-40 hover:bg-violet-600 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
