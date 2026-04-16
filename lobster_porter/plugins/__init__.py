"""
lobster_porter.plugins
Base plugin interface and built-in plugins.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BasePlugin:
    """
    Lifecycle hooks called by :class:`~lobster_porter.core.LobsterPorter`.
    Override any method you need; others are no-ops.
    """

    def on_before_transfer(self, action: str, src: Path, dst: Path) -> Path | None:
        """Return a new dst Path to rename the destination, or None to keep it."""
        return None

    def on_after_transfer(self, action: str, src: Path, dst: Path, record) -> None:
        pass
