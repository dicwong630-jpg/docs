"""
lobster_porter/core.py
----------------------

龍蝦搬運工核心模組：批量移動及複製檔案/目錄。

Features:
    - 批量複製（batch_copy）和批量移動（batch_move），保留目錄層級結構
    - 操作日誌收集（OperationLog）
    - 撤銷介面（undo）：可撤銷所有成功的 move 操作
    - dry_run 模式：模擬操作而不實際修改檔案
    - CLI 介面（main / build_cli_parser）

CLI 使用範例::

    # 批量複製
    python -m lobster_porter copy src/docs src/images --dest /tmp/backup --base src/

    # 批量移動
    python -m lobster_porter move src/docs src/images --dest /tmp/archive --base src/

    # 模擬（不做實際變更）
    python -m lobster_porter copy src/ --dest /tmp/copy_dest --dry-run
"""

import argparse
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

# 設定模組層級 logger
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OperationLog — 單次操作記錄
# ---------------------------------------------------------------------------


@dataclass
class OperationLog:
    """
    記錄單次檔案操作，用於審計與撤銷。

    Attributes:
        action (str):     操作類型，'copy'、'move' 或 'undo_move'。
        src (str):        來源路徑。
        dst (str):        目標路徑。
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
    """
    龍蝦搬運工：批量檔案/目錄移動及複製工具。

    支援功能：
        - 批量複製與移動，保留完整目錄層級
        - 操作日誌自動收集
        - 撤銷（undo）所有成功的 move 操作
        - dry_run 模式：不實際修改任何檔案

    Example::

        porter = LobsterPorter()
        porter.batch_copy(
            sources=["/data/src/a.txt", "/data/src/sub/b.txt"],
            dest_dir="/data/dst/",
            base_src="/data/src/",
        )
        porter.print_logs()
        porter.undo()  # 撤銷所有 move（copy 無法撤銷）
    """

    def __init__(self, dry_run: bool = False) -> None:
        """
        初始化 LobsterPorter。

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
        """
        返回所有操作日誌的副本列表。

        Returns:
            List[OperationLog]: 操作日誌列表（副本）。
        """
        return list(self._logs)

    # ------------------------------------------------------------------
    # 內部輔助方法
    # ------------------------------------------------------------------

    def _compute_dest(self, src: str, base_src: str, dest_dir: str) -> str:
        """
        計算目標路徑，保留相對於 base_src 的層級結構。

        例如：src="/data/src/sub/b.txt", base_src="/data/src/", dest_dir="/out/"
        → 返回 "/out/sub/b.txt"

        若 src 不在 base_src 之下，則直接以檔名放到 dest_dir 根層級。

        Args:
            src (str):      來源路徑。
            base_src (str): 來源根目錄，用於計算相對路徑。
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
            # src 不在 base_src 之下，退回使用檔名
            return str(dest_path / src_path.name)

    def _do_copy(self, src: str, dst: str) -> OperationLog:
        """
        複製單一檔案或目錄至指定目標路徑。

        目標路徑的父目錄若不存在將自動建立。
        若來源為目錄，使用 shutil.copytree（允許目標已存在）；
        若為檔案，使用 shutil.copy2（保留 metadata）。

        Args:
            src (str): 來源路徑。
            dst (str): 目標路徑。

        Returns:
            OperationLog: 此次操作的日誌記錄。
        """
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
        """
        移動單一檔案或目錄至指定目標路徑。

        目標路徑的父目錄若不存在將自動建立。
        使用 shutil.move，支援跨磁碟分區操作。

        Args:
            src (str): 來源路徑。
            dst (str): 目標路徑。

        Returns:
            OperationLog: 此次操作的日誌記錄。
        """
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
        """
        批量複製檔案/目錄到 dest_dir，自動保留層級結構。

        Args:
            sources (List[str]):
                來源檔案或目錄路徑列表。
            dest_dir (str):
                目標根目錄路徑；不存在時將自動建立。
            base_src (Optional[str]):
                用於計算相對路徑的來源根目錄。
                若不提供，預設為 sources 第一個元素的父目錄。
            on_progress (Optional[Callable[[OperationLog], None]]):
                每完成一個檔案操作後呼叫的回調函式，接收 OperationLog 參數。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。

        Example::

            porter = LobsterPorter()
            logs = porter.batch_copy(
                sources=["/src/a.txt", "/src/sub/b.md"],
                dest_dir="/dst/",
                base_src="/src/",
                on_progress=lambda log: print(log),
            )
        """
        # 若未指定 base_src，使用第一個來源的父目錄
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
        """
        批量移動檔案/目錄到 dest_dir，自動保留層級結構。

        移動後，來源路徑的檔案將不再存在。
        所有成功的 move 操作均可透過 undo() 撤銷。

        Args:
            sources (List[str]):
                來源檔案或目錄路徑列表。
            dest_dir (str):
                目標根目錄路徑；不存在時將自動建立。
            base_src (Optional[str]):
                用於計算相對路徑的來源根目錄。
                若不提供，預設為 sources 第一個元素的父目錄。
            on_progress (Optional[Callable[[OperationLog], None]]):
                每完成一個檔案操作後呼叫的回調函式，接收 OperationLog 參數。

        Returns:
            List[OperationLog]: 本次批量操作的所有日誌記錄。

        Example::

            porter = LobsterPorter()
            logs = porter.batch_move(
                sources=["/src/a.txt", "/src/sub/b.md"],
                dest_dir="/archive/",
                base_src="/src/",
            )
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

    # ------------------------------------------------------------------
    # 撤銷介面
    # ------------------------------------------------------------------

    def undo(self) -> List[OperationLog]:
        """
        撤銷所有成功的 move 操作（以逆序執行）。

        注意：copy 操作無法撤銷（不會刪除已複製的檔案）。
        撤銷結果同樣記錄於日誌中，action 標記為 'undo_move'。

        Returns:
            List[OperationLog]: 撤銷操作的日誌列表。

        Example::

            porter.batch_move(["/src/a.txt"], "/dst/", base_src="/src/")
            porter.undo()  # 將 /dst/a.txt 移回 /src/a.txt
        """
        undo_logs: List[OperationLog] = []
        # 以逆序撤銷，確保子層級先於父層級還原
        for log in reversed(self._logs):
            if log.action == "move" and log.success:
                undo_log = self._do_move(log.dst, log.src)
                undo_log.action = "undo_move"
                self._logs.append(undo_log)
                undo_logs.append(undo_log)
        return undo_logs

    # ------------------------------------------------------------------
    # 日誌輸出
    # ------------------------------------------------------------------

    def print_logs(self) -> None:
        """
        將所有操作日誌以表格形式輸出至 stdout。

        輸出欄位：ACTION、SUCCESS、SRC、DST、TIMESTAMP
        """
        header = f"{'ACTION':<12} {'STATUS':<10} {'SRC':<45} {'DST':<45} TIMESTAMP"
        print(header)
        print("-" * len(header))
        for log in self._logs:
            status = "OK" if log.success else f"FAIL: {log.error[:20]}"
            print(
                f"{log.action:<12} {status:<10} "
                f"{str(log.src):<45} {str(log.dst):<45} {log.timestamp}"
            )


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------


