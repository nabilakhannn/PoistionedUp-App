# Pattern: File Attachment in Chat

**Slice:** 19
**Category:** UX + Backend Integration

## Problem

Users have to type long answers about their background, experience, and brand. Many already have this written in a resume, bio, or notes document. Typing everything from scratch is a friction point.

## Solution

Add a file attachment button in the brand chat that:
1. Accepts .pdf, .docx, .txt, .md, .csv files (up to 5 MB)
2. Extracts text server-side using existing `ingestion.extract_text`
3. Sends the extracted text alongside the user message as `file_context`
4. Shows the file as a badge in chat history without storing the full text

## Architecture

```
[Frontend]                    [Backend]
  |                              |
  |  POST /brand/chat/upload-context (file)
  | ----------------------------->|
  |  { filename, text, chars }    |  extract_text(file_bytes, content_type, filename)
  |<-----------------------------|
  |                              |
  |  POST /brand/chat            |
  |  { message, file_context }   |
  | ----------------------------->|
  |                              |  LLM sees: message + file text
  |                              |  Chat history stores: message + file badge
  |  { reply, extracted }         |
  |<-----------------------------|
```

## Key Decisions

- **Reuse existing extraction:** `ingestion.extract_text` already handles PDF, DOCX, CSV, TXT. No new packages.
- **Two-step upload:** Upload extracts text, then user sends it with their message. This lets them preview and remove.
- **Context isolation:** Full file text is only passed to the LLM for the current turn. Chat history stores only the message + a file indicator badge.
- **Truncation:** 20k char cap on upload, 15k cap in the LLM payload. Prevents context window overflow.

## Files

| File | Change |
|------|--------|
| `apps/api/app/schemas/brand.py` | Added `file_context`, `file_name` optional fields to `BrandChatRequest` |
| `apps/api/app/routers/brand.py` | Added `POST /brand/chat/upload-context`, modified `chat` endpoint |
| `apps/web/src/lib/api.ts` | Added `uploadChatFile`, updated `sendChat` signature |
| `apps/web/src/app/brand/chat/[module]/page.tsx` | Attach button, file preview, `UserMessage` component |
| `apps/api/tests/test_brand.py` | 8 tests for schema + endpoint |
| `apps/web/tests/brand-chat.spec.ts` | 5 Playwright tests for UI |

## Reuse Checklist

When adding file attachment to another chat or form:
1. Import `extract_text` from `app.services.ingestion`
2. Add a `POST /your-feature/upload-context` endpoint (copy the pattern from `brand.py`)
3. Add `file_context` field to your request schema
4. On the frontend, add `uploadChatFile`-style FormData upload and the paperclip button pattern
