# Pattern: Document Context Injection into LLM

**Slice:** 21
**Category:** LLM Prompt Engineering / Debugging
**Date:** 2026-02-17

## Problem

Users uploaded PDFs, images, and links through the chat. The extraction pipeline worked (text was extracted), but the LLM responded with "I can't read PDFs" or ignored the document content entirely. Three root causes:

1. **Injection failure:** Extracted text was appended to the user's message string, which could get truncated or lost in the message array.
2. **"PDF" trigger word:** System prompts contained the word "PDF", which triggered GPT-4o's trained refusal template ("I can't read PDFs") even when the document text was present.
3. **No validation gate:** If extraction returned empty or near-empty text, the system silently sent garbage to the LLM instead of failing fast.

## Solution

### 1. Validation gate (fail fast)

Before calling the LLM, check that the document text meets a minimum length threshold. If extraction produced junk, return a clear error instead of wasting an LLM call.

```python
if len(doc_text.strip()) < 50:
    raise HTTPException(
        status_code=422,
        detail=f"Document text was not included properly (length={len(doc_text.strip())}). "
               "The file extraction may have failed."
    )
```

### 2. Explicit markers + SHA1 fingerprint

Wrap injected text with structured markers so you can grep the outbound payload and prove the text reached the model.

```
DOCUMENT_CONTEXT v1
source=quarterly-report.pdf
sha1=a1b2c3d4e5f6
chars=12847
--- BEGIN DOCUMENT TEXT ---
... extracted text ...
--- END DOCUMENT TEXT ---
```

Log the SHA1 and char count at injection time. If the model ignores the text, you can search logs for the marker to confirm whether it was present.

### 3. Dedicated message slot (not appended to user text)

Inject document text as its own user message early in the conversation, followed by a brief assistant acknowledgment. This prevents truncation and keeps the document separate from the user's actual question.

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": document_context_block},   # <-- dedicated slot
    {"role": "assistant", "content": '{"reply": "Got it, I have the document text.", "extracted": {}}'},
    # ... rest of conversation history ...
]
```

### 4. Remove "PDF" trigger words from prompts

Replace all mentions of "PDF" in system prompts and user-facing instructions with neutral terms:

| Bad (triggers refusal) | Good |
|---|---|
| "Read the PDF" | "Use the document text below" |
| "Extract from the PDF" | "Process the provided document text" |
| "I can read PDFs" | "I can process user-provided documents" |

## Key decisions

1. **Minimum 50 chars for document validation.** Too low catches only truly empty extractions. Too high rejects short documents. 50 is a safe floor for "something real was extracted."
2. **SHA1 fingerprint for debugging, not security.** The 12-char truncated hash is enough to match a specific document in logs without storing sensitive content.
3. **Assistant acknowledgment is JSON-formatted.** The brand chat expects `{"reply": "...", "extracted": {...}}` format, so the fake acknowledgment follows the same schema.
4. **15,000 char truncation on document text.** Balances context window usage with useful content. Most documents have their key content in the first 15k chars.

## Reuse guidance

Any feature that injects external text into an LLM prompt should follow this pattern:
1. Validate the text exists and has meaningful length
2. Wrap with markers (name, hash, length)
3. Inject as a dedicated message, not appended to user input
4. Never use file-format names ("PDF", "DOCX") in prompts, use "document text"
5. Log the injection with enough detail to debug silently
