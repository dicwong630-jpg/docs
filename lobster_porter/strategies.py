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

``RegexStrategy``
    Maps filename patterns (regex) to named categories.

``UserRuleStrategy``
    Reads classification rules from a YAML/JSON config file at runtime,
    allowing users to define their own rules without writing Python code.

``CompositeStrategy``
    Chains multiple strategies; the first non-trivial result wins.

Implementing a custom strategy
-------------------------------
Subclass ``BaseStrategy`` and implement ``classify``::

    from lobster_porter.strategies import BaseStrategy
    from pathlib import Path

    class ProjectStrategy(BaseStrategy):
        def classify(self, file_path: Path) -> str:
            if file_path.stem.startswith("KO"):
                return "ko_files"
            return "other"
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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

    Supported formats include: txt, md, pdf, docx, xlsx, pptx, csv, json,
    yaml, py, js, html, css, jpg, png, gif, mp4, mp3, zip, tar, and more.

    Example
    -------
    >>> strategy = ExtensionStrategy()
    >>> strategy.classify(Path("docs/intro.md"))
    'md'
    >>> strategy.classify(Path("report.docx"))
    'docx'
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
        small_threshold: int = 100 * 1024,
        large_threshold: int = 10 * 1024 * 1024,
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


class RegexStrategy(BaseStrategy):
    """Map filename patterns (regular expressions) to named categories.

    Rules are evaluated in order; the first matching rule wins.  If no rule
    matches, ``default_bucket`` is returned.

    Parameters
    ----------
    rules : list of (pattern, category) tuples
        Each ``pattern`` is a regex string matched against the file's full name
        (including extension).  ``category`` is the destination sub-directory.
    default_bucket : str
        Returned when no rule matches.  Defaults to ``"other"``.
    flags : int
        ``re`` flags applied to every compiled pattern (default: ``re.IGNORECASE``).

    Example
    -------
    >>> rules = [
    ...     (r"^report_\\d{4}", "reports"),
    ...     (r"\\.pdf$",        "pdf_docs"),
    ...     (r"\\.docx?$",      "word_docs"),
    ... ]
    >>> strategy = RegexStrategy(rules)
    >>> strategy.classify(Path("report_2024_q1.pdf"))
    'reports'
    >>> strategy.classify(Path("invoice.pdf"))
    'pdf_docs'
    >>> strategy.classify(Path("unknown.bin"))
    'other'
    """

    def __init__(
        self,
        rules: List[Tuple[str, str]],
        default_bucket: str = "other",
        flags: int = re.IGNORECASE,
    ) -> None:
        self.default_bucket = default_bucket
        self._compiled: List[Tuple[re.Pattern, str]] = [
            (re.compile(pattern, flags), category) for pattern, category in rules
        ]

    def classify(self, file_path: Path) -> str:  # noqa: D102
        name = file_path.name
        for pattern, category in self._compiled:
            if pattern.search(name):
                return category
        return self.default_bucket


class UserRuleStrategy(BaseStrategy):
    """Load classification rules from a JSON config file at runtime.

    This lets users define their own rules without writing Python code.
    The config file must be a JSON object with an ``"rules"`` list::

        {
            "default": "other",
            "rules": [
                {"pattern": "\\\\.pdf$",   "category": "pdf_docs"},
                {"pattern": "\\\\.docx?$", "category": "word_docs"},
                {"pattern": "^invoice_",   "category": "invoices"}
            ]
        }

    Parameters
    ----------
    config_path : str | Path
        Path to the JSON rules config file.
    flags : int
        ``re`` flags for all patterns (default: ``re.IGNORECASE``).

    Example
    -------
    >>> strategy = UserRuleStrategy("/home/user/.lobster_rules.json")
    >>> strategy.classify(Path("invoice_2024.pdf"))
    'invoices'
    """

    def __init__(
        self,
        config_path: "str | Path",
        flags: int = re.IGNORECASE,
    ) -> None:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Rules config not found: {config_path}")

        with open(config_path, encoding="utf-8") as fh:
            config: Dict = json.load(fh)

        default = config.get("default", "other")
        raw_rules: List[Dict] = config.get("rules", [])
        pairs: List[Tuple[str, str]] = [
            (r["pattern"], r["category"]) for r in raw_rules
        ]
        self._inner = RegexStrategy(pairs, default_bucket=default, flags=flags)

    def classify(self, file_path: Path) -> str:  # noqa: D102
        return self._inner.classify(file_path)


