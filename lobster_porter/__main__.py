"""
lobster_porter.__main__
Command-line interface for the lobster porter.

Usage examples::

    python -m lobster_porter move  raw/  organised/  --pattern "*.fountain"
    python -m lobster_porter copy  raw/  backup/     --recursive
    python -m lobster_porter categorize raw/ sorted/
    python -m lobster_porter tag   raw/  --manifest tags.json
"""

from __future__ import annotations

import argparse
import sys

from .core import LobsterPorter
from .strategies import ExtensionStrategy
from .plugins.logger_plugin import LoggerPlugin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lobster_porter",
        description="龍蝦搬運工 — batch file transport, categorisation, and tagging",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- move ----
    mv = sub.add_parser("move", help="Batch move files")
    mv.add_argument("src", help="Source directory")
    mv.add_argument("dst", help="Destination directory")
    mv.add_argument("--pattern", default="*", help="Glob pattern (default: *)")
    mv.add_argument("--recursive", action="store_true")
    mv.add_argument("--dry-run", action="store_true")
    mv.add_argument("--log", default=None, help="Path to JSON operation log")

    # ---- copy ----
    cp = sub.add_parser("copy", help="Batch copy files")
    cp.add_argument("src", help="Source directory")
    cp.add_argument("dst", help="Destination directory")
    cp.add_argument("--pattern", default="*", help="Glob pattern (default: *)")
    cp.add_argument("--recursive", action="store_true")
    cp.add_argument("--dry-run", action="store_true")
    cp.add_argument("--log", default=None, help="Path to JSON operation log")

    # ---- categorize ----
    cat = sub.add_parser("categorize", help="Categorize files by extension")
    cat.add_argument("src", help="Source directory")
    cat.add_argument("dst", help="Destination root directory")
    cat.add_argument("--dry-run", action="store_true")
    cat.add_argument("--log", default=None, help="Path to JSON operation log")

    # ---- tag ----
    tag = sub.add_parser("tag", help="Tag files and emit a manifest")
    tag.add_argument("src", help="Source directory")
    tag.add_argument("--manifest", default="tags.json", help="Output manifest path")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    porter = LobsterPorter(
        strategy=ExtensionStrategy(),
        plugins=[LoggerPlugin()],
        log_path=getattr(args, "log", None),
        dry_run=getattr(args, "dry_run", False),
    )

    if args.command in ("move", "copy"):
        fn = porter.batch_move if args.command == "move" else porter.batch_copy
        results = fn(
            args.src,
            args.dst,
            pattern=args.pattern,
            recursive=args.recursive,
        )
        print(f"{'Moved' if args.command == 'move' else 'Copied'} {len(results)} file(s).")

    elif args.command == "categorize":
        results = porter.batch_categorize(args.src, args.dst)
        print(f"Categorized {len(results)} file(s).")

    elif args.command == "tag":
        manifest = porter.batch_tag(
            args.src,
            tag_func=lambda p: ExtensionStrategy().classify(p),
            output_manifest=args.manifest,
        )
        print(f"Tagged {len(manifest)} file(s). Manifest saved to {args.manifest}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
