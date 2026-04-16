"""
lobster_porter.plugins
======================
Plugin sub-package for LobsterPorter.

Plugins let you hook into file operations (move, copy, index) to add custom
behaviour such as logging, tagging, notification, or post-processing.

Usage
-----
Import :class:`~lobster_porter.plugins.base.BasePlugin` to create your own
plugin, or use one of the ready-made examples in
:mod:`lobster_porter.plugins.examples`::

    from lobster_porter import LobsterPorter
    from lobster_porter.plugins.examples import LoggingPlugin

    porter = LobsterPorter(root=".")
    porter.register_plugin(LoggingPlugin())
    porter.move("old/", "new/")

Public API
----------
- :class:`~lobster_porter.plugins.base.BasePlugin`
- :class:`~lobster_porter.plugins.examples.LoggingPlugin`
- :class:`~lobster_porter.plugins.examples.TaggingPlugin`
- :class:`~lobster_porter.plugins.examples.StatisticsPlugin`
"""

from lobster_porter.plugins.base import BasePlugin  # noqa: F401
from lobster_porter.plugins.examples import (  # noqa: F401
    LoggingPlugin,
    StatisticsPlugin,
    TaggingPlugin,
)

__all__ = [
    "BasePlugin",
    "LoggingPlugin",
    "TaggingPlugin",
    "StatisticsPlugin",
]
