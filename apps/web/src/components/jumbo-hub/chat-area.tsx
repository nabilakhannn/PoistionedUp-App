"use client";

import { useState, useRef, useEffect } from "react";
import type { Conversation, ChatMessage } from "@/lib/api/jumbo-hub";
import { SaveAsNoteForm } from "./save-as-note-form";

interface ChatAreaProps {
  conversation: Conversation | null;
  chatLoading: boolean;
  brandId: string;
  onSendMessage: (message: string) => void;
  onNewChat: () => void;
}

const QUICK_ACTIONS = [
  { label: "30 Hooks", prompt: "Give me 30 hook ideas for my next LinkedIn posts" },
  { label: "5 Posts", prompt: "Write 5 LinkedIn posts based on my brand voice and positioning" },
  { label: "Content Calendar", prompt: "Create a 30-day content calendar for my brand" },
  { label: "Offer Outline", prompt: "Help me refine my offer structure and positioning" },
];

export function ChatArea({
  conversation,
  chatLoading,
  brandId,
  onSendMessage,
  onNewChat,
}: ChatAreaProps) {
  const [input, setInput] = useState("");
  const [savingNoteIdx, setSavingNoteIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages?.length, chatLoading]);

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || chatLoading) return;
    onSendMessage(trimmed);
    setInput("");
  }

  // Welcome state
  if (!conversation) {
    return (
      <div data-testid="chat-area" className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="text-5xl mb-4">🧠</div>
        <h2 className="text-lg font-semibold text-foreground mb-2">
          Chat with Jumbo
        </h2>
        <p className="text-sm text-muted-foreground text-center max-w-md mb-6">
          Your strategic AI partner. Ask anything — content ideas, strategy, feedback,
          brainstorming, or just thinking out loud.
        </p>
        <div className="grid grid-cols-2 gap-2 max-w-md w-full">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => {
                onNewChat();
                // Delay sending until conversation is created — handle in parent
              }}
              className="px-4 py-3 rounded-xl border border-border bg-card hover:bg-muted/30 text-left transition-colors"
            >
              <p className="text-sm font-medium text-foreground">{action.label}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
                {action.prompt}
              </p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const messages = conversation.messages || [];

  return (
    <div data-testid="chat-area" className="flex-1 flex flex-col min-h-0">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !chatLoading && (
          <div className="text-center py-12">
            <p className="text-sm text-muted-foreground">
              Start the conversation — ask Jumbo anything.
            </p>
          </div>
        )}

        {messages.map((msg: ChatMessage, idx: number) => (
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
              <div className="w-full max-w-[90%]">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs text-indigo-400 font-medium">🧠 Jumbo</span>
                </div>
                <div className="bg-[#161b27] border border-indigo-500/20 rounded-xl rounded-tl-sm p-4">
                  <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans leading-relaxed">
                    {msg.content}
                  </pre>
                </div>
                {/* Actions: Save as Note + Copy */}
                <div className="flex items-center gap-2 mt-1.5">
                  <button
                    onClick={() => setSavingNoteIdx(savingNoteIdx === idx ? null : idx)}
                    className="text-[11px] text-muted-foreground hover:text-indigo-400 transition-colors"
                  >
                    📌 Save as Note
                  </button>
                  <button
                    onClick={() => navigator.clipboard.writeText(msg.content)}
                    className="text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                  >
                    📋 Copy
                  </button>
                </div>
                {savingNoteIdx === idx && (
                  <SaveAsNoteForm
                    brandId={brandId}
                    content={msg.content}
                    onClose={() => setSavingNoteIdx(null)}
                  />
                )}
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {chatLoading && (
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

      {/* Input bar */}
      <div className="border-t border-border p-4">
        <div className="flex gap-2">
          <textarea
            data-testid="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask Jumbo anything..."
            rows={1}
            maxLength={5000}
            disabled={chatLoading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-[#161b27] border border-indigo-500/20 text-gray-200 placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500/50 disabled:opacity-50 resize-none"
          />
          <button
            data-testid="send-button"
            onClick={handleSend}
            disabled={chatLoading || !input.trim()}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
