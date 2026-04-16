"""
lobster_porter.plugins.examples — 插件範例
============================================

This module contains ready-to-use example plugins that demonstrate the
plugin system and provide immediately useful functionality.

Included plugins
----------------
``LoggingPlugin``
    Logs transport activity to Python's standard ``logging`` module.

``SummaryPlugin``
    Prints (or stores) a summary report after the porter finishes.

``DryRunPlugin``
    Intercepts transports before they happen and logs what *would* have
    occurred without touching the real filesystem.

``FileCounterPlugin``
    Counts files by category; exposes the counts for post-run inspection.

Usage
-----
>>> from lobster_porter import Porter
>>> from lobster_porter.plugins.examples import LoggingPlugin, SummaryPlugin

>>> porter = Porter(
...     src="./inbox",
...     dest="./organised",
...     plugins=[LoggingPlugin(), SummaryPlugin()],
... )
>>> porter.run()

TODO
----
- Add a ``SlackNotifierPlugin`` that sends a Slack message on finish.
- Add a ``IndexBuilderPlugin`` that writes an index.json / README summary.
- Add a ``DuplicateDetectorPlugin`` that skips files with identical content.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from lobster_porter.plugins.base import BasePlugin

if TYPE_CHECKING:
    from lobster_porter.core import Porter, TransportResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LoggingPlugin
# ---------------------------------------------------------------------------

class LoggingPlugin(BasePlugin):
    """Log every transport event using Python's ``logging`` module.

    Parameters
    ----------
    level : int
        The logging level to use for individual transport events.
        Defaults to ``logging.DEBUG``.
    summary_level : int
        The logging level to use for the finish summary.
        Defaults to ``logging.INFO``.

    Example
    -------
    >>> import logging
    >>> logging.basicConfig(level=logging.DEBUG)
    >>> plugin = LoggingPlugin()
    """

    def __init__(
        self,
        level: int = logging.DEBUG,
        summary_level: int = logging.INFO,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.level = level
        self.summary_level = summary_level

    def on_start(self, porter: "Porter", **kwargs: Any) -> None:  # noqa: D102
        logger.log(self.level, "[%s] Porter starting: %s → %s",
                   self.name, porter.src, porter.dest)

    def on_after_transport(self, result: "TransportResult", **kwargs: Any) -> None:  # noqa: D102
        if result.success:
            logger.log(self.level, "[%s] ✓ %s → %s", self.name, result.src, result.dest)
        else:
            logger.log(self.level, "[%s] ✗ %s  error=%s", self.name, result.src, result.error)

    def on_finish(self, porter: "Porter", results: "List[TransportResult]", **kwargs: Any) -> None:  # noqa: D102
        ok = sum(r.success for r in results)
        logger.log(self.summary_level, "[%s] Finished: %d/%d successful",
                   self.name, ok, len(results))


# ---------------------------------------------------------------------------
# SummaryPlugin
# ---------------------------------------------------------------------------

class SummaryPlugin(BasePlugin):
    """Print a human-readable summary table after the porter finishes.

    The summary is printed to stdout via ``print()`` so it is always visible
    regardless of the current logging configuration.

    Example
    -------
    >>> plugin = SummaryPlugin()
    >>> # After porter.run() you will see something like:
    >>> # ╔══════════════════════════════════════╗
    >>> # ║  Lobster Porter — Transport Summary  ║
    >>> # ╠═══════╦═══════╦══════════════════════╣
    >>> # ║  OK   ║  FAIL ║  TOTAL               ║
    >>> # ╠═══════╬═══════╬══════════════════════╣
    >>> # ║   12  ║    1  ║   13                 ║
    >>> # ╚═══════╩═══════╩══════════════════════╝
    """

    def on_finish(self, porter: "Porter", results: "List[TransportResult]", **kwargs: Any) -> None:  # noqa: D102
        ok = sum(r.success for r in results)
        fail = len(results) - ok
        print("\n╔══════════════════════════════════════╗")
        print("║  Lobster Porter — Transport Summary  ║")
        print("╠═══════╦═══════╦══════════════════════╣")
        print("║  OK   ║  FAIL ║  TOTAL               ║")
        print("╠═══════╬═══════╬══════════════════════╣")
        print(f"║  {ok:>4} ║  {fail:>4} ║  {len(results):<19} ║")
        print("╚═══════╩═══════╩══════════════════════╝\n")

        if fail:
            print("Failed files:")
            for r in results:
                if not r.success:
                    print(f"  • {r.src}  [{r.error}]")


# ---------------------------------------------------------------------------
# DryRunPlugin
# ---------------------------------------------------------------------------

class DryRunPlugin(BasePlugin):
    """Record what the porter *would* transport — without preventing any moves.

    .. important::
        This plugin does **not** prevent the ``Porter`` from actually moving or
        copying files.  It only collects the planned operations in
        ``self.planned_moves`` for post-run inspection.  If you need a true
        no-op run that never touches the filesystem, subclass ``Porter`` and
        override ``_transport`` to be a no-op, then pair it with this plugin
        for reporting.

    TODO: Integrate with a future ``DryRunPorter`` subclass that overrides
    ``_transport`` so that enabling dry-run mode is a single flag, not a
    separate class.

    Example
    -------
    >>> dry = DryRunPlugin()
    >>> porter = Porter(src="inbox", dest="organised", plugins=[dry])
    >>> porter.run()
    >>> for src, dest in dry.planned_moves:
    ...     print(f"Would move {src} → {dest}")
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.planned_moves: List[tuple[Path, Path]] = []

    def on_before_transport(self, file_path: "Path", **kwargs: Any) -> None:  # noqa: D102
        # We don't know the dest yet at this hook, so we just record the src.
        logger.info("[DryRunPlugin] Would transport: %s", file_path)

    def on_after_transport(self, result: "TransportResult", **kwargs: Any) -> None:  # noqa: D102
        self.planned_moves.append((result.src, result.dest))


# ---------------------------------------------------------------------------
# FileCounterPlugin
# ---------------------------------------------------------------------------

class FileCounterPlugin(BasePlugin):
    """Count transported files grouped by their destination sub-directory.

    After a run, inspect ``self.counts`` to see a breakdown by category.

    Attributes
    ----------
    counts : dict[str, int]
        Maps destination sub-directory names to the number of files placed
        there successfully.

    Example
    -------
    >>> counter = FileCounterPlugin()
    >>> porter = Porter(src="inbox", dest="organised", plugins=[counter])
    >>> porter.run()
    >>> print(counter.counts)
    {'md': 5, 'pdf': 3, 'no_extension': 1}
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.counts: Dict[str, int] = defaultdict(int)

    def on_start(self, porter: "Porter", **kwargs: Any) -> None:  # noqa: D102
        # Reset counts at the beginning of each run so the plugin is re-usable.
        self.counts.clear()

    def on_after_transport(self, result: "TransportResult", **kwargs: Any) -> None:  # noqa: D102
        if result.success:
            category = result.dest.parent.name
            self.counts[category] += 1