class TypeGroupStrategy(BaseStrategy):
    """Group files into broad type categories (documents, images, audio, video, code, archives, other).

    This provides a human-friendly high-level grouping that works out of the
    box without any configuration.

    Example
    -------
    >>> strategy = TypeGroupStrategy()
    >>> strategy.classify(Path("report.pdf"))
    'documents'
    >>> strategy.classify(Path("photo.jpg"))
    'images'
    >>> strategy.classify(Path("archive.zip"))
    'archives'
    """

    _TYPE_MAP: Dict[str, str] = {
        # Documents
        "pdf": "documents", "doc": "documents", "docx": "documents",
        "xls": "documents", "xlsx": "documents", "ppt": "documents",
        "pptx": "documents", "odt": "documents", "ods": "documents",
        "odp": "documents", "txt": "documents", "rtf": "documents",
        "md": "documents", "rst": "documents", "csv": "documents",
        # Images
        "jpg": "images", "jpeg": "images", "png": "images", "gif": "images",
        "bmp": "images", "tiff": "images", "tif": "images", "svg": "images",
        "webp": "images", "ico": "images", "heic": "images",
        # Audio
        "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio",
        "ogg": "audio", "m4a": "audio", "wma": "audio",
        # Video
        "mp4": "video", "mkv": "video", "avi": "video", "mov": "video",
        "wmv": "video", "flv": "video", "webm": "video",
        # Code
        "py": "code", "js": "code", "ts": "code", "java": "code",
        "c": "code", "cpp": "code", "h": "code", "hpp": "code",
        "go": "code", "rs": "code", "rb": "code", "php": "code",
        "cs": "code", "swift": "code", "kt": "code", "sh": "code",
        "bash": "code", "ps1": "code", "html": "code", "css": "code",
        "json": "code", "yaml": "code", "yml": "code", "toml": "code",
        "xml": "code", "sql": "code",
        # Archives
        "zip": "archives", "tar": "archives", "gz": "archives",
        "bz2": "archives", "xz": "archives", "7z": "archives",
        "rar": "archives", "tgz": "archives",
    }

    def __init__(self, unknown_bucket: str = "other") -> None:
        self.unknown_bucket = unknown_bucket

    def classify(self, file_path: Path) -> str:  # noqa: D102
        ext = file_path.suffix.lstrip(".").lower()
        return self._TYPE_MAP.get(ext, self.unknown_bucket)


class CompositeStrategy(BaseStrategy):
    """Chain multiple strategies: the first strategy that returns a non-empty,
    non-``"."`` result wins.

    Parameters
    ----------
    strategies : list[BaseStrategy]
        Ordered list of strategies to try.
    join : bool
        When ``True``, concatenate all results with ``"/"`` instead of
        returning the first match.  Useful to build paths like
        ``"2024/03/pdf"``.  Defaults to ``False`` (first-match).

    Example
    -------
    >>> composite = CompositeStrategy([DateStrategy(), ExtensionStrategy()])
    >>> composite.classify(Path("report.pdf"))  # date wins if available
    '2024/03'
    """

    def __init__(
        self,
        strategies: List[BaseStrategy],
        join: bool = False,
    ) -> None:
        if not strategies:
            raise ValueError("CompositeStrategy requires at least one strategy.")
        self.strategies = strategies
        self.join = join

    def classify(self, file_path: Path) -> str:  # noqa: D102
        results = []
        for strategy in self.strategies:
            result = strategy.classify(file_path)
            if result and result != ".":
                if self.join:
                    results.append(result)
                else:
                    return result
        if self.join and results:
            return "/".join(results)
        return "."
