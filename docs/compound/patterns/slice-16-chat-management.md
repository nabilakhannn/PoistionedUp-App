# Slice 16: Multi-Chat Management + Voice Input

## Pattern: Soft-Delete + Chat Switcher for Conversational UIs

### Problem
Users had one chat per module — no way to reset, try different approaches, or compare conversations. If they were "just trying," their exploratory data polluted the real brand profile.

### Solution: Multi-Chat with Soft-Delete

**Database:**
- Added `title` column to `brand_chats` for labeling
- Added `archived` status (soft-delete — data stays, just hidden)
- Multiple `active` chats can coexist per module

**API Endpoints Added:**
- `GET /brand/chats/{module}` — list all chats (active + completed, not archived)
- `GET /brand/chat/{module}?chat_id=<uuid>` — load a specific chat
- `POST /brand/chat/{module}/new` — start a fresh chat
- `DELETE /brand/chat/{chat_id}` — archive (soft-delete) a chat
- `PATCH /brand/chat/{chat_id}/title` — rename a chat

**Frontend:**
- Chat switcher bar between header and messages
- "New Chat" button always visible
- Expandable dropdown listing all chats with status indicators
- Trash icon per chat for deletion
- Active chat highlighted in blue, completed chats show "saved" badge

### Key Decisions
1. **Soft-delete over hard-delete.** `archived` status hides chats but preserves data. Users can't accidentally lose work.
2. **No limit on active chats.** Users can have multiple active chats per module. The most recent is loaded by default.
3. **Only completed chats merge into profile.** Starting a new chat doesn't affect the saved brand profile — only clicking "Done, review form" merges data.
4. **Chat switcher is minimal.** Small bar, not a full sidebar. Doesn't compete with the existing left (stages) and right (extracted data) sidebars.

### Voice Input Pattern
- Uses browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`)
- No external dependencies — works in Chrome, Edge, Safari
- Graceful degradation: hides mic button if API not available
- Shows error message if mic permission denied
- Real-time interim results fill the textarea as user speaks
- Auto-stops when user hits Send

### Gotchas
1. **Python 3.9 compatibility:** Use `Optional[str]` not `str | None` in FastAPI route params
2. **Web Speech API has no TypeScript types** — use `any` for recognition refs and events
3. **Headless browsers don't support Web Speech API** — Playwright tests check the button exists and is clickable, but don't test actual recognition
