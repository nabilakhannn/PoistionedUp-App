# Pattern: Resource Ingestion (Multi-Platform CRUD + Extraction + Chunking)

**Slice:** 5 — Resources CRUD + Ingestion
**Date:** 2026-02-14

---

## What this pattern does

Full resource lifecycle: create, upload, auto-extract text, chunk for search, list/filter/update/delete. Handles:
- **Notes** — user-entered text
- **Links** — auto-fetch web page content via trafilatura
- **YouTube videos** — two-tier transcript extraction (free captions → Whisper fallback)
- **TikTok videos** — audio download + Whisper transcription
- **Facebook videos/ads** — audio download + Whisper transcription
- **YouTube channels** — bulk import all videos with metadata + transcripts
- **Reddit threads** — post body + top 25 comments sorted by score (no auth needed)
- **Twitter/X posts** — tweet text + metrics (yt-dlp → oEmbed fallback)
- **Substack articles** — article text + publication metadata (trafilatura)
- **LinkedIn posts/articles** — Pulse articles work, regular posts may fail (auth wall)
- **File uploads** — PDF, DOCX, TXT, MD, CSV
- **Audio uploads** — MP3, WAV, M4A, OGG, FLAC → Whisper transcription (podcasts, voice memos)

## Key design decisions

### Multi-platform detection

URL detection routes to the correct extraction pipeline:
```python
detect_platform(url) → "youtube_video" | "youtube_channel" | "tiktok" | "facebook"
                      | "reddit" | "twitter" | "substack" | "linkedin" | "webpage"
```

Pattern matching uses regex for each platform. Falls back to `"webpage"` for unknown URLs.

Important: platform-specific patterns only match actionable URLs (e.g., Reddit only matches `/r/*/comments/*` posts, not subreddit listings; Twitter only matches `/status/*` tweets, not profiles).

### Video metadata + transcript header

For all video resources, content_text is prefixed with a structured header:
```
[VIDEO INFO]
Title: How to Make Pasta in 10 Minutes
Channel: Gordon Ramsay
Platform: youtube
Views: 1.5M
Duration: 10:30
Published: 2024-06-15

[TRANSCRIPT]
Today we're going to make the perfect pasta...
```

This lets the LLM pipeline naturally see video context when reading chunks. Video metadata (views, duration, thumbnail, channel) is also stored in chunk metadata JSONB for programmatic access.

### Reddit thread extraction (no auth)

Append `.json` to any Reddit URL → full post + all comments as JSON. No authentication needed.

**Extraction flow:**
1. Clean URL (strip query params, normalize old.reddit.com, handle redd.it redirects)
2. Fetch `URL.json` with proper User-Agent header (mandatory — Reddit 429s without it)
3. Parse post data (title, selftext, score, subreddit, author, created_utc)
4. Flatten nested comment tree recursively (skip deleted/removed, skip "more" stubs)
5. Sort comments by score, take top 25

**Output format:**
```
[REDDIT POST]
Subreddit: r/contentcreation
Title: How I grew to 100K subscribers
Author: u/creator123
Score: 1234
Comments: 156
Posted: 2024-06-15

The post body text here...

[TOP COMMENTS (25)]

--- Comment 1 (score: 567, u/commenter1) ---
This is the most upvoted comment...
```

### Twitter/X extraction (two-tier)

1. **Tier 1:** yt-dlp `extract_info()` — gets tweet text, author, likes, retweets
2. **Tier 2:** Twitter oEmbed API (`publish.twitter.com/oembed`) — official, no auth, returns HTML
3. **Fallback:** empty content with error message

Output uses `[TWEET]` header with author, likes, retweets, date.

### Substack extraction

Uses `trafilatura.bare_extraction()` which returns structured metadata (title, author, date) along with article text. Publication name extracted from URL subdomain. Custom domain Substacks fall through to regular `"webpage"` handler (trafilatura handles them fine).

