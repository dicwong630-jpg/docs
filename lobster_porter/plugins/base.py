"""
lobster_porter.plugins.base
============================
定義插件基礎類別 :class:`PluginBase` 及全域插件登錄表 :data:`PLUGIN_REGISTRY`。

如何編寫插件
------------
1. 繼承 :class:`PluginBase`。
2. 設定唯一的 ``name`` 類別屬性（用於 CLI ``--strategy`` 參數）。
3. 實作 :meth:`classify` 方法（繼承自 :class:`~lobster_porter.strategies.StrategyBase`）。
4. 呼叫 ``MyPlugin.register()`` 將插件加入 :data:`PLUGIN_REGISTRY`。

範例
----
::

    from lobster_porter.plugins.base import PluginBase
    from lobster_porter.strategies import ClassificationResult
    from pathlib import Path

    class SizePlugin(PluginBase):
        name = "size"

        def classify(self, path: Path) -> ClassificationResult:
            size = path.stat().st_size
            category = "large" if size > 1_000_000 else "small"
            return ClassificationResult(src_path=path, category=category)

    SizePlugin.register()
"""

from __future__ import annotations

from typing import Dict, Type

from ..strategies import ClassificationResult, StrategyBase  # noqa: F401

# 全域插件登錄表：name -> PluginBase 子類別
PLUGIN_REGISTRY: Dict[str, Type["PluginBase"]] = {}


class PluginBase(StrategyBase):
    """插件基礎類別，繼承 :class:`~lobster_porter.strategies.StrategyBase`。

    提供 :meth:`register` 類方法以便將子類別加入全域
    :data:`PLUGIN_REGISTRY`。

    Attributes
    ----------
    name : str
        插件唯一識別名稱，子類別必須覆寫。
    """

    name: str = "plugin_base"

    @classmethod
    def register(cls) -> None:
        """將目前類別手動登錄至 :data:`PLUGIN_REGISTRY`。

        此方法需由開發者在定義完插件類別後手動呼叫，例如：

        .. code-block:: python

            class MyPlugin(PluginBase):
                name = "my_plugin"
                ...

            MyPlugin.register()  # 必須手動呼叫，否則不會出現在 PLUGIN_REGISTRY

        若 ``name`` 已存在則覆寫並發出警告。
        """
        if cls.name in PLUGIN_REGISTRY:
            import warnings
            warnings.warn(
                f"Plugin '{cls.name}' is already registered and will be overwritten.",
                UserWarning,
                stacklevel=2,
            )
        PLUGIN_REGISTRY[cls.name] = cls
