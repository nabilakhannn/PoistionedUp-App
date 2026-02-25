"""Parse task_board.md into structured data and detect state changes.

Single Responsibility: Only handles parsing the task_board.md format
and computing diffs between two snapshots.

This parser understands the task_board.md checklist format:

    ## 1. BACKLOG
    - [ ] **Task Title** [ID:WOW-001] [PRIORITY:P1] [ASSIGNEE:trend-analyzer] ...
      - **Brief**: One-line description
      - **Input**: Source material
      - **Output**: Where to write result
      - **Notes**: Context

    ## 2. IN PROGRESS
    ...

    ## 3. REVIEW / APPROVAL
    ...

    ## 4. READY FOR DISTRIBUTION
    ...

    ## 5. ARCHIVE
    ...
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Section header patterns (handles numbered and unnumbered)
SECTION_PATTERN = re.compile(
    r"^##\s+(?:\d+\.\s+)?"
    r"(BACKLOG|IN\s+PROGRESS|REVIEW\s*/?\s*APPROVAL|"
    r"READY\s+FOR\s+DISTRIBUTION|ARCHIVE)\s*$",
    re.IGNORECASE,
)

# Checklist task line pattern:
# - [ ] **Task Title** [ID:WOW-001] [PRIORITY:P1] [ASSIGNEE:agent] ...
TASK_LINE_PATTERN = re.compile(
    r"^-\s+\[([x ])\]\s+\*\*(.+?)\*\*\s+(.*)",
    re.IGNORECASE,
)

# Bracket tag pattern: [KEY:VALUE]
BRACKET_TAG_PATTERN = re.compile(
    r"\[([A-Z_]+):([^\]]*)\]",
    re.IGNORECASE,
)

# Sub-field pattern (indented): - **Key**: Value
SUB_FIELD_PATTERN = re.compile(
    r"^\s+-\s+\*\*(.+?)(?:\*\*)?:\s*(.+)$",
)


@dataclass
class TaskEntry:
    """A single task parsed from task_board.md.

    Attributes:
        task_id: Unique ID (e.g., "WOW-001").
        title: Human-readable task title.
        section: Board section (backlog, in_progress, review, ready, archive).
        is_done: Whether the checkbox is checked [x].
        priority: Priority level (P0, P1, P2, P3).
        assignee: Agent responsible for this task.
        tags: List of tags.
        created: ISO timestamp when created.
        updated: ISO timestamp when last updated.
        due: ISO timestamp for deadline.
        brief: One-line description.
        input_ref: Source material or upstream task.
        output_ref: Where to write the result.
        notes: Additional context.
        raw_tags: All bracket tags as key-value dict.
    """

    task_id: str
    title: str
    section: str
    is_done: bool = False
    priority: str = ""
    assignee: str = ""
    tags: List[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    due: str = ""
    brief: str = ""
    input_ref: str = ""
    output_ref: str = ""
    notes: str = ""
    raw_tags: Dict[str, str] = field(default_factory=dict)

    @property
    def section_normalized(self) -> str:
        """Normalize section name for consistent comparisons."""
        mapping = {
            "backlog": "backlog",
            "in progress": "in_progress",
            "review / approval": "review",
            "review/approval": "review",
            "ready for distribution": "ready",
            "archive": "archive",
        }
        return mapping.get(self.section.lower().strip(), self.section.lower())


@dataclass
class BoardState:
    """Complete snapshot of the task board.

    Attributes:
        tasks: Dict mapping task_id to TaskEntry.
        timestamp: When this snapshot was taken.
        file_path: Path to the source file.
    """

    tasks: Dict[str, TaskEntry] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    file_path: str = ""

    @property
    def by_section(self) -> Dict[str, List[TaskEntry]]:
        """Group tasks by their board section."""
        groups: Dict[str, List[TaskEntry]] = {}
        for task in self.tasks.values():
            section = task.section_normalized
            if section not in groups:
                groups[section] = []
            groups[section].append(task)
        return groups

    @property
    def counts(self) -> Dict[str, int]:
        """Count tasks per section."""
        return {k: len(v) for k, v in self.by_section.items()}

    @property
    def total_tasks(self) -> int:
        """Total number of tasks on the board."""
        return len(self.tasks)


@dataclass
class BoardDiff:
    """Changes between two board snapshots.

    Attributes:
        new_tasks: Tasks that appeared (not in previous snapshot).
        removed_tasks: Tasks that disappeared.
        moved_tasks: Tasks that changed section (task_id, old_section, new_section).
        field_changes: Tasks with changed metadata (task_id, field, old_val, new_val).
        checkbox_changes: Tasks whose done status changed (task_id, old_done, new_done).
    """

    new_tasks: List[TaskEntry] = field(default_factory=list)
    removed_tasks: List[TaskEntry] = field(default_factory=list)
    moved_tasks: List[Tuple[str, str, str]] = field(default_factory=list)
    field_changes: List[Tuple[str, str, str, str]] = field(default_factory=list)
    checkbox_changes: List[Tuple[str, bool, bool]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return bool(
            self.new_tasks
            or self.removed_tasks
            or self.moved_tasks
            or self.field_changes
            or self.checkbox_changes
        )

    @property
    def summary(self) -> str:
        """Human-readable change summary."""
        parts = []
        if self.new_tasks:
            ids = [t.task_id for t in self.new_tasks]
            parts.append(f"+{len(self.new_tasks)} new ({', '.join(ids)})")
        if self.removed_tasks:
            ids = [t.task_id for t in self.removed_tasks]
            parts.append(f"-{len(self.removed_tasks)} removed ({', '.join(ids)})")
        if self.moved_tasks:
            moves = [f"{tid}: {old}->{new}" for tid, old, new in self.moved_tasks]
            parts.append(f"~{len(self.moved_tasks)} moved ({', '.join(moves)})")
        if self.checkbox_changes:
            checks = [f"{tid}: {'done' if new else 'undone'}" for tid, _, new in self.checkbox_changes]
            parts.append(f"checked {', '.join(checks)}")
        return " | ".join(parts) if parts else "no changes"


class TaskBoardParser:
    """Parse task_board.md into structured TaskEntry objects.

    Handles the checklist format with bracket tags:
        - [ ] **Title** [ID:WOW-001] [PRIORITY:P1] [ASSIGNEE:agent] [TAGS:a,b]
          - **Brief**: Description
          - **Input**: Source
          - **Output**: Destination
          - **Notes**: Context

    Usage:
        parser = TaskBoardParser()
        state = parser.parse("/path/to/task_board.md")
        print(state.counts)
        # {'backlog': 2, 'in_progress': 1, ...}

    Change detection:
        old_state = parser.parse(path)
        # ... time passes, file changes ...
        new_state = parser.parse(path)
        diff = parser.diff(old_state, new_state)
        if diff.has_changes:
            print(diff.summary)
    """

    def parse(self, file_path: str) -> BoardState:
        """Parse a task_board.md file into a BoardState.

        Args:
            file_path: Path to the task_board.md file.

        Returns:
            BoardState with all parsed tasks.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Task board not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        return self.parse_text(content, str(path))

    def parse_text(self, content: str, source: str = "") -> BoardState:
        """Parse task board content from a string.

        Args:
            content: Raw markdown content.
            source: Source identifier for logging.

        Returns:
            BoardState with all parsed tasks.
        """
        state = BoardState(file_path=source)
        current_section = ""
        current_task: Optional[TaskEntry] = None

        for line in content.split("\n"):
            stripped = line.strip()

            # Check for section headers
            section_match = SECTION_PATTERN.match(stripped)
            if section_match:
                # Save any in-progress task
                if current_task and current_task.task_id:
                    state.tasks[current_task.task_id] = current_task
                    current_task = None

                current_section = section_match.group(1).strip()
                continue

            # Check for checklist task lines
            task_match = TASK_LINE_PATTERN.match(stripped)
            if task_match and current_section:
                # Save previous task
                if current_task and current_task.task_id:
                    state.tasks[current_task.task_id] = current_task

                is_done = task_match.group(1).lower() == "x"
                title = task_match.group(2).strip()
                tag_string = task_match.group(3).strip()

                # Parse bracket tags
                raw_tags = {}
                for tag_match in BRACKET_TAG_PATTERN.finditer(tag_string):
                    key = tag_match.group(1).upper()
                    value = tag_match.group(2).strip()
                    raw_tags[key] = value

                task_id = raw_tags.get("ID", "")

                current_task = TaskEntry(
                    task_id=task_id,
                    title=title,
                    section=current_section,
                    is_done=is_done,
                    priority=raw_tags.get("PRIORITY", ""),
                    assignee=raw_tags.get("ASSIGNEE", ""),
                    created=raw_tags.get("CREATED", ""),
                    updated=raw_tags.get("UPDATED", ""),
                    due=raw_tags.get("DUE", ""),
                    raw_tags=raw_tags,
                )

                # Parse TAGS field into list
                tags_str = raw_tags.get("TAGS", "")
                if tags_str:
                    current_task.tags = [
                        t.strip() for t in tags_str.split(",") if t.strip()
                    ]

                continue

            # Check for sub-fields (indented lines under a task)
            sub_match = SUB_FIELD_PATTERN.match(line)
            if sub_match and current_task:
                key = sub_match.group(1).strip().lower()
                value = sub_match.group(2).strip()

                if key == "brief":
                    current_task.brief = value
                elif key == "input":
                    current_task.input_ref = value
                elif key == "output":
                    current_task.output_ref = value
                elif key == "notes":
                    current_task.notes = value

        # Save last task
        if current_task and current_task.task_id:
            state.tasks[current_task.task_id] = current_task

        logger.debug(
            "Parsed %d tasks from %s: %s",
            state.total_tasks,
            source,
            state.counts,
        )
        return state

    def diff(self, old: BoardState, new: BoardState) -> BoardDiff:
        """Compute differences between two board snapshots.

        Args:
            old: Previous board state.
            new: Current board state.

        Returns:
            BoardDiff describing all changes.
        """
        result = BoardDiff()

        old_ids = set(old.tasks.keys())
        new_ids = set(new.tasks.keys())

        # New tasks
        for tid in new_ids - old_ids:
            result.new_tasks.append(new.tasks[tid])

        # Removed tasks
        for tid in old_ids - new_ids:
            result.removed_tasks.append(old.tasks[tid])

        # Changed tasks
        for tid in old_ids & new_ids:
            old_task = old.tasks[tid]
            new_task = new.tasks[tid]

            # Section changed (task moved)
            old_section = old_task.section_normalized
            new_section = new_task.section_normalized
            if old_section != new_section:
                result.moved_tasks.append((tid, old_section, new_section))

            # Checkbox changed
            if old_task.is_done != new_task.is_done:
                result.checkbox_changes.append(
                    (tid, old_task.is_done, new_task.is_done)
                )

            # Field changes (assignee, priority)
            for field_name in ("priority", "assignee"):
                old_val = getattr(old_task, field_name, "")
                new_val = getattr(new_task, field_name, "")
                if old_val != new_val and (old_val or new_val):
                    result.field_changes.append(
                        (tid, field_name, old_val, new_val)
                    )

        return result
