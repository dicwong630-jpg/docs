"""
plugins/examples.py
-------------------

LobsterPorter 示範插件與測試案例。

包含：
    - DemoPlugin:              展示批量複製、移動、依副檔名分類的插件
    - TestLobsterPorterCore:   unittest 測試 lobster_porter.core 核心功能
    - TestDemoPlugin:          unittest 測試 DemoPlugin 插件行為

直接執行此檔案可選擇模式：

    # 執行 demo（在暫存目錄中展示所有功能）
    python plugins/examples.py demo

    # 執行 unittest 測試
    python plugins/examples.py

    # 或：
    python plugins/examples.py test
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List

# 確保 lobster_porter 套件可被 import（適用於直接執行此腳本的情況）
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lobster_porter.core import (  # noqa: E402
    LobsterPorter,
    OperationLog,
    collect_files,
)


# ===========================================================================
# DemoPlugin — 示範插件
# ===========================================================================


class DemoPlugin:
    """
    示範插件，展示如何以 LobsterPorter 實作自訂批量操作策略。

    包含策略：
        1. ``batch_copy_demo``   — 保留層級的批量複製
        2. ``batch_move_demo``   — 保留層級的批量移動（附撤銷展示）
        3. ``organize_by_ext``   — 依副檔名將檔案分類至子目錄

    Attributes:
        porter (LobsterPorter): 此插件使用的 LobsterPorter 實例。

    Example::

        plugin = DemoPlugin()
        plugin.run_demo()
    """

    def __init__(self, porter: LobsterPorter = None) -> None:
        """
        初始化 DemoPlugin。

        Args:
            porter (LobsterPorter, optional):
                使用的 LobsterPorter 實例。若未提供則自動建立一個新實例。
        """
        self.porter = porter if porter is not None else LobsterPorter()

    # ------------------------------------------------------------------
    # 策略 1：批量複製（保留層級）
    # ------------------------------------------------------------------

    def batch_copy_demo(
        self,
        source_dir: str,
        dest_dir: str,
        pattern: str = "**/*",
    ) -> List[OperationLog]:
        """
        批量複製 source_dir 下所有符合 pattern 的檔案到 dest_dir，
        保留完整目錄層級結構。

        Args:
            source_dir (str): 來源根目錄。
            dest_dir (str):   目標根目錄。
            pattern (str):    Glob 模式（預設 '**/*' 收集所有檔案）。

        Returns:
            List[OperationLog]: 本次批量複製的操作日誌。

        Example::

            plugin = DemoPlugin()
            logs = plugin.batch_copy_demo("/src/docs/", "/backup/docs/")
        """
        files = collect_files(source_dir, pattern=pattern)
        print(f"  📂 掃描到 {len(files)} 個檔案，開始批量複製 → {dest_dir}")
        logs = self.porter.batch_copy(
            sources=files,
            dest_dir=dest_dir,
            base_src=source_dir,
            on_progress=lambda log: print(
                f"    COPY {'✅' if log.success else '❌'} "
                f"{Path(log.src).name}  →  {log.dst}"
            ),
        )
        return logs

    # ------------------------------------------------------------------
    # 策略 2：批量移動（保留層級）
    # ------------------------------------------------------------------

    def batch_move_demo(
        self,
        source_dir: str,
        dest_dir: str,
        pattern: str = "**/*",
    ) -> List[OperationLog]:
        """
        批量移動 source_dir 下所有符合 pattern 的檔案到 dest_dir，
        保留完整目錄層級結構。

        Args:
            source_dir (str): 來源根目錄。
            dest_dir (str):   目標根目錄。
            pattern (str):    Glob 模式（預設 '**/*' 收集所有檔案）。

        Returns:
            List[OperationLog]: 本次批量移動的操作日誌。

        Example::

            plugin = DemoPlugin()
            logs = plugin.batch_move_demo("/src/old_docs/", "/archive/docs/")
        """
        files = collect_files(source_dir, pattern=pattern)
        print(f"  📂 掃描到 {len(files)} 個檔案，開始批量移動 → {dest_dir}")
        logs = self.porter.batch_move(
            sources=files,
            dest_dir=dest_dir,
            base_src=source_dir,
            on_progress=lambda log: print(
                f"    MOVE {'✅' if log.success else '❌'} "
                f"{Path(log.src).name}  →  {log.dst}"
            ),
        )
        return logs

    # ------------------------------------------------------------------
    # 策略 3：依副檔名分類
    # ------------------------------------------------------------------

    def organize_by_ext(
        self,
        source_dir: str,
        dest_dir: str,
        pattern: str = "**/*",
    ) -> List[OperationLog]:
        """
        將 source_dir 下所有符合 pattern 的檔案，
        依副檔名複製到 dest_dir/<副檔名>/ 子目錄中。

        無副檔名的檔案放入 dest_dir/no_ext/ 目錄。

        Args:
            source_dir (str): 來源根目錄。
            dest_dir (str):   目標根目錄。
            pattern (str):    Glob 模式（預設 '**/*'）。

        Returns:
            List[OperationLog]: 所有複製操作的日誌。

        Example::

            plugin = DemoPlugin()
            logs = plugin.organize_by_ext("/docs/mixed/", "/docs/organized/")
            # 結果：/docs/organized/md/xxx.md, /docs/organized/png/yyy.png …
        """
        files = collect_files(source_dir, pattern=pattern)
        print(f"  🗂️  依副檔名分類 {len(files)} 個檔案 → {dest_dir}")
        # 使用獨立 LobsterPorter，避免與 self.porter 的日誌混淆
        _porter = LobsterPorter(dry_run=self.porter.dry_run)
        logs: List[OperationLog] = []
        for f in files:
            ext = Path(f).suffix.lstrip(".").lower() or "no_ext"
            ext_dest = os.path.join(dest_dir, ext)
            batch_logs = _porter.batch_copy(
                sources=[f],
                dest_dir=ext_dest,
                base_src=str(Path(f).parent),
            )
            logs.extend(batch_logs)
            log = batch_logs[0] if batch_logs else None
            if log:
                print(
                    f"    ORG {'✅' if log.success else '❌'} "
                    f"{Path(f).name}  →  {ext}/{Path(f).name}"
                )
        return logs

    # ------------------------------------------------------------------
    # Demo 主流程
    # ------------------------------------------------------------------

    def run_demo(self) -> None:
        """
        在暫存目錄中執行完整的功能展示，涵蓋：
            1. 批量複製（保留層級）
            2. 批量移動（保留層級）
            3. 依副檔名分類複製
            4. 操作日誌摘要
            5. 撤銷（undo）移動操作

        展示結束後自動清理暫存目錄。
        """
        print("=" * 65)
        print("🦞 LobsterPorter Demo Plugin — 批量移動及複製展示")
        print("=" * 65)

        with tempfile.TemporaryDirectory(prefix="lobster_demo_") as tmpdir:
            # --- 建立示範來源目錄結構 ---
            src_root = Path(tmpdir) / "source"
            (src_root / "docs").mkdir(parents=True)
            (src_root / "docs" / "subdir").mkdir(parents=True)
            (src_root / "images").mkdir(parents=True)

            (src_root / "docs" / "readme.md").write_text("# README")
            (src_root / "docs" / "guide.md").write_text("# Guide")
            (src_root / "docs" / "subdir" / "advanced.md").write_text("# Advanced")
            (src_root / "images" / "logo.png").write_bytes(b"\x89PNG")
            (src_root / "images" / "banner.jpg").write_bytes(b"\xff\xd8\xff")
            (src_root / "notes.txt").write_text("Some notes")

            dest_copy = Path(tmpdir) / "copy_dest"
            dest_move = Path(tmpdir) / "move_dest"
            dest_org = Path(tmpdir) / "organized"

            # ------------------------------------------------------------------
            # 步驟 1：批量複製
            # ------------------------------------------------------------------
            print("\n[步驟 1] 批量複製（保留層級結構）")
            copy_plugin = DemoPlugin()
            copy_logs = copy_plugin.batch_copy_demo(str(src_root), str(dest_copy))
            print(f"  → 複製完成，共 {len(copy_logs)} 個操作")

            # ------------------------------------------------------------------
            # 步驟 2：批量移動（建立獨立來源以便展示）
            # ------------------------------------------------------------------
            print("\n[步驟 2] 批量移動（保留層級結構）")
            src_move = Path(tmpdir) / "move_source"
            (src_move / "sub").mkdir(parents=True)
            (src_move / "a.txt").write_text("A")
            (src_move / "b.txt").write_text("B")
            (src_move / "sub" / "c.txt").write_text("C")

            move_plugin = DemoPlugin()
            move_logs = move_plugin.batch_move_demo(str(src_move), str(dest_move))
            print(f"  → 移動完成，共 {len(move_logs)} 個操作")

            # ------------------------------------------------------------------
            # 步驟 3：依副檔名分類
            # ------------------------------------------------------------------
            print("\n[步驟 3] 依副檔名分類複製")
            org_plugin = DemoPlugin()
            org_logs = org_plugin.organize_by_ext(str(src_root), str(dest_org))
            print(f"  → 分類完成，共 {len(org_logs)} 個操作")
            print(f"  → 分類結果目錄：{[d.name for d in dest_org.iterdir() if d.is_dir()]}")

            # ------------------------------------------------------------------
            # 步驟 4：操作日誌摘要
            # ------------------------------------------------------------------
            print("\n[步驟 4] 操作日誌摘要（批量複製部分）")
            copy_plugin.porter.print_logs()

            # ------------------------------------------------------------------
            # 步驟 5：撤銷移動操作
            # ------------------------------------------------------------------
            print("\n[步驟 5] 撤銷移動操作（undo）")
            undo_logs = move_plugin.porter.undo()
            for log in undo_logs:
                status = "✅ OK" if log.success else f"❌ FAIL: {log.error}"
                print(f"  UNDO {Path(log.src).name}  →  {log.dst}  [{status}]")
            print(f"  → 撤銷完成，共還原 {len(undo_logs)} 個移動操作")

        print("\n🎉 Demo 完成！（暫存目錄已自動清理）")


# ===========================================================================
# 測試案例
# ===========================================================================


class TestLobsterPorterCore(unittest.TestCase):
    """
    測試 lobster_porter.core 核心功能。

    涵蓋：
        - 批量複製（保留層級、成功旗標、日誌記錄）
        - 批量移動（來源消失、成功旗標）
        - dry_run 模式（不實際產生檔案）
        - undo（成功還原已移動的檔案）
        - collect_files（遞迴收集）
    """

    def setUp(self) -> None:
        """
        在暫存目錄中建立示範來源結構。

        結構：
            src/
              a.txt
              sub/
                b.txt
        """
        self.tmpdir = tempfile.mkdtemp(prefix="lobster_test_")
        self.src = Path(self.tmpdir) / "src"
        self.dst = Path(self.tmpdir) / "dst"
        self.src.mkdir()
        self.dst.mkdir()
        (self.src / "a.txt").write_text("hello")
        (self.src / "sub").mkdir()
        (self.src / "sub" / "b.txt").write_text("world")

    def tearDown(self) -> None:
        """清除暫存目錄，避免測試間互相影響。"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # batch_copy 測試
    # ------------------------------------------------------------------

    def test_batch_copy_preserves_hierarchy(self) -> None:
        """batch_copy 應在目標目錄保留相同的目錄層級結構。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        logs = porter.batch_copy(files, str(self.dst), base_src=str(self.src))

        self.assertTrue((self.dst / "a.txt").exists(), "a.txt 應被複製")
        self.assertTrue((self.dst / "sub" / "b.txt").exists(), "sub/b.txt 應被複製（保留層級）")
        self.assertEqual(len(logs), 2, "應記錄 2 個操作日誌")
        self.assertTrue(all(log.success for log in logs), "所有操作應成功")

    def test_batch_copy_does_not_remove_source(self) -> None:
        """batch_copy 不應刪除來源檔案。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        porter.batch_copy(files, str(self.dst), base_src=str(self.src))

        self.assertTrue((self.src / "a.txt").exists(), "來源 a.txt 應保留")
        self.assertTrue((self.src / "sub" / "b.txt").exists(), "來源 sub/b.txt 應保留")

    def test_batch_copy_logs_recorded(self) -> None:
        """batch_copy 應將操作記錄於 porter.logs。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        porter.batch_copy(files, str(self.dst), base_src=str(self.src))

        self.assertEqual(len(porter.logs), 2)
        for log in porter.logs:
            self.assertEqual(log.action, "copy")
            self.assertTrue(log.success)
            self.assertIsInstance(log.timestamp, str)
            self.assertTrue(len(log.timestamp) > 0)

    # ------------------------------------------------------------------
    # batch_move 測試
    # ------------------------------------------------------------------

    def test_batch_move_preserves_hierarchy(self) -> None:
        """batch_move 應在目標目錄保留相同的目錄層級結構。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        logs = porter.batch_move(files, str(self.dst), base_src=str(self.src))

        self.assertTrue((self.dst / "a.txt").exists(), "a.txt 應被移動至目標")
        self.assertTrue((self.dst / "sub" / "b.txt").exists(), "sub/b.txt 應被移動（保留層級）")
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log.success for log in logs))

    def test_batch_move_removes_source(self) -> None:
        """batch_move 應從來源位置刪除已移動的檔案。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        porter.batch_move(files, str(self.dst), base_src=str(self.src))

        self.assertFalse((self.src / "a.txt").exists(), "a.txt 應從來源刪除")
        self.assertFalse((self.src / "sub" / "b.txt").exists(), "sub/b.txt 應從來源刪除")

    # ------------------------------------------------------------------
    # dry_run 測試
    # ------------------------------------------------------------------

    def test_dry_run_copy_no_file_changes(self) -> None:
        """dry_run=True 時，batch_copy 不應建立任何實際檔案。"""
        porter = LobsterPorter(dry_run=True)
        files = collect_files(str(self.src))
        logs = porter.batch_copy(files, str(self.dst), base_src=str(self.src))

        self.assertFalse((self.dst / "a.txt").exists(), "dry_run 不應複製 a.txt")
        self.assertFalse((self.dst / "sub" / "b.txt").exists(), "dry_run 不應複製 sub/b.txt")
        # 日誌仍應被記錄
        self.assertEqual(len(logs), 2)

    def test_dry_run_move_no_file_changes(self) -> None:
        """dry_run=True 時，batch_move 不應刪除來源檔案。"""
        porter = LobsterPorter(dry_run=True)
        files = collect_files(str(self.src))
        porter.batch_move(files, str(self.dst), base_src=str(self.src))

        self.assertTrue((self.src / "a.txt").exists(), "dry_run 不應移除來源 a.txt")

    # ------------------------------------------------------------------
    # undo 測試
    # ------------------------------------------------------------------

    def test_undo_restores_moved_files(self) -> None:
        """undo() 應將已移動的檔案還原至來源位置。"""
        porter = LobsterPorter()
        src_file = str(self.src / "a.txt")
        porter.batch_move([src_file], str(self.dst), base_src=str(self.src))

        # 確認移動後來源消失
        self.assertFalse((self.src / "a.txt").exists())

        # 撤銷
        undo_logs = porter.undo()

        # 來源應被還原
        self.assertTrue((self.src / "a.txt").exists(), "undo 後 a.txt 應還原至來源")
        self.assertEqual(len(undo_logs), 1)
        self.assertEqual(undo_logs[0].action, "undo_move")
        self.assertTrue(undo_logs[0].success)

    def test_undo_does_not_affect_copies(self) -> None:
        """undo() 不應刪除已複製的檔案。"""
        porter = LobsterPorter()
        src_file = str(self.src / "a.txt")
        porter.batch_copy([src_file], str(self.dst), base_src=str(self.src))
        porter.undo()

        # copy 不受 undo 影響，目標檔案應仍存在
        self.assertTrue((self.dst / "a.txt").exists(), "undo 不應刪除已複製的檔案")

    # ------------------------------------------------------------------
    # collect_files 測試
    # ------------------------------------------------------------------

    def test_collect_files_returns_all_files(self) -> None:
        """collect_files 應遞迴回傳目錄下所有檔案。"""
        files = collect_files(str(self.src))
        names = {Path(f).name for f in files}
        self.assertIn("a.txt", names)
        self.assertIn("b.txt", names)
        self.assertEqual(len(files), 2)

    def test_collect_files_pattern_filter(self) -> None:
        """collect_files 使用自訂 pattern 時應只收集符合的檔案。"""
        # 新增一個 .md 檔案
        (self.src / "readme.md").write_text("# README")
        md_files = collect_files(str(self.src), pattern="**/*.md")
        names = {Path(f).name for f in md_files}
        self.assertIn("readme.md", names)
        self.assertNotIn("a.txt", names)

    # ------------------------------------------------------------------
    # on_progress 回調測試
    # ------------------------------------------------------------------

    def test_on_progress_callback_called(self) -> None:
        """batch_copy 應在每次操作後呼叫 on_progress 回調。"""
        porter = LobsterPorter()
        files = collect_files(str(self.src))
        called: List[OperationLog] = []
        porter.batch_copy(files, str(self.dst), base_src=str(self.src), on_progress=called.append)
        self.assertEqual(len(called), 2, "on_progress 應被呼叫 2 次")


# ===========================================================================
# DemoPlugin 測試
# ===========================================================================


class TestDemoPlugin(unittest.TestCase):
    """
    測試 DemoPlugin 插件功能。

    涵蓋：
        - organize_by_ext 依副檔名分類
        - batch_copy_demo 批量複製
        - batch_move_demo 批量移動
    """

    def setUp(self) -> None:
        """建立含多種副檔名檔案的暫存來源目錄。"""
        self.tmpdir = tempfile.mkdtemp(prefix="lobster_plugin_test_")
        self.src = Path(self.tmpdir) / "src"
        self.dst = Path(self.tmpdir) / "dst"
        self.src.mkdir()
        self.dst.mkdir()
        (self.src / "readme.md").write_text("# README")
        (self.src / "guide.md").write_text("# Guide")
        (self.src / "logo.png").write_bytes(b"\x89PNG")
        (self.src / "notes.txt").write_text("notes")

    def tearDown(self) -> None:
        """清除暫存目錄。"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_organize_by_ext_creates_subdirs(self) -> None:
        """organize_by_ext 應依副檔名建立子目錄並複製檔案。"""
        plugin = DemoPlugin()
        logs = plugin.organize_by_ext(str(self.src), str(self.dst))

        self.assertTrue((self.dst / "md" / "readme.md").exists(), "md/readme.md 應存在")
        self.assertTrue((self.dst / "md" / "guide.md").exists(), "md/guide.md 應存在")
        self.assertTrue((self.dst / "png" / "logo.png").exists(), "png/logo.png 應存在")
        self.assertTrue((self.dst / "txt" / "notes.txt").exists(), "txt/notes.txt 應存在")
        self.assertEqual(len(logs), 4, "應記錄 4 個操作日誌")

    def test_batch_copy_demo(self) -> None:
        """batch_copy_demo 應複製所有檔案至目標目錄。"""
        plugin = DemoPlugin()
        logs = plugin.batch_copy_demo(str(self.src), str(self.dst))

        self.assertTrue((self.dst / "readme.md").exists())
        self.assertEqual(len(logs), 4)
        self.assertTrue(all(log.success for log in logs))

    def test_batch_move_demo(self) -> None:
        """batch_move_demo 應移動所有檔案並從來源目錄移除。"""
        plugin = DemoPlugin()
        logs = plugin.batch_move_demo(str(self.src), str(self.dst))

        self.assertTrue((self.dst / "readme.md").exists(), "readme.md 應出現於目標")
        self.assertFalse((self.src / "readme.md").exists(), "readme.md 應從來源移除")
        self.assertEqual(len(logs), 4)
        self.assertTrue(all(log.success for log in logs))


# ===========================================================================
# CLI 入口：demo 或 test
# ===========================================================================

if __name__ == "__main__":
    # 第一個引數為 'demo' 時執行展示，否則執行 unittest
    if len(sys.argv) > 1 and sys.argv[1] in ("demo",):
        plugin = DemoPlugin()
        plugin.run_demo()
    else:
        print("🧪 執行 LobsterPorter 單元測試...\n")
        unittest.main(argv=[sys.argv[0], "-v"])
