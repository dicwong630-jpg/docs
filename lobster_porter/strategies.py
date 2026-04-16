"""
lobster_porter.strategies
=========================
提供根據目錄、檔名或 meta 資訊決定分類標籤的策略類別。

所有策略繼承自 :class:`StrategyBase`，實作 ``classify`` 方法並回傳
:class:`ClassificationResult`。

內建策略
--------
- :class:`DirectoryStrategy`  — 依來源目錄層次（第一層子目錄名稱）分類
- :class:`KeywordStrategy`    — 依檔名關鍵字自動分類
- :class:`MetaStrategy`       — 依讀取檔案頭部 meta（YAML front-matter / JSON）分類

可擴展性
--------
繼承 :class:`StrategyBase` 並實作 ``classify``，即可註冊自訂策略::

    from lobster_porter.strategies import StrategyBase, ClassificationResult
    from pathlib import Path

    class MyStrategy(StrategyBase):
        name = "my_strategy"

        def classify(self, path: Path) -> ClassificationResult:
            # 自訂邏輯 …
            return ClassificationResult(src_path=path, category="custom")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    """單一檔案的分類結果。

    Attributes
    ----------
    src_path:
        原始檔案路徑。
    category:
        分配到的分類標籤（目錄名稱）。
    tags:
        附加的標籤列表（可為空）。
    meta:
        從檔案解析出的 meta 字典（可為空）。
    dst_path:
        分類後目的路徑，在 :func:`~lobster_porter.core.batch_classify`
        執行後才會被填入。
    """

    src_path: Path
    category: str
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, object] = field(default_factory=dict)
    dst_path: Optional[Path] = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ClassificationResult("
            f"src={self.src_path.name!r}, "
            f"category={self.category!r}, "
            f"tags={self.tags!r})"
        )


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class StrategyBase:
    """所有分類策略的抽象基礎類別。

    子類別必須：

    1. 設定唯一的 ``name`` 類別屬性。
    2. 實作 :meth:`classify` 方法。
    """

    #: 策略唯一識別名稱，子類別必須覆寫
    name: str = "base"

    def classify(self, path: Path) -> ClassificationResult:
        """對單一檔案執行分類，回傳 :class:`ClassificationResult`。

        Parameters
        ----------
        path:
            待分類的檔案路徑（絕對或相對均可）。

        Returns
        -------
        ClassificationResult
            包含 ``category``、``tags`` 與 ``meta`` 的結果物件。

        Raises
        ------
        NotImplementedError
            若子類別未實作此方法。
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement classify()")


# ---------------------------------------------------------------------------
# Built-in strategies
# ---------------------------------------------------------------------------

class DirectoryStrategy(StrategyBase):
    """依來源目錄層次分類策略。

    規則：取檔案相對根目錄的第一層子目錄名稱做為分類標籤。
    若檔案直接位於根目錄（無子目錄），則分類為 ``"root"``。

    Parameters
    ----------
    root:
        計算相對路徑的根目錄。若為 ``None``，則使用檔案的父目錄名稱。
    default_category:
        無法判斷層次時的預設分類標籤，預設 ``"root"``。

    Examples
    --------
    ::

        from lobster_porter.strategies import DirectoryStrategy
        from pathlib import Path

        s = DirectoryStrategy(root=Path("/data"))
        r = s.classify(Path("/data/images/photo.jpg"))
        assert r.category == "images"
    """

    name = "directory"

    def __init__(
        self,
        root: Optional[Path] = None,
        default_category: str = "root",
    ) -> None:
        self.root = root
        self.default_category = default_category

    def classify(self, path: Path) -> ClassificationResult:
        """依目錄層次分類。"""
        path = Path(path)
        category = self.default_category

        if self.root:
            try:
                rel = path.relative_to(self.root)
                parts = rel.parts
                # 第一層子目錄名稱即為分類
                category = parts[0] if len(parts) > 1 else self.default_category
            except ValueError:
                # path 不在 root 之下，退回父目錄名稱
                category = path.parent.name or self.default_category
        else:
            # 未指定 root：使用父目錄名稱
            category = path.parent.name or self.default_category

        return ClassificationResult(src_path=path, category=category)


