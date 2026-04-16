"""
lobster_porter.plugins — 插件子套件
=====================================

This sub-package contains the plugin system for Lobster Porter.

Public exports
--------------
``BasePlugin``
    Abstract base class every plugin must inherit from.

Lifecycle hooks (called by ``Porter._notify_plugins``)
-------------------------------------------------------
All hooks are optional.  Only implement the ones you need.

+------------------------+----------------------------------------------+
| Hook                   | When it is called                            |
+========================+==============================================+
| ``on_start``           | Before the porter begins discovery           |
+------------------------+----------------------------------------------+
| ``on_before_transport``| Before each individual file is transported  |
+------------------------+----------------------------------------------+
| ``on_after_transport`` | After each individual file transport         |
+------------------------+----------------------------------------------+
| ``on_finish``          | After *all* files have been processed        |
+------------------------+----------------------------------------------+
"""

from lobster_porter.plugins.base import BasePlugin  # noqa: F401

__all__ = ["BasePlugin"]
