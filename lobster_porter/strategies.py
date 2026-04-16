"""
lobster_porter.strategies
Built-in classification strategies for routing files to category folders.
"""

from __future__ import annotations

from pathlib import Path


class BaseStrategy:
    """Override :meth:`classify` to return a folder name for *file_path*."""

    def classify(self, file_path: Path) -> str:
        raise NotImplementedError


class ExtensionStrategy(BaseStrategy):
    """Route files by extension using a user-supplied mapping."""

    DEFAULT_MAP: dict[str, str] = {
        # Scripts & documents
        ".fountain": "scripts",
        ".fdx": "scripts",
        ".txt": "scripts",
        ".md": "scripts",
        ".docx": "documents",
        ".doc": "documents",
        ".pdf": "documents",
        ".odt": "documents",
        # Storyboards & images
        ".psd": "storyboards",
        ".png": "images",
        ".jpg": "images",
        ".jpeg": "images",
        ".tif": "images",
        ".tiff": "images",
        ".webp": "images",
        # AI / prompt files
        ".json": "prompts",
        ".yaml": "prompts",
        ".yml": "prompts",
        # Audio
        ".wav": "audio",
        ".aif": "audio",
        ".aiff": "audio",
        ".mp3": "audio",
        ".flac": "audio",
        # Video / editorial
        ".mov": "video",
        ".mp4": "video",
        ".mxf": "video",
        ".r3d": "video",
        # 3D / VFX
        ".blend": "vfx",
        ".ma": "vfx",
        ".mb": "vfx",
        ".obj": "vfx",
        ".fbx": "vfx",
        ".usd": "vfx",
        ".usda": "vfx",
        ".usdc": "vfx",
    }

    def __init__(self, ext_map: dict[str, str] | None = None) -> None:
        self.ext_map = {**self.DEFAULT_MAP, **(ext_map or {})}

    def classify(self, file_path: Path) -> str:
        return self.ext_map.get(file_path.suffix.lower(), "misc")


class KeywordStrategy(BaseStrategy):
    """Route files whose names contain specific keywords."""

    def __init__(self, rules: list[tuple[str, str]]) -> None:
        # rules: [(keyword, category), ...] – first match wins
        self.rules = [(kw.lower(), cat) for kw, cat in rules]

    def classify(self, file_path: Path) -> str:
        name_lower = file_path.stem.lower()
        for keyword, category in self.rules:
            if keyword in name_lower:
                return category
        return "misc"


class DateStrategy(BaseStrategy):
    """Route files into year/month sub-folders based on mtime."""

    def classify(self, file_path: Path) -> str:
        mtime = file_path.stat().st_mtime
        from datetime import datetime

        dt = datetime.utcfromtimestamp(mtime)
        return f"{dt.year}/{dt.month:02d}"


class ChainStrategy(BaseStrategy):
    """Apply a list of strategies in order; first non-'misc' result wins."""

    def __init__(self, strategies: list[BaseStrategy]) -> None:
        self.strategies = strategies

    def classify(self, file_path: Path) -> str:
        for strategy in self.strategies:
            result = strategy.classify(file_path)
            if result != "misc":
                return result
        return "misc"