def collect_files(directory: str, pattern: str = "**/*") -> List[str]:
    """
    遞迴收集目錄下所有符合 glob pattern 的檔案路徑。

    Args:
        directory (str):  要搜尋的根目錄。
        pattern (str):    Glob 模式（預設 '**/*' 匹配所有檔案）。
                          例如：'**/*.md' 只收集 Markdown 檔案。

    Returns:
        List[str]: 符合條件的檔案完整路徑列表（排除目錄）。

    Example::

        md_files = collect_files("/docs/", pattern="**/*.md")
    """
    root = Path(directory)
    return [str(p) for p in root.glob(pattern) if p.is_file()]


# ---------------------------------------------------------------------------
# CLI 介面
# ---------------------------------------------------------------------------


def build_cli_parser() -> argparse.ArgumentParser:
    """
    建立 LobsterPorter CLI 的 argparse 解析器。

    子命令：
        move  — 批量移動檔案/目錄
        copy  — 批量複製檔案/目錄

    共用選項：
        --base      來源根目錄（用於保留層級，可選）
        --dry-run   模擬執行，不實際修改檔案

    Returns:
        argparse.ArgumentParser: 已設定的解析器物件。
    """
    parser = argparse.ArgumentParser(
        prog="lobster_porter",
        description="🦞 LobsterPorter — 批量檔案移動及複製工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 批量複製（保留層級）
  python -m lobster_porter copy /src/docs /src/images --dest /tmp/backup --base /src/

  # 批量移動
  python -m lobster_porter move /src/docs /src/images --dest /tmp/archive --base /src/

  # 模擬（dry-run，不實際修改）
  python -m lobster_porter copy /src/ --dest /tmp/copy_dest --dry-run
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- move 子命令 ----
    move_parser = subparsers.add_parser("move", help="批量移動檔案/目錄")
    move_parser.add_argument("sources", nargs="+", help="來源檔案或目錄路徑（可多個）")
    move_parser.add_argument("--dest", required=True, help="目標根目錄")
    move_parser.add_argument("--base", default=None, help="來源根目錄（用於保留層級結構）")
    move_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="模擬執行，不實際修改任何檔案",
    )

    # ---- copy 子命令 ----
    copy_parser = subparsers.add_parser("copy", help="批量複製檔案/目錄")
    copy_parser.add_argument("sources", nargs="+", help="來源檔案或目錄路徑（可多個）")
    copy_parser.add_argument("--dest", required=True, help="目標根目錄")
    copy_parser.add_argument("--base", default=None, help="來源根目錄（用於保留層級結構）")
    copy_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="模擬執行，不實際修改任何檔案",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    LobsterPorter CLI 主入口。

    解析命令列參數，執行批量移動或複製操作，並輸出操作日誌摘要。

    Args:
        argv (Optional[List[str]]):
            命令列參數列表。若為 None，則使用 sys.argv[1:]。

    Returns:
        int: 退出碼。0 表示所有操作成功，1 表示有操作失敗。

    Example::

        # 程式內呼叫
        from lobster_porter.core import main
        exit_code = main(["copy", "/src/a.txt", "--dest", "/dst/"])
    """
    # 設定基本日誌輸出至 stderr
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    parser = build_cli_parser()
    args = parser.parse_args(argv)

    porter = LobsterPorter(dry_run=args.dry_run)

    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式啟動，不會實際修改任何檔案。\n")

    def on_progress(log: OperationLog) -> None:
        """每次操作完成後列印進度至 stdout。"""
        status = "✅ OK" if log.success else f"❌ FAIL: {log.error}"
        print(f"  [{log.action.upper()}] {log.src}  →  {log.dst}  [{status}]")

    if args.command == "move":
        print(f"🦞 批量移動 {len(args.sources)} 個項目 → {args.dest}")
        porter.batch_move(
            sources=args.sources,
            dest_dir=args.dest,
            base_src=args.base,
            on_progress=on_progress,
        )
    elif args.command == "copy":
        print(f"🦞 批量複製 {len(args.sources)} 個項目 → {args.dest}")
        porter.batch_copy(
            sources=args.sources,
            dest_dir=args.dest,
            base_src=args.base,
            on_progress=on_progress,
        )

    # 輸出操作摘要
    print("\n--- 操作日誌摘要 ---")
    porter.print_logs()

    # 若有任何失敗，返回非零退出碼
    failed = [log for log in porter.logs if not log.success]
    if failed:
        print(f"\n⚠️  {len(failed)} 個操作失敗。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
