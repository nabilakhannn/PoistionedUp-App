# Pattern: Universal Content Ingestion in Chat

**Slice:** 20
**Category:** Feature Integration
**Date:** 2026-02-16

## Problem

The brand chat could only read text-based files (PDF text layer, DOCX, TXT). Scanned PDFs came back empty. Images were rejected entirely. Links to YouTube videos, websites, Reddit posts, and other platforms could not be processed despite the app already having all the extraction logic in `ingestion.py`.

## Solution

Three layers of content ingestion, all routed through the existing chat attachment flow:

### Layer 1: Enhanced file upload (images + OCR fallback)

```
File upload → extension check
  → Document? → extract_text() (pypdf, docx, csv, plain)
      → PDF empty? → PyMuPDF page→image → GPT-4 Vision OCR
  → Image? → GPT-4 Vision OCR directly
```

### Layer 2: Link extraction (new endpoint)

```
POST /brand/chat/extract-link
  → detect_platform(url)
  → extract_text_from_url(url)
    → YouTube: captions → Whisper fallback
    → TikTok/Facebook: Whisper transcription
    → Reddit: post body + comments
    → Twitter/X: tweet + metrics
    → Substack/LinkedIn: article text
    → Anything else: trafilatura article extraction
```

### Layer 3: Frontend UX

- Paperclip button: files + images (expanded accept types)
- Chain-link button: opens URL input bar
- Both show attachment preview with source type badge
- Both feed extracted text into the same `file_context` field on the chat request

## Key decisions

1. **GPT-4 Vision over Tesseract for OCR.** More reliable across layouts, no binary dependency, already available via OpenAI key.
2. **PyMuPDF for PDF page rendering.** Lighter than poppler/pdf2image. Converts pages to PNG at 200 DPI.
3. **Full reuse of ingestion.py.** Zero duplicate extraction logic. The chat just calls the same functions the resource pipeline uses.
4. **Max 10 pages for PDF OCR.** Cost control at ~$0.01-0.03 per page.

## Reuse guidance

Any new feature that needs to read user content (email import, social media analyzer, competitor research) should call the same `extract_text_from_url()` and `extract_text()` functions. The pattern is: detect what it is, extract, truncate, inject into prompt.
