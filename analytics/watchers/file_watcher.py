"""File system monitoring for OpenClaw agent activity tracking.

Single Responsibility: Watches file system changes and emits callbacks.
Open/Closed: New file watchers can be created by subclassing FileWatcher
or composing with TaskBoardWatcher.

Uses watchdog library for cross-platform file system events.
Falls back to polling if watchdog is not available.
"""

import logging
import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

from analytics.parsers.task_board import TaskBoardParser, BoardState, BoardDiff
from analytics.tracker import AgentTracker

logger = logging.getLogger(__name__)

# Type alias for change callbacks
ChangeCallback = Callable[[str, str], None]  # (file_path, change_type)
DiffCallback = Callable[[BoardDiff, BoardState], None]  # (diff, new_state)


class FileWatcher:
    """Watch files for changes using polling (no external dependency).

    This is the fallback watcher that works everywhere. It polls
    specified files at a configurable interval and calls back
    when content changes.

    For production, install watchdog for event-driven file watching.

    Example:
        watcher = FileWatcher(interval_sec=5)
        watcher.watch("/path/to/task_board.md", on_change)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, interval_sec: float = 5.0) -> None:
        """Initialize the polling watcher.

        Args:
            interval_sec: How often to check files for changes (seconds).
        """
        self._interval = interval_sec
        self._watched: Dict[str, float] = {}  # path -> last_mtime
        self._callbacks: Dict[str, List[ChangeCallback]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def watch(self, file_path: str, callback: ChangeCallback) -> None:
        """Register a file to watch with a change callback.

        Args:
            file_path: Absolute path to watch.
            callback: Function called with (file_path, "modified") on change.
        """
        path = str(Path(file_path).resolve())
        if path not in self._callbacks:
            self._callbacks[path] = []
            self._watched[path] = self._get_mtime(path)
        self._callbacks[path].append(callback)
        logger.info("Watching: %s (poll interval: %.1fs)", path, self._interval)

    def start(self) -> None:
        """Start the polling loop in a background thread."""
        if self._running:
            logger.warning("Watcher already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="analytics-file-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info("File watcher started (%d files)", len(self._watched))

    def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval + 1)
        logger.info("File watcher stopped")

    def _poll_loop(self) -> None:
        """Internal polling loop, runs in background thread."""
        while self._running:
            for path in list(self._watched.keys()):
                try:
                    current_mtime = self._get_mtime(path)
                    if current_mtime > self._watched[path]:
                        self._watched[path] = current_mtime
                        self._notify(path, "modified")
                except Exception as exc:
                    logger.error("Error checking %s: %s", path, exc)

            time.sleep(self._interval)

    def _notify(self, file_path: str, change_type: str) -> None:
        """Invoke all callbacks for a changed file."""
        callbacks = self._callbacks.get(file_path, [])
        for cb in callbacks:
            try:
                cb(file_path, change_type)
            except Exception as exc:
                logger.error(
                    "Callback error for %s: %s", file_path, exc
                )

    @staticmethod
    def _get_mtime(path: str) -> float:
        """Get file modification time, returning 0 if file missing."""
        try:
            return Path(path).stat().st_mtime
        except FileNotFoundError:
            return 0.0


class TaskBoardWatcher:
    """Specialized watcher for task_board.md with diff detection.

    Combines FileWatcher + TaskBoardParser to detect task state
    changes and emit analytics events automatically.

    Example:
        tracker = AgentTracker.create()
        watcher = TaskBoardWatcher(
            task_board_path="/path/to/task_board.md",
            tracker=tracker,
        )
        watcher.start()
        # Automatically tracks task state changes via PostHog
    """

    def __init__(
        self,
        task_board_path: str,
        tracker: AgentTracker,
        poll_interval: float = 5.0,
        on_diff: Optional[DiffCallback] = None,
    ) -> None:
        """Initialize the task board watcher.

        Args:
            task_board_path: Path to task_board.md.
            tracker: AgentTracker for sending events.
            poll_interval: Polling interval in seconds.
            on_diff: Optional extra callback for diffs.
        """
        self._path = str(Path(task_board_path).resolve())
        self._tracker = tracker
        self._parser = TaskBoardParser()
        self._watcher = FileWatcher(interval_sec=poll_interval)
        self._last_state: Optional[BoardState] = None
        self._on_diff = on_diff

        # Register ourselves as the callback
        self._watcher.watch(self._path, self._on_file_change)

    def start(self) -> None:
        """Start watching task_board.md for changes."""
        # Take initial snapshot
        try:
            self._last_state = self._parser.parse(self._path)
            logger.info(
                "Initial board state: %d tasks %s",
                self._last_state.total_tasks,
                self._last_state.counts,
            )
        except FileNotFoundError:
            logger.warning("task_board.md not found, will watch for creation")
            self._last_state = BoardState()

        self._watcher.start()

    def stop(self) -> None:
        """Stop watching."""
        self._watcher.stop()

    def _on_file_change(self, file_path: str, change_type: str) -> None:
        """Handle task_board.md modification."""
        try:
            new_state = self._parser.parse(file_path)
        except Exception as exc:
            logger.error("Failed to parse task_board.md: %s", exc)
            self._tracker.system_error(
                error=str(exc),
                component="task_board_watcher",
            )
            return

        if self._last_state is None:
            self._last_state = new_state
            return

        diff = self._parser.diff(self._last_state, new_state)

        if diff.has_changes:
            logger.info("Board changes: %s", diff.summary)
            self._emit_diff_events(diff, new_state)

            if self._on_diff:
                try:
                    self._on_diff(diff, new_state)
                except Exception as exc:
                    logger.error("Diff callback error: %s", exc)

        self._last_state = new_state

    def _emit_diff_events(
        self,
        diff: BoardDiff,
        state: BoardState,
    ) -> None:
        """Convert board diff into PostHog tracking events."""

        # New tasks added
        for task in diff.new_tasks:
            self._tracker.task_created(
                agent_id=task.assignee or "unknown",
                task_id=task.task_id,
                title=task.title,
                priority=task.priority,
                tags=task.tags,
                assignee=task.assignee,
            )

        # Tasks removed (unusual, but track it)
        for task in diff.removed_tasks:
            self._tracker.system_error(
                error=f"Task {task.task_id} removed from board",
                component="task_board",
            )

        # Tasks moved between sections
        for task_id, old_section, new_section in diff.moved_tasks:
            task = state.tasks.get(task_id)
            agent_id = task.assignee if task else "unknown"

            # Map section transitions to events
            if new_section == "in_progress":
                self._tracker.task_claimed(
                    agent_id=agent_id,
                    task_id=task_id,
                    title=task.title if task else "",
                )
            elif new_section == "review":
                self._tracker.task_completed(
                    agent_id=agent_id,
                    task_id=task_id,
                    title=task.title if task else "",
                )
            elif new_section == "ready":
                self._tracker.task_approved(task_id=task_id)
            elif new_section == "archive":
                # Derive platform from tags if available
                platform = ""
                if task and task.tags:
                    for tag in task.tags:
                        if tag in ("facebook", "instagram", "youtube", "tiktok"):
                            platform = tag
                            break
                self._tracker.task_published(
                    agent_id=agent_id,
                    task_id=task_id,
                    platform=platform,
                )

        # Track board state as heartbeat context
        counts = state.counts
        self._tracker.heartbeat_pulse(
            agent_id="task_board_watcher",
            backlog=counts.get("backlog", 0),
            in_progress=counts.get("in_progress", 0),
            review=counts.get("review", 0),
            ready=counts.get("ready", 0),
            archived=counts.get("archive", 0),
            rule_triggered="board_change_detected",
            actions_taken=len(diff.new_tasks) + len(diff.moved_tasks),
        )

        self._tracker.flush()
