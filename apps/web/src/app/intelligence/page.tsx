"use client";

/**
 * Jumbo Hub — Slice 107
 *
 * Persistent multi-turn chat with Jumbo (general-purpose AI partner).
 * 2-column layout: conversation sidebar (280px) + chat area.
 * Accessible via /intelligence (nav label: "Jumbo").
 */

import { useEffect } from "react";
import Link from "next/link";
import { useBrand } from "@/lib/brand-context";
import {
  ConversationSidebar,
  ChatArea,
  useJumboChat,
} from "@/components/jumbo-hub";

export default function JumboHubPage() {
  const { currentBrand, brands, loading: brandLoading } = useBrand();

  const {
    conversations,
    activeConversation,
    loading,
    chatLoading,
    error,
    loadConversations,
    createConversation,
    selectConversation,
    sendMessage,
    archiveConversation,
  } = useJumboChat();

  // Load conversations when brand is available
  useEffect(() => {
    if (currentBrand) {
      loadConversations(currentBrand.id);
    }
  }, [currentBrand, loadConversations]);

  // Brand guard — no brand selected
  if (!brandLoading && !currentBrand) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="jumbo-hub-no-brand">
        <div className="text-center max-w-sm space-y-3">
          <div className="text-4xl">🧠</div>
          <h2 className="text-lg font-bold text-foreground">Select a brand to chat with Jumbo</h2>
          <p className="text-sm text-muted-foreground">
            Jumbo needs a brand context to give you relevant advice and content.
          </p>
          {brands.length === 0 ? (
            <Link
              href="/onboarding"
              className="inline-block mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium"
            >
              Create your first brand
            </Link>
          ) : (
            <p className="text-xs text-muted-foreground">
              Use the brand selector in the sidebar to pick a brand.
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex" data-testid="jumbo-hub">
      {/* Sidebar — conversation list */}
      <aside className="w-[280px] shrink-0 border-r border-border bg-card/50 flex flex-col h-screen sticky top-0">
        <div className="px-4 py-4 border-b border-border">
          <h1 className="text-base font-bold text-foreground flex items-center gap-2">
            🧠 Jumbo
          </h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Your AI partner — strategy, content, anything.
          </p>
          {currentBrand && (
            <span className="inline-block mt-2 text-[10px] text-muted-foreground border border-border rounded px-2 py-0.5 truncate max-w-full">
              {currentBrand.name}
            </span>
          )}
        </div>
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversation?.id ?? null}
          loading={loading}
          onSelect={selectConversation}
          onNewChat={() => currentBrand && createConversation(currentBrand.id)}
          onArchive={archiveConversation}
        />
      </aside>

      {/* Main — chat area */}
      <main className="flex-1 flex flex-col h-screen">
        {error && (
          <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-400">
            {error}
          </div>
        )}
        <ChatArea
          conversation={activeConversation}
          chatLoading={chatLoading}
          brandId={currentBrand?.id ?? ""}
          onSendMessage={sendMessage}
          onNewChat={() => currentBrand && createConversation(currentBrand.id)}
        />
      </main>
    </div>
  );
}
