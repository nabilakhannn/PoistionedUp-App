"""Text extraction and chunking for uploaded resources.

Supports:
  - Files: PDF, DOCX, TXT, MD, CSV, audio (MP3, WAV, M4A)
  - URLs: web pages (auto-fetch readable text)
  - Videos: YouTube, TikTok, Facebook (transcript + metadata extraction)
  - YouTube channels: bulk import all videos with metadata
  - Audio: podcast/voice files transcribed via OpenAI Whisper
  - Social: Reddit threads, Twitter/X posts, Substack articles, LinkedIn posts

Produces ~500-token chunks (approx 2000 chars) with 200-char overlap.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional

# ── Constants ─────────────────────────────────────────────

CHUNK_SIZE = 2000  # ~500 tokens at 4 chars/token
CHUNK_OVERLAP = 200

# Max video duration (seconds) for Whisper transcription
MAX_VIDEO_DURATION = 3600  # 60 minutes


# ── Text extraction (files) ──────────────────────────────


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file.

    Strategy (best quality first, cheapest first):
      1. Try pypdf (fast, handles most standard PDFs)
      2. If pypdf returns empty/very short text, try PyMuPDF (handles
         CIDFont, Google Drive exports, Canva, Word-to-PDF, etc.)
      3. Caller can still fall back to Vision OCR if both return empty
    """
    import logging

    logger = logging.getLogger(__name__)

    # ── Tier 1: pypdf (fast, good for standard PDFs) ──
    text = ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        text = "\n\n".join(pages)
    except Exception as e:
        logger.warning("pypdf extraction failed, will try PyMuPDF: %s", e)

    # ── Tier 2: PyMuPDF (handles CIDFont, complex encodings, etc.) ──
    # Trigger if pypdf returned nothing useful (empty or under 20 chars
    # for a multi-page doc, which usually means garbled/encoded text)
    if not text.strip() or len(text.strip()) < 20:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=file_bytes, filetype="pdf")
            fitz_pages = []
            for page in doc:
                page_text = page.get_text()
                if page_text and page_text.strip():
                    fitz_pages.append(page_text.strip())
            doc.close()

            fitz_text = "\n\n".join(fitz_pages)

            # Use PyMuPDF result if it got more text than pypdf
            if len(fitz_text.strip()) > len(text.strip()):
                logger.info(
                    "PyMuPDF extracted %d chars vs pypdf %d chars, using PyMuPDF",
                    len(fitz_text), len(text),
                )
                text = fitz_text
        except ImportError:
            logger.debug("PyMuPDF not installed, skipping fallback")
        except Exception as e:
            logger.warning("PyMuPDF extraction also failed: %s", e)

    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text from a CSV file (all cells joined)."""
    text_content = file_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text_content))
    rows = []
    for row in reader:
        rows.append(" | ".join(row))
    return "\n".join(rows)


def extract_text_from_plain(file_bytes: bytes) -> str:
    """Extract text from TXT or MD files."""
    return file_bytes.decode("utf-8", errors="replace")


def extract_text(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Route to the correct extractor based on MIME type or filename."""
    ct = content_type.lower()

    if ct == "application/pdf" or filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)

    if (
        ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or filename.lower().endswith(".docx")
    ):
        return extract_text_from_docx(file_bytes)

    if ct == "text/csv" or filename.lower().endswith(".csv"):
        return extract_text_from_csv(file_bytes)

    # Default: treat as plain text (txt, md, etc.)
    return extract_text_from_plain(file_bytes)


# ── Platform detection ───────────────────────────────────


# YouTube URL patterns (single video)
_YT_VIDEO_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]{11})"),
    re.compile(r"(?:https?://)?youtu\.be/([\w-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]{11})"),
]

# YouTube channel/user URL patterns
_YT_CHANNEL_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/@[\w.-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/c/[\w.-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/user/[\w.-]+"),
]

# TikTok video URL patterns
_TIKTOK_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/(\d+)"),
    re.compile(r"(?:https?://)?(?:vm\.)?tiktok\.com/[\w-]+"),
]

