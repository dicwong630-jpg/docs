"""
lobster_porter.plugins.rename_plugin
Auto-rename files with a configurable prefix or date stamp.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import BasePlugin


class RenamePrefixPlugin(BasePlugin):
    """Prefix destination file names with a fixed string."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def on_before_transfer(self, action: str, src: Path, dst: Path) -> Path:
        new_name = self.prefix + dst.name
        return dst.parent / new_name


class DateStampPlugin(BasePlugin):
    """Prepend YYYYMMDD_ to destination file names."""

    def on_before_transfer(self, action: str, src: Path, dst: Path) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d")
        return dst.parent / f"{stamp}_{dst.name}"
