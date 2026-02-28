"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  notificationsApi,
  AgentNotification,
  UnreadCount,
} from "@/lib/api/notifications";

const TYPE_ICONS: Record<string, string> = {
  briefing: "📋",
  reminder: "⏰",
  alert: "🚨",
  suggestion: "💡",
  insight: "🔍",
  goal_update: "🎯",
};

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-amber-500",
  medium: "bg-blue-500",
  low: "bg-zinc-500",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function NotificationBell() {
  const router = useRouter();
  const [unread, setUnread] = useState<UnreadCount>({ count: 0, by_priority: {} });
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchCount = useCallback(async () => {
    try {
      const data = await notificationsApi.unreadCount();
      setUnread(data);
    } catch {
      // Silently fail — bell just shows 0
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notificationsApi.list({ limit: 10 });
      setNotifications(data);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll unread count every 30s
  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30_000);
    return () => clearInterval(interval);
  }, [fetchCount]);

  // Fetch full list when dropdown opens
  useEffect(() => {
    if (open) fetchNotifications();
  }, [open, fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleClick = async (notif: AgentNotification) => {
    if (notif.status === "unread") {
      await notificationsApi.markRead(notif.id);
      setUnread((prev) => ({ ...prev, count: Math.max(0, prev.count - 1) }));
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, status: "read" as const } : n))
      );
    }
    if (notif.action_url) {
      router.push(notif.action_url);
      setOpen(false);
    }
  };

  const handleMarkAllRead = async () => {
    await notificationsApi.markAllRead();
    setUnread({ count: 0, by_priority: {} });
    setNotifications((prev) => prev.map((n) => ({ ...n, status: "read" as const })));
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition"
        aria-label="Notifications"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
        </svg>
        {unread.count > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-bold">
            {unread.count > 99 ? "99+" : unread.count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
            <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Notifications</h3>
            {unread.count > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[10px] text-blue-400 hover:text-blue-300 transition"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto">
            {loading && notifications.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-6">Loading...</p>
            ) : notifications.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-6">No notifications yet</p>
            ) : (
              notifications.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleClick(notif)}
                  className={`w-full text-left px-4 py-3 border-b border-zinc-800/50 hover:bg-zinc-800/50 transition ${
                    notif.status === "unread" ? "bg-zinc-800/30" : ""
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <span className="text-base mt-0.5">{TYPE_ICONS[notif.notification_type] || "📌"}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-medium ${notif.status === "unread" ? "text-zinc-100" : "text-zinc-400"}`}>
                          {notif.title}
                        </span>
                        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${PRIORITY_COLORS[notif.priority] || "bg-zinc-500"}`} />
                      </div>
                      <p className="text-[11px] text-zinc-500 line-clamp-2 mt-0.5">{notif.body.slice(0, 120)}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {notif.from_agent_id && (
                          <span className="text-[9px] text-zinc-600">from {notif.from_agent_id}</span>
                        )}
                        <span className="text-[9px] text-zinc-600">{timeAgo(notif.created_at)}</span>
                      </div>
                    </div>
                    {notif.status === "unread" && (
                      <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0 mt-1.5" />
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
