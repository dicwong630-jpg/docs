"""
lobster_porter
==============

Lobster Porter — a lightweight document-organisation toolkit for the docs
knowledge base.  It provides:

* A **Strategy** protocol so that new transport behaviours (copy, move,
  sync, archive …) can be added without touching core logic.
* A **Plugin** protocol so that cross-cutting concerns (indexing, logging,
  tag-classification, statistics …) can be attached at runtime.
* A **Porter** orchestrator that wires strategies and plugins together
  around a stable, fixed entry-point.
* A **Config** dataclass that captures every tuneable parameter in one place.
* A **CLI** entry-point (``python -m lobster_porter``) for day-to-day use.

Typical usage
-------------
::

    from lobster_porter import Porter, Config
    from lobster_porter.strategies import CopyStrategy
    from lobster_porter.plugins import IndexPlugin

    porter = Porter(
        config=Config(source="docs/raw", destination="docs/organised"),
        strategy=CopyStrategy(),
        plugins=[IndexPlugin()],
    )
    porter.run()

Public API
----------
Only the symbols listed in ``__all__`` are considered stable.
"""

from lobster_porter.config import Config
from lobster_porter.core import Porter
from lobster_porter.plugins import BasePlugin, IndexPlugin, LogPlugin
from lobster_porter.strategies import BaseStrategy, CopyStrategy, MoveStrategy

__all__ = [
    # core
    "Config",
    "Porter",
    # strategies
    "BaseStrategy",
    "CopyStrategy",
    "MoveStrategy",
    # plugins
    "BasePlugin",
    "IndexPlugin",
    "LogPlugin",
]

__version__ = "0.1.0"
