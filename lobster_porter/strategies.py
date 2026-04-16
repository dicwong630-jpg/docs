"""
strategies.py — 分類策略模組
定義可組合的檔案分類邏輯，供龍蝦搬運工根據策略自動路由檔案。
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict


class ClassificationStrategy(ABC):
    """
    分類策略抽象基類。
    所有分類策略必須實作 classify(file_path) 方法。
    """

    @abstractmethod
    def classify(self, file_path: str) -> Optional[str]:
        """
        判斷檔案應歸屬的分類標籤（資料夾名稱）。

        Args:
            file_path: 要分類的檔案路徑。

        Returns:
            分類標籤字串；若不匹配任何規則則回傳 None。
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ---------------------------------------------------------------------------
# 基於副檔名的分類策略
# ---------------------------------------------------------------------------

class FormatStrategy(ClassificationStrategy):
    """
    根據檔案副檔名自動分類。

    Example::

        strategy = FormatStrategy({
            "劇本": [".fountain", ".fdx", ".pdf"],
            "美術": [".psd", ".ai", ".png", ".jpg"],
            "音效": [".wav", ".mp3", ".aiff"],
            "影片": [".mp4", ".mov", ".avi"],
        })
        strategy.classify("scene_01.pdf")  # → "劇本"
    """

    DEFAULT_RULES: Dict[str, List[str]] = {
        "劇本": [".fountain", ".fdx", ".pdf", ".docx", ".txt"],
        "美術": [".psd", ".ai", ".png", ".jpg", ".jpeg", ".tiff", ".svg"],
        "音效": [".wav", ".mp3", ".aiff", ".flac", ".ogg"],
        "影片": [".mp4", ".mov", ".avi", ".mkv", ".prproj"],
        "資料": [".json", ".csv", ".xlsx", ".yaml", ".xml"],
        "提示詞": [".prompt", ".md"],
    }

    def __init__(self, rules: Optional[Dict[str, List[str]]] = None):
        """
        Args:
            rules: 分類標籤 → 副檔名列表的映射，若未提供則使用預設規則。
        """
        self.rules = rules or self.DEFAULT_RULES

    def classify(self, file_path: str) -> Optional[str]:
        suffix = Path(file_path).suffix.lower()
        for category, extensions in self.rules.items():
            if suffix in extensions:
                return category
        return None


# ---------------------------------------------------------------------------
# 基於關鍵字的分類策略
# ---------------------------------------------------------------------------

class KeywordStrategy(ClassificationStrategy):
    """
    根據檔名中的關鍵字自動分類。

    Example::

        strategy = KeywordStrategy({
            "分鏡": ["storyboard", "分鏡", "sb_"],
            "特效": ["vfx", "特效", "fx_"],
        })
        strategy.classify("scene_03_storyboard_v2.png")  # → "分鏡"
    """

    def __init__(self, rules: Dict[str, List[str]], case_sensitive: bool = False):
        """
        Args:
            rules:          分類標籤 → 關鍵字列表的映射。
            case_sensitive: 是否區分大小寫，預設不區分。
        """
        self.rules = rules
        self.case_sensitive = case_sensitive

    def classify(self, file_path: str) -> Optional[str]:
        name = Path(file_path).name
        if not self.case_sensitive:
            name = name.lower()
        for category, keywords in self.rules.items():
            for kw in keywords:
                check = kw if self.case_sensitive else kw.lower()
                if check in name:
                    return category
        return None


# ---------------------------------------------------------------------------
# 基於正則表達式的分類策略
# ---------------------------------------------------------------------------

class RegexStrategy(ClassificationStrategy):
    """
    根據正則表達式匹配檔名進行分類。

    Example::

        strategy = RegexStrategy({
            "場景": r"^scene_\\d+",
            "版本": r"_v\\d+\\.",
        })
    """

    def __init__(self, rules: Dict[str, str], case_sensitive: bool = False):
        """
        Args:
            rules:          分類標籤 → 正則表達式字串的映射。
            case_sensitive: 是否區分大小寫，預設不區分。
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        self._compiled = {
            category: re.compile(pattern, flags)
            for category, pattern in rules.items()
        }

    def classify(self, file_path: str) -> Optional[str]:
        name = Path(file_path).name
        for category, pattern in self._compiled.items():
            if pattern.search(name):
                return category
        return None


# ---------------------------------------------------------------------------
# 策略鏈（組合多個策略，按優先順序依次嘗試）
# ---------------------------------------------------------------------------

class StrategyChain(ClassificationStrategy):
    """
    將多個分類策略串聯，依序嘗試直到某策略返回非 None 結果。

    Example::

        chain = StrategyChain([keyword_strategy, format_strategy])
        chain.classify("scene_01_storyboard.pdf")
    """

    def __init__(self, strategies: List[ClassificationStrategy]):
        self.strategies = strategies

    def classify(self, file_path: str) -> Optional[str]:
        for strategy in self.strategies:
            result = strategy.classify(file_path)
            if result is not None:
                return result
        return None
