"""Entry point for `python -m analytics`.

Supports two modes:
    python -m analytics track <event> [options]    # Single event
    python -m analytics report <type> [options]    # Generate report
    python -m analytics daemon [options]           # Continuous monitoring
"""

import sys

from analytics.cli import main as cli_main
from analytics.daemon import main as daemon_main


def main() -> None:
    """Route to CLI or daemon based on command."""
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        daemon_main(sys.argv[2:])
    else:
        cli_main()


if __name__ == "__main__":
    main()