Output uses `[SUBSTACK ARTICLE]` header.

### LinkedIn extraction (graceful fallback)

LinkedIn Pulse articles (`/pulse/` URLs) are public web pages — trafilatura works. Regular LinkedIn posts are behind an auth wall and will likely fail. The function returns a helpful error message suggesting manual copy-paste as a note.

Output uses `[LINKEDIN ARTICLE]` or `[LINKEDIN POST]` header.

### YouTube channel bulk import (async)

When user provides a channel URL (`@MrBeast`, `/c/...`, `/channel/...`):
1. yt-dlp lists all videos with `extract_flat="in_playlist"` (fast, no downloads)
2. Each video becomes a separate resource with metadata header (instant)
3. **Response returns immediately** — user sees all videos with "processing" status
4. **Background task** extracts transcripts (captions first, Whisper fallback) and updates each resource
5. Duplicate detection: skips videos already imported (by source_url)
6. Max 500 videos per import (configurable)

Uses FastAPI `BackgroundTasks` — no extra worker infrastructure needed. User can poll `GET /resources/{id}` to check if transcript is ready (content_text will contain `[TRANSCRIPT]` section).

### Auto-extraction for links

When a user creates a resource with `type=link` and provides a `source_url`:
- **YouTube videos** → Free captions first, Whisper fallback. Type auto-changes to `transcript`
- **TikTok/Facebook videos** → Whisper transcription. Type auto-changes to `transcript`
- **YouTube channels** → Returns 400 with guidance to use `/resources/channel`
- **Reddit threads** → Post body + top comments. Stays as `link` type.
- **Twitter/X posts** → Tweet text + metrics. Stays as `link` type.
- **Substack articles** → Article text + metadata. Stays as `link` type.
- **LinkedIn posts** → Attempted extraction (may fail). Stays as `link` type.
- **Regular web pages** → Extracts readable article text via `trafilatura`
- **Fallback** → Resource still created with empty content_text if extraction fails

### Audio upload → Whisper

Upload endpoint accepts audio files (MP3, WAV, M4A, OGG, FLAC, WebM). Audio is sent directly to OpenAI Whisper for transcription. Resource type is set to `transcript`. Useful for podcasts, voice memos, competitor audio content.

### Chunking strategy

- **Target:** ~500 tokens per chunk (~2000 characters)
- **Overlap:** 200 characters between chunks (for context continuity)
- **Split priority:** paragraph boundaries > sentence boundaries > word boundaries > hard cut
- **Empty text:** Returns zero chunks (not an error)

### Chunk metadata

Each chunk stores metadata in its JSONB field:
```json
{
  "char_count": 1847,
  "source_type": "youtube_transcript",
  "auto_extracted": true,
  "video_id": "dQw4w9WgXcQ",
  "channel": "MrBeast",
  "views": 150000000,
  "duration": 630,
  "thumbnail": "https://i.ytimg.com/...",
  "upload_date": "20240615",
  "language": "en",
  "method": "captions"
}
```

## Files

| File | Purpose |
|------|---------|
| `app/schemas/resource.py` | Request/response Pydantic models + channel import models |
| `app/services/ingestion.py` | Multi-platform extraction (12 platforms), metadata, chunking, channel scraping |
| `app/routers/resources.py` | 7 endpoints (CRUD + upload + channel import) with auth |
| `tests/test_resources.py` | 27 integration tests |
| `tests/test_ingestion.py` | 87 unit tests (no network) |

## Endpoints

| Method | URL | What |
|--------|-----|------|
| POST | `/resources` | Create note/link/transcript (auto-detects all platforms) |
| POST | `/resources/upload` | Upload file or audio (PDF/DOCX/TXT/MD/CSV/MP3/WAV/M4A) |
| POST | `/resources/channel` | Bulk import YouTube channel (all videos + transcripts) |
| GET | `/resources` | List with filters (?tag=, ?is_gold=, ?type=) |
| GET | `/resources/{id}` | Detail with chunks |
| PATCH | `/resources/{id}` | Update title, tags, gold |
| DELETE | `/resources/{id}` | Delete resource + chunks + storage file |

