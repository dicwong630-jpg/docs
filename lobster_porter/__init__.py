"""
lobster_porter（龍蝦搬運工）
A batch file transport, categorization, and tagging toolkit
designed to streamline film-production asset pipelines.
"""

from .core import LobsterPorter
from .strategies import (
    BaseStrategy,
    ExtensionStrategy,
    KeywordStrategy,
    DateStrategy,
)
from .plugins import BasePlugin

__version__ = "1.0.0"
__all__ = [
    "LobsterPorter",
    "BaseStrategy",
    "ExtensionStrategy",
    "KeywordStrategy",
    "DateStrategy",
    "BasePlugin",
]
