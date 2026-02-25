"""Monitoring daemon for continuous OpenClaw agent analytics.

Runs as a long-lived process alongside the OpenClaw gateway.
Watches task_board.md and agent activity files for changes,
emits PostHog events, and optionally runs periodic health checks.

Usage:
    python -m analytics daemon
    python -m analytics daemon --poll-interval 10
    python -m analytics daemon --watch-dirs drafts/ research/ assets/

Architecture:
    The daemon composes FileWatcher and TaskBoardWatcher instances
    and runs them in the main thread. It handles SIGINT/SIGTERM
    for clean shutdown with event queue flushing.
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import List, Optional

from analytics.config import AnalyticsConfig
from analytics.tracker import AgentTracker
from analytics.watchers.file_watcher import FileWatcher, TaskBoardWatcher
from analytics.parsers.task_board import BoardDiff, BoardState

logger = logging.getLogger(__name__)


class AnalyticsDaemon:
    """Long-running daemon that monitors OpenClaw agent activity.

    Combines multiple watchers:
    1. TaskBoardWatcher: Monitors task_board.md for state changes
    2. FileWatcher: Monitors drafts/, research/, assets/ for new files

    Emits PostHog events for all detected changes.

    Example:
        daemon = AnalyticsDaemon(config)
        daemon.start()  # Blocks until interrupted
    """

    def __init__(
        self,
        config: AnalyticsConfig,
        poll_interval: float = 5.0,
        extra_watch_dirs: Optional[List[str]] = None,
    ) -> None:
        """Initialize the daemon.

        Args:
            config: Analytics configuration.
            poll_interval: File polling interval in seconds.
            extra_watch_dirs: Additional directories to monitor.
        """
        self._config = config
        self._poll_interval = poll_interval
        self._extra_dirs = extra_watch_dirs or []
        self._running = False

        # Components (created on start)
        self._tracker: Optional[AgentTracker] = None
        self._board_watcher: Optional[TaskBoardWatcher] = None
        self._file_watchers: List[FileWatcher] = []

    def start(self) -> None:
        """Start all watchers and block until interrupted.

        Handles SIGINT and SIGTERM for clean shutdown.
        """
        self._running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Initialize tracker
        self._tracker = AgentTracker.create(self._config)
        self._tracker.system_startup(version="1.0.0")

        logger.info(
            "Analytics daemon starting (poll=%.1fs, posthog=%s)",
            self._poll_interval,
            "enabled" if self._tracker.is_enabled else "disabled",
        )

        # Start task board watcher
        task_board_path = str(self._config.task_board_path)
        if Path(task_board_path).exists():
            self._board_watcher = TaskBoardWatcher(
                task_board_path=task_board_path,
                tracker=self._tracker,
                poll_interval=self._poll_interval,
                on_diff=self._on_board_diff,
            )
            self._board_watcher.start()
            logger.info("Watching task_board.md: %s", task_board_path)
        else:
            logger.warning(
                "task_board.md not found at %s, skipping board watcher",
                task_board_path,
            )

        # Start extra directory watchers
        for dir_path in self._extra_dirs:
            full_path = self._config.project_root / dir_path
            if full_path.is_dir():
                watcher = FileWatcher(interval_sec=self._poll_interval)
                # Watch for any file changes in the directory
                for file_path in full_path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        watcher.watch(
                            str(file_path),
                            self._on_file_change,
                        )
                watcher.start()
                self._file_watchers.append(watcher)
                logger.info("Watching directory: %s", full_path)

        # Main loop
        logger.info("Daemon running. Press Ctrl+C to stop.")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        self._shutdown()

    def stop(self) -> None:
        """Signal the daemon to stop."""
        self._running = False

    def _shutdown(self) -> None:
        """Clean shutdown: stop watchers, flush events."""
        logger.info("Daemon shutting down...")

        if self._board_watcher:
            self._board_watcher.stop()

        for watcher in self._file_watchers:
            watcher.stop()

        if self._tracker:
            self._tracker.system_shutdown()

        logger.info("Daemon stopped")

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle SIGINT/SIGTERM for clean shutdown."""
        logger.info("Signal %d received, stopping...", signum)
        self._running = False

    def _on_board_diff(self, diff: BoardDiff, state: BoardState) -> None:
        """Callback when task board changes are detected.

        This is called in addition to the automatic event emission
        by TaskBoardWatcher. Use it for custom logic like alerting.
        """
        if diff.new_tasks:
            for task in diff.new_tasks:
                logger.info(
                    "NEW TASK: %s - %s [%s] -> %s",
                    task.task_id,
                    task.title,
                    task.priority,
                    task.assignee or "unassigned",
                )

        if diff.moved_tasks:
            for task_id, old_section, new_section in diff.moved_tasks:
                logger.info(
                    "TASK MOVED: %s | %s -> %s",
                    task_id,
                    old_section,
                    new_section,
                )

    def _on_file_change(self, file_path: str, change_type: str) -> None:
        """Callback when a watched file changes."""
        path = Path(file_path)
        relative = path.relative_to(self._config.project_root)

        logger.info("File changed: %s (%s)", relative, change_type)

        # Detect content type from directory
        if self._tracker:
            parts = relative.parts
            if len(parts) > 0:
                directory = parts[0].lower()
                if directory == "drafts":
                    self._tracker.content_drafted(
                        agent_id="file_watcher",
                        content_type=_guess_content_type(path.name),
                        platform="",
                        file_path=str(relative),
                    )
                elif directory == "research":
                    self._tracker.research_completed(
                        agent_id="file_watcher",
                        source="file",
                        findings_file=str(relative),
                    )


def _guess_content_type(filename: str) -> str:
    """Guess content type from filename pattern."""
    lower = filename.lower()
    if "carousel" in lower:
        return "carousel"
    elif "caption" in lower:
        return "caption"
    elif "script" in lower:
        return "script"
    elif "thread" in lower:
        return "thread"
    elif "trend" in lower or "research" in lower:
        return "research"
    elif "report" in lower:
        return "report"
    return "unknown"


def build_daemon_parser() -> argparse.ArgumentParser:
    """Build argument parser for daemon mode."""
    parser = argparse.ArgumentParser(
        prog="analytics daemon",
        description="OpenClaw Analytics Monitoring Daemon",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root directory (default: cwd)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="File polling interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--watch-dirs",
        nargs="*",
        default=["drafts", "research", "assets"],
        help="Extra directories to monitor (default: drafts research assets)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Daemon entry point."""
    parser = build_daemon_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = AnalyticsConfig.from_env(project_root=args.project_root)

    if not config.validate():
        logger.error("Invalid configuration, exiting")
        sys.exit(1)

    daemon = AnalyticsDaemon(
        config=config,
        poll_interval=args.poll_interval,
        extra_watch_dirs=args.watch_dirs,
    )
    daemon.start()


if __name__ == "__main__":
    main()
