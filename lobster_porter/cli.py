"""
lobster_porter.cli
==================

Command-line interface for Lobster Porter.

Usage
-----
::

    # Copy files (default)
    python -m lobster_porter --source docs/raw --destination docs/organised

    # Move files with dry-run preview
    python -m lobster_porter --source docs/raw --destination docs/organised \\
        --strategy move --dry-run

    # Use the index plugin in addition to the default log plugin
    python -m lobster_porter --source docs/raw --destination docs/organised \\
        --plugins log index

Extension guide
---------------
To expose a new strategy or plugin via the CLI, add its name to the
``STRATEGY_MAP`` or ``PLUGIN_MAP`` dictionaries near the bottom of this
module.  No other changes are needed.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from lobster_porter.config import Config
from lobster_porter.core import Porter
from lobster_porter.plugins import BasePlugin, IndexPlugin, LogPlugin
from lobster_porter.strategies import BaseStrategy, CopyStrategy, MoveStrategy

# Registry maps for strategies and plugins.
# Add new entries here to expose them through the CLI.
STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "copy": CopyStrategy,
    "move": MoveStrategy,
}

PLUGIN_MAP: dict[str, type[BasePlugin]] = {
    "log": LogPlugin,
    "index": IndexPlugin,
}


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="lobster_porter",
        description="Lobster Porter — batch document organiser for your docs knowledge base.",
    )
    parser.add_argument(
        "--source",
        default=".",
        metavar="DIR",
        help="Source directory to process (default: current directory).",
    )
    parser.add_argument(
        "--destination",
        default="output",
        metavar="DIR",
        help="Destination directory (default: output/).",
    )
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGY_MAP),
        default="copy",
        help="Transport strategy to use (default: copy).",
    )
    parser.add_argument(
        "--plugins",
        nargs="*",
        choices=list(PLUGIN_MAP),
        default=["log"],
        metavar="PLUGIN",
        help="Plugins to activate (default: log). Available: "
        + ", ".join(PLUGIN_MAP),
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=None,
        metavar="GLOB",
        help="File glob patterns to include (e.g. '*.md' '*.pdf'). "
        "Defaults to common document formats.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without modifying any files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the destination.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="lobster_porter 0.1.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry-point for ``python -m lobster_porter``.

    Parameters
    ----------
    argv:
        Argument vector; defaults to ``sys.argv[1:]`` when *None*.

    Returns
    -------
    int
        Exit code (0 = success, non-zero = failure).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    config_kwargs: dict[str, Any] = dict(
        source=args.source,
        destination=args.destination,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        recursive=not args.no_recursive,
    )
    if args.patterns:
        config_kwargs["file_patterns"] = args.patterns

    config = Config(**config_kwargs)
    strategy = STRATEGY_MAP[args.strategy]()
    plugins = [PLUGIN_MAP[name]() for name in (args.plugins or [])]

    porter = Porter(config=config, strategy=strategy, plugins=plugins)
    try:
        porter.run()
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Use --overwrite to replace existing files.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
