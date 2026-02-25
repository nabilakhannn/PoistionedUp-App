"""CLI interface for OpenClaw agents to emit analytics events.

Agents can call this via shell tool:
    python -m analytics track task_created --agent jarvis --task WOW-001 --title "Research"
    python -m analytics track heartbeat --agent jarvis --backlog 3
    python -m analytics track llm_call --agent copywriter --model opus --input 1200 --output 800 --cost 0.04
    python -m analytics report summary
    python -m analytics report board

This CLI provides a clean boundary between the OpenClaw agent runtime
(which uses shell commands) and the Python analytics module.
"""

import argparse
import json
import logging
import sys
from typing import List, Optional

from analytics.config import AnalyticsConfig
from analytics.tracker import AgentTracker
from analytics.parsers.task_board import TaskBoardParser

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    root = argparse.ArgumentParser(
        prog="analytics",
        description="OpenClaw Agent Analytics CLI",
    )
    root.add_argument(
        "--project-root",
        help="Project root directory (default: cwd)",
    )
    root.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    sub = root.add_subparsers(dest="command", help="Command")

    # ---- track command ----
    track = sub.add_parser("track", help="Track an analytics event")
    track_sub = track.add_subparsers(dest="event_type", help="Event type")

    # track task_created
    tc = track_sub.add_parser("task_created", help="Track new task")
    tc.add_argument("--agent", required=True, help="Agent ID")
    tc.add_argument("--task", required=True, help="Task ID (e.g., WOW-001)")
    tc.add_argument("--title", required=True, help="Task title")
    tc.add_argument("--priority", default="P2", help="Priority (P0-P3)")
    tc.add_argument("--tags", default="", help="Comma-separated tags")
    tc.add_argument("--assignee", default="", help="Assigned agent")
    tc.add_argument("--type", default="", dest="content_type", help="Content type")
    tc.add_argument("--platform", default="", help="Target platform")

    # track task_claimed
    tcl = track_sub.add_parser("task_claimed", help="Track task claimed")
    tcl.add_argument("--agent", required=True, help="Agent ID")
    tcl.add_argument("--task", required=True, help="Task ID")
    tcl.add_argument("--title", default="", help="Task title")

    # track task_completed
    tco = track_sub.add_parser("task_completed", help="Track task completed")
    tco.add_argument("--agent", required=True, help="Agent ID")
    tco.add_argument("--task", required=True, help="Task ID")
    tco.add_argument("--title", default="", help="Task title")
    tco.add_argument("--duration", type=int, default=None, help="Duration in seconds")
    tco.add_argument("--deliverable", default=None, help="Deliverable file path")

    # track task_failed
    tf = track_sub.add_parser("task_failed", help="Track task failure")
    tf.add_argument("--agent", required=True, help="Agent ID")
    tf.add_argument("--task", required=True, help="Task ID")
    tf.add_argument("--reason", default="", help="Failure reason")

    # track task_blocked
    tb = track_sub.add_parser("task_blocked", help="Track task blocked")
    tb.add_argument("--agent", required=True, help="Agent ID")
    tb.add_argument("--task", required=True, help="Task ID")
    tb.add_argument("--reason", default="", help="Blocked reason")

    # track task_approved
    ta = track_sub.add_parser("task_approved", help="Track task approved")
    ta.add_argument("--task", required=True, help="Task ID")
    ta.add_argument("--approver", default="human", help="Approver ID")

    # track task_rejected
    tr = track_sub.add_parser("task_rejected", help="Track task rejected")
    tr.add_argument("--task", required=True, help="Task ID")
    tr.add_argument("--feedback", default="", help="Rejection feedback")

    # track heartbeat
    hb = track_sub.add_parser("heartbeat", help="Track heartbeat pulse")
    hb.add_argument("--agent", required=True, help="Agent ID")
    hb.add_argument("--backlog", type=int, default=0, help="Tasks in backlog")
    hb.add_argument("--in-progress", type=int, default=0, help="Tasks in progress")
    hb.add_argument("--review", type=int, default=0, help="Tasks in review")
    hb.add_argument("--rule", default=None, help="Rule that triggered action")
    hb.add_argument("--actions", type=int, default=0, help="Actions taken")

    # track llm_call
    lc = track_sub.add_parser("llm_call", help="Track LLM API call")
    lc.add_argument("--agent", required=True, help="Agent ID")
    lc.add_argument("--model", required=True, help="Model name")
    lc.add_argument("--input", type=int, required=True, dest="input_tokens", help="Input tokens")
    lc.add_argument("--output", type=int, required=True, dest="output_tokens", help="Output tokens")
    lc.add_argument("--cost", type=float, required=True, help="Cost in USD")
    lc.add_argument("--step", default=None, help="Pipeline step name")

    # track content_drafted
    cd = track_sub.add_parser("content_drafted", help="Track content draft")
    cd.add_argument("--agent", required=True, help="Agent ID")
    cd.add_argument("--type", required=True, dest="content_type", help="Content type")
    cd.add_argument("--platform", required=True, help="Target platform")
    cd.add_argument("--words", type=int, default=0, help="Word count")
    cd.add_argument("--file", default="", help="File path")

    # track content_posted
    cp = track_sub.add_parser("content_posted", help="Track content posted")
    cp.add_argument("--agent", required=True, help="Agent ID")
    cp.add_argument("--platform", required=True, help="Platform")
    cp.add_argument("--url", default="", help="Post URL")

    # track research_started
    rs = track_sub.add_parser("research_started", help="Track research start")
    rs.add_argument("--agent", required=True, help="Agent ID")
    rs.add_argument("--source", required=True, help="Research source")
    rs.add_argument("--query", default="", help="Search query")

    # track research_completed
    rc = track_sub.add_parser("research_completed", help="Track research complete")
    rc.add_argument("--agent", required=True, help="Agent ID")
    rc.add_argument("--source", required=True, help="Research source")
    rc.add_argument("--results", type=int, default=0, help="Results count")
    rc.add_argument("--score", type=float, default=0.0, help="Top score")
    rc.add_argument("--file", default=None, help="Findings file path")

    # track agent_spawned
    asp = track_sub.add_parser("agent_spawned", help="Track agent spawn")
    asp.add_argument("--agent", required=True, help="New agent ID")
    asp.add_argument("--role", required=True, help="Agent role")
    asp.add_argument("--parent", default="jarvis", help="Parent agent")
    asp.add_argument("--model", default="", help="LLM model")

    # ---- report command ----
    report = sub.add_parser("report", help="Generate analytics reports")
    report_sub = report.add_subparsers(dest="report_type", help="Report type")

    # report summary
    report_sub.add_parser("summary", help="Board state summary")

    # report board
    board = report_sub.add_parser("board", help="Task board state as JSON")
    board.add_argument("--file", default=None, help="task_board.md path")

    return root


