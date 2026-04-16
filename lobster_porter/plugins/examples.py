"""
lobster_porter.plugins.examples — 示範插件
============================================

提供立即可用的插件範例，展示 LobsterPorter 插件系統的能力。

插件清單
--------
``LoggingPlugin``
    記錄每次搬運操作的詳細資訊（使用 Python logging 模組）。

``SummaryPlugin``
    收集統計數據並在 on_finish 時輸出摘要報告。

``FileCounterPlugin``
    按副檔名統計已搬運的檔案數量。

``ErrorCollectorPlugin``
    收集所有失敗的操作，方便批量處理後檢查錯誤。

``ProgressBarPlugin``
    在終端機顯示進度百分比（不依賴外部套件）。

使用範例
--------
::

    from lobster_porter import Porter
    from lobster_porter.plugins.examples import (
        LoggingPlugin, SummaryPlugin, FileCounterPlugin
    )

    counter = FileCounterPlugin()
    porter = Porter(
        src="./inbox",
        dest="./organised",
        plugins=[LoggingPlugin(), SummaryPlugin(), counter],
    )
    porter.run()
    print(counter.counts)  # {'md': 5, 'pdf': 3, ...}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from lobster_porter.plugins.base import BasePlugin

if TYPE_CHECKING:
    from lobster_porter.core import Porter, TransportResult

logger = logging.getLogger(__name__)


class LoggingPlugin(BasePlugin):
    """使用 Python logging 記錄每次搬運操作的詳細資訊。

    Parameters
    ----------
    level : int
        日誌級別。預設為 ``logging.INFO``。

    Example
    -------
    ::

        porter = Porter(src="./in", dest="./out", plugins=[LoggingPlugin()])
        porter.run()
    """

    def __init__(self, level: int = logging.INFO) -> None:
        self.level = level

    def on_start(self, porter: "Porter") -> None:
        logger.log(self.level, "🦞 LobsterPorter 開始：%s → %s", porter.src, porter.dest)

    def on_after_transport(self, result: "TransportResult") -> None:
        if result.success:
            logger.log(self.level, "  ✅ %s → %s", result.src, result.dest)
        else:
            logger.warning("  ❌ 失敗：%s (%s)", result.src, result.error)

    def on_finish(self, porter: "Porter", results: "List[TransportResult]") -> None:
        successes = sum(r.success for r in results)
        logger.log(self.level, "🦞 完成：%d/%d 個檔案成功搬運", successes, len(results))


class SummaryPlugin(BasePlugin):
    """收集統計數據並在搬運完成時輸出摘要報告。

    Attributes
    ----------
    total : int
        處理的總檔案數。
    success_count : int
        成功搬運的檔案數。
    failure_count : int
        失敗的檔案數。

    Example
    -------
    ::

        summary = SummaryPlugin()
        porter = Porter(src="./in", dest="./out", plugins=[summary])
        porter.run()
        print(f"成功：{summary.success_count}, 失敗：{summary.failure_count}")
    """

    def __init__(self) -> None:
        self.total = 0
        self.success_count = 0
        self.failure_count = 0

    def on_after_transport(self, result: "TransportResult") -> None:
        self.total += 1
        if result.success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def on_finish(self, porter: "Porter", results: "List[TransportResult]") -> None:
        print("\n" + "=" * 50)
        print("🦞 龍蝦搬運工 — 操作摘要")
        print("=" * 50)
        print(f"  來源目錄：{porter.src}")
        print(f"  目標目錄：{porter.dest}")
        print(f"  模式：    {'複製' if porter.copy else '移動'}")
        print(f"  乾跑：    {'是' if porter.dry_run else '否'}")
        print(f"  總計：    {self.total} 個檔案")
        print(f"  成功：    {self.success_count} ✅")
        print(f"  失敗：    {self.failure_count} ❌")
        print("=" * 50)


class FileCounterPlugin(BasePlugin):
    """按副檔名統計已搬運的檔案數量。

    Attributes
    ----------
    counts : dict
        副檔名到數量的映射，例如 ``{'md': 5, 'pdf': 3, 'no_ext': 1}``。

    Example
    -------
    ::

        counter = FileCounterPlugin()
        Porter(src="./in", dest="./out", plugins=[counter]).run()
        print(counter.counts)  # {'md': 5, 'pdf': 3}
    """

    def __init__(self) -> None:
        self.counts: Dict[str, int] = defaultdict(int)

    def on_after_transport(self, result: "TransportResult") -> None:
        if result.success:
            ext = result.src.suffix.lstrip(".").lower() or "no_ext"
            self.counts[ext] += 1


class ErrorCollectorPlugin(BasePlugin):
    """收集所有失敗的搬運操作，方便批量完成後檢查錯誤。

    Attributes
    ----------
    errors : list[TransportResult]
        失敗的搬運操作列表。

    Example
    -------
    ::

        collector = ErrorCollectorPlugin()
        Porter(src="./in", dest="./out", plugins=[collector]).run()
        if collector.errors:
            for err in collector.errors:
                print(f"失敗：{err.src} — {err.error}")
    """

    def __init__(self) -> None:
        self.errors: List["TransportResult"] = []

    def on_after_transport(self, result: "TransportResult") -> None:
        if not result.success:
            self.errors.append(result)

    def on_finish(self, porter: "Porter", results: "List[TransportResult]") -> None:
        if self.errors:
            logger.warning("⚠️  共 %d 個檔案搬運失敗：", len(self.errors))
            for err in self.errors:
                logger.warning("   - %s: %s", err.src, err.error)


class ProgressBarPlugin(BasePlugin):
    """在終端機顯示進度百分比（不依賴外部套件）。

    Example
    -------
    ::

        Porter(src="./in", dest="./out", plugins=[ProgressBarPlugin()]).run()
        # [##########----------]  50%  (5/10)
    """

    def __init__(self, width: int = 40) -> None:
        self.width = width
        self._total = 0
        self._done = 0

    def on_start(self, porter: "Porter") -> None:
        # 預先計算總數（走訪一次目錄）
        try:
            from lobster_porter.operations import collect_files
            self._total = len(collect_files(str(porter.src)))
        except Exception:
            self._total = 0
        self._done = 0
        print()  # 換行

    def on_after_transport(self, result: "TransportResult") -> None:
        self._done += 1
        if self._total > 0:
            pct = self._done / self._total
        else:
            pct = 0.0
        filled = int(self.width * pct)
        bar = "#" * filled + "-" * (self.width - filled)
        print(f"\r  [{bar}] {pct:5.1%}  ({self._done}/{self._total})", end="", flush=True)

    def on_finish(self, porter: "Porter", results: "List[TransportResult]") -> None:
        print()  # 完成後換行
