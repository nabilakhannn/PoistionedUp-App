"""Tests for Slice 69: Gateway Bridge — OpenClaw gateway connection.

Covers:
- Gateway client health check (healthy, unreachable, timeout, not configured)
- Agent listing (from gateway and config fallback)
- Full status aggregation
- Deployment checklist generation
- URL masking for security
- Router endpoint authentication
- Message relay validation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

import pytest


# ── Gateway Client Unit Tests ────────────────────────────────────


class TestGatewayHealthCheck:
    """Test gateway health check logic."""

    @pytest.mark.asyncio
    async def test_health_check_not_configured(self):
        """Health check raises when OPENCLAW_GATEWAY_URL is empty."""
        from app.services.gateway_client import check_health, GatewayError

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = ""
            # _get_base_url raises GatewayError when url is empty
            # check_health catches it and returns error dict
            try:
                result = await check_health()
                assert result["connected"] is False
            except GatewayError:
                # Also acceptable — unconfigured raises
                pass

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        """Health check returns connected=True when gateway responds 200."""
        from app.services.gateway_client import check_health

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "1.2.3"}
        mock_response.headers = {"content-type": "application/json"}

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = "test-token"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await check_health()
            assert result["connected"] is True
            assert result["status"] == "healthy"
            assert result["version"] == "1.2.3"
            assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_health_check_connect_error(self):
        """Health check returns unreachable when connection refused."""
        import httpx
        from app.services.gateway_client import check_health

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await check_health()
            assert result["connected"] is False
            assert result["status"] == "unreachable"

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Health check returns timeout when gateway doesn't respond."""
        import httpx
        from app.services.gateway_client import check_health

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
            mock_client_cls.return_value = mock_client

            result = await check_health()
            assert result["connected"] is False
            assert result["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Health check returns unhealthy when gateway returns non-200."""
        from app.services.gateway_client import check_health

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.headers = {}

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await check_health()
            assert result["connected"] is True
            assert result["status"] == "unhealthy"
            assert result["http_status"] == 503


class TestGatewayAgents:
    """Test agent listing logic."""

    @pytest.mark.asyncio
    async def test_agents_from_gateway(self):
        """Returns agent list from gateway API response."""
        from app.services.gateway_client import list_gateway_agents

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "jumbo", "name": "Jumbo", "status": "active", "default": True},
            {"id": "copywriter", "name": "Copywriter", "status": "idle"},
        ]

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = "test"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            agents = await list_gateway_agents()
            assert len(agents) == 2
            assert agents[0]["id"] == "jumbo"
            assert agents[0]["is_default"] is True
            assert agents[1]["id"] == "copywriter"

    @pytest.mark.asyncio
    async def test_agents_fallback_to_config(self):
        """Falls back to config-based agent list when gateway unreachable."""
        import httpx
        from app.services.gateway_client import list_gateway_agents

        with patch("app.services.gateway_client.settings") as mock_settings, \
             patch("app.services.gateway_client.httpx.AsyncClient") as mock_client_cls:
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = ""

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value = mock_client

            agents = await list_gateway_agents()
            assert len(agents) == 6  # All 6 config agents
            assert agents[0]["id"] == "jumbo"
            assert agents[0]["status"] == "unknown"


class TestDeploymentChecklist:
    """Test the deployment checklist builder."""

    def test_checklist_all_pass(self):
        from app.services.gateway_client import _build_deployment_checklist

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = "token"
            mock_settings.agent_api_key = "key"
            mock_settings.openai_api_key = "sk-test"

            health = {"connected": True, "status": "healthy", "latency_ms": 50}
            agents = [{"id": "jumbo"}]

            checklist = _build_deployment_checklist(health, agents)
            assert all(item["status"] == "pass" for item in checklist)

    def test_checklist_no_config(self):
        from app.services.gateway_client import _build_deployment_checklist

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_gateway_url = ""
            mock_settings.openclaw_gateway_token = ""
            mock_settings.agent_api_key = ""
            mock_settings.openai_api_key = ""

            health = {"connected": False, "status": "not_configured"}
            agents = []

            checklist = _build_deployment_checklist(health, agents)
            fail_count = sum(1 for item in checklist if item["status"] == "fail")
            assert fail_count >= 4  # At least 4 fails (url, token, key, openai)

    def test_checklist_gateway_unreachable(self):
        from app.services.gateway_client import _build_deployment_checklist

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_gateway_url = "http://vps:18789"
            mock_settings.openclaw_gateway_token = "token"
            mock_settings.agent_api_key = "key"
            mock_settings.openai_api_key = "sk-test"

            health = {"connected": False, "status": "unreachable", "error": "Connection refused"}
            agents = []

            checklist = _build_deployment_checklist(health, agents)
            ids = {c["id"]: c["status"] for c in checklist}
            assert ids["gateway_url"] == "pass"
            assert ids["gateway_reachable"] == "fail"