def run_track(args: argparse.Namespace, tracker: AgentTracker) -> None:
    """Execute a track command."""
    event_type = args.event_type

    if event_type == "task_created":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        tracker.task_created(
            agent_id=args.agent,
            task_id=args.task,
            title=args.title,
            priority=args.priority,
            tags=tags,
            assignee=args.assignee,
            content_type=args.content_type,
            platform=args.platform,
        )
    elif event_type == "task_claimed":
        tracker.task_claimed(args.agent, args.task, args.title)
    elif event_type == "task_completed":
        tracker.task_completed(
            args.agent, args.task, args.title,
            duration_seconds=args.duration,
            deliverable_path=args.deliverable,
        )
    elif event_type == "task_failed":
        tracker.task_failed(args.agent, args.task, args.reason)
    elif event_type == "task_blocked":
        tracker.task_blocked(args.agent, args.task, args.reason)
    elif event_type == "task_approved":
        tracker.task_approved(args.task, approver=args.approver)
    elif event_type == "task_rejected":
        tracker.task_rejected(args.task, feedback=args.feedback)
    elif event_type == "heartbeat":
        tracker.heartbeat_pulse(
            agent_id=args.agent,
            backlog=args.backlog,
            in_progress=args.in_progress,
            review=args.review,
            rule_triggered=args.rule,
            actions_taken=args.actions,
        )
    elif event_type == "llm_call":
        tracker.llm_call(
            agent_id=args.agent,
            model=args.model,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            cost_usd=args.cost,
            step_name=args.step,
        )
    elif event_type == "content_drafted":
        tracker.content_drafted(
            agent_id=args.agent,
            content_type=args.content_type,
            platform=args.platform,
            word_count=args.words,
            file_path=args.file,
        )
    elif event_type == "content_posted":
        tracker.content_posted(args.agent, args.platform, args.url)
    elif event_type == "research_started":
        tracker.research_started(args.agent, args.source, args.query)
    elif event_type == "research_completed":
        tracker.research_completed(
            args.agent, args.source,
            results_count=args.results,
            top_score=args.score,
            findings_file=args.file,
        )
    elif event_type == "agent_spawned":
        tracker.agent_spawned(
            args.agent, args.role,
            parent_agent=args.parent,
            model=args.model,
        )
    else:
        print(f"Unknown event type: {event_type}", file=sys.stderr)
        sys.exit(1)

    tracker.flush()
    print(f"OK: {event_type} tracked")