class KeywordStrategy(StrategyBase):
    """依檔名關鍵字自動分類策略。

    Parameters
    ----------
    keywords:
        關鍵字列表。檔名（不含副檔名，不分大小寫）包含某個關鍵字時，
        即分類到對應的標籤。可傳入字串列表（分類名稱即關鍵字本身），
        或傳入 ``{category: [kw1, kw2]}`` 字典指定對應關係。
    default_category:
        無關鍵字匹配時的預設分類標籤，預設 ``"misc"``。

    Examples
    --------
    使用字串列表::

        s = KeywordStrategy(keywords=["invoice", "report", "photo"])
        r = s.classify(Path("invoice_2024.pdf"))
        assert r.category == "invoice"

    使用字典::

        s = KeywordStrategy(
            keywords={"finance": ["invoice", "receipt"], "media": ["photo", "video"]}
        )
    """

    name = "keyword"

    def __init__(
        self,
        keywords: List[str] | Dict[str, List[str]] | None = None,
        default_category: str = "misc",
    ) -> None:
        self.default_category = default_category
        # 統一轉換為 {category: [pattern, ...]} 字典
        if keywords is None:
            self._mapping: Dict[str, List[str]] = {}
        elif isinstance(keywords, list):
            self._mapping = {kw: [kw] for kw in keywords}
        else:
            self._mapping = dict(keywords)

    def classify(self, path: Path) -> ClassificationResult:
        """依檔名關鍵字分類。"""
        stem = path.stem.lower()
        matched_category = self.default_category
        matched_tags: List[str] = []

        for category, patterns in self._mapping.items():
            for pattern in patterns:
                if re.search(re.escape(pattern.lower()), stem):
                    matched_category = category
                    matched_tags.append(pattern)
                    break  # 一個 category 只需匹配一次

        return ClassificationResult(
            src_path=path,
            category=matched_category,
            tags=matched_tags,
        )


class MetaStrategy(StrategyBase):
    """依讀取檔案頭部 meta 資訊分類策略。

    支援兩種 meta 格式：

    - **YAML front-matter**：以 ``---`` 包圍的 YAML 區塊（常見於 MDX/MD 檔案）。
    - **JSON**：以 ``{`` 開頭的 JSON 物件（常見於 JSON 設定檔）。

    從 meta 中讀取 ``category`` 欄位做為分類標籤，並將其餘欄位存入結果的
    ``meta`` 字典；若存在 ``tags`` 欄位（list 或逗號分隔字串）也一併擷取。

    Parameters
    ----------
    category_key:
        meta 中代表分類標籤的欄位名稱，預設 ``"category"``。
    tags_key:
        meta 中代表標籤的欄位名稱，預設 ``"tags"``。
    default_category:
        meta 中無分類欄位時的預設標籤，預設 ``"uncategorized"``。
    encoding:
        讀取檔案時使用的編碼，預設 ``"utf-8"``。

    Examples
    --------
    ::

        # file: doc.mdx
        # ---
        # category: finance
        # tags: [invoice, 2024]
        # ---

        from lobster_porter.strategies import MetaStrategy
        r = MetaStrategy().classify(Path("doc.mdx"))
        assert r.category == "finance"
        assert "invoice" in r.tags
    """

    name = "meta"

    def __init__(
        self,
        category_key: str = "category",
        tags_key: str = "tags",
        default_category: str = "uncategorized",
        encoding: str = "utf-8",
    ) -> None:
        self.category_key = category_key
        self.tags_key = tags_key
        self.default_category = default_category
        self.encoding = encoding

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_meta(self, path: Path) -> Dict[str, object]:
        """嘗試從檔案頭部解析 meta，失敗時回傳空字典。"""
        try:
            content = path.read_text(encoding=self.encoding, errors="ignore")
        except OSError:
            return {}

        # 嘗試 YAML front-matter
        fm = self._parse_yaml_frontmatter(content)
        if fm:
            return fm

        # 嘗試 JSON
        stripped = content.lstrip()
        if stripped.startswith("{"):
            return self._parse_json(stripped)

        return {}

    @staticmethod
    def _parse_yaml_frontmatter(content: str) -> Dict[str, object]:
        """解析 YAML front-matter（不依賴 PyYAML，採簡易正則）。"""
        pattern = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
        match = pattern.match(content)
        if not match:
            return {}
        fm: Dict[str, object] = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # 嘗試解析列表 [a, b, c]
                list_match = re.match(r"^\[(.*)\]$", value)
                if list_match:
                    items = [v.strip().strip("'\"") for v in list_match.group(1).split(",")]
                    fm[key] = [i for i in items if i]
                else:
                    fm[key] = value.strip("'\"")
        return fm

    @staticmethod
    def _parse_json(content: str) -> Dict[str, object]:
        """嘗試將 content 解析為 JSON 物件，失敗回傳空字典。"""
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        return {}

    @staticmethod
    def _to_tags(value: object) -> List[str]:
        """將 meta tags 欄位值統一轉為字串列表。"""
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        return []

    # ------------------------------------------------------------------
    # classify
    # ------------------------------------------------------------------

    def classify(self, path: Path) -> ClassificationResult:
        """依 meta 欄位分類。"""
        meta = self._parse_meta(path)
        category = str(meta.get(self.category_key, self.default_category)) or self.default_category
        tags = self._to_tags(meta.get(self.tags_key, []))
        return ClassificationResult(
            src_path=path,
            category=category,
            tags=tags,
            meta=meta,
        )