# Facebook video/ad URL patterns
_FACEBOOK_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?facebook\.com/.+/videos/"),
    re.compile(r"(?:https?://)?(?:www\.)?facebook\.com/reel/"),
    re.compile(r"(?:https?://)?(?:www\.)?facebook\.com/ads/library/"),
    re.compile(r"(?:https?://)?(?:www\.)?facebook\.com/watch/"),
    re.compile(r"(?:https?://)?(?:fb\.watch)/"),
]

# Reddit post URL patterns (must match /r/*/comments/* to detect actual posts)
_REDDIT_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/\w+"),
    re.compile(r"(?:https?://)?old\.reddit\.com/r/\w+/comments/\w+"),
    re.compile(r"(?:https?://)?redd\.it/\w+"),
]

# Substack article URL patterns
_SUBSTACK_PATTERNS = [
    re.compile(r"(?:https?://)?[\w-]+\.substack\.com/p/[\w-]+"),
    re.compile(r"(?:https?://)?[\w-]+\.substack\.com/publish/post/\d+"),
]

# Twitter/X post URL patterns
_TWITTER_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?twitter\.com/\w+/status/(\d+)"),
    re.compile(r"(?:https?://)?(?:www\.)?x\.com/\w+/status/(\d+)"),
    re.compile(r"(?:https?://)?(?:mobile\.)?twitter\.com/\w+/status/(\d+)"),
    re.compile(r"(?:https?://)?(?:mobile\.)?x\.com/\w+/status/(\d+)"),
]

# LinkedIn URL patterns (posts, articles, feed updates)
_LINKEDIN_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/posts/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/pulse/[\w-]+"),
    re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/feed/update/[\w:]+"),
]


def _extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL. Returns None if not a YouTube video link."""
    for pattern in _YT_VIDEO_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to.

    Returns one of: 'youtube_video', 'youtube_channel', 'tiktok', 'facebook',
    'reddit', 'twitter', 'substack', 'linkedin', or 'webpage'.
    """
    # YouTube single video
    if _extract_youtube_id(url):
        return "youtube_video"

    # YouTube channel/user
    for pattern in _YT_CHANNEL_PATTERNS:
        if pattern.match(url):
            return "youtube_channel"

    # TikTok
    for pattern in _TIKTOK_PATTERNS:
        if pattern.match(url):
            return "tiktok"

    # Facebook
    for pattern in _FACEBOOK_PATTERNS:
        if pattern.match(url):
            return "facebook"

    # Reddit post
    for pattern in _REDDIT_PATTERNS:
        if pattern.match(url):
            return "reddit"

    # Twitter/X
    for pattern in _TWITTER_PATTERNS:
        if pattern.match(url):
            return "twitter"

    # Substack article
    for pattern in _SUBSTACK_PATTERNS:
        if pattern.match(url):
            return "substack"

    # LinkedIn
    for pattern in _LINKEDIN_PATTERNS:
        if pattern.match(url):
            return "linkedin"

    return "webpage"


# ── Video metadata extraction (no download) ──────────────


