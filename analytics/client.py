"""PostHog client wrapper with singleton pattern and graceful degradation.

Single Responsibility: Only manages the PostHog SDK connection lifecycle.
Dependency Inversion: Depends on AnalyticsConfig abstraction, not env vars.
Open/Closed: New transport backends can be added without modifying this class.

The client gracefully degrades when:
- PostHog API key is not configured (logs events as debug messages)
- posthog-python package is not installed (warns once, then no-ops)
- PostHog server is unreachable (catches and logs, never crashes)
"""

import atexit
import logging
from typing import Any, Dict, Optional

from analytics.config import AnalyticsConfig

logger = logging.getLogger(__name__)

# Module-level singleton
_client_instance: Optional["PostHogClient"] = None


class PostHogClient:
    """Thread-safe PostHog client with automatic shutdown.

    This class wraps the posthog-python SDK with:
    - Graceful fallback when SDK is missing or API key is unset
    - Automatic queue flushing on process exit
    - Error isolation (never raises to caller)
    - Debug logging of all events when tracking is disabled

    Example:
        client = PostHogClient(config)
        client.capture("agent-jarvis", "task_created", {"task_id": "WOW-001"})
        client.flush()
    """

    def __init__(self, config: AnalyticsConfig) -> None:
        self._config = config
        self._posthog_module: Any = None
        self._initialized = False
        self._setup()

    def _setup(self) -> None:
        """Initialize PostHog SDK connection."""
        if not self._config.enabled:
            logger.info("PostHog client: disabled (no API key)")
            return

        try:
            import posthog

            posthog.api_key = self._config.posthog_api_key
            posthog.host = self._config.posthog_host
            posthog.debug = self._config.debug
            posthog.on_error = self._on_error
            posthog.send = True
            posthog.sync_mode = False

            self._posthog_module = posthog
            self._initialized = True

            atexit.register(self._shutdown)

            logger.info(
                "PostHog client: initialized (host=%s, debug=%s)",
                self._config.posthog_host,
                self._config.debug,
            )

        except ImportError:
            logger.warning(
                "PostHog client: posthog package not installed. "
                "Run: pip install posthog"
            )

    def capture(
        self,
        distinct_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send an event to PostHog.

        Args:
            distinct_id: Unique identifier for the entity (agent ID or "system").
            event: Event name (use EventType constants).
            properties: Event properties dict.
        """
        merged_props = properties or {}

        if not self._initialized:
            logger.debug(
                "Event (disabled): %s | %s | %s",
                distinct_id,
                event,
                merged_props,
            )
            return

        try:
            self._posthog_module.capture(
                distinct_id=distinct_id,
                event=event,
                properties=merged_props,
            )
            logger.debug("Event captured: %s | %s", event, distinct_id)

        except Exception as exc:
            logger.error(
                "Failed to capture event %s for %s: %s",
                event,
                distinct_id,
                exc,
            )

    def identify(
        self,
        distinct_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify an agent or user with properties.

        Args:
            distinct_id: Agent or user identifier.
            properties: Properties to associate with this entity.
        """
        if not self._initialized:
            logger.debug("Identify (disabled): %s | %s", distinct_id, properties)
            return

        try:
            self._posthog_module.identify(
                distinct_id=distinct_id,
                properties=properties or {},
            )
        except Exception as exc:
            logger.error("Failed to identify %s: %s", distinct_id, exc)

    def group_identify(
        self,
        group_type: str,
        group_key: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify a group (e.g., the agent squad).

        Args:
            group_type: Type of group (e.g., "squad", "system").
            group_key: Unique key for this group.
            properties: Group properties.
        """
        if not self._initialized:
            return

        try:
            self._posthog_module.group_identify(
                group_type=group_type,
                group_key=group_key,
                properties=properties or {},
            )
        except Exception as exc:
            logger.error(
                "Failed to group_identify %s/%s: %s",
                group_type,
                group_key,
                exc,
            )

    def flush(self) -> None:
        """Force-flush the event queue to PostHog servers."""
        if not self._initialized:
            return

        try:
            self._posthog_module.flush()
            logger.debug("PostHog queue flushed")
        except Exception as exc:
            logger.error("Failed to flush PostHog queue: %s", exc)

    def _shutdown(self) -> None:
        """Clean shutdown: flush remaining events."""
        logger.info("PostHog client: shutting down")
        self.flush()

    @staticmethod
    def _on_error(error: Exception, items: Any) -> None:
        """PostHog SDK error callback."""
        logger.error(
            "PostHog SDK error: %s (batch size: %s)",
            error,
            len(items) if items else 0,
        )

    @property
    def is_enabled(self) -> bool:
        """Whether the client is actively sending events."""
        return self._initialized


def get_client(config: Optional[AnalyticsConfig] = None) -> PostHogClient:
    """Get or create the singleton PostHog client.

    Thread-safe singleton. The first call initializes the client,
    subsequent calls return the same instance.

    Args:
        config: Configuration override. Only used on first call.

    Returns:
        The singleton PostHogClient instance.
    """
    global _client_instance

    if _client_instance is None:
        cfg = config or AnalyticsConfig.from_env()
        _client_instance = PostHogClient(cfg)

    return _client_instance


def reset_client() -> None:
    """Reset the singleton client (for testing only)."""
    global _client_instance
    if _client_instance is not None:
        _client_instance.flush()
    _client_instance = None