## Dependencies

```
pypdf==5.1.0              # PDF text extraction
python-docx==1.1.2        # DOCX text extraction
youtube-transcript-api==1.2.4  # YouTube captions (free, fast)
trafilatura==2.0.0        # Web page + Substack + LinkedIn extraction
yt-dlp==2025.10.14        # Video download + Twitter/X (1800+ sites)
openai==1.82.1            # Whisper speech-to-text
httpx==0.28.1             # Reddit JSON API (already a FastAPI dependency)
```

**System dependency:** `ffmpeg` must be installed (used by yt-dlp for audio extraction).

**No new dependencies added for Reddit/Substack/Twitter/LinkedIn** — all use existing packages (httpx, trafilatura, yt-dlp).

## Platform support

| Platform | Works? | Method | Auth? | Notes |
|----------|--------|--------|-------|-------|
| YouTube videos | Yes | Captions → Whisper | No | Two-tier: free first |
| YouTube channels | Yes | Bulk import | No | Async background transcripts |
| TikTok | Yes (public) | Whisper | No | ~$0.006/min |
| Facebook videos/ads | Yes (public) | Whisper | No | ~$0.006/min |
| Reddit threads | Yes | JSON API | No | Post + top 25 comments, free |
| Twitter/X posts | Partial | yt-dlp → oEmbed | No | May fail if X blocks |
| Substack articles | Yes | trafilatura | No | Custom domains fall to webpage |
| LinkedIn articles | Partial | trafilatura | No | Pulse works, regular posts fail |
| Instagram | Not yet | — | Yes | Requires login cookies (deferred) |
| Web pages | Yes | trafilatura | No | May fail on JS-heavy SPAs |
| Audio files | Yes | Whisper | No | MP3/WAV/M4A/OGG/FLAC |

## Gotchas

1. **YouTube transcripts — two-tier approach:** Try free captions first. If none exist, fall back to Whisper audio transcription. Whisper costs ~$0.006/min but works on any video with spoken words. Videos longer than 60 min are rejected (Whisper 25MB limit).
2. **TikTok/Facebook always use Whisper:** No free caption API exists for these platforms. Cost is minimal for short videos (~$0.001 per TikTok).
3. **trafilatura may fail on JavaScript-heavy sites:** Single-page apps that render client-side won't extract well. User should manually paste content.
4. **Channel import is async:** Resource rows created instantly, transcripts extract in the background via FastAPI BackgroundTasks. User polls individual resources to check completion.
5. **yt-dlp version matters:** Platforms change their frontends frequently. Keep yt-dlp updated (`pip install --upgrade yt-dlp`).
6. **No metadata column on resources table yet:** Video metadata stored in chunk metadata JSONB and content_text header. A future migration will add `metadata JSONB` to the resources table.
7. **Reddit User-Agent mandatory:** Reddit returns 429 without a proper User-Agent header. Must include descriptive User-Agent string.
8. **Reddit redd.it shortlinks:** Must follow redirect first, then append `.json` (redd.it itself doesn't support `.json` suffix).
9. **Reddit replies field type:** Can be empty string `""` instead of dict when no replies. Must check `isinstance(replies, dict)`.
10. **Twitter/X instability:** yt-dlp's X extractor breaks periodically. oEmbed fallback is essential but only returns basic text.
11. **LinkedIn auth wall:** Most regular LinkedIn posts return a login page. Only Pulse articles (`/pulse/` URLs) are reliably extractable. Error message guides user to paste text manually.
12. **Substack custom domains:** Publications with custom domains (e.g., stratechery.com) won't match Substack patterns — they correctly fall through to `"webpage"` handler.
