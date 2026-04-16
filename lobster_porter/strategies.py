"""
lobster_porter.strategies — 搬運策略與分類方法
================================================

Strategies decide **where** a file should go inside the destination root.
Each strategy exposes a single method::

    classify(file_path: Path) -> str

…which returns a *relative sub-path string* (e.g. ``"markdown"`` or
``"2024/reports"``).  The ``Porter`` appends this to the destination root
to form the final destination directory.

Built-in strategies
-------------------
``FlatStrategy``
    All files land in the destination root — no sub-directories.

``ExtensionStrategy``
    Groups files by lowercase file extension (e.g. ``.md`` → ``md/``).

``DateStrategy``
    Groups files by their last-modified date (``YYYY/MM``).

``SizeStrategy``
    Groups files by size bucket: ``small``, ``medium``, ``large``.

Implementing a custom strategy
-------------------------------
Subclass ``BaseStrategy`` and implement ``classify``::

    from lobster_porter.strategies import BaseStrategy
    from pathlib import Path

    class ProjectStrategy(BaseStrategy):
        def classify(self, file_path: Path) -> str:
            # Example: put files whose name starts with "KO" into "ko_files/"
            if file_path.stem.startswith("KO"):
                return "ko_files"
            return "other"

TODO
----
- Add a ``RegexStrategy`` that maps filename patterns to categories.
- Add a ``MLStrategy`` placeholder that calls an AI classifier.
- Allow strategies to be composed / chained.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class BaseStrategy(ABC):
    """Abstract base class for all transport/classification strategies.

    All concrete strategies **must** inherit from this class and implement
    the :meth:`classify` method.
    """

    @abstractmethod
    def classify(self, file_path: Path) -> str:
        """Return a relative sub-directory path for *file_path*.

        Parameters
        ----------
        file_path : Path
            The file to classify.

        Returns
        -------
        str
            A relative path string used as a sub-directory under the Porter's
            destination root.  Must not be an absolute path.
        """

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__}>"


class FlatStrategy(BaseStrategy):
    """Place every file directly in the destination root (no sub-directories).

    Useful when you just want to gather files from a nested tree into a
    single flat directory.

    Example
    -------
    >>> strategy = FlatStrategy()
    >>> strategy.classify(Path("deep/nested/report.md"))
    '.'
    """

    def classify(self, file_path: Path) -> str:  # noqa: D102
        return "."


class ExtensionStrategy(BaseStrategy):
    """Group files by their lowercase file extension.

    Files with no extension land in the ``"no_extension"`` bucket.

    Parameters
    ----------
    unknown_bucket : str
        Name of the bucket for files without an extension.
        Defaults to ``"no_extension"``.

    Example
    -------
    >>> strategy = ExtensionStrategy()
    >>> strategy.classify(Path("docs/intro.md"))
    'md'
    >>> strategy.classify(Path("Makefile"))
    'no_extension'
    """

    def __init__(self, unknown_bucket: str = "no_extension") -> None:
        self.unknown_bucket = unknown_bucket

    def classify(self, file_path: Path) -> str:  # noqa: D102
        suffix = file_path.suffix.lstrip(".").lower()
        return suffix if suffix else self.unknown_bucket


class DateStrategy(BaseStrategy):
    """Group files by last-modified date into ``YYYY/MM`` sub-directories.

    Example
    -------
    >>> import os, time
    >>> strategy = DateStrategy()
    >>> category = strategy.classify(Path("report.pdf"))
    >>> # e.g. '2024/03'
    """

    def classify(self, file_path: Path) -> str:  # noqa: D102
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime("%Y/%m")
        except OSError:
            # File may not exist yet in tests / dry-run scenarios.
            return "unknown_date"


class SizeStrategy(BaseStrategy):
    """Group files into size buckets: ``small``, ``medium``, or ``large``.

    Parameters
    ----------
    small_threshold : int
        Files smaller than this (bytes) are ``"small"``.  Default: 100 KB.
    large_threshold : int
        Files this size or larger are ``"large"``.  Default: 10 MB.

    Example
    -------
    >>> strategy = SizeStrategy()
    >>> strategy.classify(Path("tiny.txt"))  # assuming file < 100 KB
    'small'
    """

    def __init__(
        self,
        small_threshold: int = 100 * 1024,       # 100 KB
        large_threshold: int = 10 * 1024 * 1024, # 10 MB
    ) -> None:
        self.small_threshold = small_threshold
        self.large_threshold = large_threshold

    def classify(self, file_path: Path) -> str:  # noqa: D102
        try:
            size = file_path.stat().st_size
        except OSError:
            return "unknown_size"

        if size < self.small_threshold:
            return "small"
        if size < self.large_threshold:
            return "medium"
        return "large"


class CompositeStrategy(BaseStrategy):
    """Chain multiple strategies: the first strategy that returns a non-empty,
    non-``"."`` result wins.

    This lets you combine coarse and fine classification logic without
    writing a new strategy class from scratch.

    Parameters
    ----------
    strategies : list[BaseStrategy]
        Ordered list of strategies to try.

    Example
    -------
    >>> composite = CompositeStrategy([DateStrategy(), ExtensionStrategy()])
    >>> composite.classify(Path("report.pdf"))  # date wins if available
    '2024/03'

    TODO
    ----
    - Add a ``mode`` parameter (``"first_match"`` vs ``"join"``) so you can
      build paths like ``"2024/03/pdf"``.
    """

    def __init__(self, strategies: list[BaseStrategy]) -> None:
        if not strategies:
            raise ValueError("CompositeStrategy requires at least one strategy.")
        self.strategies = strategies

    def classify(self, file_path: Path) -> str:  # noqa: D102
        for strategy in self.strategies:
            result = strategy.classify(file_path)
            if result and result != ".":
                return result
        return "."
