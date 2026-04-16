"""
lobster_porter.plugins — 插件子套件
=====================================

提供 LobsterPorter 插件系統的公開 API。
"""

from lobster_porter.plugins.base import BasePlugin
from lobster_porter.plugins.examples import (
    ErrorCollectorPlugin,
    FileCounterPlugin,
    LoggingPlugin,
    ProgressBarPlugin,
    SummaryPlugin,
)

__all__ = [
    "BasePlugin",
    "LoggingPlugin",
    "SummaryPlugin",
    "FileCounterPlugin",
    "ErrorCollectorPlugin",
    "ProgressBarPlugin",
]
