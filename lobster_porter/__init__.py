"""
lobster_porter
==============

龍蝦搬運工 (Lobster Porter) — 批量檔案移動及複製工具套件。

Provides:
    - LobsterPorter: 核心批量操作類別
    - OperationLog:  單次操作日誌紀錄
    - collect_files: 遞迴收集檔案工具函式
    - main:          CLI 入口

Typical usage::

    from lobster_porter.core import LobsterPorter, collect_files

    porter = LobsterPorter()
    porter.batch_copy(["/src/a.txt", "/src/b/"], "/dst/", base_src="/src/")
    porter.print_logs()
"""

from lobster_porter.core import LobsterPorter, OperationLog, collect_files, main

__version__ = "0.1.0"
__all__ = ["LobsterPorter", "OperationLog", "collect_files", "main"]
