"""
plugins/__init__.py — 插件系統初始化
"""

from .base import BasePlugin
from .format_classifier import FormatClassifierPlugin

__all__ = ["BasePlugin", "FormatClassifierPlugin"]
