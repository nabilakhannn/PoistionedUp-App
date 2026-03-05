"use client";

import { useState, useCallback } from "react";
import {
  jumboHubApi,
  type Conversation,
  type ConversationSummary,
  type ChatMessage,
} from "@/lib/api/jumbo-hub";

interface UseJumboChatReturn {
  conversations: ConversationSummary[];
  activeConversation: Conversation | null;
  loading: boolean;
  chatLoading: boolean;
  error: string | null;
  loadConversations: (brandId: string) => Promise<void>;
  createConversation: (brandId: string) => Promise<void>;
  selectConversation: (conversationId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  archiveConversation: (conversationId: string) => Promise<void>;
}

export function useJumboChat(): UseJumboChatReturn {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async (brandId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await jumboHubApi.listConversations(brandId);
      setConversations(data.conversations);
    } catch {
      setError("Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, []);

  const createConversation = useCallback(async (brandId: string) => {
    setError(null);
    try {
      const conv = await jumboHubApi.createConversation(brandId);
      setActiveConversation({ ...conv, messages: [], status: "active", updated_at: conv.created_at });
      setConversations((prev) => [
        { id: conv.id, title: conv.title, brand_id: conv.brand_id, status: "active", created_at: conv.created_at, updated_at: conv.created_at },
        ...prev,
      ]);
    } catch {
      setError("Failed to create conversation");
    }
  }, []);

  const selectConversation = useCallback(async (conversationId: string) => {
    setLoading(true);
    setError(null);
    try {
      const conv = await jumboHubApi.getConversation(conversationId);
      setActiveConversation(conv);
    } catch {
      setError("Failed to load conversation");
    } finally {
      setLoading(false);
    }
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!activeConversation) return;
    setChatLoading(true);
    setError(null);

    // Optimistic: append user message immediately
    const now = new Date().toISOString();
    const userMsg: ChatMessage = { role: "user", content: message, created_at: now };
    setActiveConversation((prev) =>
      prev ? { ...prev, messages: [...prev.messages, userMsg] } : prev
    );

    try {
      const res = await jumboHubApi.chat(activeConversation.id, message);
      const jumboMsg: ChatMessage = { role: "jumbo", content: res.response, created_at: new Date().toISOString() };
      setActiveConversation((prev) =>
        prev ? { ...prev, title: res.title, messages: [...prev.messages, jumboMsg] } : prev
      );
      // Update title in sidebar list
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversation.id
            ? { ...c, title: res.title, updated_at: new Date().toISOString() }
            : c
        )
      );
    } catch {
      setError("Failed to send message. Try again.");
      // Remove optimistic user message on failure
      setActiveConversation((prev) =>
        prev ? { ...prev, messages: prev.messages.filter((m) => m !== userMsg) } : prev
      );
    } finally {
      setChatLoading(false);
    }
  }, [activeConversation]);

  const archiveConversation = useCallback(async (conversationId: string) => {
    try {
      await jumboHubApi.archiveConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (activeConversation?.id === conversationId) {
        setActiveConversation(null);
      }
    } catch {
      setError("Failed to archive conversation");
    }
  }, [activeConversation]);

  return {
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
  };
}
