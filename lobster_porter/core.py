"""
lobster_porter.core
===================

The :class:`Porter` class is the single, stable entry-point that
orchestrates a transport run.  It knows nothing about *how* files are
moved (that is the strategy's job) or *what side-effects* should happen
(that is the plugins' job).  This clean separation of concerns makes the
system straightforward to extend without risking regressions in existing
behaviour.

Architecture overview
---------------------
::

    ┌─────────────────────────────────────────────────────────────┐
    │  Porter.run()                                               │
    │                                                             │
    │  1. collect files matching config.file_patterns             │
    │  2. plugins[*].on_start(files, config)                      │
    │  3. for each file:                                          │
    │       a. ensure destination parent exists                   │
    │       b. strategy.execute(src, dst, config)                 │
    │       c. plugins[*].on_file(src, dst, config)               │
    │  4. plugins[*].on_finish(files, config)                     │
    └─────────────────────────────────────────────────────────────┘

The strategy and plugin lists are injected at construction time, so the
Porter itself never needs to change when new strategies or plugins are
added.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import List, Optional

from lobster_porter.config import Config
from lobster_porter.plugins import BasePlugin, LogPlugin
from lobster_porter.strategies import BaseStrategy, CopyStrategy


class Porter:
    """Orchestrate a document-transport run.

    Parameters
    ----------
    config:
        A :class:`~lobster_porter.config.Config` instance that describes
        the source, destination, and all tuneable parameters.
    strategy:
        The transport strategy to use.  Defaults to
        :class:`~lobster_porter.strategies.CopyStrategy`.
    plugins:
        Zero or more plugins to attach.  Defaults to
        ``[LogPlugin()]`` so that runs produce visible output by default.
        Pass an empty list to silence all output.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        strategy: Optional[BaseStrategy] = None,
        plugins: Optional[List[BasePlugin]] = None,
    ) -> None:
        self.config: Config = config or Config()
        self.strategy: BaseStrategy = strategy or CopyStrategy()
        self.plugins: List[BasePlugin] = plugins if plugins is not None else [LogPlugin()]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[Path]:
        """Execute the transport run.

        Returns
        -------
        list[Path]
            The list of source files that were (or would have been, in a
            dry run) processed.
        """
        files = self._collect_files()

        for plugin in self.plugins:
            plugin.on_start(files, self.config)

        for source_file in files:
            destination_file = self._destination_for(source_file)
            if not self.config.dry_run:
                destination_file.parent.mkdir(parents=True, exist_ok=True)
            self.strategy.execute(source_file, destination_file, self.config)
            for plugin in self.plugins:
                plugin.on_file(source_file, destination_file, self.config)

        for plugin in self.plugins:
            plugin.on_finish(files, self.config)

        return files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_files(self) -> List[Path]:
        """Return all files under *config.source* matching *config.file_patterns*."""
        source = Path(self.config.source)
        collected: List[Path] = []

        glob_method = source.rglob if self.config.recursive else source.glob
        # Collect all files first, then filter by pattern
        for path in glob_method("*"):
            if not path.is_file():
                continue
            if any(fnmatch.fnmatch(path.name, pat) for pat in self.config.file_patterns):
                collected.append(path)

        return sorted(collected)

    def _destination_for(self, source_file: Path) -> Path:
        """Compute the destination path for *source_file*.

        The relative path of *source_file* below *config.source* is
        mirrored under *config.destination*, preserving the directory
        structure.
        """
        relative = source_file.relative_to(self.config.source)
        return Path(self.config.destination) / relative