class TestURLMasking:
    """Test that URLs with credentials are safely masked."""

    def test_mask_plain_url(self):
        from app.services.gateway_client import _mask_url

        assert _mask_url("http://localhost:18789") == "http://localhost:18789"

    def test_mask_url_with_credentials(self):
        from app.services.gateway_client import _mask_url

        result = _mask_url("http://user:pass@example.com:18789")
        assert "pass" not in result
        assert "***" in result

    def test_mask_empty_url(self):
        from app.services.gateway_client import _mask_url

        assert _mask_url("") == "(not set)"


class TestAgentSanitization:
    """Test that agent data is sanitized before returning to frontend."""

    def test_sanitize_normal_agent(self):
        from app.services.gateway_client import _sanitize_agent

        raw = {
            "id": "jumbo",
            "name": "Jumbo (Orchestrator)",
            "status": "active",
            "model": {"provider": "openai", "model": "gpt-4o"},
            "workspace": "./agents/jumbo",
            "channels": ["telegram"],
            "default": True,
            "internal_secret": "should-not-leak",
        }
        result = _sanitize_agent(raw)
        assert result["id"] == "jumbo"
        assert result["model"] == "gpt-4o"
        assert result["is_default"] is True
        assert "internal_secret" not in result

    def test_sanitize_non_dict_agent(self):
        from app.services.gateway_client import _sanitize_agent

        result = _sanitize_agent("jumbo")
        assert result == {"id": "jumbo"}


class TestFullStatus:
    """Test the full status aggregation."""

    @pytest.mark.asyncio
    async def test_full_status_not_connected(self):
        """When gateway is not connected, agents and sessions are empty."""
        from app.services.gateway_client import get_full_status

        with patch("app.services.gateway_client.check_health", new_callable=AsyncMock) as mock_health, \
             patch("app.services.gateway_client.settings") as mock_settings:
            mock_health.return_value = {"connected": False, "status": "unreachable"}
            mock_settings.openclaw_mock_mode = False
            mock_settings.openclaw_gateway_url = "http://localhost:18789"
            mock_settings.openclaw_gateway_token = ""
            mock_settings.agent_api_key = ""
            mock_settings.openai_api_key = ""

            result = await get_full_status()
            assert result["health"]["connected"] is False
            assert result["agents"] == []
            assert result["sessions"] == []
            assert "checklist" in result
            assert "config" in result


# ── Router Tests ─────────────────────────────────────────────────


