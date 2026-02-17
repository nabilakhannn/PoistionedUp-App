"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { scheduleApi, KanbanBoard, ScheduledItem } from "@/lib/api";
import {
  CalendarIcon,
  ViewColumnsIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@/components/icons";
import { createClient } from "@/lib/supabase/client";

// ── Platform badges ──────────────────────────────────

const PLATFORM_COLORS: Record<string, string> = {
  youtube: "bg-red-100 text-red-700",
  linkedin: "bg-blue-100 text-blue-700",
  twitter: "bg-sky-100 text-sky-700",
  tiktok: "bg-pink-100 text-pink-700",
  instagram: "bg-purple-100 text-purple-700",
  other: "bg-gray-100 text-gray-600",
};

const COLOR_LABEL_STYLES: Record<string, string> = {
  red: "border-l-red-500",
  orange: "border-l-orange-500",
  yellow: "border-l-yellow-500",
  green: "border-l-green-500",
  blue: "border-l-blue-500",
  purple: "border-l-purple-500",
  pink: "border-l-pink-500",
};

const COLUMN_HEADERS: Record<string, { label: string; bgClass: string; dotClass: string }> = {
  draft: { label: "Draft", bgClass: "bg-gray-50", dotClass: "bg-gray-400" },
  scheduled: { label: "Scheduled", bgClass: "bg-blue-50", dotClass: "bg-blue-400" },
  published: { label: "Published", bgClass: "bg-green-50", dotClass: "bg-green-400" },
  archived: { label: "Archived", bgClass: "bg-yellow-50", dotClass: "bg-yellow-400" },
};

// ── Utility ──────────────────────────────────────────

function formatDate(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTime(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ── Sub-components ───────────────────────────────────

function PlatformBadge({ platform }: { platform: string }) {
  const cls = PLATFORM_COLORS[platform] || PLATFORM_COLORS.other;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {platform}
    </span>
  );
}

function KanbanCard({
  item,
  onDragStart,
  onEdit,
  onDelete,
}: {
  item: ScheduledItem;
  onDragStart: (e: React.DragEvent, item: ScheduledItem) => void;
  onEdit: (item: ScheduledItem) => void;
  onDelete: (id: string) => void;
}) {
  const colorBorder = item.color_label
    ? COLOR_LABEL_STYLES[item.color_label] || ""
    : "";

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, item)}
      className={`bg-white rounded-lg shadow-sm border border-gray-200 p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow group ${
        colorBorder ? `border-l-4 ${colorBorder}` : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2 flex-1">
          {item.title}
        </h4>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={() => onEdit(item)}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
          >
            <PencilIcon className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(item.id)}
            className="p-1 text-gray-400 hover:text-red-500 rounded"
          >
            <TrashIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {item.body_preview && (
        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.body_preview}</p>
      )}

      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <PlatformBadge platform={item.platform} />
        {item.scheduled_at && (
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <CalendarIcon className="h-3 w-3" />
            {formatDate(item.scheduled_at)}
          </span>
        )}
        {item.workflow_id && (
          <Link
            href={`/content/${item.workflow_id}`}
            className="text-xs text-blue-500 hover:text-blue-700"
            onClick={(e) => e.stopPropagation()}
          >
            workflow
          </Link>
        )}
      </div>

      {item.notes && (
        <p className="text-xs text-gray-400 mt-1.5 italic line-clamp-1">{item.notes}</p>
      )}
    </div>
  );
}

function KanbanColumn({
  columnKey,
  items,
  onDragStart,
  onDrop,
  onDragOver,
  onEdit,
  onDelete,
}: {
  columnKey: string;
  items: ScheduledItem[];
  onDragStart: (e: React.DragEvent, item: ScheduledItem) => void;
  onDrop: (e: React.DragEvent, targetStatus: string) => void;
  onDragOver: (e: React.DragEvent) => void;
  onEdit: (item: ScheduledItem) => void;
  onDelete: (id: string) => void;
}) {
  const header = COLUMN_HEADERS[columnKey] || COLUMN_HEADERS.draft;

  return (
    <div
      className={`flex-1 min-w-[260px] max-w-[340px] rounded-xl ${header.bgClass} p-3`}
      onDrop={(e) => onDrop(e, columnKey)}
      onDragOver={onDragOver}
    >
      <div className="flex items-center gap-2 mb-3 px-1">
        <div className={`w-2.5 h-2.5 rounded-full ${header.dotClass}`} />
        <h3 className="text-sm font-semibold text-gray-700">{header.label}</h3>
        <span className="text-xs text-gray-400 bg-white px-1.5 py-0.5 rounded-full ml-auto">
          {items.length}
        </span>
      </div>
      <div className="space-y-2 min-h-[80px]">
        {items.map((item) => (
          <KanbanCard
            key={item.id}
            item={item}
            onDragStart={onDragStart}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
        {items.length === 0 && (
          <div className="text-center py-8 text-xs text-gray-400">
            Drag items here
          </div>
        )}
      </div>
    </div>
  );
}

// ── New Item Modal ───────────────────────────────────

function NewItemModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [contentType, setContentType] = useState("youtube_long");
  const [scheduledAt, setScheduledAt] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError("");
    try {
      await scheduleApi.create({
        title: title.trim(),
        platform,
        content_type: contentType,
        scheduled_at: scheduledAt || undefined,
        notes: notes.trim() || undefined,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">New Scheduled Item</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What are you publishing?"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="youtube">YouTube</option>
                <option value="linkedin">LinkedIn</option>
                <option value="twitter">Twitter/X</option>
                <option value="tiktok">TikTok</option>
                <option value="instagram">Instagram</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Content Type</label>
              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="youtube_long">YouTube Long</option>
                <option value="youtube_short">YouTube Short</option>
                <option value="linkedin_post">LinkedIn Post</option>
                <option value="twitter_post">Tweet</option>
                <option value="short_form">Short-Form Video</option>
                <option value="note">Note / Idea</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scheduled Date (optional)
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Any notes or reminders..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Edit Item Modal ──────────────────────────────────

function EditItemModal({
  item,
  onClose,
  onSaved,
}: {
  item: ScheduledItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [scheduledAt, setScheduledAt] = useState(
    item.scheduled_at ? item.scheduled_at.slice(0, 16) : ""
  );
  const [notes, setNotes] = useState(item.notes || "");
  const [publishedUrl, setPublishedUrl] = useState(item.published_url || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await scheduleApi.update(item.id, {
        title: title.trim(),
        scheduled_at: scheduledAt || null,
        notes: notes.trim() || null,
        published_url: publishedUrl.trim() || null,
      } as any);
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Edit Item</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Date</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Published URL</label>
            <input
              type="url"
              value={publishedUrl}
              onChange={(e) => setPublishedUrl(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button type="submit" disabled={loading} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50">
              {loading ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Calendar View ────────────────────────────────────

function CalendarView({ items }: { items: ScheduledItem[] }) {
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const daysInMonth = new Date(
    currentMonth.getFullYear(),
    currentMonth.getMonth() + 1,
    0
  ).getDate();

  const firstDayOfWeek = currentMonth.getDay(); // 0=Sun

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  };
  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  };

  // Build day -> items map
  const dayItems: Record<number, ScheduledItem[]> = {};
  for (const item of items) {
    if (!item.scheduled_at) continue;
    const d = new Date(item.scheduled_at);
    if (
      d.getFullYear() === currentMonth.getFullYear() &&
      d.getMonth() === currentMonth.getMonth()
    ) {
      const day = d.getDate();
      if (!dayItems[day]) dayItems[day] = [];
      dayItems[day].push(item);
    }
  }

  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === currentMonth.getFullYear() &&
    today.getMonth() === currentMonth.getMonth();

  const monthLabel = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div>
      {/* Month nav */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={prevMonth} className="p-2 hover:bg-gray-100 rounded-lg">
          <ChevronLeftIcon className="h-5 w-5 text-gray-600" />
        </button>
        <h3 className="text-lg font-semibold text-gray-900">{monthLabel}</h3>
        <button onClick={nextMonth} className="p-2 hover:bg-gray-100 rounded-lg">
          <ChevronRightIcon className="h-5 w-5 text-gray-600" />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 mb-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="text-center text-xs font-medium text-gray-500 py-2">
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7 border-t border-l border-gray-200">
        {/* Empty cells before first day */}
        {Array.from({ length: firstDayOfWeek }).map((_, i) => (
          <div key={`empty-${i}`} className="border-r border-b border-gray-200 bg-gray-50 min-h-[90px]" />
        ))}

        {/* Day cells */}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const isToday = isCurrentMonth && today.getDate() === day;
          const dItems = dayItems[day] || [];

          return (
            <div
              key={day}
              className={`border-r border-b border-gray-200 min-h-[90px] p-1 ${
                isToday ? "bg-blue-50" : "bg-white"
              }`}
            >
              <div
                className={`text-xs font-medium mb-1 ${
                  isToday
                    ? "text-white bg-blue-600 w-5 h-5 rounded-full flex items-center justify-center"
                    : "text-gray-600 px-0.5"
                }`}
              >
                {day}
              </div>
              {dItems.slice(0, 3).map((item) => (
                <div
                  key={item.id}
                  className={`text-[10px] px-1 py-0.5 rounded mb-0.5 truncate ${
                    PLATFORM_COLORS[item.platform] || PLATFORM_COLORS.other
                  }`}
                  title={`${item.title} (${formatTime(item.scheduled_at)})`}
                >
                  {item.title}
                </div>
              ))}
              {dItems.length > 3 && (
                <div className="text-[10px] text-gray-400 px-1">
                  +{dItems.length - 3} more
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────

export default function SchedulePage() {
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState<"kanban" | "calendar">("kanban");
  const [showNewModal, setShowNewModal] = useState(false);
  const [editingItem, setEditingItem] = useState<ScheduledItem | null>(null);

  // Drag state
  const dragItem = useRef<ScheduledItem | null>(null);

  const fetchBoard = useCallback(async () => {
    try {
      const data = await scheduleApi.getBoard();
      setBoard(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  // Realtime subscription
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel("scheduled_items_changes")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "scheduled_items" },
        () => {
          fetchBoard();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchBoard]);

  const handleDragStart = (e: React.DragEvent, item: ScheduledItem) => {
    dragItem.current = item;
    e.dataTransfer.effectAllowed = "move";
    // Transparent drag image for cleaner look
    const el = e.currentTarget as HTMLElement;
    e.dataTransfer.setDragImage(el, el.offsetWidth / 2, 20);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: string) => {
    e.preventDefault();
    const item = dragItem.current;
    if (!item || item.status === targetStatus) {
      dragItem.current = null;
      return;
    }

    // Optimistic update
    if (board) {
      const oldCol = item.status as keyof KanbanBoard;
      const newCol = targetStatus as keyof KanbanBoard;
      const updated = { ...board };
      updated[oldCol] = updated[oldCol].filter((i) => i.id !== item.id);
      const movedItem = { ...item, status: targetStatus as ScheduledItem["status"], column_order: updated[newCol].length };
      updated[newCol] = [...updated[newCol], movedItem];
      setBoard(updated);
    }

    try {
      await scheduleApi.move(item.id, targetStatus, board ? (board[targetStatus as keyof KanbanBoard]?.length || 0) : 0);
    } catch (err) {
      // Revert on failure
      fetchBoard();
    }
    dragItem.current = null;
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this item?")) return;
    try {
      await scheduleApi.delete(id);
      fetchBoard();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const allItems = board
    ? [...board.draft, ...board.scheduled, ...board.published, ...board.archived]
    : [];

  if (loading) {
    return (
      <main className="max-w-7xl mx-auto p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="flex gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex-1 h-64 bg-gray-100 rounded-xl" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Content Schedule</h1>
          <p className="text-sm text-gray-500 mt-1">
            Plan, schedule, and track your content across all platforms
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setView("kanban")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                view === "kanban"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <ViewColumnsIcon className="h-4 w-4" />
              Board
            </button>
            <button
              onClick={() => setView("calendar")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                view === "calendar"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <CalendarIcon className="h-4 w-4" />
              Calendar
            </button>
          </div>

          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
          >
            <PlusIcon className="h-4 w-4" />
            New Item
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Board or Calendar */}
      {view === "kanban" && board && (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {(["draft", "scheduled", "published", "archived"] as const).map((col) => (
            <KanbanColumn
              key={col}
              columnKey={col}
              items={board[col]}
              onDragStart={handleDragStart}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onEdit={setEditingItem}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {view === "calendar" && <CalendarView items={allItems} />}

      {/* Quick stats */}
      {board && (
        <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-900">{board.draft.length}</div>
            <div className="text-xs text-gray-500 mt-1">Drafts</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">{board.scheduled.length}</div>
            <div className="text-xs text-blue-600 mt-1">Scheduled</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-700">{board.published.length}</div>
            <div className="text-xs text-green-600 mt-1">Published</div>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-yellow-700">{board.archived.length}</div>
            <div className="text-xs text-yellow-600 mt-1">Archived</div>
          </div>
        </div>
      )}

      {/* Import hint */}
      {board && board.draft.length === 0 && board.scheduled.length === 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
          <h3 className="text-blue-900 font-medium mb-2">No content in your schedule yet</h3>
          <p className="text-blue-700 text-sm mb-4">
            Create items manually or go to an approved workflow and import content into your schedule.
          </p>
          <Link
            href="/content"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Go to Content Dashboard
          </Link>
        </div>
      )}

      {/* Modals */}
      {showNewModal && (
        <NewItemModal
          onClose={() => setShowNewModal(false)}
          onCreated={fetchBoard}
        />
      )}

      {editingItem && (
        <EditItemModal
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onSaved={fetchBoard}
        />
      )}
    </main>
  );
}
