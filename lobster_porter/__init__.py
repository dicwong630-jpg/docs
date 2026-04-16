"""
lobster_porter — 龍蝦搬運工
============================
批量檔案搬運、分類與標籤功能套件。

Modules
-------
core        : 批量移動/複製/分類核心邏輯與 CLI 入口
strategies  : 根據目錄、檔名、meta 決定分類的策略類別
plugins     : 可擴展的插件子套件
"""

from .core import batch_move, batch_copy, batch_classify  # noqa: F401

__version__ = "0.2.0"
__all__ = ["batch_move", "batch_copy", "batch_classify"]
