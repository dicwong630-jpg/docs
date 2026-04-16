"""
lobster_porter.plugins
======================
可擴展插件子套件。

所有自訂插件應繼承 :class:`~lobster_porter.plugins.base.PluginBase`
並以 ``register`` 類方法向 :data:`PLUGIN_REGISTRY` 登錄。
"""

from .base import PluginBase, PLUGIN_REGISTRY  # noqa: F401

__all__ = ["PluginBase", "PLUGIN_REGISTRY"]
