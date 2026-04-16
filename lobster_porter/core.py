"""
lobster_porter.core — 核心功能模組
====================================

This module contains the ``Porter`` class, the main orchestrator of the
Lobster Porter system.  It is responsible for:

1. **Discovery** — scanning the source directory for eligible files.
2. **Classification** — delegating file classification to a ``Strategy``.
3. **Transport** — moving / copying files to their destination paths.
4. **Plugin hooks** — notifying registered plugins at each stage.

Usage
-----
Minimal example::

    from lobster_porter import Porter
    from lobster_porter.strategies import ExtensionStrategy

    porter = Porter(
        src="./inbox",
        dest="./organised",
        strategy=ExtensionStrategy(),
    )
    porter.run()

Architecture notes
------------------
- ``Porter`` is intentionally thin.  Heavy lifting belongs in strategies and
  plugins so the core stays easy to read and test.
- All filesystem side-effects are isolated to the ``_transport`` method so
  you can subclass and override only that part in tests.

TODO
----
- Add async / concurrent transport for large batches.
- Add dry-run mode (log what *would* happen without touching the FS).
- Add progress-bar support (e.g. via ``tqdm``).
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

from lobster_porter.strategies import BaseStrategy, ExtensionStrategy

logger = logging.getLogger(__name__)


class TransportResult:
    """Records the outcome of a single file transport operation.

    Attributes
    ----------
    src : Path
        The original file path.
    dest : Path
        The destination file path (where the file ended up).
    success : bool
        ``True`` if the file was transported successfully.
    error : Optional[Exception]
        Populated when ``success`` is ``False``.
    """

    def __init__(
        self,
        src: Path,
        dest: Path,
        success: bool,
        error: Optional[Exception] = None,
    ) -> None:
        self.src = src
        self.dest = dest
        self.success = success
        self.error = error

    def __repr__(self) -> str:  # pragma: no cover
        status = "OK" if self.success else f"ERR({self.error})"
        return f"<TransportResult {self.src} → {self.dest} [{status}]>"


class Porter:
    """The main Lobster Porter orchestrator.

    Parameters
    ----------
    src : str | Path
        Source directory to scan for files.
    dest : str | Path
        Root destination directory.  Sub-directories are created automatically
        based on the active strategy's classification.
    strategy : BaseStrategy, optional
        The classification / routing strategy to use.  Defaults to
        ``ExtensionStrategy`` which groups files by their file extension.
    plugins : list, optional
        Ordered list of plugin instances to notify at each lifecycle hook.
    copy : bool
        When ``True`` the porter *copies* files instead of *moving* them.
        Defaults to ``False`` (move).
    overwrite : bool
        When ``True`` existing destination files are silently overwritten.
        Defaults to ``False`` (skip with a warning).

    Examples
    --------
    >>> porter = Porter(src="inbox", dest="organised")
    >>> results = porter.run()
    >>> print(f"Transported {sum(r.success for r in results)} files.")
    """

    def __init__(
        self,
        src: str | Path,
        dest: str | Path,
        strategy: Optional[BaseStrategy] = None,
        plugins: Optional[list] = None,
        copy: bool = False,
        overwrite: bool = False,
    ) -> None:
        self.src = Path(src)
        self.dest = Path(dest)
        self.strategy = strategy or ExtensionStrategy()
        self.plugins: list = plugins or []
        self.copy = copy
        self.overwrite = overwrite

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> List[TransportResult]:
        """Discover, classify, and transport all eligible files.

        Returns
        -------
        list[TransportResult]
            One entry per discovered file; inspect ``.success`` to determine
            whether each transport succeeded.
        """
        self._notify_plugins("on_start", porter=self)

        files = list(self._discover())
        logger.info("Discovered %d files in %s", len(files), self.src)

        results: List[TransportResult] = []
        for file_path in files:
            result = self._handle_file(file_path)
            results.append(result)

        self._notify_plugins("on_finish", porter=self, results=results)

        successes = sum(r.success for r in results)
        logger.info("Transport complete: %d/%d successful", successes, len(results))
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _discover(self) -> Iterable[Path]:
        """Yield all files inside ``self.src`` (recursively).

        TODO: Add configurable include/exclude glob patterns.
        """
        if not self.src.exists():
            raise FileNotFoundError(f"Source directory not found: {self.src}")
        for root, _dirs, files in os.walk(self.src):
            for fname in files:
                yield Path(root) / fname

    def _handle_file(self, file_path: Path) -> TransportResult:
        """Classify and transport a single file.

        Parameters
        ----------
        file_path : Path
            Absolute (or relative-to-cwd) path to the file.
        """
        self._notify_plugins("on_before_transport", file_path=file_path)

        # Let the strategy decide which sub-directory this file belongs in.
        category = self.strategy.classify(file_path)
        dest_dir = self.dest / category
        dest_path = dest_dir / file_path.name

        result = self._transport(file_path, dest_path)
        self._notify_plugins("on_after_transport", result=result)
        return result

    def _transport(self, src: Path, dest: Path) -> TransportResult:
        """Perform the actual filesystem operation (move or copy).

        This method is deliberately isolated so you can override it in a
        subclass without touching any other logic (e.g. for unit tests that
        should not touch the real filesystem).

        TODO: Implement a DryRunPorter subclass that overrides this method.
        """
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and not self.overwrite:
                logger.warning("Skipping %s — destination already exists: %s", src, dest)
                return TransportResult(src=src, dest=dest, success=False,
                                       error=FileExistsError(str(dest)))

            if self.copy:
                shutil.copy2(src, dest)
                logger.debug("Copied %s → %s", src, dest)
            else:
                shutil.move(str(src), dest)
                logger.debug("Moved %s → %s", src, dest)

            return TransportResult(src=src, dest=dest, success=True)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to transport %s: %s", src, exc)
            return TransportResult(src=src, dest=dest, success=False, error=exc)

    def _notify_plugins(self, hook: str, **kwargs) -> None:
        """Call ``hook`` on every registered plugin (if the plugin has it).

        Parameters
        ----------
        hook : str
            Name of the plugin lifecycle method, e.g. ``"on_start"``.
        **kwargs
            Extra keyword arguments forwarded to the hook method.
        """
        for plugin in self.plugins:
            method = getattr(plugin, hook, None)
            if callable(method):
                try:
                    method(**kwargs)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Plugin %s raised in %s: %s", plugin, hook, exc)
