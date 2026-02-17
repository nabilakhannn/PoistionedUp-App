# Pattern: Kanban Board + Calendar (Schedule Feature)

**Date:** 2026-02-16
**Used in:** Schedule page (`/schedule`)

---

## Problem

Users need a visual way to plan and track content across platforms. A flat list is not enough. They need columns (like Trello/Notion) and a calendar view.

## Solution

### Database

One table: `scheduled_items` with a `status` column that doubles as the kanban column:

```sql
CREATE TABLE scheduled_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  title TEXT NOT NULL,
  platform TEXT NOT NULL,
  content_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'scheduled', 'published', 'archived')),
  column_order INT NOT NULL DEFAULT 0,
  scheduled_at TIMESTAMPTZ,
  -- ... other fields
);
```

Key design choices:
- `status` is the kanban column (not a separate `column` field)
- `column_order` controls position within a column
- `scheduled_at` enables calendar view (nullable, only set when date is picked)
- Moving to "published" auto-sets `published_at`

### Backend API

7 endpoints on `/schedule`:
- `GET /schedule` returns `{ draft: [], scheduled: [], published: [], archived: [] }`
- `GET /schedule/calendar?start=X&end=Y` returns items in date range
- `POST /schedule` creates an item
- `POST /schedule/import/{workflow_id}` bulk-imports from a content workflow
- `PATCH /schedule/{id}` updates fields
- `PATCH /schedule/{id}/move` handles drag-and-drop (status + column_order)
- `DELETE /schedule/{id}` removes

### Frontend

- **Kanban view:** 4 columns, each renders cards. HTML5 `draggable` + `onDrop` handles drag-and-drop.
- **Calendar view:** Client-side month grid. Maps `scheduled_at` dates to grid cells.
- **Toggle:** Board/Calendar switch in the header.
- **Optimistic updates:** On drag, update local state immediately, then call API. Revert on error.
- **Realtime:** Supabase Realtime subscription on `scheduled_items` table refreshes the board on changes from other tabs/devices.

### Import from Workflow

When a content workflow is approved, users click "Add to Schedule" which:
1. Reads the workflow's content pack from snapshots
2. Creates one scheduled_item per content piece (YouTube script, LinkedIn post, tweet, etc.)
3. All items start as "draft" in the kanban

## Gotchas

1. **@heroicons/react won't install** with React 19 + Next.js 15. Use `@/components/icons` instead.
2. **Supabase `not_` in mock chains** is accessed as a property, not called as a function. Mock it as `chain.not_ = chain`, not `chain.not_.return_value = chain`.
3. **HTML5 drag-and-drop** doesn't work well on mobile. A touch library (dnd-kit) would be needed for mobile support.
4. **Calendar rendering** is client-side only. For 100+ items per month, consider server-side filtering.

## Reuse

This pattern works for any kanban-style feature. Change the status values and column headers, keep the same drag-and-drop, optimistic update, and Realtime subscription approach.