def _format_duration(seconds: Optional[int]) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    if not seconds:
        return "unknown"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_views(count: Optional[int]) -> str:
    """Format view count as human-readable string."""
    if count is None:
        return "unknown"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def extract_video_metadata(url: str) -> Dict[str, Any]:
    """Extract video metadata using yt-dlp without downloading the video.

    Works for YouTube, TikTok, Facebook, and 1800+ other platforms.

    Returns dict with:
      - title, channel, platform, views, duration, duration_str,
        thumbnail, upload_date, description, like_count
      - error: empty string on success, error message on failure
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {"error": "Could not extract metadata"}

        duration = info.get("duration")
        views = info.get("view_count")

        return {
            "title": info.get("title", ""),
            "channel": info.get("channel") or info.get("uploader") or "",
            "platform": info.get("extractor_key", "unknown").lower(),
            "views": views,
            "views_str": _format_views(views),
            "duration": duration,
            "duration_str": _format_duration(duration),
            "thumbnail": info.get("thumbnail", ""),
            "upload_date": info.get("upload_date", ""),  # YYYYMMDD format
            "description": (info.get("description") or "")[:1000],
            "like_count": info.get("like_count"),
            "error": "",
        }

    except Exception as e:
        return {"error": f"Metadata extraction failed: {str(e)}"}


def format_metadata_header(meta: Dict[str, Any]) -> str:
    """Format video metadata as a text header to prepend to content_text.

    This lets the LLM pipeline see the context naturally when reading chunks.
    """
    lines = ["[VIDEO INFO]"]

    if meta.get("title"):
        lines.append(f"Title: {meta['title']}")
    if meta.get("channel"):
        lines.append(f"Channel: {meta['channel']}")
    if meta.get("platform"):
        lines.append(f"Platform: {meta['platform']}")
    if meta.get("views_str"):
        lines.append(f"Views: {meta['views_str']}")
    if meta.get("duration_str"):
        lines.append(f"Duration: {meta['duration_str']}")
    if meta.get("upload_date"):
        # Format YYYYMMDD to YYYY-MM-DD
        d = meta["upload_date"]
        if len(d) == 8:
            lines.append(f"Published: {d[:4]}-{d[4:6]}-{d[6:8]}")
        else:
            lines.append(f"Published: {d}")
    if meta.get("description"):
        lines.append(f"Description: {meta['description'][:300]}")

    lines.append("")
    lines.append("[TRANSCRIPT]")
    return "\n".join(lines)


# ── YouTube captions (free) ──────────────────────────────


def _transcribe_with_captions(video_id: str) -> Optional[Dict[str, str]]:
    """Try to get transcript from YouTube captions (free, instant).

    Returns dict with text/language/error, or None if no captions available.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prefer English, fall back to any available, then try auto-generated
        transcript = None
        lang = "unknown"
        try:
            transcript = transcript_list.find_transcript(["en"])
            lang = "en"
        except Exception:
            try:
                for t in transcript_list:
                    if not t.is_generated:
                        transcript = t
                        lang = t.language_code
                        break
            except Exception:
                pass

        if transcript is None:
            try:
                for t in transcript_list:
                    transcript = t
                    lang = t.language_code
                    break
            except Exception:
                pass

        if transcript is None:
            return None

        entries = transcript.fetch()
        lines = [entry.text for entry in entries]
        full_text = " ".join(lines)

        return {"text": full_text, "language": lang, "error": "", "method": "captions"}

    except Exception:
        return None


# ── Whisper transcription (any platform) ─────────────────


def _transcribe_url_with_whisper(url: str) -> Dict[str, str]:
    """Download audio from any yt-dlp-supported URL and transcribe with Whisper.

    Works for YouTube, TikTok, Facebook, and 1800+ other platforms.
    Costs ~$0.006/min of audio. Requires: yt-dlp, ffmpeg, openai.
    """
    import os
    import tempfile

    try:
        import yt_dlp
        from openai import OpenAI
        from app.config import settings

        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return {
                "text": "", "language": "", "error": "OPENAI_API_KEY not configured",
                "method": "whisper",
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.m4a")

            ydl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": audio_path,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "match_filter": yt_dlp.utils.match_filter_func(
                    f"duration <= {MAX_VIDEO_DURATION}"
                ),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded file (yt-dlp may add extension)
            actual_path = audio_path
            if not os.path.exists(actual_path):
                for f in os.listdir(tmpdir):
                    actual_path = os.path.join(tmpdir, f)
                    break

            if not os.path.exists(actual_path):
                return {
                    "text": "", "language": "", "error": "Failed to download audio",
                    "method": "whisper",
                }

            # Check file size (Whisper API limit: 25MB)
            file_size = os.path.getsize(actual_path)
            if file_size > 25 * 1024 * 1024:
                return {
                    "text": "", "language": "",
                    "error": "Audio file too large for Whisper (>25MB). Try a shorter video.",
                    "method": "whisper",
                }

            client = OpenAI(api_key=api_key)
            with open(actual_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )

            text = result if isinstance(result, str) else str(result)

            return {
                "text": text.strip(),
                "language": "en",
                "error": "",
                "method": "whisper",
            }

    except Exception as e:
        return {
            "text": "", "language": "", "error": f"Whisper transcription failed: {str(e)}",
            "method": "whisper",
        }


