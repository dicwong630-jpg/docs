"""
龍蝦搬運工 (Lobster Porter)
=============================
一套專為大型專案（電影製作、知識管理、AI 資源整理）設計的批量檔案搬運與分類工具。

主要功能:
- 批量移動 / 複製 / 刪除檔案
- 自訂分類策略（基於格式、關鍵字、正則表達式）
- 插件式擴展架構
- 操作歷史記錄與撤銷（undo）系統
- 命令行介面（CLI）

版本: 0.9.0（1.0 版本開發中）
"""

from .core import LobsterPorter
from .strategies import ClassificationStrategy, FormatStrategy, KeywordStrategy
from .history import OperationHistory

__version__ = "0.9.0"
__all__ = [
    "LobsterPorter",
    "ClassificationStrategy",
    "FormatStrategy",
    "KeywordStrategy",
    "OperationHistory",
]
