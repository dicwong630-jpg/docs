"""
lobster_porter.strategies
=========================

Transport strategy interface and built-in implementations.

Extension guide
---------------
To add a new transport strategy:

1. Create a class that inherits from :class:`BaseStrategy`.
2. Override :meth:`BaseStrategy.execute` with your logic.
3. Pass an instance of your class to :class:`~lobster_porter.core.Porter`.

Example::

    from lobster_porter.strategies import BaseStrategy
    from lobster_porter.config import Config

    class ArchiveStrategy(BaseStrategy):
        \"\"\"Compress source files into a ZIP archive.\"\"\"

        name = "archive"

        def execute(self, source_file, destination_file, config):
            # ... zip logic here ...
            pass

No changes to core are required — the Porter calls ``strategy.execute``
through the stable :class:`BaseStrategy` interface.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from lobster_porter.config import Config


class BaseStrategy(ABC):
    """Abstract base class for all transport strategies.

    Every concrete strategy **must** implement :meth:`execute`.

    Attributes
    ----------
    name:
        A short, human-readable identifier used in log messages and CLI
        output.  Override this in subclasses.
    """

    name: str = "base"

    @abstractmethod
    def execute(
        self,
        source_file: Path,
        destination_file: Path,
        config: Config,
    ) -> None:
        """Transport *source_file* to *destination_file*.

        Parameters
        ----------
        source_file:
            Absolute path to the file that should be transported.
        destination_file:
            Absolute path to the desired output location (parent directory
            is guaranteed to exist before this method is called).
        config:
            The active :class:`~lobster_porter.config.Config` instance.
            Strategies may read ``config.dry_run``, ``config.overwrite``,
            and ``config.extra`` as needed.
        """


class CopyStrategy(BaseStrategy):
    """Copy files from source to destination, preserving the originals."""

    name = "copy"

    def execute(
        self,
        source_file: Path,
        destination_file: Path,
        config: Config,
    ) -> None:
        if config.dry_run:
            return
        if destination_file.exists() and not config.overwrite:
            raise FileExistsError(
                f"Destination already exists: {destination_file}"
            )
        shutil.copy2(source_file, destination_file)


class MoveStrategy(BaseStrategy):
    """Move files from source to destination, removing the originals."""

    name = "move"

    def execute(
        self,
        source_file: Path,
        destination_file: Path,
        config: Config,
    ) -> None:
        if config.dry_run:
            return
        if destination_file.exists() and not config.overwrite:
            raise FileExistsError(
                f"Destination already exists: {destination_file}"
            )
        shutil.move(source_file, destination_file)
