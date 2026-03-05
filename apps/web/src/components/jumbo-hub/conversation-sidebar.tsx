"use client";

import Link from "next/link";
import type { ConversationSummary } from "@/lib/api/jumbo-hub";

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onArchive: (id: string) => void;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export function ConversationSidebar({
  conversations,
  activeId,
  loading,
  onNewChat,
  onSelect,
  onArchive,
}: ConversationSidebarProps) {
  return (
    <aside
      data-testid="conversation-sidebar"
      className="flex flex-col h-full border-r border-border bg-card/30"
    >
      {/* New Chat button */}
      <div className="p-3 border-b border-border">
        <button
          onClick={onNewChat}
          data-testid="new-chat-button"
          className="w-full px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-all"
        >
          + New Chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-3 space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-muted/20 animate-pulse" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-xs text-muted-foreground">
              No conversations yet.
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Start one with Jumbo above.
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-0.5">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                  conv.id === activeId
                    ? "bg-indigo-500/15 border border-indigo-500/30"
                    : "hover:bg-muted/30 border border-transparent"
                }`}
                onClick={() => onSelect(conv.id)}
              >
                <div className="flex-1 min-w-0">
                  <p className={`text-sm truncate ${
                    conv.id === activeId ? "text-indigo-300 font-medium" : "text-foreground"
                  }`}>
                    {conv.title}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {relativeTime(conv.updated_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onArchive(conv.id);
                  }}
                  title="Archive conversation"
                  className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 text-xs transition-all shrink-0"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom links */}
      <div className="border-t border-border p-3 space-y-1.5">
        <Link
          href="/studio/agents"
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1.5 rounded-lg hover:bg-muted/20"
        >
          <span>🤖</span> Manage Agents
        </Link>
        <Link
          href="/deliverables"
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1.5 rounded-lg hover:bg-muted/20"
        >
          <span>📦</span> Deliverables
        </Link>
        <Link
          href="/studio/hooks"
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1.5 rounded-lg hover:bg-muted/20"
        >
          <span>🪝</span> Hook Library
        </Link>
      </div>
    </aside>
  );
}
