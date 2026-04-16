"""
lobster_porter.core
===================
Core engine of the LobsterPorter document-moving utility.

Classes
-------
- :class:`LobsterPorter`  — orchestrates file operations using pluggable strategies

Convenience helpers
-------------------
- :func:`batch_move`  — move files without instantiating the class manually
- :func:`batch_copy`  — copy files without instantiating the class manually
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Callable, Iterable, Optional

from lobster_porter.strategies import BaseStrategy, get_strategy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class LobsterPorter:
    """Orchestrates batch document operations inside a docs workspace.

    Parameters
    ----------
    root:
        Absolute or relative path to the root of the documentation workspace.
    dry_run:
        When ``True`` log every planned operation without actually touching
        the filesystem.  Useful for previewing changes before committing.
    on_conflict:
        How to handle a destination file that already exists.
        ``"skip"``      – leave the destination unchanged (default).
        ``"overwrite"`` – replace the destination file.
        ``"rename"``    – append a numeric suffix to the new filename.
    """

    def __init__(
        self,
        root: str | Path = ".",
        dry_run: bool = False,
        on_conflict: str = "skip",
    ) -> None:
        self.root = Path(root).resolve()
        self.dry_run = dry_run
        self.on_conflict = on_conflict
        self._plugins: list = []
        logger.debug("LobsterPorter initialised at root=%s", self.root)

    # ------------------------------------------------------------------
    # Plugin management
    # ------------------------------------------------------------------

    def register_plugin(self, plugin) -> None:
        """Register a :class:`~lobster_porter.plugins.base.BasePlugin` instance.

        Plugins are called in registration order after every file operation.
        """
        self._plugins.append(plugin)
        logger.debug("Plugin registered: %s", plugin)

    # ------------------------------------------------------------------
    # Core file operations
    # ------------------------------------------------------------------

    def move(
        self,
        src: str | Path,
        dst: str | Path,
        strategy: str | BaseStrategy = "flat",
        glob_pattern: str = "**/*",
        filter_fn: Optional[Callable[[Path], bool]] = None,
    ) -> list[tuple[Path, Path]]:
        """Move files from *src* to *dst* using the given *strategy*.

        Parameters
        ----------
        src:
            Source directory (relative to :attr:`root`).
        dst:
            Destination directory (relative to :attr:`root`).
        strategy:
            Name of a built-in strategy or a :class:`BaseStrategy` instance.
            Built-in names: ``"flat"``, ``"by_extension"``, ``"by_category"``.
        glob_pattern:
            Glob expression used to collect candidate files inside *src*.
        filter_fn:
            Optional callable ``(Path) -> bool``; return ``True`` to include a
            file, ``False`` to skip it.

        Returns
        -------
        list[tuple[Path, Path]]
            List of ``(source, destination)`` pairs that were (or would be)
            processed.
        """
        strategy_obj = (
            strategy if isinstance(strategy, BaseStrategy) else get_strategy(strategy)
        )
        files = self._collect_files(
            self.root / src, glob_pattern=glob_pattern, filter_fn=filter_fn
        )
        pairs = strategy_obj.plan(files, src_root=self.root / src, dst_root=self.root / dst)
        return self._execute(pairs, operation="move")

    def copy(
        self,
        src: str | Path,
        dst: str | Path,
        strategy: str | BaseStrategy = "flat",
        glob_pattern: str = "**/*",
        filter_fn: Optional[Callable[[Path], bool]] = None,
    ) -> list[tuple[Path, Path]]:
        """Copy files from *src* to *dst* (same signature as :meth:`move`).

        Returns
        -------
        list[tuple[Path, Path]]
            List of ``(source, destination)`` pairs that were processed.
        """
        strategy_obj = (
            strategy if isinstance(strategy, BaseStrategy) else get_strategy(strategy)
        )
        files = self._collect_files(
            self.root / src, glob_pattern=glob_pattern, filter_fn=filter_fn
        )
        pairs = strategy_obj.plan(files, src_root=self.root / src, dst_root=self.root / dst)
        return self._execute(pairs, operation="copy")

    def index(self, directory: str | Path, output_file: str = "INDEX.md") -> Path:
        """Generate a Markdown index for all documents found under *directory*.

        Parameters
        ----------
        directory:
            Directory to scan (relative to :attr:`root`).
        output_file:
            Filename for the generated index, written inside *directory*.

        Returns
        -------
        Path
            Absolute path of the generated index file.
        """
        target_dir = self.root / directory
        files = sorted(
            p for p in target_dir.rglob("*") if p.is_file() and p.suffix in {".md", ".mdx"}
        )
        lines = [f"# Index of `{directory}`\n"]
        for f in files:
            rel = f.relative_to(self.root)
            lines.append(f"- [{rel}]({rel})")

        output_path = target_dir / output_file
        if not self.dry_run:
            output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Index written to %s (%d entries)", output_path, len(files))
        self._notify_plugins("index", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_files(
        self,
        directory: Path,
        glob_pattern: str,
        filter_fn: Optional[Callable[[Path], bool]],
    ) -> list[Path]:
        """Return a list of files under *directory* matching *glob_pattern*."""
        candidates = [p for p in directory.glob(glob_pattern) if p.is_file()]
        if filter_fn is not None:
            candidates = [p for p in candidates if filter_fn(p)]
        return candidates

    def _resolve_destination(self, dst: Path) -> Path:
        """Apply the configured conflict-resolution policy to *dst*."""
        if not dst.exists() or self.on_conflict == "overwrite":
            return dst
        if self.on_conflict == "skip":
            logger.debug("Skipping existing destination: %s", dst)
            return dst  # caller checks existence again
        # on_conflict == "rename"
        stem, suffix, parent = dst.stem, dst.suffix, dst.parent
        counter = 1
        while dst.exists():
            dst = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        return dst

    def _execute(
        self,
        pairs: list[tuple[Path, Path]],
        operation: str,
    ) -> list[tuple[Path, Path]]:
        """Carry out the planned file *operation* (``"move"`` or ``"copy"``)."""
        processed: list[tuple[Path, Path]] = []
        for src, dst in pairs:
            dst = self._resolve_destination(dst)
            if dst.exists() and self.on_conflict == "skip":
                logger.info("SKIP (conflict): %s -> %s", src, dst)
                continue
            if self.dry_run:
                logger.info("DRY-RUN %s: %s -> %s", operation.upper(), src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if operation == "move":
                    shutil.move(str(src), str(dst))
                else:
                    shutil.copy2(str(src), str(dst))
                logger.info("%s: %s -> %s", operation.upper(), src, dst)
            processed.append((src, dst))
            self._notify_plugins(operation, src, dst)
        return processed

    def _notify_plugins(self, event: str, *args) -> None:
        """Broadcast an event to all registered plugins."""
        for plugin in self._plugins:
            try:
                plugin.on_event(event, *args)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Plugin %s raised an error: %s", plugin, exc)


# ---------------------------------------------------------------------------
# Convenience module-level helpers
# ---------------------------------------------------------------------------


def batch_move(
    src: str | Path,
    dst: str | Path,
    root: str | Path = ".",
    strategy: str = "flat",
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    """Move files without explicitly instantiating :class:`LobsterPorter`.

    Parameters
    ----------
    src, dst:
        Source and destination directories (relative to *root*).
    root:
        Workspace root.
    strategy:
        Name of the built-in strategy to use.
    dry_run:
        If ``True``, only log what *would* happen.

    Returns
    -------
    list[tuple[Path, Path]]
        Processed ``(source, destination)`` pairs.
    """
    return LobsterPorter(root=root, dry_run=dry_run).move(src, dst, strategy=strategy)


def batch_copy(
    src: str | Path,
    dst: str | Path,
    root: str | Path = ".",
    strategy: str = "flat",
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    """Copy files without explicitly instantiating :class:`LobsterPorter`.

    Parameters
    ----------
    src, dst:
        Source and destination directories (relative to *root*).
    root:
        Workspace root.
    strategy:
        Name of the built-in strategy to use.
    dry_run:
        If ``True``, only log what *would* happen.

    Returns
    -------
    list[tuple[Path, Path]]
        Processed ``(source, destination)`` pairs.
    """
    return LobsterPorter(root=root, dry_run=dry_run).copy(src, dst, strategy=strategy)


# ---------------------------------------------------------------------------
# Iterable overloads (advanced usage)
# ---------------------------------------------------------------------------


def move_files(
    files: Iterable[Path],
    dst_root: Path,
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    """Move an explicit list of *files* into *dst_root*, preserving filenames.

    Parameters
    ----------
    files:
        Iterable of absolute :class:`~pathlib.Path` objects to move.
    dst_root:
        Target directory; created automatically if it does not exist.
    dry_run:
        If ``True``, only log what *would* happen.
    """
    porter = LobsterPorter(root=dst_root.parent, dry_run=dry_run)
    pairs = [(f, dst_root / f.name) for f in files]
    return porter._execute(pairs, operation="move")  # noqa: SLF001
