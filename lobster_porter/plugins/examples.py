"""
lobster_porter.plugins.examples
================================
示範策略插件範例與簡易測試用例。

提供兩個示範插件：

- :class:`ExtensionPlugin`  — 依副檔名（副檔名群組）分類
- :class:`DatePlugin`       — 依檔名中的日期前綴（YYYY-MM-DD 或 YYYYMMDD）分類

如何執行測試
------------
::

    python -m lobster_porter.plugins.examples

或使用 ``unittest``::

    python -m unittest lobster_porter.plugins.examples
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Dict, List, Optional

from .base import PluginBase, PLUGIN_REGISTRY
from ..strategies import ClassificationResult


# ---------------------------------------------------------------------------
# Plugin 1: ExtensionPlugin — 依副檔名群組分類
# ---------------------------------------------------------------------------

class ExtensionPlugin(PluginBase):
    """依副檔名分類策略插件。

    將副檔名映射到群組名稱（例如圖片、文件、影片），
    未匹配時分類到 ``default_category``。

    Parameters
    ----------
    ext_groups:
        ``{group_name: [".ext1", ".ext2", ...]}`` 字典。
        若為 ``None``，使用內建預設群組（images/docs/videos/archives）。
    default_category:
        無法匹配副檔名時的預設分類，預設 ``"others"``。

    Examples
    --------
    ::

        plugin = ExtensionPlugin()
        r = plugin.classify(Path("photo.jpg"))
        assert r.category == "images"
        assert ".jpg" in r.tags
    """

    name = "extension"

    # 內建預設副檔名群組
    _DEFAULT_GROUPS: Dict[str, List[str]] = {
        "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "docs":   [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
                   ".txt", ".md", ".mdx", ".rst"],
        "videos": [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"],
        "audios": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
        "archives": [".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"],
        "code":   [".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp",
                   ".h", ".css", ".html", ".json", ".yaml", ".yml", ".toml"],
    }

    def __init__(
        self,
        ext_groups: Optional[Dict[str, List[str]]] = None,
        default_category: str = "others",
    ) -> None:
        self.default_category = default_category
        # 建立副檔名 → 群組的反查映射
        groups = ext_groups if ext_groups is not None else self._DEFAULT_GROUPS
        self._ext_map: Dict[str, str] = {}
        for group, exts in groups.items():
            for ext in exts:
                self._ext_map[ext.lower()] = group

    def classify(self, path: Path) -> ClassificationResult:
        """依副檔名分類。"""
        path = Path(path)
        ext = path.suffix.lower()
        category = self._ext_map.get(ext, self.default_category)
        tags = [ext] if ext else []
        return ClassificationResult(
            src_path=path,
            category=category,
            tags=tags,
        )


# 自動登錄
ExtensionPlugin.register()


# ---------------------------------------------------------------------------
# Plugin 2: DatePlugin — 依檔名日期前綴分類
# ---------------------------------------------------------------------------

class DatePlugin(PluginBase):
    """依檔名中的日期前綴分類策略插件。

    識別以下格式的日期前綴：

    - ``YYYY-MM-DD_...``（例如 ``2024-03-15_report.pdf``）
    - ``YYYYMMDD_...``（例如 ``20240315_photo.jpg``）

    分類標籤格式為 ``YYYY-MM``（年-月），方便按月份彙整。
    無法識別日期時分類為 ``default_category``。

    Parameters
    ----------
    default_category:
        無日期前綴時的預設分類，預設 ``"undated"``。

    Examples
    --------
    ::

        plugin = DatePlugin()
        r = plugin.classify(Path("2024-03-15_invoice.pdf"))
        assert r.category == "2024-03"
        assert "2024-03-15" in r.tags
    """

    name = "date"

    # 支援的日期正則格式
    _DATE_PATTERNS = [
        re.compile(r"^(\d{4})-(\d{2})-(\d{2})"),  # YYYY-MM-DD
        re.compile(r"^(\d{4})(\d{2})(\d{2})"),      # YYYYMMDD
    ]

    def __init__(self, default_category: str = "undated") -> None:
        self.default_category = default_category

    def classify(self, path: Path) -> ClassificationResult:
        """依日期前綴分類。"""
        path = Path(path)
        stem = path.stem

        for pattern in self._DATE_PATTERNS:
            m = pattern.match(stem)
            if m:
                year, month, day = m.group(1), m.group(2), m.group(3)
                category = f"{year}-{month}"
                tags = [f"{year}-{month}-{day}"]
                return ClassificationResult(
                    src_path=path,
                    category=category,
                    tags=tags,
                )

        # 無日期前綴
        return ClassificationResult(
            src_path=path,
            category=self.default_category,
        )


# 自動登錄
DatePlugin.register()


# ---------------------------------------------------------------------------
# 簡易測試用例
# ---------------------------------------------------------------------------

class TestExtensionPlugin(unittest.TestCase):
    """ExtensionPlugin 單元測試。"""

    def setUp(self) -> None:
        self.plugin = ExtensionPlugin()

    def test_image_classification(self) -> None:
        """JPG 應分類為 images。"""
        result = self.plugin.classify(Path("photo.jpg"))
        self.assertEqual(result.category, "images")
        self.assertIn(".jpg", result.tags)

    def test_doc_classification(self) -> None:
        """PDF 應分類為 docs。"""
        result = self.plugin.classify(Path("report.pdf"))
        self.assertEqual(result.category, "docs")

    def test_code_classification(self) -> None:
        """Python 檔應分類為 code。"""
        result = self.plugin.classify(Path("script.py"))
        self.assertEqual(result.category, "code")

    def test_unknown_extension(self) -> None:
        """未知副檔名應分類為 others。"""
        result = self.plugin.classify(Path("data.xyz"))
        self.assertEqual(result.category, "others")

    def test_no_extension(self) -> None:
        """無副檔名的檔案應分類為 others。"""
        result = self.plugin.classify(Path("Makefile"))
        self.assertEqual(result.category, "others")

    def test_custom_ext_groups(self) -> None:
        """自訂副檔名群組應覆蓋預設。"""
        plugin = ExtensionPlugin(ext_groups={"data": [".csv", ".tsv"]})
        result = plugin.classify(Path("dataset.csv"))
        self.assertEqual(result.category, "data")

    def test_uppercase_extension(self) -> None:
        """大寫副檔名應不分大小寫地匹配。"""
        result = self.plugin.classify(Path("PHOTO.JPG"))
        self.assertEqual(result.category, "images")

    def test_registry(self) -> None:
        """ExtensionPlugin 應已登錄至 PLUGIN_REGISTRY。"""
        self.assertIn("extension", PLUGIN_REGISTRY)
        self.assertIs(PLUGIN_REGISTRY["extension"], ExtensionPlugin)


class TestDatePlugin(unittest.TestCase):
    """DatePlugin 單元測試。"""

    def setUp(self) -> None:
        self.plugin = DatePlugin()

    def test_dash_format(self) -> None:
        """YYYY-MM-DD 格式應分類為對應年月。"""
        result = self.plugin.classify(Path("2024-03-15_invoice.pdf"))
        self.assertEqual(result.category, "2024-03")
        self.assertIn("2024-03-15", result.tags)

    def test_compact_format(self) -> None:
        """YYYYMMDD 格式應分類為對應年月。"""
        result = self.plugin.classify(Path("20240315_photo.jpg"))
        self.assertEqual(result.category, "2024-03")
        self.assertIn("2024-03-15", result.tags)

    def test_no_date(self) -> None:
        """無日期前綴應分類為 undated。"""
        result = self.plugin.classify(Path("report_final.pdf"))
        self.assertEqual(result.category, "undated")
        self.assertEqual(result.tags, [])

    def test_custom_default_category(self) -> None:
        """自訂 default_category 應生效。"""
        plugin = DatePlugin(default_category="no_date")
        result = plugin.classify(Path("readme.md"))
        self.assertEqual(result.category, "no_date")

    def test_registry(self) -> None:
        """DatePlugin 應已登錄至 PLUGIN_REGISTRY。"""
        self.assertIn("date", PLUGIN_REGISTRY)
        self.assertIs(PLUGIN_REGISTRY["date"], DatePlugin)


# ---------------------------------------------------------------------------
# 直接執行測試入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
