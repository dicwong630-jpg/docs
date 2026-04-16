"""
tests/test_strategies.py — 分類策略單元測試
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

from lobster_porter.strategies import (
    CompositeStrategy,
    DateStrategy,
    ExtensionStrategy,
    FlatStrategy,
    RegexStrategy,
    SizeStrategy,
    TypeGroupStrategy,
    UserRuleStrategy,
)


class TestFlatStrategy(unittest.TestCase):
    def test_classify_returns_dot(self):
        s = FlatStrategy()
        self.assertEqual(s.classify(Path("deep/nested/file.txt")), ".")

    def test_classify_any_path(self):
        s = FlatStrategy()
        self.assertEqual(s.classify(Path("a/b/c/d/e.pdf")), ".")


class TestExtensionStrategy(unittest.TestCase):
    def setUp(self):
        self.s = ExtensionStrategy()

    def test_md_file(self):
        self.assertEqual(self.s.classify(Path("docs/readme.md")), "md")

    def test_pdf_file(self):
        self.assertEqual(self.s.classify(Path("report.PDF")), "pdf")

    def test_docx_file(self):
        self.assertEqual(self.s.classify(Path("letter.docx")), "docx")

    def test_no_extension(self):
        self.assertEqual(self.s.classify(Path("Makefile")), "no_extension")

    def test_custom_unknown_bucket(self):
        s = ExtensionStrategy(unknown_bucket="misc")
        self.assertEqual(s.classify(Path("Makefile")), "misc")

    def test_case_insensitive(self):
        self.assertEqual(self.s.classify(Path("IMAGE.JPG")), "jpg")


class TestDateStrategy(unittest.TestCase):
    def test_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as fh:
            fh.write(b"test")
            name = fh.name
        try:
            s = DateStrategy()
            result = s.classify(Path(name))
            # 應為 YYYY/MM 格式
            self.assertRegex(result, r"^\d{4}/\d{2}$")
        finally:
            os.unlink(name)

    def test_nonexistent_file(self):
        s = DateStrategy()
        result = s.classify(Path("/nonexistent/path/file.txt"))
        self.assertEqual(result, "unknown_date")


class TestSizeStrategy(unittest.TestCase):
    def setUp(self):
        self.s = SizeStrategy()

    def test_small_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            fh.write(b"x" * 100)
            name = fh.name
        try:
            self.assertEqual(self.s.classify(Path(name)), "small")
        finally:
            os.unlink(name)

    def test_medium_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            fh.write(b"x" * (200 * 1024))  # 200 KB
            name = fh.name
        try:
            self.assertEqual(self.s.classify(Path(name)), "medium")
        finally:
            os.unlink(name)

    def test_nonexistent_file(self):
        self.assertEqual(self.s.classify(Path("/no/file.bin")), "unknown_size")


class TestRegexStrategy(unittest.TestCase):
    def setUp(self):
        rules = [
            (r"^report_\d{4}", "reports"),
            (r"\.pdf$", "pdf_docs"),
            (r"\.docx?$", "word_docs"),
        ]
        self.s = RegexStrategy(rules)

    def test_first_match_wins(self):
        self.assertEqual(self.s.classify(Path("report_2024.pdf")), "reports")

    def test_second_rule(self):
        self.assertEqual(self.s.classify(Path("invoice.pdf")), "pdf_docs")

    def test_third_rule(self):
        self.assertEqual(self.s.classify(Path("letter.docx")), "word_docs")

    def test_no_match_default(self):
        self.assertEqual(self.s.classify(Path("unknown.bin")), "other")

    def test_case_insensitive_by_default(self):
        self.assertEqual(self.s.classify(Path("Invoice.PDF")), "pdf_docs")

    def test_case_sensitive(self):
        s = RegexStrategy([(r"\.PDF$", "pdf_docs")], flags=0)  # no IGNORECASE
        self.assertEqual(s.classify(Path("file.pdf")), "other")
        self.assertEqual(s.classify(Path("file.PDF")), "pdf_docs")


class TestUserRuleStrategy(unittest.TestCase):
    def test_load_json_rules(self):
        config = {
            "default": "misc",
            "rules": [
                {"pattern": r"\.pdf$", "category": "pdf"},
                {"pattern": r"\.docx?$", "category": "word"},
            ]
        }
        import json
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(config, fh)
            name = fh.name
        try:
            s = UserRuleStrategy(name)
            self.assertEqual(s.classify(Path("file.pdf")), "pdf")
            self.assertEqual(s.classify(Path("file.doc")), "word")
            self.assertEqual(s.classify(Path("file.bin")), "misc")
        finally:
            os.unlink(name)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            UserRuleStrategy("/no/such/file.json")


class TestTypeGroupStrategy(unittest.TestCase):
    def setUp(self):
        self.s = TypeGroupStrategy()

    def test_pdf_is_document(self):
        self.assertEqual(self.s.classify(Path("report.pdf")), "documents")

    def test_docx_is_document(self):
        self.assertEqual(self.s.classify(Path("letter.docx")), "documents")

    def test_jpg_is_image(self):
        self.assertEqual(self.s.classify(Path("photo.jpg")), "images")

    def test_png_is_image(self):
        self.assertEqual(self.s.classify(Path("icon.png")), "images")

    def test_mp3_is_audio(self):
        self.assertEqual(self.s.classify(Path("song.mp3")), "audio")

    def test_mp4_is_video(self):
        self.assertEqual(self.s.classify(Path("clip.mp4")), "video")

    def test_py_is_code(self):
        self.assertEqual(self.s.classify(Path("script.py")), "code")

    def test_zip_is_archive(self):
        self.assertEqual(self.s.classify(Path("backup.zip")), "archives")

    def test_unknown_is_other(self):
        self.assertEqual(self.s.classify(Path("file.xyz")), "other")


class TestCompositeStrategy(unittest.TestCase):
    def test_first_match_wins(self):
        s = CompositeStrategy([FlatStrategy(), ExtensionStrategy()])
        # FlatStrategy returns ".", so ExtensionStrategy should be tried
        # But FlatStrategy always returns ".", which is falsy in composite
        result = s.classify(Path("file.md"))
        self.assertEqual(result, "md")

    def test_first_non_dot_wins(self):
        s = CompositeStrategy([ExtensionStrategy(), DateStrategy()])
        self.assertEqual(s.classify(Path("file.md")), "md")

    def test_requires_at_least_one_strategy(self):
        with self.assertRaises(ValueError):
            CompositeStrategy([])

    def test_join_mode(self):
        # In join mode, results are concatenated
        rules = [(r"\.md$", "markdown")]
        s = CompositeStrategy(
            [RegexStrategy(rules, default_bucket="other"), ExtensionStrategy()],
            join=True,
        )
        result = s.classify(Path("readme.md"))
        self.assertIn("/", result)  # Should be "markdown/md"


if __name__ == "__main__":
    unittest.main()
