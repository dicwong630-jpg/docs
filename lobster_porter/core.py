"""
core.py — 龍蝦搬運工核心模組
提供批量移動、複製、刪除等基礎搬運操作，並整合操作日誌與撤銷機制。
"""

import shutil
import os
from pathlib import Path
from typing import List, Optional, Callable
from .history import OperationHistory, OperationRecord


class LobsterPorter:
    """
    龍蝦搬運工主類別。

    負責執行批量檔案搬運操作，支援：
    - 批量移動（move）
    - 批量複製（copy）
    - 批量刪除（delete）
    - 批量重新命名（rename）
    - 操作歷史記錄與撤銷（undo）
    """

    def __init__(self, dry_run: bool = False):
        """
        初始化龍蝦搬運工。

        Args:
            dry_run: 若為 True，只模擬操作而不實際執行（沙盒測試模式）。
        """
        self.dry_run = dry_run
        self.history = OperationHistory()
        self._hooks: List[Callable] = []

    # ------------------------------------------------------------------
    # 批量移動
    # ------------------------------------------------------------------

    def batch_move(
        self,
        sources: List[str],
        destination: str,
        overwrite: bool = False,
    ) -> List[str]:
        """
        批量移動檔案到指定目標資料夾。

        Args:
            sources:     來源檔案路徑列表。
            destination: 目標資料夾路徑。
            overwrite:   是否覆蓋已存在的同名檔案。

        Returns:
            成功移動的檔案路徑列表。
        """
        dest_path = Path(destination)
        if not self.dry_run:
            dest_path.mkdir(parents=True, exist_ok=True)

        moved = []
        for src in sources:
            src_path = Path(src)
            dst_file = dest_path / src_path.name
            if dst_file.exists() and not overwrite:
                continue
            if not self.dry_run:
                shutil.move(str(src_path), str(dst_file))
            self.history.record(
                OperationRecord(
                    action="move",
                    source=str(src_path),
                    destination=str(dst_file),
                    dry_run=self.dry_run,
                )
            )
            moved.append(str(dst_file))
            self._run_hooks("after_move", src=src, dst=str(dst_file))
        return moved

    # ------------------------------------------------------------------
    # 批量複製
    # ------------------------------------------------------------------

    def batch_copy(
        self,
        sources: List[str],
        destination: str,
        overwrite: bool = False,
    ) -> List[str]:
        """
        批量複製檔案到指定目標資料夾。

        Args:
            sources:     來源檔案路徑列表。
            destination: 目標資料夾路徑。
            overwrite:   是否覆蓋已存在的同名檔案。

        Returns:
            成功複製的檔案路徑列表。
        """
        dest_path = Path(destination)
        if not self.dry_run:
            dest_path.mkdir(parents=True, exist_ok=True)

        copied = []
        for src in sources:
            src_path = Path(src)
            dst_file = dest_path / src_path.name
            if dst_file.exists() and not overwrite:
                continue
            if not self.dry_run:
                shutil.copy2(str(src_path), str(dst_file))
            self.history.record(
                OperationRecord(
                    action="copy",
                    source=str(src_path),
                    destination=str(dst_file),
                    dry_run=self.dry_run,
                )
            )
            copied.append(str(dst_file))
            self._run_hooks("after_copy", src=src, dst=str(dst_file))
        return copied

    # ------------------------------------------------------------------
    # 批量刪除
    # ------------------------------------------------------------------

    def batch_delete(self, targets: List[str]) -> List[str]:
        """
        批量刪除指定檔案列表。

        Args:
            targets: 要刪除的檔案路徑列表。

        Returns:
            成功刪除的檔案路徑列表。
        """
        deleted = []
        for target in targets:
            target_path = Path(target)
            if not target_path.exists():
                continue
            if not self.dry_run:
                backup = str(target_path) + ".bak"
                shutil.copy2(str(target_path), backup)
                target_path.unlink()
            self.history.record(
                OperationRecord(
                    action="delete",
                    source=str(target_path),
                    destination=None,
                    dry_run=self.dry_run,
                )
            )
            deleted.append(str(target_path))
            self._run_hooks("after_delete", target=target)
        return deleted

    # ------------------------------------------------------------------
    # 批量重新命名
    # ------------------------------------------------------------------

    def batch_rename(
        self,
        targets: List[str],
        rename_fn: Callable[[str], str],
    ) -> List[str]:
        """
        批量重新命名檔案，規則由呼叫者以函式形式傳入。

        Args:
            targets:   要重新命名的檔案路徑列表。
            rename_fn: 接受原始檔名（不含路徑），回傳新檔名的函式。

        Returns:
            成功重新命名後的新路徑列表。
        """
        renamed = []
        for target in targets:
            target_path = Path(target)
            new_name = rename_fn(target_path.name)
            new_path = target_path.parent / new_name
            if not self.dry_run:
                target_path.rename(new_path)
            self.history.record(
                OperationRecord(
                    action="rename",
                    source=str(target_path),
                    destination=str(new_path),
                    dry_run=self.dry_run,
                )
            )
            renamed.append(str(new_path))
            self._run_hooks("after_rename", src=target, dst=str(new_path))
        return renamed

    # ------------------------------------------------------------------
    # 撤銷（Undo）
    # ------------------------------------------------------------------

    def undo(self, steps: int = 1) -> List[OperationRecord]:
        """
        撤銷最近 N 步操作。

        Args:
            steps: 要撤銷的步驟數，預設為 1。

        Returns:
            被撤銷的操作記錄列表。
        """
        return self.history.undo(steps=steps, dry_run=self.dry_run)

    # ------------------------------------------------------------------
    # Hook 機制
    # ------------------------------------------------------------------

    def register_hook(self, fn: Callable) -> None:
        """
        注冊操作後回調鉤子（hook）函式。

        Args:
            fn: 接受 **kwargs 的可呼叫物件。
        """
        self._hooks.append(fn)

    def _run_hooks(self, event: str, **kwargs) -> None:
        for hook in self._hooks:
            try:
                hook(event=event, **kwargs)
            except Exception:
                pass
