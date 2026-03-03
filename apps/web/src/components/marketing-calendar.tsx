"use client";

/**
 * Marketing Calendar — Slice 92c
 *
 * Month-view calendar showing scheduled content.
 * - Platform emoji badges per day cell
 * - Click a day to expand that day's items
 * - ← / → month navigation (fetches new range from /schedule/calendar)
 * - "Today" ring highlight
 * - Graceful empty states
 */

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { scheduleApi, type ScheduledItem } from "@/lib/api/schedule";

interface Props {
  brandId: string;
}

// Platform display badges
const PLATFORM_BADGE: Record<string, string> = {
  linkedin: "🔵",
  twitter: "🐦",
  instagram: "📸",
  youtube: "📺",
  tiktok: "🎵",
  other: "📄",
};

// Status pill styles
const STATUS_STYLES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  scheduled: "bg-blue-500/15 text-blue-400",
  published: "bg-green-500/15 text-green-400",
  archived: "bg-muted/50 text-muted-foreground/50",
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

// Monday-first: 0=Mon ... 6=Sun
function getFirstDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay(); // 0=Sun
  return day === 0 ? 6 : day - 1;
}

export function MarketingCalendar({ brandId }: Props) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [items, setItems] = useState<ScheduledItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  const loadItems = useCallback(async () => {
    if (!brandId) return;
    setLoading(true);
    try {
      const start = new Date(year, month, 1).toISOString();
      const end = new Date(year, month + 1, 0, 23, 59, 59).toISOString();
      const data = await scheduleApi.getCalendar(start, end, brandId);
      setItems(data);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [brandId, year, month]);

  useEffect(() => {
    loadItems();
    setSelectedDay(null);
  }, [loadItems]);

  // Group items by day-of-month
  const dayMap: Record<number, ScheduledItem[]> = {};
  for (const item of items) {
    const dateStr = item.scheduled_at ?? item.published_at ?? null;
    if (!dateStr) continue;
    const d = new Date(dateStr);
    if (d.getFullYear() === year && d.getMonth() === month) {
      const day = d.getDate();
      if (!dayMap[day]) dayMap[day] = [];
      dayMap[day].push(item);
    }
  }

  const daysInMonth = getDaysInMonth(year, month);
  const firstDayOffset = getFirstDayOfWeek(year, month);
  const totalCells = Math.ceil((firstDayOffset + daysInMonth) / 7) * 7;
  const cells: (number | null)[] = [
    ...Array(firstDayOffset).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
    ...Array(totalCells - firstDayOffset - daysInMonth).fill(null),
  ];

  const isToday = (day: number) =>
    day === today.getDate() &&
    month === today.getMonth() &&
    year === today.getFullYear();

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11); }
    else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0); }
    else setMonth(m => m + 1);
  };

  const selectedItems = selectedDay ? (dayMap[selectedDay] ?? []) : [];

  return (
    <div className="space-y-4">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={prevMonth}
            className="p-1.5 rounded-md hover:bg-muted transition text-muted-foreground hover:text-foreground"
            aria-label="Previous month"
          >
            ←
          </button>
          <span className="text-sm font-semibold text-foreground min-w-[140px] text-center">
            {MONTH_NAMES[month]} {year}
          </span>
          <button
            onClick={nextMonth}
            className="p-1.5 rounded-md hover:bg-muted transition text-muted-foreground hover:text-foreground"
            aria-label="Next month"
          >
            →
          </button>
        </div>
        <Link
          href="/mission-control/content"
          className="text-xs text-primary hover:underline"
        >
          View Kanban →
        </Link>
      </div>

      {/* ── Grid ─────────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {/* Weekday headers */}
        <div className="grid grid-cols-7 border-b border-border">
          {WEEKDAYS.map(d => (
            <div
              key={d}
              className="py-2 text-center text-xs font-medium text-muted-foreground"
            >
              {d}
            </div>
          ))}
        </div>

        {/* Day cells */}
        {loading ? (
          <div className="grid grid-cols-7">
            {Array.from({ length: 35 }).map((_, i) => (
              <div
                key={i}
                className="min-h-[72px] border-b border-r border-border/50 p-1.5 animate-pulse bg-muted/20"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-7">
            {cells.map((day, i) => {
              if (!day) {
                return (
                  <div
                    key={`empty-${i}`}
                    className="min-h-[72px] border-b border-r border-border/30 bg-muted/5"
                  />
                );
              }

              const dayItems = dayMap[day] ?? [];
              const isSelected = selectedDay === day;
              const todayCell = isToday(day);
              const visibleBadges = dayItems.slice(0, 3);
              const overflow = dayItems.length - 3;

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDay(isSelected ? null : day)}
                  className={`min-h-[72px] border-b border-r border-border/50 p-1.5 text-left transition-colors hover:bg-muted/30 ${
                    isSelected ? "bg-primary/5 ring-1 ring-inset ring-primary/30" : ""
                  }`}
                >
                  {/* Day number */}
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-xs font-medium w-5 h-5 flex items-center justify-center rounded-full ${
                        todayCell
                          ? "bg-primary text-primary-foreground"
                          : "text-foreground"
                      }`}
                    >
                      {day}
                    </span>
                    {dayItems.length > 0 && (
                      <span className="text-[10px] text-muted-foreground">
                        {dayItems.length}
                      </span>
                    )}
                  </div>

                  {/* Platform badges */}
                  {visibleBadges.length > 0 && (
                    <div className="flex flex-wrap gap-0.5">
                      {visibleBadges.map((item, idx) => (
                        <span key={idx} className="text-[11px] leading-none">
                          {PLATFORM_BADGE[item.platform] ?? "📄"}
                        </span>
                      ))}
                      {overflow > 0 && (
                        <span className="text-[10px] text-muted-foreground leading-none">
                          +{overflow}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Day expansion panel ─────────────────────────────── */}
      {selectedDay && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-foreground">
              {MONTH_NAMES[month]} {selectedDay}
              {isToday(selectedDay) && (
                <span className="ml-2 text-primary text-[10px]">Today</span>
              )}
            </h3>
            <button
              onClick={() => setSelectedDay(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>

          {selectedItems.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No content scheduled for this day.
            </p>
          ) : (
            <div className="space-y-1.5">
              {selectedItems.map(item => (
                <div
                  key={item.id}
                  className="flex items-center gap-2 rounded-lg bg-muted/30 px-3 py-2"
                >
                  <span className="text-sm">
                    {PLATFORM_BADGE[item.platform] ?? "📄"}
                  </span>
                  <span className="flex-1 text-xs text-foreground line-clamp-1">
                    {item.title}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                      STATUS_STYLES[item.status] ?? STATUS_STYLES.draft
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────── */}
      {!loading && items.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-2">
            No content scheduled for {MONTH_NAMES[month]}.
          </p>
          <Link
            href="/mission-control/content"
            className="text-xs text-primary hover:underline"
          >
            Go to Kanban to schedule content →
          </Link>
        </div>
      )}
    </div>
  );
}