def _transcribe_with_whisper(video_id: str) -> Dict[str, str]:
    """Download YouTube audio by video ID and transcribe with Whisper.

    Kept for backward compatibility. Delegates to the generic URL transcriber.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    return _transcribe_url_with_whisper(url)


def transcribe_audio_bytes(file_bytes: bytes, filename: str) -> Dict[str, str]:
    """Transcribe an uploaded audio file (MP3, WAV, M4A, etc.) with Whisper.

    For podcast episodes, voice memos, or any audio file.
    """
    import os
    import tempfile

    try:
        from openai import OpenAI
        from app.config import settings

        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return {
                "text": "", "language": "",
                "error": "OPENAI_API_KEY not configured",
                "method": "whisper",
            }

        if len(file_bytes) > 25 * 1024 * 1024:
            return {
                "text": "", "language": "",
                "error": "Audio file too large for Whisper (>25MB).",
                "method": "whisper",
            }

        with tempfile.NamedTemporaryFile(suffix=f"_{filename}", delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()

            client = OpenAI(api_key=api_key)
            with open(tmp.name, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )

        text = result if isinstance(result, str) else str(result)
        return {"text": text.strip(), "language": "en", "error": "", "method": "whisper"}

    except Exception as e:
        return {
            "text": "", "language": "",
            "error": f"Audio transcription failed: {str(e)}",
            "method": "whisper",
        }


# ── YouTube transcript (two-tier) ────────────────────────


def extract_youtube_transcript(video_id: str) -> Dict[str, str]:
    """Fetch YouTube transcript for a video.

    Strategy (cheapest first):
      1. Try YouTube captions (free, instant)
      2. Fall back to Whisper audio transcription (~$0.006/min, 30-60s)

    Returns dict with keys:
      - text: the full transcript as plain text
      - language: which language was fetched
      - error: error message if extraction failed (text will be empty)
      - method: "captions" or "whisper"
    """
    # Step 1: Try free captions first
    result = _transcribe_with_captions(video_id)
    if result and result["text"]:
        return result

    # Step 2: Fall back to Whisper (costs money, but works on any video)
    return _transcribe_with_whisper(video_id)


# ── Reddit extraction (public JSON API) ──────────────────


def _clean_reddit_url(url: str) -> str:
    """Normalize a Reddit URL for .json fetching."""
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    clean = urllib.parse.urlunparse((
        parsed.scheme or "https",
        parsed.netloc,
        parsed.path.rstrip("/"),
        "", "", "",
    ))

    # Remove trailing .json if already present
    if clean.endswith(".json"):
        clean = clean[:-5]

    # Normalize old.reddit.com → www.reddit.com
    clean = clean.replace("old.reddit.com", "www.reddit.com")

    return clean


def _fetch_reddit_json(url: str) -> list:
    """Fetch Reddit post data as JSON by appending .json to the URL."""
    import httpx

    clean_url = _clean_reddit_url(url)

    headers = {
        "User-Agent": "ContentOrchestrator/1.0 (resource-ingestion)",
    }

    # For redd.it shortlinks, resolve the redirect first
    if "redd.it" in clean_url:
        resolve_resp = httpx.head(
            clean_url, headers=headers, follow_redirects=True, timeout=10.0,
        )
        clean_url = _clean_reddit_url(str(resolve_resp.url))

    json_url = clean_url + ".json"

    response = httpx.get(
        json_url,
        headers=headers,
        follow_redirects=True,
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


def _flatten_comments(
    children: list, result: list, max_depth: int = 10,
) -> None:
    """Recursively flatten Reddit comment tree into a flat list."""
    if max_depth <= 0:
        return

    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("kind") != "t1":
            continue

        data = child.get("data", {})
        body = data.get("body", "")
        author = data.get("author", "[deleted]")

        # Skip deleted/removed comments
        if body in ("[deleted]", "[removed]", ""):
            continue

        result.append({
            "body": body,
            "score": data.get("score", 0),
            "author": author,
            "created_utc": data.get("created_utc", 0),
        })

        # Recurse into replies (can be "" instead of dict when empty)
        replies = data.get("replies")
        if isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            _flatten_comments(reply_children, result, max_depth - 1)


def _parse_reddit_post(json_data: list) -> Dict[str, Any]:
    """Parse Reddit JSON response into structured post + comments."""
    if not json_data or len(json_data) < 2:
        return {"error": "Invalid Reddit JSON structure"}

    post_data = json_data[0]["data"]["children"][0]["data"]

    post = {
        "title": post_data.get("title", ""),
        "selftext": post_data.get("selftext", ""),
        "score": post_data.get("score", 0),
        "num_comments": post_data.get("num_comments", 0),
        "subreddit": post_data.get("subreddit", ""),
        "author": post_data.get("author", "[deleted]"),
        "created_utc": post_data.get("created_utc", 0),
        "url": post_data.get("url", ""),
        "is_self": post_data.get("is_self", True),
    }

    # Flatten comment tree and collect all comments
    comments: List[Dict[str, Any]] = []
    _flatten_comments(json_data[1]["data"]["children"], comments)

    # Sort by score descending, take top 25
    comments.sort(key=lambda c: c.get("score", 0), reverse=True)
    top_comments = comments[:25]

    return {"post": post, "comments": top_comments, "error": ""}


def _format_reddit_header(post: Dict[str, Any], comment_count: int) -> str:
    """Format Reddit post as a text header."""
    from datetime import datetime, timezone

    lines = ["[REDDIT POST]"]
    lines.append(f"Subreddit: r/{post['subreddit']}")
    lines.append(f"Title: {post['title']}")
    lines.append(f"Author: u/{post['author']}")
    lines.append(f"Score: {post['score']}")
    lines.append(f"Comments: {post['num_comments']}")

    if post.get("created_utc"):
        dt = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)
        lines.append(f"Posted: {dt.strftime('%Y-%m-%d')}")

    if not post.get("is_self") and post.get("url"):
        lines.append(f"Link: {post['url']}")

    lines.append("")

    if post.get("selftext"):
        lines.append(post["selftext"])
        lines.append("")

    if comment_count > 0:
        lines.append(f"[TOP COMMENTS ({comment_count})]")

    return "\n".join(lines)


def _format_reddit_comments(comments: List[Dict[str, Any]]) -> str:
    """Format top Reddit comments as text."""
    lines: List[str] = []
    for i, comment in enumerate(comments, 1):
        lines.append(
            f"\n--- Comment {i} (score: {comment['score']}, u/{comment['author']}) ---"
        )
        lines.append(comment["body"])
    return "\n".join(lines)


def _extract_reddit_post(url: str) -> Dict[str, Any]:
    """Extract text from a Reddit post URL (post body + top comments).

    Uses Reddit's public JSON API (no authentication needed).
    """
    try:
        json_data = _fetch_reddit_json(url)
        parsed = _parse_reddit_post(json_data)

        if parsed.get("error"):
            return {
                "text": "",
                "source_type": "reddit",
                "error": parsed["error"],
                "metadata": {},
            }

        post = parsed["post"]
        comments = parsed["comments"]

        header = _format_reddit_header(post, len(comments))
        comment_text = _format_reddit_comments(comments) if comments else ""
        full_text = header + "\n" + comment_text

        return {
            "text": full_text.strip(),
            "source_type": "reddit",
            "error": "",
            "metadata": {
                "subreddit": post["subreddit"],
                "author": post["author"],
                "score": post["score"],
                "num_comments": post["num_comments"],
                "comment_count_extracted": len(comments),
                "auto_extracted": True,
            },
        }

    except Exception as e:
        return {
            "text": "",
            "source_type": "reddit",
            "error": f"Reddit extraction failed: {str(e)}",
            "metadata": {},
        }


# ── Twitter/X extraction (yt-dlp + oEmbed fallback) ─────


def _extract_twitter_post(url: str) -> Dict[str, Any]:
    """Extract text from a Twitter/X post.

    Strategy:
      1. Try yt-dlp extract_info (gets tweet text, author, metrics)
      2. Fallback: Twitter oEmbed API (official, no auth, returns HTML with tweet text)
      3. If both fail: return empty content with error message
    """
    # Normalize: ensure https
    if not url.startswith("http"):
        url = "https://" + url

    tweet_text = ""
    author = ""
    like_count = None
    retweet_count = None
    upload_date = ""

    # ── Tier 1: yt-dlp ──
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info:
            tweet_text = info.get("description") or ""
            author = info.get("uploader") or info.get("channel") or ""
            like_count = info.get("like_count")
            retweet_count = info.get("repost_count") or info.get("retweet_count")
            upload_date = info.get("upload_date", "")
    except Exception:
        pass  # Fall through to oEmbed

    # ── Tier 2: oEmbed fallback ──
    if not tweet_text:
        try:
            import httpx

            oembed_url = f"https://publish.twitter.com/oembed?url={url}&omit_script=true"
            resp = httpx.get(oembed_url, follow_redirects=True, timeout=10.0)
            resp.raise_for_status()
            oembed_data = resp.json()

            # oEmbed returns HTML in "html" field — strip tags
            raw_html = oembed_data.get("html", "")
            tweet_text = re.sub(r"<[^>]+>", " ", raw_html)
            tweet_text = " ".join(tweet_text.split())  # collapse whitespace

            if not author:
                author = oembed_data.get("author_name", "")
        except Exception:
            pass

    # ── Build result ──
    if not tweet_text:
        return {
            "text": "",
            "source_type": "twitter",
            "error": "Could not extract tweet text. Twitter may require authentication.",
            "metadata": {"auto_extracted": False},
        }

    lines = ["[TWEET]"]
    if author:
        lines.append(f"Author: @{author}")
    if like_count is not None:
        lines.append(f"Likes: {_format_views(like_count)}")
    if retweet_count is not None:
        lines.append(f"Retweets: {_format_views(retweet_count)}")
    if upload_date and len(upload_date) == 8:
        lines.append(f"Date: {upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}")
    lines.append("")
    lines.append(tweet_text)

    full_text = "\n".join(lines)

    return {
        "text": full_text,
        "source_type": "twitter",
        "error": "",
        "metadata": {
            "author": author,
            "like_count": like_count,
            "retweet_count": retweet_count,
            "upload_date": upload_date,
            "auto_extracted": True,
        },
    }


# ── Substack extraction (trafilatura) ────────────────────


def _extract_substack_article(url: str) -> Dict[str, Any]:
    """Extract text from a Substack article using trafilatura.

    Substack articles are server-rendered HTML, so trafilatura works well.
    """
    try:
        import trafilatura
        import urllib.parse

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "text": "", "source_type": "substack",
                "error": "Could not fetch Substack URL", "metadata": {},
            }

        result = trafilatura.bare_extraction(
            downloaded, include_comments=False, include_tables=True,
        )

        if not result or not result.get("text"):
            return {
                "text": "", "source_type": "substack",
                "error": "Could not extract text from Substack article",
                "metadata": {},
            }

        # Extract publication from URL subdomain
        parsed = urllib.parse.urlparse(url)
        publication = parsed.netloc.replace(".substack.com", "")

        title = result.get("title", "")
        author = result.get("author", "")
        date = result.get("date", "")
        text = result["text"]

        lines = ["[SUBSTACK ARTICLE]"]
        if publication:
            lines.append(f"Publication: {publication}")
        if title:
            lines.append(f"Title: {title}")
        if author:
            lines.append(f"Author: {author}")
        if date:
            lines.append(f"Date: {date}")
        lines.append("")

        full_text = "\n".join(lines) + text

        return {
            "text": full_text,
            "source_type": "substack",
            "error": "",
            "metadata": {
                "publication": publication,
                "title": title,
                "author": author,
                "date": date,
                "auto_extracted": True,
            },
        }

    except Exception as e:
        return {
            "text": "", "source_type": "substack",
            "error": f"Substack extraction failed: {str(e)}",
            "metadata": {},
        }


# ── LinkedIn extraction (trafilatura with graceful fallback) ─


def _extract_linkedin_content(url: str) -> Dict[str, Any]:
    """Extract text from a LinkedIn URL.

    LinkedIn Pulse articles (blog posts) are public and work with trafilatura.
    Regular LinkedIn posts are behind an auth wall and will likely fail.
    """
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "text": "", "source_type": "linkedin",
                "error": "Could not fetch LinkedIn URL. LinkedIn posts often require authentication. Try pasting the text manually as a note.",
                "metadata": {"auto_extracted": False},
            }

        result = trafilatura.bare_extraction(
            downloaded, include_comments=False, include_tables=True,
        )

        if not result or not result.get("text"):
            return {
                "text": "", "source_type": "linkedin",
                "error": "Could not extract text. LinkedIn posts are often behind an auth wall. Try pasting the text manually as a note.",
                "metadata": {"auto_extracted": False},
            }

        title = result.get("title", "")
        author = result.get("author", "")
        date = result.get("date", "")
        text = result["text"]

        is_pulse = "/pulse/" in url
        header_label = "LINKEDIN ARTICLE" if is_pulse else "LINKEDIN POST"

        lines = [f"[{header_label}]"]
        if title:
            lines.append(f"Title: {title}")
        if author:
            lines.append(f"Author: {author}")
        if date:
            lines.append(f"Date: {date}")
        lines.append("")

        full_text = "\n".join(lines) + text

        return {
            "text": full_text,
            "source_type": "linkedin",
            "error": "",
            "metadata": {
                "title": title,
                "author": author,
                "date": date,
                "is_pulse": is_pulse,
                "auto_extracted": True,
            },
        }

    except Exception as e:
        return {
            "text": "", "source_type": "linkedin",
            "error": f"LinkedIn extraction failed: {str(e)}",
            "metadata": {},
        }


# ── Multi-platform URL extraction ────────────────────────


def extract_text_from_url(url: str) -> Dict[str, Any]:
    """Fetch and extract text from a URL. Supports all major platforms.

    For YouTube videos: free captions first, then Whisper fallback.
    For TikTok/Facebook videos: Whisper transcription + metadata.
    For Reddit: post body + top comments (sorted by score).
    For Twitter/X: tweet text + metrics (yt-dlp, oEmbed fallback).
    For Substack: article text + publication metadata.
    For LinkedIn: article text (Pulse works, regular posts may fail).
    For regular links: fetches the page and extracts article text.

    Returns dict with keys:
      - text: extracted text content (with metadata header for videos)
      - source_type: platform identifier string
      - error: error message if extraction failed
      - metadata: platform-specific info
    """
    platform = detect_platform(url)

    # ── YouTube single video ──
    if platform == "youtube_video":
        video_id = _extract_youtube_id(url)
        transcript = extract_youtube_transcript(video_id)
        meta = extract_video_metadata(url)

        text = transcript["text"]
        if text and not meta.get("error"):
            text = format_metadata_header(meta) + "\n" + text

        return {
            "text": text,
            "source_type": "youtube_transcript",
            "error": transcript["error"],
            "metadata": {
                "video_id": video_id,
                "language": transcript["language"],
                "method": transcript.get("method", ""),
                **{k: v for k, v in meta.items() if k != "error"},
            },
        }

    # ── YouTube channel (returns list indicator) ──
    if platform == "youtube_channel":
        return {
            "text": "",
            "source_type": "youtube_channel",
            "error": "Use the /resources/channel endpoint for channel imports",
            "metadata": {},
        }

    # ── TikTok video ──
    if platform == "tiktok":
        meta = extract_video_metadata(url)
        transcript = _transcribe_url_with_whisper(url)

        text = transcript["text"]
        if text and not meta.get("error"):
            text = format_metadata_header(meta) + "\n" + text

        return {
            "text": text,
            "source_type": "tiktok_transcript",
            "error": transcript["error"],
            "metadata": {
                "language": transcript["language"],
                "method": "whisper",
                **{k: v for k, v in meta.items() if k != "error"},
            },
        }

    # ── Facebook video ──
    if platform == "facebook":
        meta = extract_video_metadata(url)
        transcript = _transcribe_url_with_whisper(url)

        text = transcript["text"]
        if text and not meta.get("error"):
            text = format_metadata_header(meta) + "\n" + text

        return {
            "text": text,
            "source_type": "facebook_transcript",
            "error": transcript["error"],
            "metadata": {
                "language": transcript["language"],
                "method": "whisper",
                **{k: v for k, v in meta.items() if k != "error"},
            },
        }

    # ── Reddit post ──
    if platform == "reddit":
        return _extract_reddit_post(url)

    # ── Twitter/X post ──
    if platform == "twitter":
        return _extract_twitter_post(url)

    # ── Substack article ──
    if platform == "substack":
        return _extract_substack_article(url)

    # ── LinkedIn ──
    if platform == "linkedin":
        return _extract_linkedin_content(url)

    # ── Regular webpage ──
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "text": "",
                "source_type": "webpage",
                "error": "Could not fetch URL",
                "metadata": {},
            }

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
        )

        return {
            "text": text or "",
            "source_type": "webpage",
            "error": "" if text else "Could not extract readable text from page",
            "metadata": {},
        }

    except Exception as e:
        return {
            "text": "",
            "source_type": "webpage",
            "error": str(e),
            "metadata": {},
        }


# ── YouTube channel extraction ───────────────────────────


def extract_channel_videos(channel_url: str, max_videos: int = 500) -> Dict[str, Any]:
    """List all videos from a YouTube channel using yt-dlp.

    Returns dict with:
      - channel_name: the channel name
      - videos: list of dicts with video metadata (title, url, views, duration, etc.)
      - count: total number of videos found
      - error: empty on success
    """
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "playlistend": max_videos,
        }

        # Ensure we're looking at the videos tab
        url = channel_url.rstrip("/")
        if not url.endswith("/videos"):
            url = url + "/videos"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {"channel_name": "", "videos": [], "count": 0, "error": "Could not access channel"}

        channel_name = info.get("channel") or info.get("uploader") or info.get("title", "")
        entries = info.get("entries", [])

        videos = []
        for entry in entries:
            if entry is None:
                continue
            video_id = entry.get("id", "")
            videos.append({
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else entry.get("url", ""),
                "title": entry.get("title", "Untitled"),
                "duration": entry.get("duration"),
                "duration_str": _format_duration(entry.get("duration")),
                "views": entry.get("view_count"),
                "views_str": _format_views(entry.get("view_count")),
                "thumbnail": entry.get("thumbnails", [{}])[-1].get("url", "") if entry.get("thumbnails") else "",
                "upload_date": entry.get("upload_date", ""),
            })

        return {
            "channel_name": channel_name,
            "videos": videos,
            "count": len(videos),
            "error": "",
        }

    except Exception as e:
        return {
            "channel_name": "",
            "videos": [],
            "count": 0,
            "error": f"Channel extraction failed: {str(e)}",
        }


# ── Chunking ──────────────────────────────────────────────


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Split text into chunks of approximately chunk_size characters with overlap.

    Strategy:
    1. Split on double newlines (paragraphs) first.
    2. If a paragraph is too long, split on single newlines.
    3. If still too long, split on sentences.
    4. Combine small paragraphs into chunks up to chunk_size.
    """
    if not text or not text.strip():
        return []

    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph would exceed chunk_size, save current and start new
        if current_chunk and len(current_chunk) + len(para) + 2 > chunk_size:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap from end of previous
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        elif not current_chunk:
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para

        # If a single paragraph exceeds chunk_size, split it
        while len(current_chunk) > chunk_size * 1.5:
            split_point = _find_split_point(current_chunk, chunk_size)
            chunks.append(current_chunk[:split_point].strip())
            remainder = current_chunk[split_point:].strip()
            if overlap > 0 and split_point > overlap:
                current_chunk = current_chunk[split_point - overlap:split_point].strip() + " " + remainder
            else:
                current_chunk = remainder

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _find_split_point(text: str, target: int) -> int:
    """Find the best split point near target length.

    Prefers: sentence boundary > newline > word boundary > hard cut.
    """
    if len(text) <= target:
        return len(text)

    # Look for sentence boundary near target
    for delim in [". ", ".\n", "! ", "? ", ";\n", "\n"]:
        idx = text.rfind(delim, target // 2, min(target + 200, len(text)))
        if idx > 0:
            return idx + len(delim)

    # Look for word boundary
    idx = text.rfind(" ", target // 2, min(target + 200, len(text)))
    if idx > 0:
        return idx + 1

    # Hard cut
    return target
