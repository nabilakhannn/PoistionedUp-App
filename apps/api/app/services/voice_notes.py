"""Voice notes service — Slice 87.

Download and transcribe Telegram voice messages using Whisper.
Called by Jumbo via POST /agent-api/voice/transcribe when a voice
note arrives on Telegram.

Security:
- Bot token comes from settings (env var), never from the request
- Only api.telegram.org is allowed as the download domain
- File path is validated before constructing the download URL
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

import httpx

logger = logging.getLogger("app.services.voice_notes")

# Only allow file paths that Telegram returns — no path traversal
_SAFE_FILE_PATH_RE = re.compile(r"^[a-zA-Z0-9/_\-]+\.(?:oga|ogg|mp3|wav|m4a|flac|webm)$")

TELEGRAM_API_BASE = "https://api.telegram.org"


def _validate_file_path(file_path: str) -> str:
    """Validate Telegram file_path before using it in a download URL.

    Raises ValueError if the path looks suspicious (path traversal, unusual chars).
    Returns the validated file_path.
    """
    if not _SAFE_FILE_PATH_RE.match(file_path):
        raise ValueError(f"Telegram returned unexpected file_path format: {file_path!r}")
    return file_path


async def download_telegram_audio(file_id: str, bot_token: str) -> Tuple[bytes, str]:
    """Download a Telegram voice note by file_id.

    Two-step process:
    1. GET /bot{token}/getFile?file_id={id}  → get file_path
    2. GET /file/bot{token}/{file_path}       → download bytes

    Returns (audio_bytes, filename).
    Raises RuntimeError on Telegram API errors.
    """
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    async with httpx.AsyncClient(base_url=TELEGRAM_API_BASE, timeout=30.0) as client:
        # Step 1: resolve file_id → file_path
        get_file_resp = await client.get(
            f"/bot{bot_token}/getFile",
            params={"file_id": file_id},
        )
        if get_file_resp.status_code != 200:
            raise RuntimeError(
                f"Telegram getFile failed: HTTP {get_file_resp.status_code}"
            )
        data = get_file_resp.json()
        if not data.get("ok"):
            desc = data.get("description", "unknown error")
            raise RuntimeError(f"Telegram getFile error: {desc}")

        raw_path: str = data["result"]["file_path"]
        file_path = _validate_file_path(raw_path)

        # Derive a clean filename from the path
        filename = file_path.rsplit("/", 1)[-1]

        # Step 2: download audio bytes
        download_resp = await client.get(f"/file/bot{bot_token}/{file_path}")
        if download_resp.status_code != 200:
            raise RuntimeError(
                f"Telegram file download failed: HTTP {download_resp.status_code}"
            )

        audio_bytes = download_resp.content
        if not audio_bytes:
            raise RuntimeError("Telegram returned empty audio file")

        logger.info(
            "Downloaded Telegram audio file_id=%s path=%s size=%d",
            file_id,
            file_path,
            len(audio_bytes),
        )
        return audio_bytes, filename


def transcribe_voice(audio_bytes: bytes, filename: str) -> dict:
    """Transcribe audio bytes using the existing Whisper integration.

    Delegates to ingestion.transcribe_audio_bytes() which handles:
    - 25MB size limit
    - Temp file creation + cleanup
    - Whisper API call
    - Error wrapping

    Returns dict: {text, language, error, method}
    """
    from app.services.ingestion import transcribe_audio_bytes

    return transcribe_audio_bytes(audio_bytes, filename)


async def process_telegram_voice(
    file_id: str,
    bot_token: str,
    duration_seconds: Optional[int] = None,
) -> dict:
    """Full pipeline: download from Telegram → transcribe with Whisper.

    Returns:
        {
            "transcript": str,
            "language": str,
            "char_count": int,
            "duration_seconds": Optional[int],
            "error": str  # empty on success
        }
    """
    try:
        audio_bytes, filename = await download_telegram_audio(file_id, bot_token)
    except RuntimeError as e:
        logger.warning("Telegram download failed for file_id=%s: %s", file_id, e)
        return {
            "transcript": "",
            "language": "",
            "char_count": 0,
            "duration_seconds": duration_seconds,
            "error": str(e),
        }

    result = transcribe_voice(audio_bytes, filename)

    if result.get("error"):
        logger.warning("Whisper failed for file_id=%s: %s", file_id, result["error"])
        return {
            "transcript": "",
            "language": "",
            "char_count": 0,
            "duration_seconds": duration_seconds,
            "error": result["error"],
        }

    transcript = result.get("text", "").strip()
    language = result.get("language", "en")

    return {
        "transcript": transcript,
        "language": language,
        "char_count": len(transcript),
        "duration_seconds": duration_seconds,
        "error": "",
    }
