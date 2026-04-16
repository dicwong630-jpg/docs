"""
lobster_porter.strategies
=========================
Pluggable file-placement strategies used by :class:`~lobster_porter.core.LobsterPorter`.

A strategy receives a list of source :class:`~pathlib.Path` objects and
returns a list of ``(source, destination)`` pairs.  Strategies never touch
the filesystem themselves — that is the responsibility of the core engine.

Built-in strategies
-------------------
- :class:`FlatStrategy`        — keep all files in one flat destination folder
- :class:`ByExtensionStrategy` — place files in sub-folders named by extension
- :class:`ByCategoryStrategy`  — place files in semantic sub-folders (docs, images, …)

Registry helpers
----------------
- :func:`get_strategy`   — look up a built-in strategy by name
- :func:`list_strategies` — return names of all registered strategies
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseStrategy(ABC):
    """Abstract base class for all placement strategies.

    Subclasses must implement :meth:`plan`.
    """

    #: Short snake-case name used for registration (e.g. ``"flat"``).
    name: ClassVar[str] = ""

    @abstractmethod
    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Compute ``(source, destination)`` pairs for each file.

        Parameters
        ----------
        files:
            List of absolute source file paths to be moved/copied.
        src_root:
            Root directory from which relative paths are computed.
        dst_root:
            Root of the destination tree.

        Returns
        -------
        list[tuple[Path, Path]]
            Ordered list of ``(source_path, destination_path)`` pairs.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Built-in strategy: flat
# ---------------------------------------------------------------------------


class FlatStrategy(BaseStrategy):
    """Place every file directly inside *dst_root*, discarding subdirectory structure.

    Example
    -------
    ::

        src_root/a/b/file.md  →  dst_root/file.md
        src_root/c/other.mdx  →  dst_root/other.mdx
    """

    name = "flat"

    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Return pairs mapping each file to ``dst_root/<filename>``."""
        return [(f, dst_root / f.name) for f in files]


# ---------------------------------------------------------------------------
# Built-in strategy: by_extension
# ---------------------------------------------------------------------------


class ByExtensionStrategy(BaseStrategy):
    """Organize files into sub-folders named after their file extension.

    Example
    -------
    ::

        src_root/guide.md   →  dst_root/md/guide.md
        src_root/schema.json →  dst_root/json/schema.json
        src_root/logo.svg   →  dst_root/svg/logo.svg

    Files without an extension are placed in ``dst_root/misc/``.
    """

    name = "by_extension"

    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Return pairs mapping each file to ``dst_root/<ext>/<filename>``."""
        pairs: list[tuple[Path, Path]] = []
        for f in files:
            ext_folder = f.suffix.lstrip(".") or "misc"
            pairs.append((f, dst_root / ext_folder / f.name))
        return pairs


# ---------------------------------------------------------------------------
# Built-in strategy: by_category
# ---------------------------------------------------------------------------

#: Mapping of file-extension sets to semantic category folder names.
_CATEGORY_MAP: dict[str, set[str]] = {
    "docs": {".md", ".mdx", ".rst", ".txt"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"},
    "data": {".json", ".yaml", ".yml", ".toml", ".csv", ".xml"},
    "scripts": {".py", ".js", ".ts", ".sh", ".bash"},
    "archives": {".zip", ".tar", ".gz", ".bz2"},
    "office": {".pdf", ".docx", ".doc", ".xlsx", ".pptx"},
}


class ByCategoryStrategy(BaseStrategy):
    """Organize files into semantic category sub-folders.

    Categories are resolved using :data:`_CATEGORY_MAP`.  Files that do not
    match any known category go into ``dst_root/misc/``.

    Example
    -------
    ::

        src_root/readme.md      →  dst_root/docs/readme.md
        src_root/logo.png       →  dst_root/images/logo.png
        src_root/config.yaml    →  dst_root/data/config.yaml

    Custom category mappings
    ------------------------
    Pass *category_map* to override the default mapping::

        strategy = ByCategoryStrategy(
            category_map={"notes": {".md", ".txt"}, "web": {".html", ".css"}}
        )
    """

    name = "by_category"

    def __init__(self, category_map: dict[str, set[str]] | None = None) -> None:
        self._map = category_map or _CATEGORY_MAP
        # Build reverse lookup: extension → category
        self._ext_to_category: dict[str, str] = {}
        for category, exts in self._map.items():
            for ext in exts:
                self._ext_to_category[ext] = category

    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Return pairs mapping each file to ``dst_root/<category>/<filename>``."""
        pairs: list[tuple[Path, Path]] = []
        for f in files:
            category = self._ext_to_category.get(f.suffix.lower(), "misc")
            pairs.append((f, dst_root / category / f.name))
        return pairs


