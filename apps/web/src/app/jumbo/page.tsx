"use client";

import { useEffect } from "react";
import { useBrand } from "@/lib/brand-context";
import Link from "next/link";
import {
  ConversationSidebar,
  ChatArea,
  useJumboChat,
} from "@/components/jumbo-hub";

export default function JumboPage() {
  const { currentBrand } = useBrand();
  const {
    conversations,
    activeConversation,
    loading,
    chatLoading,
    loadConversations,
    createConversation,
    selectConversation,
    sendMessage,
    archiveConversation,
  } = useJumboChat();

  useEffect(() => {
    if (currentBrand?.id) loadConversations(currentBrand.id);
  }, [currentBrand?.id, loadConversations]);

  if (!currentBrand) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card text-center max-w-sm">
          <p className="text-sm text-zinc-400 mb-3">Select a brand to chat with Jumbo.</p>
          <Link href="/brand" className="glass-button-primary text-sm">Go to Brand →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Conversation sidebar */}
      <aside className="w-72 flex-shrink-0 border-r border-white/[0.06] bg-white/[0.01] hidden md:flex md:flex-col">
        <div className="px-4 pt-6 pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-zinc-200">Jumbo</span>
          </div>
        </div>
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversation?.id ?? null}
          loading={loading}
          onSelect={(id) => selectConversation(id)}
          onNewChat={() => createConversation(currentBrand.id)}
          onArchive={archiveConversation}
        />
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col">
        <ChatArea
          conversation={activeConversation}
          chatLoading={chatLoading}
          onSendMessage={(msg) => sendMessage(msg)}
          onNewChat={() => createConversation(currentBrand.id)}
          brandId={currentBrand.id}
        />
      </main>
    </div>
  );
}
