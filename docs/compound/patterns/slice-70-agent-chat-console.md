# Slice 70: Agent Chat Console + Deliverable Approval

**Date:** 2026-02-26
**Status:** Complete
**Methodology:** Compound Engineering + Ralph Loop

## Requirements

Build a chat interface in Mission Control that lets users interact with OpenClaw agents via the gateway bridge (built in Slice 69). Fix the broken approve/reject buttons on the orchestrator page.

## Architecture

```
┌─────────────────┐       ┌────────────────┐       ┌──────────────────┐
│ /mission-control │  JWT  │ /gateway/message│ Bearer│ OpenClaw Gateway  │
│ /chat (Next.js)  │ ────► │ (FastAPI proxy) │ ────► │ (VPS :18789)     │
│                  │       │                │       │                  │
│ Agent sidebar    │       │ Input validated│       │ Routes to agent  │
│ Chat bubbles     │       │ Rate limited   │       │ Returns response │
│ Quick prompts    │       │ Response sanitized     │                  │
└─────────────────┘       └────────────────┘       └──────────────────┘
```

## Changes

| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/app/mission-control/chat/page.tsx` | Created | Agent Chat Console: sidebar + chat panel + quick prompts |
| `apps/web/src/app/mission-control/orchestrator/page.tsx` | Updated | Fixed approve/reject buttons (wired to real API calls) |
| `apps/web/src/app/mission-control/page.tsx` | Updated | Added Chat link to sub-nav |
| `apps/web/src/app/mission-control/analytics/page.tsx` | Updated | Added Chat link to sub-nav |
| `apps/web/src/app/mission-control/orchestrator/page.tsx` | Updated | Added Chat link to sub-nav |
| `apps/web/src/app/mission-control/gateway/page.tsx` | Updated | Added Chat link to sub-nav |

## Chat Console Features

### Agent Sidebar (Left Panel)
- Lists all agents from gateway + mission control merged data
- Shows avatar emoji, name, model badge, status dot
- LEAD badge for orchestrator (Jumbo)
- Preview of last message in each conversation
- Auto-selects Jumbo (default orchestrator) on first load

### Chat Panel (Right Panel)
- **Welcome state**: Agent avatar, description, gateway status warning if offline
- **Quick prompts**: Context-aware suggestions (different for Jumbo vs specialists)
- **Message bubbles**: User messages right-aligned (violet), agent messages left-aligned (card bg)
- **Agent responses**: Avatar + name + timestamp header, card-style bubble
- **Error messages**: Red-highlighted bubble for failed deliveries
- **Typing indicator**: Animated dots while waiting for response
- **Session continuity**: Tracks session_id per agent for multi-turn conversations
- **New Chat button**: Clears conversation and session for fresh start

### Input Area
- Auto-resizing textarea with Enter-to-send, Shift+Enter for newline
- Character counter, gateway attribution line
- Send button with loading spinner state
- Disabled state while sending

## Deliverable Approval Fix

**Before (broken):**
```tsx
// TODO: Implement approve/reject via deliverable status update
await missionControlApi.listDeliverables({ task_id: d.task_id });
```

**After (working):**
```tsx
// Approve
await missionControlApi.updateDeliverable(d.id, "approved");
await loadData();

// Reject (with optional reason)
const reason = prompt("Rejection reason (optional):");
await missionControlApi.updateDeliverable(d.id, "rejected", reason || undefined);
await loadData();
```

## Security

1. **No XSS**: All message content rendered via JSX auto-escaping (no dangerouslySetInnerHTML)
2. **Input validation**: Backend validates agent_id with regex, caps messages at 10k chars
3. **Rate limiting**: `/gateway/message` at LLM tier (30 req/min) from Slice 69
4. **JWT auth**: All gateway and mission control endpoints require authentication
5. **No user-controlled URLs**: Chat only calls fixed backend endpoints via `apiFetch`
6. **Session IDs**: In-memory only (client-side), from gateway responses

## Patterns

- **Agent merge pattern**: Combine gateway agents (live status) with MC agents (avatars, roles) into single list
- **Optimistic UI**: User message appears instantly, agent response appended when gateway responds
- **Context-aware quick prompts**: Different prompts for orchestrator vs specialist agents
- **Sub-nav consistency**: All 5 MC pages share the same 5-link nav bar (Dashboard, Analytics, Orchestrator, Gateway, Chat)
- **Deliverable approval flow**: `updateDeliverable(id, status, feedback?)` → refresh data — uses existing PATCH endpoint

## Tests

- 856/856 Python tests passing (no new backend code needed)
- 0 TypeScript errors
