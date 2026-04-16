"""
tests/test_cli.py — CLI 命令列介面單元測試
"""

import os
import tempfile
import unittest
from pathlib import Path

from lobster_porter.cli import main


def _make_files(tmpdir: str, names: list) -> list:
    paths = []
    for name in names:
        p = Path(tmpdir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test")
        paths.append(str(p))
    return paths


class TestCLICopy(unittest.TestCase):
    def test_copy_basic(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt"])
            rc = main(["copy", files[0], "--dest", dst, "--base", src])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "a.txt").exists())

    def test_copy_dry_run(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt"])
            rc = main(["copy", files[0], "--dest", dst, "--base", src, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertFalse(Path(dst, "a.txt").exists())

    def test_copy_multiple(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt", "b.md"])
            rc = main(["copy"] + files + ["--dest", dst, "--base", src])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "a.txt").exists())
            self.assertTrue(Path(dst, "b.md").exists())

    def test_copy_with_log_export_json(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt"])
            log_out = os.path.join(dst, "log.json")
            rc = main(["copy", files[0], "--dest", dst, "--base", src,
                       "--log-out", log_out])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(log_out).exists())


class TestCLIMove(unittest.TestCase):
    def test_move_basic(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt"])
            rc = main(["move", files[0], "--dest", dst, "--base", src])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "a.txt").exists())
            self.assertFalse(Path(src, "a.txt").exists())

    def test_move_dry_run(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            files = _make_files(src, ["a.txt"])
            rc = main(["move", files[0], "--dest", dst, "--base", src, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(src, "a.txt").exists())


class TestCLIDelete(unittest.TestCase):
    def test_delete_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_files(tmpdir, ["a.txt"])
            rc = main(["delete", files[0], "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(files[0]).exists())

    def test_delete_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_files(tmpdir, ["to_delete.txt"])
            rc = main(["delete", files[0], "--force"])
            self.assertEqual(rc, 0)
            self.assertFalse(Path(files[0]).exists())

    def test_delete_nonexistent_returns_failure(self):
        rc = main(["delete", "/no/such/file.txt", "--force"])
        self.assertEqual(rc, 1)


class TestCLIRename(unittest.TestCase):
    def test_rename_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_files(tmpdir, ["report_2023.txt"])
            rc = main([
                "rename", files[0],
                "--pattern", r"report_(\d+)\.txt",
                "--replacement", r"annual_\1.txt",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(tmpdir, "annual_2023.txt").exists())

    def test_rename_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = _make_files(tmpdir, ["old.txt"])
            rc = main([
                "rename", files[0],
                "--pattern", r"old",
                "--replacement", r"new",
                "--dry-run",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(files[0]).exists())


class TestCLISort(unittest.TestCase):
    def test_sort_extension_strategy(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt", "b.md", "c.pdf"])
            rc = main(["sort", src, "--dest", dst, "--strategy", "extension"])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "txt", "a.txt").exists())
            self.assertTrue(Path(dst, "md", "b.md").exists())
            self.assertTrue(Path(dst, "pdf", "c.pdf").exists())

    def test_sort_typegroup_strategy(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["doc.pdf", "photo.jpg"])
            rc = main([
                "sort", src, "--dest", dst,
                "--strategy", "typegroup",
                "--copy",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "documents", "doc.pdf").exists())
            self.assertTrue(Path(dst, "images", "photo.jpg").exists())

    def test_sort_flat_strategy(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt", "b.md"])
            rc = main(["sort", src, "--dest", dst, "--strategy", "flat", "--copy"])
            self.assertEqual(rc, 0)

    def test_sort_dry_run(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            rc = main(["sort", src, "--dest", dst, "--strategy", "extension", "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertFalse(Path(dst, "txt", "a.txt").exists())

    def test_sort_user_strategy_missing_rules(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.txt"])
            rc = main(["sort", src, "--dest", dst, "--strategy", "user"])
            self.assertEqual(rc, 1)

    def test_sort_regex_strategy(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["invoice.pdf", "report.pdf"])
            rc = main([
                "sort", src, "--dest", dst,
                "--strategy", "regex",
                "--regex-rules", r"^invoice:bills", r"\.pdf$:pdfs",
                "--copy",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "bills", "invoice.pdf").exists())
            self.assertTrue(Path(dst, "pdfs", "report.pdf").exists())

    def test_sort_with_include(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.md", "b.txt", "c.pdf"])
            rc = main([
                "sort", src, "--dest", dst,
                "--strategy", "extension",
                "--copy",
                "--include", "*.md",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(dst, "md", "a.md").exists())
            # .txt and .pdf should NOT be in dest
            self.assertFalse(Path(dst, "txt", "b.txt").exists())

    def test_sort_with_log_export(self):
        with tempfile.TemporaryDirectory() as src, \
             tempfile.TemporaryDirectory() as dst:
            _make_files(src, ["a.md"])
            log_out = os.path.join(dst, "log.json")
            rc = main([
                "sort", src, "--dest", dst,
                "--strategy", "extension",
                "--copy",
                "--log-out", log_out,
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(Path(log_out).exists())


class TestCLIHelp(unittest.TestCase):
    def test_no_command_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_invalid_strategy_exits(self):
        with self.assertRaises(SystemExit):
            main(["sort", "/tmp", "--dest", "/tmp/out", "--strategy", "invalid"])


if __name__ == "__main__":
    unittest.main()
