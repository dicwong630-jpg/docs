"""
lobster_porter — 龍蝦搬運工
============================
A batch document-moving and organization utility for the docs repository.

The LobsterPorter package provides tools to bulk-move, copy, classify, and
index Markdown / MDX / PDF / Word files inside a documentation workspace.

Typical usage::

    from lobster_porter import LobsterPorter

    porter = LobsterPorter(root="/path/to/docs")
    porter.move("old_section/", "new_section/", strategy="by_category")

Public API
----------
- :class:`~lobster_porter.core.LobsterPorter`   — main entry-point class
- :func:`~lobster_porter.core.batch_move`        — convenience function
- :func:`~lobster_porter.core.batch_copy`        — convenience function
"""

__version__ = "0.1.0"
__author__ = "docs project"

from lobster_porter.core import LobsterPorter, batch_move, batch_copy  # noqa: F401

__all__ = [
    "LobsterPorter",
    "batch_move",
    "batch_copy",
]
