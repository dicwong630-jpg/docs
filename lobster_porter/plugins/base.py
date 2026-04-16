"""
plugins/base.py — 插件基礎抽象類別
定義所有龍蝦搬運工插件必須實作的介面。
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class BasePlugin(ABC):
    """
    龍蝦搬運工插件基類。

    插件可擴展批量搬運流程的前置（pre_process）或後置（post_process）邏輯，
    例如：格式轉換、自動標籤、雲端同步、通知發送等。
    """

    #: 插件名稱，用於日誌識別
    name: str = "unnamed_plugin"

    #: 插件版本
    version: str = "0.1.0"

    #: 插件描述
    description: str = ""

    def pre_process(self, files: List[str]) -> List[str]:
        """
        前置處理：在搬運操作開始前執行。

        Args:
            files: 即將被處理的檔案路徑列表。

        Returns:
            處理後（可能過濾或轉換）的檔案路徑列表。
        """
        return files

    def post_process(self, files: List[str], destination: str) -> None:
        """
        後置處理：在搬運操作完成後執行。

        Args:
            files:       已完成搬運的檔案路徑列表。
            destination: 搬運目標資料夾路徑。
        """

    def on_error(self, file: str, error: Exception) -> Optional[str]:
        """
        錯誤處理：當某個檔案的搬運操作失敗時呼叫。

        Args:
            file:  發生錯誤的檔案路徑。
            error: 發生的例外。

        Returns:
            可選的替代目標路徑；若為 None 則跳過該檔案。
        """
        return None

    def __repr__(self) -> str:
        return f"<Plugin name={self.name!r} version={self.version!r}>"
