"""
lobster_porter — 龍蝦搬運工 公開 API
======================================

龍蝦搬運工 (Lobster Porter) 1.0 — 批量檔案搬運、分類、刪除與重命名工具套件。

公開匯出
--------
核心類別：
    Porter          — 基於策略的目錄分類搬運器（來自 core）
    LobsterPorter   — 批量操作器：copy/move/delete/rename/undo/export（來自 operations）

資料類別：
    TransportResult — 單次搬運操作結果（來自 core）
    OperationLog    — 單次操作日誌記錄（來自 operations）

工具函式：
    collect_files   — 遞迴收集目錄下符合 glob 模式的檔案

典型用法
--------
使用策略分類搬運整個目錄::

    from lobster_porter import Porter
    from lobster_porter.strategies import ExtensionStrategy

    porter = Porter(
        src="./inbox",
        dest="./organised",
        strategy=ExtensionStrategy(),
        copy=True,
    )
    results = porter.run()
    print(f"搬運 {sum(r.success for r in results)} 個檔案")

批量操作（含 undo）::

    from lobster_porter import LobsterPorter

    porter = LobsterPorter()
    porter.batch_move(["/src/a.txt", "/src/b.txt"], "/dst/", base_src="/src/")
    porter.print_logs()
    porter.undo()  # 撤銷所有移動

使用插件::

    from lobster_porter import Porter
    from lobster_porter.plugins import LoggingPlugin, SummaryPlugin, FileCounterPlugin

    counter = FileCounterPlugin()
    porter = Porter(
        src="./inbox",
        dest="./organised",
        plugins=[LoggingPlugin(), SummaryPlugin(), counter],
    )
    porter.run()
    print(counter.counts)
"""

from lobster_porter.core import Porter, TransportResult
from lobster_porter.operations import LobsterPorter, OperationLog, collect_files

__version__ = "1.0.0"

__all__ = [
    "Porter",
    "TransportResult",
    "LobsterPorter",
    "OperationLog",
    "collect_files",
    "__version__",
]
