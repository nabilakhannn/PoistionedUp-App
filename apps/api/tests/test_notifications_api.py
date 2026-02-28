"""Tests for Slice 73: Notifications API.

Covers:
- NotificationOut / UnreadCount schema validation
- AgentNotifyRequest schema validation
- Notification router endpoint registration
- Notification types and priorities
- Notification status transitions
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


# ── Schema Validation Tests ─────────────────────────────────────

class TestNotificationSchemas:
    """Test Pydantic schemas for notifications."""

    def test_notification_out_valid(self):
        from app.schemas.notifications import NotificationOut

        notif = NotificationOut(
            id="notif-1",
            title="Test Alert",
            body="Something happened",
            notification_type="alert",
            priority="high",
            status="unread",
            created_at=datetime.now(timezone.utc),
        )
        assert notif.title == "Test Alert"
        assert notif.notification_type == "alert"
        assert notif.status == "unread"

    def test_notification_out_all_types_valid(self):
        from app.schemas.notifications import NotificationOut

        for ntype in ("briefing", "reminder", "alert", "suggestion", "insight", "goal_update"):
            notif = NotificationOut(
                id="notif-1",
                title="Test",
                body="Test body",
                notification_type=ntype,
                priority="medium",
                status="unread",
                created_at=datetime.now(timezone.utc),
            )
            assert notif.notification_type == ntype

    def test_notification_out_all_priorities_valid(self):
        from app.schemas.notifications import NotificationOut

        for priority in ("low", "medium", "high", "urgent"):
            notif = NotificationOut(
                id="notif-1",
                title="Test",
                body="Test body",
                notification_type="alert",
                priority=priority,
                status="unread",
                created_at=datetime.now(timezone.utc),
            )
            assert notif.priority == priority

    def test_notification_out_all_statuses_valid(self):
        from app.schemas.notifications import NotificationOut

        for status in ("unread", "read", "dismissed", "actioned"):
            notif = NotificationOut(
                id="notif-1",
                title="Test",
                body="Test body",
                notification_type="alert",
                priority="medium",
                status=status,
                created_at=datetime.now(timezone.utc),
            )
            assert notif.status == status

    def test_notification_out_with_optional_fields(self):
        from app.schemas.notifications import NotificationOut

        notif = NotificationOut(
            id="notif-1",
            title="Test",
            body="Test body",
            notification_type="suggestion",
            priority="medium",
            status="unread",
            from_agent_id="jumbo",
            action_url="/mission-control",
            read_at=None,
            created_at=datetime.now(timezone.utc),
        )
        assert notif.from_agent_id == "jumbo"
        assert notif.action_url == "/mission-control"

    def test_unread_count_schema(self):
        from app.schemas.notifications import UnreadCount

        uc = UnreadCount(count=5, by_priority={"high": 2, "medium": 3})
        assert uc.count == 5
        assert uc.by_priority["high"] == 2

    def test_unread_count_empty(self):
        from app.schemas.notifications import UnreadCount

        uc = UnreadCount(count=0, by_priority={})
        assert uc.count == 0
        assert uc.by_priority == {}

    def test_agent_notify_request_valid(self):
        from app.schemas.notifications import AgentNotifyRequest

        req = AgentNotifyRequest(
            title="Agent Alert",
            body="Something detected",
            notification_type="alert",
            priority="high",
            agent_id="analytics",
        )
        assert req.title == "Agent Alert"
        assert req.agent_id == "analytics"

    def test_agent_notify_request_defaults(self):
        from app.schemas.notifications import AgentNotifyRequest

        req = AgentNotifyRequest(
            title="Test",
            body="Test body",
            agent_id="jumbo",
        )
        assert req.notification_type == "insight"
        assert req.priority == "medium"


# ── Route Registration Tests ────────────────────────────────────

class TestNotificationsRouteRegistration:
    """Test that notification routes are registered."""

    def test_notifications_router_has_prefix(self):
        from app.routers.notifications import router

        assert router.prefix == "/notifications"

    def test_notifications_router_has_tag(self):
        from app.routers.notifications import router

        assert "notifications" in router.tags

    def test_notifications_has_list_endpoint(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications" in routes

    def test_notifications_has_unread_count(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications/unread-count" in routes

    def test_notifications_has_mark_read(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications/{notification_id}/read" in routes

    def test_notifications_has_dismiss(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications/{notification_id}/dismiss" in routes

    def test_notifications_has_read_all(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications/read-all" in routes

    def test_notifications_has_latest_briefing(self):
        from app.routers.notifications import router

        routes = [r.path for r in router.routes]
        assert "/notifications/briefing/latest" in routes


# ── Rate Limit Tier Tests ──────────────────────────────────────

class TestNotificationsRateLimits:
    """Test rate limit tier assignments for notification endpoints."""

    def test_notifications_list_uses_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/notifications", "GET")
        assert tier == TIER_READ

    def test_notifications_unread_uses_read_tier(self):
        from app.middleware.rate_limit import _get_tier, TIER_READ

        tier = _get_tier("/notifications/unread-count", "GET")
        assert tier == TIER_READ


# ── Agent Bridge /notify Tests ──────────────────────────────────

class TestAgentBridgeNotify:
    """Test the agent bridge notify endpoint registration."""

    def test_agent_bridge_has_notify_route(self):
        from app.routers.agent_bridge import router

        routes = [r.path for r in router.routes]
        assert "/agent-api/notify" in routes

    def test_agent_bridge_notify_is_post(self):
        from app.routers.agent_bridge import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/agent-api/notify":
                assert "POST" in route.methods
                break
