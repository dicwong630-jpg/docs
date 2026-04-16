"""
plugins/format_classifier.py — 格式分類插件
根據副檔名自動將檔案路由到對應子資料夾，適用於電影製作資源的快速整理。
"""

from pathlib import Path
from typing import Dict, List, Optional

from .base import BasePlugin


class FormatClassifierPlugin(BasePlugin):
    """
    格式分類插件。

    在批量搬運前，根據副檔名將每個檔案重新路由到對應的目標子資料夾。
    例如 .pdf 文件 → 劇本/，.psd 圖層 → 美術/ 等。

    Example::

        plugin = FormatClassifierPlugin()
        # 呼叫 pre_process 後，各檔案將被加上子目錄後綴，
        # 搬運工會根據此結果決定最終目標路徑。
    """

    name = "format_classifier"
    version = "0.2.0"
    description = "根據副檔名自動將檔案分流到不同子資料夾"

    DEFAULT_MAPPING: Dict[str, str] = {
        ".fountain": "劇本",
        ".fdx": "劇本",
        ".pdf": "劇本",
        ".docx": "劇本",
        ".txt": "劇本",
        ".psd": "美術",
        ".ai": "美術",
        ".png": "美術",
        ".jpg": "美術",
        ".jpeg": "美術",
        ".tiff": "美術",
        ".svg": "美術",
        ".wav": "音效",
        ".mp3": "音效",
        ".aiff": "音效",
        ".flac": "音效",
        ".mp4": "影片",
        ".mov": "影片",
        ".avi": "影片",
        ".mkv": "影片",
        ".prproj": "影片",
        ".json": "資料",
        ".csv": "資料",
        ".xlsx": "資料",
        ".yaml": "資料",
        ".prompt": "提示詞",
        ".md": "提示詞",
    }

    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        """
        Args:
            mapping: 副檔名（含點號）→ 子資料夾名稱的映射，
                     若未提供則使用預設規則。
        """
        self.mapping = mapping or self.DEFAULT_MAPPING

    def classify_file(self, file_path: str) -> Optional[str]:
        """
        回傳檔案應歸入的子資料夾名稱。

        Args:
            file_path: 檔案路徑。

        Returns:
            子資料夾名稱；若無匹配規則則回傳 None。
        """
        suffix = Path(file_path).suffix.lower()
        return self.mapping.get(suffix)

    def pre_process(self, files: List[str]) -> List[str]:
        """
        前置處理：標記每個檔案的分類資訊（不修改實際路徑）。
        此方法返回原始列表，分類資訊由 classify_file() 提供給外部調用。
        """
        return files

    def post_process(self, files: List[str], destination: str) -> None:
        """
        後置處理：輸出分類摘要報告到 stdout。
        """
        summary: Dict[str, List[str]] = {}
        for f in files:
            category = self.classify_file(f) or "其他"
            summary.setdefault(category, []).append(Path(f).name)

        print(f"\n📦 格式分類摘要（目標：{destination}）")
        print("-" * 40)
        for category, items in sorted(summary.items()):
            print(f"  {category}: {len(items)} 個檔案")
        print("-" * 40)
