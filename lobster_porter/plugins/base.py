"""
lobster_porter.plugins.base — 插件基礎抽象類別
===============================================

所有 LobsterPorter 插件都應繼承 ``BasePlugin``，並選擇性地覆寫
生命週期鉤子方法。

生命週期鉤子
------------
``on_start(porter)``
    Porter.run() 開始時觸發，在任何檔案處理之前。

``on_before_transport(file_path)``
    每個檔案被搬運之前觸發。

``on_after_transport(result)``
    每個檔案搬運完成後觸發（無論成功或失敗）。

``on_finish(porter, results)``
    Porter.run() 結束時觸發，在所有檔案處理之後。

實作範例
--------
::

    from lobster_porter.plugins.base import BasePlugin

    class MyPlugin(BasePlugin):
        def on_start(self, porter):
            print(f"開始搬運 {porter.src} → {porter.dest}")

        def on_after_transport(self, result):
            if not result.success:
                print(f"⚠️  搬運失敗：{result.src}")
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from lobster_porter.core import Porter, TransportResult


class BasePlugin(ABC):
    """LobsterPorter 插件的抽象基礎類別。

    繼承此類別並選擇性地覆寫生命週期方法。
    所有方法都有預設的空實作，因此插件只需要覆寫關心的鉤子。
    """

    def on_start(self, porter: "Porter") -> None:
        """Porter.run() 開始時觸發。

        Parameters
        ----------
        porter : Porter
            正在執行的 Porter 實例。
        """

    def on_before_transport(self, file_path: Path) -> None:
        """每個檔案被搬運之前觸發。

        Parameters
        ----------
        file_path : Path
            即將被搬運的來源檔案路徑。
        """

    def on_after_transport(self, result: "TransportResult") -> None:
        """每個檔案搬運完成後觸發。

        Parameters
        ----------
        result : TransportResult
            搬運操作的結果物件（含 src、dest、success、error）。
        """

    def on_finish(self, porter: "Porter", results: "List[TransportResult]") -> None:
        """Porter.run() 結束時觸發。

        Parameters
        ----------
        porter : Porter
            已完成執行的 Porter 實例。
        results : list[TransportResult]
            所有搬運操作的結果列表。
        """
