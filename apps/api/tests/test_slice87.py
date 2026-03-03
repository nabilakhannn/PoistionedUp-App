"""Slice 87 — Starter Kit Export + Voice Note Input.

Tests cover:
- Telegram audio download (success, HTTP errors, missing token)
- Voice transcription (delegates to Whisper, error pass-through)
- Full pipeline (download → transcribe)
- Voice API endpoint (auth, success, token-from-env security)
- Security (token never in request/response, file_path validation)
- Starter kit file existence
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ────────────────────────────────────────────────


def _mock_telegram_getfile_response(file_path: str = "voice/file_001.oga"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"ok": True, "result": {"file_path": file_path}}
    return resp


def _mock_telegram_download_response(content: bytes = b"FAKE_AUDIO_DATA"):
    resp = MagicMock()
    resp.status_code = 200
    resp.content = content
    return resp


# ── TestTelegramAudioDownload ──────────────────────────────


class TestTelegramAudioDownload:
    """Tests for voice_notes.download_telegram_audio()."""

    @pytest.mark.asyncio
    async def test_download_success(self):
        """Happy path: getFile returns path, download returns bytes."""
        from app.services.voice_notes import download_telegram_audio

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=[
                _mock_telegram_getfile_response("voice/file_abc.oga"),
                _mock_telegram_download_response(b"AUDIO_BYTES"),
            ]
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.voice_notes.httpx.AsyncClient", return_value=mock_client):
            audio_bytes, filename = await download_telegram_audio(
                file_id="FAKE_FILE_ID", bot_token="FAKE_TOKEN"
            )

        assert audio_bytes == b"AUDIO_BYTES"
        assert filename == "file_abc.oga"

    @pytest.mark.asyncio
    async def test_getfile_http_error_raises(self):
        """Non-200 from getFile raises RuntimeError."""
        from app.services.voice_notes import download_telegram_audio

        mock_resp = MagicMock()
        mock_resp.status_code = 400

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.voice_notes.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="Telegram getFile failed"):
                await download_telegram_audio(
                    file_id="FAKE_FILE_ID", bot_token="FAKE_TOKEN"
                )

    @pytest.mark.asyncio
    async def test_missing_bot_token_raises(self):
        """Empty bot_token raises RuntimeError before any HTTP call."""
        from app.services.voice_notes import download_telegram_audio

        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN not configured"):
            await download_telegram_audio(file_id="FAKE_FILE_ID", bot_token="")


# ── TestTranscribeVoice ────────────────────────────────────


class TestTranscribeVoice:
    """Tests for voice_notes.transcribe_voice()."""

    def test_delegates_to_ingestion(self):
        """transcribe_voice calls transcribe_audio_bytes with correct args."""
        from app.services.voice_notes import transcribe_voice

        mock_result = {"text": "Hello world", "language": "en", "error": "", "method": "whisper"}

        # Patch at the source module since it's imported locally
        with patch(
            "app.services.ingestion.transcribe_audio_bytes",
            return_value=mock_result,
        ) as mock_fn:
            result = transcribe_voice(b"AUDIO_BYTES", "voice.oga")

        mock_fn.assert_called_once_with(b"AUDIO_BYTES", "voice.oga")
        assert result["text"] == "Hello world"

    def test_error_pass_through(self):
        """Errors from Whisper are passed through unchanged."""
        from app.services.voice_notes import transcribe_voice

        mock_result = {
            "text": "", "language": "", "error": "Audio transcription failed: timeout", "method": "whisper"
        }

        with patch(
            "app.services.ingestion.transcribe_audio_bytes",
            return_value=mock_result,
        ):
            result = transcribe_voice(b"AUDIO_BYTES", "voice.oga")

        assert result["error"] == "Audio transcription failed: timeout"
        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_transcript_stripped(self):
        """Whitespace is stripped from transcript in process_telegram_voice."""
        from app.services.voice_notes import process_telegram_voice

        mock_whisper = {"text": "  Hello from voice note  ", "language": "en", "error": "", "method": "whisper"}

        with patch(
            "app.services.voice_notes.download_telegram_audio",
            new=AsyncMock(return_value=(b"AUDIO", "voice.oga")),
        ):
            with patch(
                "app.services.ingestion.transcribe_audio_bytes",
                return_value=mock_whisper,
            ):
                result = await process_telegram_voice("FID", "TOKEN")

        assert result["transcript"] == "Hello from voice note"
        assert result["char_count"] == len("Hello from voice note")


# ── TestVoiceService ───────────────────────────────────────


class TestVoiceService:
    """Tests for process_telegram_voice full pipeline."""

    @pytest.mark.asyncio
    async def test_download_error_returns_error_dict(self):
        """If Telegram download fails, returns error dict with empty transcript."""
        from app.services.voice_notes import process_telegram_voice

        with patch(
            "app.services.voice_notes.download_telegram_audio",
            new=AsyncMock(side_effect=RuntimeError("Telegram getFile failed: HTTP 400")),
        ):
            result = await process_telegram_voice("BAD_FID", "TOKEN", duration_seconds=10)

        assert result["transcript"] == ""
        assert "Telegram getFile failed" in result["error"]
        assert result["duration_seconds"] == 10

    @pytest.mark.asyncio
    async def test_transcription_error_returns_error_dict(self):
        """If Whisper fails, returns error dict."""
        from app.services.voice_notes import process_telegram_voice

        mock_fail = {"text": "", "language": "", "error": "API key missing", "method": "whisper"}

        with patch(
            "app.services.voice_notes.download_telegram_audio",
            new=AsyncMock(return_value=(b"AUDIO", "voice.oga")),
        ):
            with patch(
                "app.services.ingestion.transcribe_audio_bytes",
                return_value=mock_fail,
            ):
                result = await process_telegram_voice("FID", "TOKEN")

        assert result["transcript"] == ""
        assert result["error"] == "API key missing"


# ── TestVoiceEndpointSecurity ──────────────────────────────


class TestVoiceEndpointSecurity:
    """Security tests: token handling, file_path validation."""

    def test_bot_token_never_accepted_from_request(self):
        """Endpoint code must NOT read bot_token from the request body."""
        import inspect
        from app.routers import agent_bridge

        source = inspect.getsource(agent_bridge.transcribe_voice_note)
        assert 'body.get("bot_token"' not in source, (
            "Endpoint must NOT read bot_token from request body — server env only"
        )
        assert "body.get('bot_token'" not in source, (
            "Endpoint must NOT read bot_token from request body — server env only"
        )

    def test_file_path_validation_blocks_traversal(self):
        """_validate_file_path rejects path traversal and unusual extensions."""
        from app.services.voice_notes import _validate_file_path

        with pytest.raises(ValueError):
            _validate_file_path("../../etc/passwd")

        with pytest.raises(ValueError):
            _validate_file_path("voice/file.exe")

        with pytest.raises(ValueError):
            _validate_file_path("voice/file.oga; rm -rf /")

    def test_file_path_validation_allows_valid_telegram_paths(self):
        """Valid Telegram file_path patterns are accepted."""
        from app.services.voice_notes import _validate_file_path

        assert _validate_file_path("voice/file_001.oga") == "voice/file_001.oga"
        assert _validate_file_path("voice/AwACAgI123.ogg") == "voice/AwACAgI123.ogg"

    def test_telegram_api_base_is_hardcoded(self):
        """TELEGRAM_API_BASE must point to official Telegram domain only."""
        from app.services.voice_notes import TELEGRAM_API_BASE

        assert TELEGRAM_API_BASE == "https://api.telegram.org"
        assert not TELEGRAM_API_BASE.startswith("http://"), "Must use HTTPS"


# ── TestStarterKitFiles ────────────────────────────────────


class TestStarterKitFiles:
    """Verify all starter kit files were created."""

    # From apps/api/tests/ go up 3 levels to project root, then into starter-kit/
    STARTER_KIT_ROOT = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../../starter-kit")
    )

    def _path(self, *parts) -> str:
        return os.path.join(self.STARTER_KIT_ROOT, *parts)

    def test_readme_exists(self):
        assert os.path.isfile(self._path("README.md")), \
            f"Missing: {self._path('README.md')}"

    def test_user_md_exists_and_has_required_sections(self):
        path = self._path("user.md")
        assert os.path.isfile(path), f"Missing: {path}"
        content = open(path).read()
        for section in ["Identity", "Goals", "Brand Voice", "Communication Preferences", "Platforms"]:
            assert section in content, f"user.md missing section: {section}"

    def test_soul_md_exists(self):
        assert os.path.isfile(self._path("SOUL.md")), \
            f"Missing: {self._path('SOUL.md')}"

    def test_heartbeat_md_exists(self):
        assert os.path.isfile(self._path("HEARTBEAT.md")), \
            f"Missing: {self._path('HEARTBEAT.md')}"

    def test_openclaw_template_exists(self):
        assert os.path.isfile(self._path("openclaw-template.json")), \
            f"Missing: {self._path('openclaw-template.json')}"

    def test_architecture_md_exists(self):
        assert os.path.isfile(self._path("architecture.md")), \
            f"Missing: {self._path('architecture.md')}"

    def test_all_five_agent_soul_files_exist(self):
        for agent in ["orchestrator", "researcher", "writer", "qa-reviewer", "publisher"]:
            path = self._path("agents", agent, "SOUL.md")
            assert os.path.isfile(path), f"Missing: starter-kit/agents/{agent}/SOUL.md"

    def test_openclaw_template_is_valid_json(self):
        import json
        path = self._path("openclaw-template.json")
        with open(path) as f:
            data = json.load(f)
        assert "agents" in data
        assert "channels" in data
        assert "cron" in data
        assert len(data["agents"]["list"]) == 5

    def test_jumbo_soul_has_voice_note_section(self):
        """Production Jumbo SOUL.md must have the new voice note section."""
        jumbo_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "../../../agents/jumbo/SOUL.md")
        )
        content = open(jumbo_path).read()
        assert "VOICE NOTE HANDLING" in content, "Missing: ## VOICE NOTE HANDLING section"
        assert "STARTUP BEHAVIOR" in content, "Missing: ## STARTUP BEHAVIOR section"
        assert "user.md" in content, "Missing: user.md reference"
