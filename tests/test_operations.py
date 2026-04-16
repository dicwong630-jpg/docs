"""
tests/test_operations.py — 批量操作單元測試
"""

import os
import tempfile
import unittest
from pathlib import Path

from lobster_porter.operations import LobsterPorter, OperationLog, collect_files


def _make_temp_files(tmpdir: str, names: list) -> list:
    """在 tmpdir 中建立一組空檔案，回傳路徑列表。"""
    paths = []
    for name in names:
        p = Path(tmpdir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test content")
        paths.append(str(p))
    return paths


class TestOperationLog(unittest.TestCase):
    def test_str_success(self):
        log = OperationLog(action="copy", src="/a", dst="/b")
        self.assertIn("COPY", str(log))
        self.assertIn("OK", str(log))

    def test_str_failure(self):
        log = OperationLog(action="move", src="/a", dst="/b", success=False, error="err")
        self.assertIn("FAIL", str(log))


class TestBatchCopy(unittest.TestCase):
    def test_copy_single_file(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            logs = porter.batch_copy(files, dst_dir, base_src=src_dir)
            self.assertEqual(len(logs), 1)
            self.assertTrue(logs[0].success)
            self.assertTrue(Path(dst_dir, "a.txt").exists())

    def test_copy_multiple_files(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt", "b.md", "c.pdf"])
            porter = LobsterPorter()
            logs = porter.batch_copy(files, dst_dir, base_src=src_dir)
            self.assertEqual(len(logs), 3)
            self.assertTrue(all(l.success for l in logs))

    def test_copy_preserves_structure(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["sub/nested/file.txt"])
            porter = LobsterPorter()
            porter.batch_copy(files, dst_dir, base_src=src_dir)
            self.assertTrue(Path(dst_dir, "sub", "nested", "file.txt").exists())

    def test_copy_dry_run(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter(dry_run=True)
            logs = porter.batch_copy(files, dst_dir, base_src=src_dir)
            self.assertTrue(logs[0].success)
            # 乾跑模式：目標不應存在
            self.assertFalse(Path(dst_dir, "a.txt").exists())

    def test_copy_on_progress_called(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt", "b.txt"])
            called = []
            porter = LobsterPorter()
            porter.batch_copy(files, dst_dir, base_src=src_dir,
                              on_progress=lambda log: called.append(log))
            self.assertEqual(len(called), 2)


class TestBatchMove(unittest.TestCase):
    def test_move_single_file(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            logs = porter.batch_move(files, dst_dir, base_src=src_dir)
            self.assertTrue(logs[0].success)
            self.assertTrue(Path(dst_dir, "a.txt").exists())
            self.assertFalse(Path(src_dir, "a.txt").exists())

    def test_move_dry_run(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter(dry_run=True)
            porter.batch_move(files, dst_dir, base_src=src_dir)
            # 乾跑模式：來源應仍存在
            self.assertTrue(Path(src_dir, "a.txt").exists())

    def test_logs_recorded(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            porter.batch_move(files, dst_dir, base_src=src_dir)
            self.assertEqual(len(porter.logs), 1)
            self.assertEqual(porter.logs[0].action, "move")


class TestBatchDelete(unittest.TestCase):
    def test_delete_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["to_delete.txt"])
            porter = LobsterPorter()
            logs = porter.batch_delete(files)
            self.assertTrue(logs[0].success)
            self.assertFalse(Path(files[0]).exists())

    def test_delete_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["keep.txt"])
            porter = LobsterPorter(dry_run=True)
            logs = porter.batch_delete(files)
            self.assertTrue(logs[0].success)
            self.assertTrue(Path(files[0]).exists())

    def test_delete_nonexistent(self):
        porter = LobsterPorter()
        logs = porter.batch_delete(["/no/such/file.txt"])
        self.assertFalse(logs[0].success)
        self.assertNotEqual(logs[0].error, "")

    def test_delete_on_progress_called(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["a.txt", "b.txt"])
            called = []
            porter = LobsterPorter()
            porter.batch_delete(files, on_progress=lambda l: called.append(l))
            self.assertEqual(len(called), 2)


class TestBatchRename(unittest.TestCase):
    def test_rename_with_pattern(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["report_2023.txt", "report_2024.txt"])
            porter = LobsterPorter()
            logs = porter.batch_rename(
                files,
                pattern=r"report_(\d+)\.txt",
                replacement=r"annual_\1.txt",
            )
            self.assertEqual(len(logs), 2)
            self.assertTrue(all(l.success for l in logs))
            self.assertTrue(Path(tmpdir, "annual_2023.txt").exists())
            self.assertTrue(Path(tmpdir, "annual_2024.txt").exists())

    def test_rename_no_match_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["unrelated.txt"])
            porter = LobsterPorter()
            logs = porter.batch_rename(files, pattern=r"xyz", replacement=r"abc")
            # 不匹配，應跳過（無日誌）
            self.assertEqual(len(logs), 0)

    def test_rename_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["old_name.txt"])
            porter = LobsterPorter(dry_run=True)
            porter.batch_rename(files, pattern=r"old", replacement=r"new")
            # 乾跑：原始檔案仍存在
            self.assertTrue(Path(files[0]).exists())

    def test_rename_case_insensitive_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["FILE.TXT"])
            porter = LobsterPorter()
            logs = porter.batch_rename(files, pattern=r"\.txt$", replacement=r".md")
            self.assertEqual(len(logs), 1)


class TestUndo(unittest.TestCase):
    def test_undo_move(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            porter.batch_move(files, dst_dir, base_src=src_dir)
            self.assertTrue(Path(dst_dir, "a.txt").exists())

            undo_logs = porter.undo()
            self.assertEqual(len(undo_logs), 1)
            self.assertEqual(undo_logs[0].action, "undo_move")
            self.assertTrue(Path(src_dir, "a.txt").exists())
            self.assertFalse(Path(dst_dir, "a.txt").exists())

    def test_undo_rename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["old_name.txt"])
            porter = LobsterPorter()
            porter.batch_rename(files, pattern=r"old", replacement=r"new")
            self.assertTrue(Path(tmpdir, "new_name.txt").exists())

            undo_logs = porter.undo()
            self.assertTrue(any(l.action == "undo_rename" for l in undo_logs))
            self.assertTrue(Path(tmpdir, "old_name.txt").exists())

    def test_undo_copy_not_reversed(self):
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            porter.batch_copy(files, dst_dir, base_src=src_dir)
            undo_logs = porter.undo()
            # copy 操作不可撤銷
            self.assertEqual(len(undo_logs), 0)

    def test_undo_delete_not_reversed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_temp_files(tmpdir, ["del.txt"])
            porter = LobsterPorter()
            porter.batch_delete(files)
            undo_logs = porter.undo()
            # delete 操作不可撤銷
            self.assertEqual(len(undo_logs), 0)


class TestExportLog(unittest.TestCase):
    def test_export_json(self):
        import json
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["a.txt"])
            porter = LobsterPorter()
            porter.batch_copy(files, dst_dir, base_src=src_dir)

            out = os.path.join(dst_dir, "log.json")
            porter.export_log(out, fmt="json")
            self.assertTrue(Path(out).exists())
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["action"], "copy")

    def test_export_csv(self):
        import csv
        with tempfile.TemporaryDirectory() as src_dir, \
             tempfile.TemporaryDirectory() as dst_dir:
            files = _make_temp_files(src_dir, ["b.txt"])
            porter = LobsterPorter()
            porter.batch_copy(files, dst_dir, base_src=src_dir)

            out = os.path.join(dst_dir, "log.csv")
            porter.export_log(out, fmt="csv")
            self.assertTrue(Path(out).exists())
            with open(out, encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["action"], "copy")

    def test_export_invalid_format(self):
        porter = LobsterPorter()
        with self.assertRaises(ValueError):
            porter.export_log("/tmp/log.xml", fmt="xml")


class TestCollectFiles(unittest.TestCase):
    def test_collect_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_temp_files(tmpdir, ["a.txt", "b.md", "sub/c.py"])
            files = collect_files(tmpdir)
            self.assertEqual(len(files), 3)

    def test_collect_with_glob(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_temp_files(tmpdir, ["a.txt", "b.md", "c.txt"])
            files = collect_files(tmpdir, pattern="**/*.txt")
            self.assertEqual(len(files), 2)
            for f in files:
                self.assertTrue(f.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
