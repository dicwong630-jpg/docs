"""
lobster_porter.core
Core engine: batch move, copy, categorize, and tag files.
Maintains an operation log for undo support.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, List, Optional

logger = logging.getLogger(__name__)


class OperationRecord:
    """Single reversible file operation entry."""

    def __init__(self, action: str, src: Path, dst: Path) -> None:
        self.action = action          # "move" | "copy"
        self.src = src
        self.dst = dst
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "src": str(self.src),
            "dst": str(self.dst),
            "timestamp": self.timestamp,
        }


class LobsterPorter:
    """
    Batch file porter with undo log, strategy routing, and plugin hooks.

    Usage::

        porter = LobsterPorter(log_path="porter_ops.json")
        porter.batch_move(src_dir="raw_assets", dst_dir="organised")
    """

    def __init__(
        self,
        strategy=None,
        plugins: Optional[List] = None,
        log_path: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        self.strategy = strategy
        self.plugins: List = plugins or []
        self.log_path = Path(log_path) if log_path else None
        self.dry_run = dry_run
        self._history: List[OperationRecord] = []

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def batch_move(
        self,
        src_dir: str | Path,
        dst_dir: str | Path,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[Path]:
        """Move all files matching *pattern* from src_dir to dst_dir."""
        return self._batch_transfer("move", src_dir, dst_dir, pattern, recursive)

    def batch_copy(
        self,
        src_dir: str | Path,
        dst_dir: str | Path,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[Path]:
        """Copy all files matching *pattern* from src_dir to dst_dir."""
        return self._batch_transfer("copy", src_dir, dst_dir, pattern, recursive)

    def batch_categorize(
        self,
        src_dir: str | Path,
        dst_root: str | Path,
        pattern: str = "**/*",
    ) -> List[Path]:
        """
        Walk src_dir, route each file through the active strategy,
        and move it into the resolved sub-folder under dst_root.
        Falls back to 'uncategorized/' when no strategy is set.
        """
        src_dir = Path(src_dir)
        dst_root = Path(dst_root)
        moved: List[Path] = []

        for file_path in src_dir.glob(pattern):
            if not file_path.is_file():
                continue

            category = (
                self.strategy.classify(file_path)
                if self.strategy
                else "uncategorized"
            )
            target_dir = dst_root / category
            dst = target_dir / file_path.name
            final_dst = self._execute("move", file_path, dst)
            moved.append(final_dst)

        return moved

    def batch_tag(
        self,
        src_dir: str | Path,
        tag_func: Callable[[Path], str],
        output_manifest: Optional[str | Path] = None,
    ) -> dict:
        """
        Apply tag_func to every file under src_dir.
        Returns a mapping of {relative_path: tag} and optionally
        writes a JSON manifest.
        """
        src_dir = Path(src_dir)
        manifest: dict = {}

        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                tag = tag_func(file_path)
                manifest[str(file_path.relative_to(src_dir))] = tag
                logger.info("Tagged %s → %s", file_path.name, tag)

        if output_manifest:
            Path(output_manifest).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        return manifest

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def undo_last(self) -> bool:
        """Reverse the most recent operation (move only)."""
        if not self._history:
            logger.warning("Nothing to undo.")
            return False

        record = self._history.pop()
        if record.action == "move":
            logger.info("Undoing move: %s → %s", record.dst, record.src)
            if not self.dry_run:
                record.src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(record.dst), str(record.src))
            self._flush_log()
            return True

        logger.warning("Cannot undo action '%s'.", record.action)
        return False

    def undo_all(self) -> int:
        """Reverse all operations in reverse chronological order."""
        count = 0
        while self._history:
            if self.undo_last():
                count += 1
        return count

    # ------------------------------------------------------------------
    # Plugin hooks
    # ------------------------------------------------------------------

    def register_plugin(self, plugin) -> None:
        self.plugins.append(plugin)

    def _run_plugins(self, event: str, **kwargs) -> None:
        for plugin in self.plugins:
            handler = getattr(plugin, f"on_{event}", None)
            if callable(handler):
                handler(**kwargs)

    def _run_plugins_before_transfer(self, action: str, src: Path, dst: Path) -> Path:
        """Call on_before_transfer on each plugin; plugins may return a new dst."""
        for plugin in self.plugins:
            handler = getattr(plugin, "on_before_transfer", None)
            if callable(handler):
                result = handler(action=action, src=src, dst=dst)
                if isinstance(result, Path):
                    dst = result
        return dst

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _batch_transfer(
        self,
        action: str,
        src_dir: str | Path,
        dst_dir: str | Path,
        pattern: str,
        recursive: bool,
    ) -> List[Path]:
        src_dir = Path(src_dir)
        dst_dir = Path(dst_dir)
        glob_fn = src_dir.rglob if recursive else src_dir.glob
        results: List[Path] = []

        for file_path in glob_fn(pattern):
            if not file_path.is_file():
                continue
            dst = dst_dir / file_path.name
            final_dst = self._execute(action, file_path, dst)
            results.append(final_dst)

        return results

    def _execute(self, action: str, src: Path, dst: Path) -> Path:
        dst = self._run_plugins_before_transfer(action=action, src=src, dst=dst)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if not self.dry_run:
            if action == "move":
                shutil.move(str(src), str(dst))
            elif action == "copy":
                shutil.copy2(str(src), str(dst))

        record = OperationRecord(action, src, dst)
        self._history.append(record)
        self._flush_log()
        logger.info("[%s] %s → %s", action.upper(), src, dst)
        self._run_plugins("after_transfer", action=action, src=src, dst=dst, record=record)
        return dst

    def _flush_log(self) -> None:
        if self.log_path:
            self.log_path.write_text(
                json.dumps(
                    [r.to_dict() for r in self._history],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
