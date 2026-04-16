"""
tests/test_core.py — Porter 核心協調器單元測試
"""

import os
import tempfile
import unittest
from pathlib import Path

from lobster_porter.core import Porter, TransportResult
from lobster_porter.strategies import ExtensionStrategy, FlatStrategy, TypeGroupStrategy


def _make_files(tmpdir: str, names: list) -> None:
    """在 tmpdir 中建立一組測試檔案。"""
    for name in names:
        p = Path(tmpdir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test")


class TestTransportResult(unittest.TestCase):
    def test_success_repr(self):
        r = TransportResult(src=Path("/a"), dest=Path("/b"), success=True)
        self.assertTrue(r.success)
        self.assertIsNone(r.error)

    def test_failure_repr(self):
        r = TransportResult(
            src=Path("/a"), dest=Path("/b"), success=False, error=IOError("test")
        )
        self.assertFalse(r.success)
        self.assertIsNotNone(r.error)


class TestPorterRun(unittest.TestCase):
    def test_move_by_extension(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt", "b.md", "c.pdf"])
            porter = Porter(src=src, dest=dst, strategy=ExtensionStrategy())
            results = porter.run()
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r.success for r in results))
            self.assertTrue(Path(dst, "txt", "a.txt").exists())
            self.assertTrue(Path(dst, "md", "b.md").exists())
            self.assertTrue(Path(dst, "pdf", "c.pdf").exists())

    def test_copy_mode(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            porter = Porter(src=src, dest=dst, strategy=FlatStrategy(), copy=True)
            results = porter.run()
            self.assertTrue(results[0].success)
            # 複製模式：來源仍存在
            self.assertTrue(Path(src, "a.txt").exists())
            self.assertTrue(Path(dst, ".", "a.txt").exists() or
                            Path(dst, "a.txt").exists())

    def test_dry_run_mode(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            porter = Porter(src=src, dest=dst, strategy=FlatStrategy(), dry_run=True)
            results = porter.run()
            self.assertTrue(results[0].success)
            # 乾跑：目標目錄中不應有檔案
            self.assertFalse(Path(dst, "a.txt").exists())
            # 來源仍存在
            self.assertTrue(Path(src, "a.txt").exists())

    def test_overwrite_false_skips(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            # 預先建立目標檔案
            Path(dst, "txt").mkdir()
            Path(dst, "txt", "a.txt").write_text("existing")
            porter = Porter(
                src=src, dest=dst, strategy=ExtensionStrategy(),
                overwrite=False, copy=True
            )
            results = porter.run()
            # 應跳過（返回 success=False）
            self.assertFalse(results[0].success)

    def test_overwrite_true_replaces(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            Path(dst, "txt").mkdir()
            Path(dst, "txt", "a.txt").write_text("old content")
            porter = Porter(
                src=src, dest=dst, strategy=ExtensionStrategy(),
                overwrite=True, copy=True
            )
            results = porter.run()
            self.assertTrue(results[0].success)
            content = Path(dst, "txt", "a.txt").read_text()
            self.assertEqual(content, "test")

    def test_source_not_found(self):
        porter = Porter(src="/no/such/dir", dest="/tmp/out")
        with self.assertRaises(FileNotFoundError):
            porter.run()

    def test_include_patterns(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.md", "b.txt", "c.pdf"])
            porter = Porter(
                src=src, dest=dst,
                strategy=FlatStrategy(),
                copy=True,
                include_patterns=["*.md"],
            )
            results = porter.run()
            # 只有 .md 檔案被處理
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].src.suffix, ".md")

    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.md", "b.txt", "c.pdf"])
            porter = Porter(
                src=src, dest=dst,
                strategy=FlatStrategy(),
                copy=True,
                exclude_patterns=["*.txt"],
            )
            results = porter.run()
            names = [r.src.name for r in results]
            self.assertNotIn("b.txt", names)

    def test_type_group_strategy(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["doc.pdf", "photo.jpg", "script.py", "archive.zip"])
            porter = Porter(
                src=src, dest=dst,
                strategy=TypeGroupStrategy(),
                copy=True,
            )
            results = porter.run()
            self.assertTrue(all(r.success for r in results))
            self.assertTrue(Path(dst, "documents", "doc.pdf").exists())
            self.assertTrue(Path(dst, "images", "photo.jpg").exists())
            self.assertTrue(Path(dst, "code", "script.py").exists())
            self.assertTrue(Path(dst, "archives", "archive.zip").exists())


class TestPorterPlugins(unittest.TestCase):
    def test_plugin_hooks_called(self):
        from lobster_porter.plugins.examples import (
            FileCounterPlugin, SummaryPlugin
        )
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.md", "b.md", "c.pdf"])
            counter = FileCounterPlugin()
            porter = Porter(
                src=src, dest=dst,
                strategy=FlatStrategy(),
                plugins=[counter],
                copy=True,
            )
            porter.run()
            self.assertEqual(counter.counts.get("md", 0), 2)
            self.assertEqual(counter.counts.get("pdf", 0), 1)

    def test_error_collector_plugin(self):
        from lobster_porter.plugins.examples import ErrorCollectorPlugin
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            # 預先建立目標，強制 overwrite=False 失敗
            Path(dst, ".").mkdir(exist_ok=True)
            Path(dst, "a.txt").write_text("existing")
            collector = ErrorCollectorPlugin()
            porter = Porter(
                src=src, dest=dst,
                strategy=FlatStrategy(),
                copy=True,
                overwrite=False,
                plugins=[collector],
            )
            porter.run()
            # 應有一個錯誤
            self.assertEqual(len(collector.errors), 1)


if __name__ == "__main__":
    unittest.main()
