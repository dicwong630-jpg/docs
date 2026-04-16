"""
history.py — 操作歷史記錄與撤銷（Undo）模組
確保所有搬運操作均可追溯與回滾，保障大批檔案操作的安全性。
"""

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class OperationRecord:
    """
    單條操作記錄。

    Attributes:
        action:      操作類型（move / copy / delete / rename）。
        source:      來源路徑。
        destination: 目標路徑（刪除操作為 None）。
        timestamp:   操作發生的時間戳記。
        dry_run:     是否為模擬操作（不真正執行）。
    """

    action: str
    source: str
    destination: Optional[str]
    dry_run: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        prefix = "[DRY-RUN] " if self.dry_run else ""
        return f"{prefix}[{ts}] {self.action}: {self.source} → {self.destination or '(deleted)'}"


class OperationHistory:
    """
    操作歷史管理器。

    儲存所有已執行的操作記錄，並提供 undo 功能，
    支援多步驟回滾（批量撤銷）。
    """

    def __init__(self, max_records: int = 1000):
        """
        Args:
            max_records: 最多保留的歷史記錄數，超過後自動捨棄最舊記錄。
        """
        self._records: List[OperationRecord] = []
        self.max_records = max_records

    def record(self, op: OperationRecord) -> None:
        """
        新增一條操作記錄。

        Args:
            op: OperationRecord 實例。
        """
        self._records.append(op)
        if len(self._records) > self.max_records:
            self._records.pop(0)

    def undo(self, steps: int = 1, dry_run: bool = False) -> List[OperationRecord]:
        """
        撤銷最近 N 步操作。

        撤銷邏輯：
        - move → 將檔案移回原位
        - copy → 刪除複製品
        - delete → 從備份（.bak）還原
        - rename → 改回原名

        Args:
            steps:   要撤銷的步驟數。
            dry_run: 是否以模擬模式執行撤銷。

        Returns:
            被撤銷的操作記錄列表。
        """
        to_undo = self._records[-steps:][::-1]
        undone = []

        for record in to_undo:
            if record.dry_run:
                undone.append(record)
                continue

            try:
                if record.action == "move" and record.destination:
                    dst = Path(record.destination)
                    src = Path(record.source)
                    if dst.exists() and not dry_run:
                        src.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst), str(src))

                elif record.action == "copy" and record.destination:
                    dst = Path(record.destination)
                    if dst.exists() and not dry_run:
                        dst.unlink()

                elif record.action == "delete":
                    bak = Path(record.source + ".bak")
                    src = Path(record.source)
                    if bak.exists() and not dry_run:
                        src.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(bak), str(src))

                elif record.action == "rename" and record.destination:
                    new_path = Path(record.destination)
                    old_path = Path(record.source)
                    if new_path.exists() and not dry_run:
                        new_path.rename(old_path)

                undone.append(record)
            except Exception:
                pass

        if not dry_run:
            del self._records[-steps:]

        return undone

    def all_records(self) -> List[OperationRecord]:
        """回傳所有歷史操作記錄（最舊到最新）。"""
        return list(self._records)

    def clear(self) -> None:
        """清空所有歷史記錄。"""
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)

    def __repr__(self) -> str:
        return f"<OperationHistory records={len(self._records)}>"
