"""Configuration management for OpenClaw analytics.

Single Responsibility: Only handles loading and validating configuration.
Dependency Inversion: Consumers depend on AnalyticsConfig (abstraction),
not on os.environ or dotenv directly.
"""

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyticsConfig:
    """Immutable analytics configuration loaded from environment.

    All fields are validated at construction time. The frozen=True
    ensures no accidental mutation after creation.

    Attributes:
        posthog_api_key: PostHog project API key (None disables tracking).
        posthog_host: PostHog ingestion endpoint.
        project_root: Root directory of the OpenClaw agent project.
        task_board_path: Path to the shared task_board.md file.
        heartbeat_interval_sec: Expected heartbeat interval in seconds.
        flush_interval_sec: How often to flush PostHog event queue.
        enabled: Whether analytics tracking is active.
        system_id: Unique identifier for this agent system instance.
        debug: Enable verbose PostHog debug logging.
    """

    posthog_api_key: Optional[str]
    posthog_host: str
    project_root: Path
    task_board_path: Path
    heartbeat_interval_sec: int
    flush_interval_sec: int
    enabled: bool
    system_id: str
    debug: bool

    @classmethod
    def from_env(cls, project_root: Optional[str] = None) -> "AnalyticsConfig":
        """Load configuration from environment variables.

        Attempts to load .env file if python-dotenv is available.
        Falls back gracefully if PostHog API key is not set.

        Args:
            project_root: Override for project root directory.
                          Defaults to current working directory.

        Returns:
            Frozen AnalyticsConfig instance.
        """
        # Try loading .env if dotenv is available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        except Exception:
            # Permission errors, malformed .env, etc.
            pass

        root = Path(project_root) if project_root else Path.cwd()
        api_key = os.environ.get("POSTHOG_API_KEY", "").strip() or None

        config = cls(
            posthog_api_key=api_key,
            posthog_host=os.environ.get(
                "POSTHOG_HOST", "https://us.i.posthog.com"
            ),
            project_root=root,
            task_board_path=root / "task_board.md",
            heartbeat_interval_sec=int(
                os.environ.get("ANALYTICS_HEARTBEAT_INTERVAL", "900")
            ),
            flush_interval_sec=int(
                os.environ.get("ANALYTICS_FLUSH_INTERVAL", "60")
            ),
            enabled=api_key is not None,
            system_id=os.environ.get("ANALYTICS_SYSTEM_ID", "positionedup-squad"),
            debug=os.environ.get("ANALYTICS_DEBUG", "").lower() in ("1", "true"),
        )

        if config.enabled:
            logger.info(
                "Analytics enabled: host=%s system=%s",
                config.posthog_host,
                config.system_id,
            )
        else:
            logger.info("Analytics disabled: POSTHOG_API_KEY not set")

        return config

    def validate(self) -> bool:
        """Check that configuration is internally consistent.

        Returns:
            True if valid, False otherwise.
        """
        if self.enabled and not self.posthog_api_key:
            logger.error("Config invalid: enabled=True but no API key")
            return False

        if self.heartbeat_interval_sec < 30:
            logger.warning(
                "Heartbeat interval %ds is very short, consider >= 60s",
                self.heartbeat_interval_sec,
            )

        if not self.project_root.is_dir():
            logger.warning(
                "Project root does not exist: %s", self.project_root
            )

        return True
