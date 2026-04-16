"""
plugins/base.py — 插件基類
============================
所有龍蝦搬運工插件必須繼承 BasePlugin 並實作 run() 方法。

開發新插件範例
--------------
from lobster_porter.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    description = "做一些自訂搬運工作"

    def run(self, porter, **kwargs):
        # porter 是 LobsterPorter 實例
        # kwargs 是 CLI 或程式碼傳入的額外參數
        print("MyPlugin 正在運行！")
        return {"status": "ok"}
"""

from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    """
    插件基類。
    """

    # 插件唯一名稱（子類必須定義）
    name: str = "base_plugin"
    # 插件說明（顯示在 --list-plugins 輸出中）
    description: str = "（無說明）"

    @abstractmethod
    def run(self, porter: Any, **kwargs) -> Any:
        """
        執行插件邏輯。

        參數
        ----
        porter : LobsterPorter 實例，可呼叫其搜尋、搬運等方法
        **kwargs: 插件自訂參數

        回傳
        ----
        任意結果（字典、字串、列表等）
        """

    def __repr__(self) -> str:
        return f"<Plugin name={self.name!r} desc={self.description!r}>"