def run_report(args: argparse.Namespace, config: AnalyticsConfig) -> None:
    """Execute a report command."""
    report_type = args.report_type

    if report_type == "summary":
        _print_board_summary(config)
    elif report_type == "board":
        file_path = args.file or str(config.task_board_path)
        _print_board_json(file_path)
    else:
        print(f"Unknown report type: {report_type}", file=sys.stderr)
        sys.exit(1)


def _print_board_summary(config: AnalyticsConfig) -> None:
    """Print a human-readable board summary."""
    parser = TaskBoardParser()
    try:
        state = parser.parse(str(config.task_board_path))
    except FileNotFoundError:
        print("task_board.md not found", file=sys.stderr)
        sys.exit(1)

    print(f"Task Board Summary ({state.total_tasks} total)")
    print("=" * 40)
    for section, tasks in state.by_section.items():
        print(f"\n{section.upper()} ({len(tasks)})")
        for t in tasks:
            assignee = f" [{t.assignee}]" if t.assignee else ""
            priority = f" {t.priority}" if t.priority else ""
            print(f"  {t.task_id}: {t.title}{priority}{assignee}")


def _print_board_json(file_path: str) -> None:
    """Print board state as JSON (for piping to other tools)."""
    parser = TaskBoardParser()
    try:
        state = parser.parse(file_path)
    except FileNotFoundError:
        print(json.dumps({"error": "file not found"}))
        sys.exit(1)

    output = {
        "total_tasks": state.total_tasks,
        "counts": state.counts,
        "timestamp": state.timestamp,
        "tasks": {
            tid: {
                "title": t.title,
                "section": t.section_normalized,
                "priority": t.priority,
                "assignee": t.assignee,
                "tags": t.tags,
                "is_done": t.is_done,
                "brief": t.brief,
            }
            for tid, t in state.tasks.items()
        },
    }
    print(json.dumps(output, indent=2))


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = AnalyticsConfig.from_env(project_root=args.project_root)

    if args.command == "track":
        if not args.event_type:
            parser.parse_args(["track", "--help"])
            return
        tracker = AgentTracker.create(config)
        run_track(args, tracker)

    elif args.command == "report":
        if not args.report_type:
            parser.parse_args(["report", "--help"])
            return
        run_report(args, config)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
