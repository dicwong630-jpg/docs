"""
plugins/__init__.py — 插件子包
"""

from .base import BasePlugin  # noqa: F401
from .examples import (  # noqa: F401
    IndexGeneratorPlugin,
    TagExporterPlugin,
    BulkRenamePlugin,
    FormatScannerPlugin,
)

__all__ = [
    "BasePlugin",
    "IndexGeneratorPlugin",
    "TagExporterPlugin",
    "BulkRenamePlugin",
    "FormatScannerPlugin",
]