class TestGatewayRouter:
    """Test the gateway router endpoints require auth."""

    def test_health_requires_auth(self):
        """Gateway health endpoint requires JWT auth."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/gateway/health")
        # Should be 401 or 403 (no auth token)
        assert resp.status_code in (401, 403, 422)

    def test_status_requires_auth(self):
        """Gateway status endpoint requires JWT auth."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/gateway/status")
        assert resp.status_code in (401, 403, 422)

    def test_agents_requires_auth(self):
        """Gateway agents endpoint requires JWT auth."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/gateway/agents")
        assert resp.status_code in (401, 403, 422)

    def test_sessions_requires_auth(self):
        """Gateway sessions endpoint requires JWT auth."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/gateway/sessions")
        assert resp.status_code in (401, 403, 422)

    def test_message_requires_auth(self):
        """Gateway message endpoint requires JWT auth."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/gateway/message", json={
            "agent_id": "jumbo",
            "message": "hello",
        })
        assert resp.status_code in (401, 403, 422)


class TestMessageValidation:
    """Test the gateway message request validation."""

    def test_message_model_valid(self):
        from app.routers.gateway import GatewayMessageRequest

        msg = GatewayMessageRequest(agent_id="jumbo", message="hello")
        assert msg.agent_id == "jumbo"
        assert msg.message == "hello"
        assert msg.session_id is None

    def test_message_model_with_session(self):
        from app.routers.gateway import GatewayMessageRequest

        msg = GatewayMessageRequest(
            agent_id="trend-analyzer",
            message="Research AI trends",
            session_id="sess-123",
        )
        assert msg.session_id == "sess-123"

    def test_message_model_rejects_empty_agent(self):
        from app.routers.gateway import GatewayMessageRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GatewayMessageRequest(agent_id="", message="hello")

    def test_message_model_rejects_empty_message(self):
        from app.routers.gateway import GatewayMessageRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GatewayMessageRequest(agent_id="jumbo", message="")

    def test_message_model_rejects_invalid_agent_id(self):
        from app.routers.gateway import GatewayMessageRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GatewayMessageRequest(agent_id="agent with spaces", message="hello")

    def test_message_model_rejects_sql_injection_agent_id(self):
        from app.routers.gateway import GatewayMessageRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GatewayMessageRequest(agent_id="'; DROP TABLE--", message="hello")


class TestMockGateway:
    """Test mock gateway mode for local development."""

    @pytest.mark.asyncio
    async def test_mock_health_returns_connected(self):
        from app.services.gateway_mock import mock_check_health

        result = await mock_check_health()
        assert result["connected"] is True
        assert result["status"] == "healthy"
        assert result["mock_mode"] is True
        assert "latency_ms" in result
        assert result["agents_loaded"] == 6

    @pytest.mark.asyncio
    async def test_mock_agents_returns_six(self):
        from app.services.gateway_mock import mock_list_agents

        agents = await mock_list_agents()
        assert len(agents) == 6
        jumbo = next(a for a in agents if a["id"] == "jumbo")
        assert jumbo["is_default"] is True
        assert jumbo["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_mock_sessions_returns_list(self):
        from app.services.gateway_mock import mock_get_sessions

        sessions = await mock_get_sessions()
        assert len(sessions) >= 1
        assert "id" in sessions[0]
        assert "agent_id" in sessions[0]
        assert "message_count" in sessions[0]

    @pytest.mark.asyncio
    async def test_mock_send_message_returns_response(self):
        from app.services.gateway_mock import mock_send_message

        result = await mock_send_message("jumbo", "Hello")
        assert result["status"] == "delivered"
        assert result["agent_id"] == "jumbo"
        assert result["session_id"] is not None
        assert result["response"] is not None
        assert len(result["response"]) > 10

    @pytest.mark.asyncio
    async def test_mock_send_message_unknown_agent(self):
        from app.services.gateway_mock import mock_send_message

        result = await mock_send_message("unknown-agent", "test")
        assert result["status"] == "delivered"
        assert "demo response" in result["response"].lower() or "mock" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_mock_send_message_preserves_session(self):
        from app.services.gateway_mock import mock_send_message

        result = await mock_send_message("copywriter", "Write a post", session_id="sess-existing")
        assert result["session_id"] == "sess-existing"

    @pytest.mark.asyncio
    async def test_mock_mode_check_health_via_client(self):
        """When mock mode is enabled, gateway_client delegates to mock."""
        from app.services.gateway_client import check_health

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_mock_mode = True
            result = await check_health()
            assert result["connected"] is True
            assert result["mock_mode"] is True

    @pytest.mark.asyncio
    async def test_mock_mode_list_agents_via_client(self):
        """When mock mode is enabled, gateway_client returns mock agents."""
        from app.services.gateway_client import list_gateway_agents

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_mock_mode = True
            agents = await list_gateway_agents()
            assert len(agents) == 6

    @pytest.mark.asyncio
    async def test_mock_mode_send_message_via_client(self):
        """When mock mode is enabled, gateway_client returns mock response."""
        from app.services.gateway_client import send_message_to_agent

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_mock_mode = True
            result = await send_message_to_agent("jumbo", "Hello from test")
            assert result["status"] == "delivered"
            assert result["response"] is not None

    @pytest.mark.asyncio
    async def test_mock_mode_full_status_includes_flag(self):
        """Full status includes mock_mode flag when enabled."""
        from app.services.gateway_client import get_full_status

        with patch("app.services.gateway_client.settings") as mock_settings:
            mock_settings.openclaw_mock_mode = True
            mock_settings.openclaw_gateway_url = ""
            mock_settings.openclaw_gateway_token = ""
            mock_settings.agent_api_key = ""
            mock_settings.openai_api_key = ""
            result = await get_full_status()
            assert result["mock_mode"] is True
            assert result["health"]["connected"] is True
            assert len(result["agents"]) == 6


class TestConfigAgentsFallback:
    """Test the fallback config agent list."""

    def test_config_agents_count(self):
        from app.services.gateway_client import _get_config_agents

        agents = _get_config_agents()
        assert len(agents) == 6

    def test_config_agents_has_jumbo(self):
        from app.services.gateway_client import _get_config_agents

        agents = _get_config_agents()
        jumbo = next(a for a in agents if a["id"] == "jumbo")
        assert jumbo["is_default"] is True
        assert jumbo["model"] == "gpt-4o"
        assert "telegram" in jumbo["channels"]

    def test_config_agents_all_have_required_fields(self):
        from app.services.gateway_client import _get_config_agents

        agents = _get_config_agents()
        for agent in agents:
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent
            assert "model" in agent
            assert "is_default" in agent
            assert "channels" in agent