# ---------------------------------------------------------------------------
# Built-in strategy: mirror (preserve relative paths)
# ---------------------------------------------------------------------------


class MirrorStrategy(BaseStrategy):
    """Reproduce the full directory tree from *src_root* under *dst_root*.

    Example
    -------
    ::

        src_root/a/b/file.md  →  dst_root/a/b/file.md
        src_root/c/other.mdx  →  dst_root/c/other.mdx
    """

    name = "mirror"

    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Return pairs that mirror the relative path under *dst_root*."""
        pairs: list[tuple[Path, Path]] = []
        for f in files:
            try:
                rel = f.relative_to(src_root)
            except ValueError:
                rel = Path(f.name)
            pairs.append((f, dst_root / rel))
        return pairs


# ---------------------------------------------------------------------------
# Built-in strategy: by_date (YYYY/MM sub-folders based on mtime)
# ---------------------------------------------------------------------------


class ByDateStrategy(BaseStrategy):
    """Organize files into ``YYYY/MM`` sub-folders based on modification time.

    Example
    -------
    ::

        src_root/old.md   (mtime 2024-03-15)  →  dst_root/2024/03/old.md
        src_root/new.mdx  (mtime 2025-01-02)  →  dst_root/2025/01/new.mdx
    """

    name = "by_date"

    def plan(
        self,
        files: list[Path],
        src_root: Path,
        dst_root: Path,
    ) -> list[tuple[Path, Path]]:
        """Return pairs placing each file under ``dst_root/YYYY/MM/``."""
        import datetime

        pairs: list[tuple[Path, Path]] = []
        for f in files:
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            sub = Path(str(mtime.year)) / f"{mtime.month:02d}"
            pairs.append((f, dst_root / sub / f.name))
        return pairs


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[BaseStrategy]] = {
    cls.name: cls  # type: ignore[misc]
    for cls in [FlatStrategy, ByExtensionStrategy, ByCategoryStrategy, MirrorStrategy, ByDateStrategy]
}


def get_strategy(name: str) -> BaseStrategy:
    """Return an instance of the named built-in strategy.

    Parameters
    ----------
    name:
        One of: ``"flat"``, ``"by_extension"``, ``"by_category"``,
        ``"mirror"``, ``"by_date"``.

    Raises
    ------
    ValueError
        If *name* is not found in the registry.
    """
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown strategy {name!r}. Available: {available}")
    return _REGISTRY[name]()


def list_strategies() -> list[str]:
    """Return the names of all registered built-in strategies.

    Returns
    -------
    list[str]
        Sorted list of strategy names.
    """
    return sorted(_REGISTRY)


def register_strategy(cls: type[BaseStrategy]) -> type[BaseStrategy]:
    """Register a custom strategy class in the global registry.

    Can be used as a class decorator::

        @register_strategy
        class MyStrategy(BaseStrategy):
            name = "my_strategy"
            ...

    Parameters
    ----------
    cls:
        A subclass of :class:`BaseStrategy` with a non-empty :attr:`name`.

    Returns
    -------
    type[BaseStrategy]
        The same class (unchanged), enabling decorator usage.
    """
    if not cls.name:
        raise ValueError("Strategy class must define a non-empty 'name' attribute.")
    _REGISTRY[cls.name] = cls
    return cls
