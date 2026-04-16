"""
lobster_porter.operations — 批量操作、操作日誌與撤銷支援
==========================================================

提供 LobsterPorter 類別，負責：

- 批量複製（batch_copy）
- 批量移動（batch_move）
- 批量刪除（batch_delete）
- 批量重命名（batch_rename）
- 操作日誌（OperationLog）自動記錄
- 撤銷（undo）：可撤銷所有成功的 move/rename 操作
- dry_run 模式：模擬操作而不實際修改任何檔案
- 日誌匯出（export_log）：將操作記錄儲存至 JSON/CSV

CLI 使用範例（透過 cli.py）::

    python -m lobster_porter copy /src/docs /src/images --dest /tmp/backup --base /src/
    python -m lobster_porter move /src/docs --dest /tmp/archive --base /src/
    python -m lobster_porter delete /tmp/archive/old*.txt --dry-run
    python -m lobster_porter rename /src/ --pattern "(.*)\\.txt" --replacement "\\1_bak.txt"
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OperationLog — 單次操作記錄
# ---------------------------------------------------------------------------


@dataclass
class OperationLog:
    """記錄單次檔案操作，用於審計與撤銷。

    Attributes:
        action (str):     操作類型，'copy'、'move'、'delete'、'rename'、'undo_move'、'undo_rename'。
        src (str):        來源路徑（刪除時即為被刪除路徑）。
        dst (str):        目標路徑（刪除時為空字串）。
        timestamp (str):  操作發生時間（ISO-8601 格式）。
        success (bool):   操作是否成功。
        error (str):      失敗時的錯誤訊息；成功時為空字串。
    """

    action: str
    src: str
    dst: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True
    error: str = ""

    def __str__(self) -> str:
        status = "OK" if self.success else f"FAIL({self.error})"
        return f"[{self.action.upper()}] {self.src} -> {self.dst} [{status}] @ {self.timestamp}"


# ---------------------------------------------------------------------------
# LobsterPorter — 主要批量操作類別
# ---------------------------------------------------------------------------


class LobsterPorter:
    """龍蝦搬運工：批量檔案移動、複製、刪除及重命名工具。

    支援功能：
        - 批量複製（batch_copy）
        - 批量移動（batch_move）
        - 批量刪除（batch_delete）
        - 批量重命名（batch_rename）
        - 操作日誌自動收集
        - 撤銷（undo）所有成功的 move 與 rename 操作
        - dry_run 模式：不實際修改任何檔案
        - 日誌匯出為 JSON 或 CSV 檔案

    Example::

        porter = LobsterPorter()
        porter.batch_copy(
            sources=["/data/src/a.txt", "/data/src/sub/b.txt"],
            dest_dir="/data/dst/",
            base_src="/data/src/",
        )
        porter.print_logs()
        porter.undo()  # 撤銷所有可撤銷操作（move/rename）
    """

    def __init__(self, dry_run: bool = False) -> None:
        """初始化 LobsterPorter。

        Args:
            dry_run (bool): 若為 True，所有操作只記錄日誌而不實際修改檔案。
        """
        self.dry_run = dry_run
        self._logs: List[OperationLog] = []

    # ------------------------------------------------------------------
    # 公開屬性
    # ------------------------------------------------------------------

    @property
    def logs(self) -> List[OperationLog]:
        """返回所有操作日誌的副本列表。"""
        return list(self._logs)

    # ------------------------------------------------------------------
    # 內部輔助方法
    # ------------------------------------------------------------------

    def _compute_dest(self, src: str, base_src: str, dest_dir: str) -> str:
        """計算目標路徑，保留相對於 base_src 的層級結構。

        Args:
            src (str):      來源路徑。
            base_src (str): 來源根目錄。
            dest_dir (str): 目標根目錄。

        Returns:
            str: 計算後的目標完整路徑。
        """
        src_path = Path(src).resolve()
        base_path = Path(base_src).resolve()
        dest_path = Path(dest_dir).resolve()
        try:
            rel = src_path.relative_to(base_path)
            return str(dest_path / rel)
        except ValueError:
            return str(dest_path / src_path.name)

    def _do_copy(self, src: str, dst: str) -> OperationLog:
        """複製單一檔案或目錄至指定目標路徑。"""
        log = OperationLog(action="copy", src=src, dst=dst)
        try:
            if not self.dry_run:
                dst_path = Path(dst)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                if Path(src).is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            logger.info("[COPY] %s -> %s", src, dst)
        except (OSError, shutil.Error) as exc:
            log.success = False
            log.error = str(exc)
            logger.error("[COPY FAILED] %s -> %s : %s", src, dst, exc)
        return log

    def _do_move(self, src: str, dst: str) -> OperationLog:
        """移動單一檔案或目錄至指定目標路徑。"""
        log = OperationLog(action="move", src=src, dst=dst)
        try:
            if not self.dry_run:
                dst_path = Path(dst)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(src, dst)
            logger.info("[MOVE] %s -> %s", src, dst)
        except (OSError, shutil.Error) as exc:
            log.success = False
            log.error = str(exc)
            logger.error("[MOVE FAILED] %s -> %s : %s", src, dst, exc)
        return log

    def _do_delete(self, src: str) -> OperationLog:
        """刪除單一檔案或目錄。

        注意：刪除操作無法透過 undo() 還原。
        """
        log = OperationLog(action="delete", src=src, dst="")
        try:
            if not self.dry_run:
                p = Path(src)
                if p.is_dir():
                    shutil.rmtree(src)
                else:
                    p.unlink()
            logger.info("[DELETE] %s", src)
        except OSError as exc:
            log.success = False
            log.error = str(exc)
            logger.error("[DELETE FAILED] %s : %s", src, exc)
        return log

    def _do_rename(self, src: str, dst: str) -> OperationLog:
        """重命名（原地重命名）單一檔案或目錄。

        僅重命名檔名，不移動到其他目錄。
        """
        log = OperationLog(action="rename", src=src, dst=dst)
        try:
            if not self.dry_run:
                Path(src).rename(dst)
            logger.info("[RENAME] %s -> %s", src, dst)
        except OSError as exc:
            log.success = False
            log.error = str(exc)
            logger.error("[RENAME FAILED] %s -> %s : %s", src, dst, exc)
        return log

    # ------------------------------------------------------------------
    # 批量操作公開方法
    # ------------------------------------------------------------------

    def batch_copy(
        self,
        sources: List[str],
        dest_dir: str,
        base_src: Optional[str] = None,
        on_progress: Optional[Callable[[OperationLog], None]] = None,
    ) -> List[OperationLog]:
        """批量複製檔案/目錄到 dest_dir，自動保留層級結構。

        Args:
            sources (List[str]):   來源檔案或目錄路徑列表。
            dest_dir (str):        目標根目錄路徑；不存在時將自動建立。
            base_src (Optional[str]): 用於計算相對路徑的來源根目錄。
            on_progress (Optional[Callable]): 每完成一個操作後呼叫的回調函式。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。
        """
        base = base_src if base_src else (str(Path(sources[0]).parent) if sources else dest_dir)
        logs: List[OperationLog] = []
        for src in sources:
            dst = self._compute_dest(src, base, dest_dir)
            log = self._do_copy(src, dst)
            self._logs.append(log)
            logs.append(log)
            if on_progress:
                on_progress(log)
        return logs

    def batch_move(
        self,
        sources: List[str],
        dest_dir: str,
        base_src: Optional[str] = None,
        on_progress: Optional[Callable[[OperationLog], None]] = None,
    ) -> List[OperationLog]:
        """批量移動檔案/目錄到 dest_dir，自動保留層級結構。

        移動後來源路徑的檔案將不再存在。
        所有成功的 move 操作均可透過 undo() 撤銷。

        Args:
            sources (List[str]):   來源檔案或目錄路徑列表。
            dest_dir (str):        目標根目錄路徑；不存在時將自動建立。
            base_src (Optional[str]): 用於計算相對路徑的來源根目錄。
            on_progress (Optional[Callable]): 每完成一個操作後呼叫的回調函式。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。
        """
        base = base_src if base_src else (str(Path(sources[0]).parent) if sources else dest_dir)
        logs: List[OperationLog] = []
        for src in sources:
            dst = self._compute_dest(src, base, dest_dir)
            log = self._do_move(src, dst)
            self._logs.append(log)
            logs.append(log)
            if on_progress:
                on_progress(log)
        return logs

    def batch_delete(
        self,
        sources: List[str],
        on_progress: Optional[Callable[[OperationLog], None]] = None,
    ) -> List[OperationLog]:
        """批量刪除檔案或目錄。

        注意：刪除操作不可透過 undo() 還原。在非 dry_run 模式下請謹慎使用。

        Args:
            sources (List[str]):   要刪除的檔案或目錄路徑列表。
            on_progress (Optional[Callable]): 每完成一個操作後呼叫的回調函式。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。

        Example::

            porter = LobsterPorter(dry_run=True)  # 建議先用 dry_run 預覽
            porter.batch_delete(["/tmp/old_files/a.txt", "/tmp/old_files/b.txt"])
        """
        logs: List[OperationLog] = []
        for src in sources:
            log = self._do_delete(src)
            self._logs.append(log)
            logs.append(log)
            if on_progress:
                on_progress(log)
        return logs

    def batch_rename(
        self,
        sources: List[str],
        pattern: str,
        replacement: str,
        flags: int = re.IGNORECASE,
        on_progress: Optional[Callable[[OperationLog], None]] = None,
    ) -> List[OperationLog]:
        """批量重命名檔案，使用正規表達式模式替換。

        對每個來源路徑，使用 ``re.sub(pattern, replacement, filename)``
        計算新的檔名，並在原目錄中執行重命名。

        所有成功的 rename 操作均可透過 undo() 撤銷。

        Args:
            sources (List[str]):  要重命名的檔案路徑列表。
            pattern (str):        正規表達式模式（匹配對象為檔名，不含路徑）。
            replacement (str):    替換字串（支援反向參照，如 ``\\1``）。
            flags (int):          正規表達式旗標，預設為 ``re.IGNORECASE``。
            on_progress (Optional[Callable]): 每完成一個操作後呼叫的回調函式。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。

        Example::

            porter = LobsterPorter()
            porter.batch_rename(
                sources=["/docs/report_2023.txt", "/docs/report_2024.txt"],
                pattern=r"report_(\\d+)\\.txt",
                replacement=r"annual_report_\\1.txt",
            )
            # /docs/report_2023.txt -> /docs/annual_report_2023.txt
        """
        compiled = re.compile(pattern, flags)
        logs: List[OperationLog] = []
        for src in sources:
            src_path = Path(src)
            new_name = compiled.sub(replacement, src_path.name)
            dst = str(src_path.parent / new_name)
            if dst == src:
                # 沒有變化，跳過
                continue
            log = self._do_rename(src, dst)
            log.action = "rename"
            self._logs.append(log)
            logs.append(log)
            if on_progress:
                on_progress(log)
        return logs

    # ------------------------------------------------------------------
    # 撤銷介面
    # ------------------------------------------------------------------

    def undo(self) -> List[OperationLog]:
        """撤銷所有成功的 move 與 rename 操作（以逆序執行）。

        注意：copy 和 delete 操作無法撤銷。
        撤銷結果同樣記錄於日誌中（action 標記為 'undo_move' 或 'undo_rename'）。

        Returns:
            List[OperationLog]: 撤銷操作的日誌列表。

        Example::

            porter.batch_move(["/src/a.txt"], "/dst/", base_src="/src/")
            porter.undo()  # 將 /dst/a.txt 移回 /src/a.txt
        """
        undo_logs: List[OperationLog] = []
        for log in reversed(self._logs):
            if log.action in ("move", "rename") and log.success:
                undo_log = self._do_move(log.dst, log.src)
                undo_log.action = f"undo_{log.action}"
                self._logs.append(undo_log)
                undo_logs.append(undo_log)
        return undo_logs

    def clear_logs(self) -> None:
        """清除所有操作日誌記錄。"""
        self._logs.clear()

    # ------------------------------------------------------------------
    # 日誌輸出與匯出
    # ------------------------------------------------------------------

    def print_logs(self) -> None:
        """將所有操作日誌以表格形式輸出至 stdout。"""
        header = f"{'ACTION':<14} {'STATUS':<12} {'SRC':<40} {'DST':<40} TIMESTAMP"
        print(header)
        print("-" * len(header))
        for log in self._logs:
            status = "OK" if log.success else f"FAIL: {log.error[:20]}"
            print(
                f"{log.action:<14} {status:<12} "
                f"{str(log.src):<40} {str(log.dst):<40} {log.timestamp}"
            )

    def export_log(self, path: str, fmt: str = "json") -> None:
        """將操作日誌匯出至檔案。

        Args:
            path (str): 輸出檔案路徑。
            fmt (str):  輸出格式，支援 ``"json"`` 和 ``"csv"``。預設為 ``"json"``。

        Raises:
            ValueError: 若 fmt 不是 'json' 或 'csv'。

        Example::

            porter.export_log("/var/log/lobster_porter.json")
            porter.export_log("/var/log/lobster_porter.csv", fmt="csv")
        """
        if fmt == "json":
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([asdict(log) for log in self._logs], fh, ensure_ascii=False, indent=2)
        elif fmt == "csv":
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(
                    fh, fieldnames=["action", "src", "dst", "timestamp", "success", "error"]
                )
                writer.writeheader()
                writer.writerows(asdict(log) for log in self._logs)
        else:
            raise ValueError(f"Unsupported log format: {fmt!r}. Use 'json' or 'csv'.")


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------


def collect_files(directory: str, pattern: str = "**/*") -> List[str]:
    """遞迴收集目錄下所有符合 glob pattern 的檔案路徑。

    Args:
        directory (str):  要搜尋的根目錄。
        pattern (str):    Glob 模式（預設 ``'**/*'`` 匹配所有檔案）。

    Returns:
        List[str]: 符合條件的檔案完整路徑列表（排除目錄）。

    Example::

        md_files = collect_files("/docs/", pattern="**/*.md")
        pdf_files = collect_files("/docs/", pattern="**/*.pdf")
    """
    root = Path(directory)
    return [str(p) for p in root.glob(pattern) if p.is_file()]
