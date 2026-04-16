"""
strategies.py — 整理策略模組
==============================
提供可插拔的整理策略，每個策略負責把文件歸類到不同子目錄。

策略列表
--------
- ByFormatStrategy   : 按副檔名（格式）分類
- ByTagStrategy      : 按 Markdown frontmatter 中的 tags 分類
- ByDateStrategy     : 按文件最後修改時間（年/月）分類
- ByKeywordStrategy  : 按文件名或路徑中包含的關鍵字分類

使用範例
--------
>>> from lobster_porter.core import LobsterPorter
>>> from lobster_porter.strategies import ByFormatStrategy
>>> porter = LobsterPorter("/docs")
>>> strategy = ByFormatStrategy()
>>> strategy.apply(porter, src="/docs/inbox", dst="/docs/sorted")
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class BaseStrategy:
    """
    整理策略基類。
    子類必須實作 classify(file: Path) -> str 方法，
    回傳文件應歸入的子目錄名稱（相對於 dst）。
    """

    name: str = "base"

    def classify(self, file: Path) -> Optional[str]:
        """
        回傳文件應歸入的子目錄名稱。
        回傳 None 表示跳過此文件。
        """
        raise NotImplementedError

    def apply(
        self,
        porter,  # LobsterPorter instance
        src: str,
        dst: str,
        move: bool = False,
    ) -> Dict[str, List[Path]]:
        """
        對 src 目錄下所有文件執行本策略，
        分類後複製（或移動）到 dst/<子目錄>。

        參數
        ----
        porter : LobsterPorter 實例
        src    : 來源目錄
        dst    : 目標根目錄
        move   : True = 移動；False = 複製（預設）

        回傳每個子目錄對應已處理文件列表的字典。
        """
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()

        # 搜尋所有文件（不限格式，讓策略自行過濾）
        files = [f for f in src_p.rglob("*") if f.is_file()]

        result: Dict[str, List[Path]] = {}
        batch_records = []

        for f in files:
            subdir = self.classify(f)
            if subdir is None:
                continue

            target_dir = dst_p / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f.name

            if move:
                shutil.move(str(f), str(target))
                # 記錄為移動（可撤銷）
                from lobster_porter.core import OperationRecord
                batch_records.append(OperationRecord("move", str(target), str(f)))
            else:
                shutil.copy2(str(f), str(target))
                from lobster_porter.core import OperationRecord
                batch_records.append(OperationRecord("copy", str(f), str(target)))

            result.setdefault(subdir, []).append(target)

        # 將整批操作寫入 porter 歷史（便於撤銷）
        if batch_records:
            porter._history.append(batch_records)

        return result


# ── 具體策略 ────────────────────────────────────────────────────────────────

class ByFormatStrategy(BaseStrategy):
    """
    按副檔名分類：
      .md / .mdx  → markdown/
      .pdf        → pdf/
      .docx / .doc→ word/
      其他         → other/
    """

    name = "by_format"

    # 副檔名 → 子目錄名稱 映射
    EXT_MAP = {
        ".md":   "markdown",
        ".mdx":  "markdown",
        ".pdf":  "pdf",
        ".docx": "word",
        ".doc":  "word",
        ".txt":  "text",
        ".json": "json",
    }

    def classify(self, file: Path) -> str:
        return self.EXT_MAP.get(file.suffix.lower(), "other")


class ByTagStrategy(BaseStrategy):
    """
    讀取 Markdown frontmatter 中的 tags 欄位，
    將文件複製到每個 tag 對應的子目錄。

    若文件沒有 tags，歸入 untagged/。
    """

    name = "by_tag"

    # 簡單的 frontmatter tags 正則
    # 使用 [\s\S]*? 跨行匹配（替代 re.DOTALL），用 re.MULTILINE 令 ^ 匹配行首
    _TAG_RE = re.compile(
        r"^---[\s\S]*?^tags\s*:\s*\[?([^\]\n]+)\]?", re.MULTILINE
    )

    def _parse_tags(self, file: Path) -> List[str]:
        """從 Markdown frontmatter 提取標籤列表。"""
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        m = self._TAG_RE.search(text)
        if not m:
            return []

        # 支援逗號分隔或 YAML 列表格式
        raw = m.group(1)
        tags = [t.strip().strip("\"'") for t in raw.split(",") if t.strip()]
        return tags

    def classify(self, file: Path) -> Optional[str]:
        # ByTagStrategy 需要逐 tag 複製，不適用 classify 單值回傳。
        # 在此回傳第一個 tag；多 tag 場景請直接呼叫 apply_multi。
        if file.suffix.lower() not in (".md", ".mdx"):
            return None
        tags = self._parse_tags(file)
        return tags[0] if tags else "untagged"

    def apply(
        self,
        porter,
        src: str,
        dst: str,
        move: bool = False,
    ) -> Dict[str, List[Path]]:
        """
        重寫 apply：一個文件若有多個 tag，
        會被複製到多個目標目錄（每個 tag 各一份）。
        """
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()

        md_files = [
            f for f in src_p.rglob("*")
            if f.is_file() and f.suffix.lower() in (".md", ".mdx")
        ]

        result: Dict[str, List[Path]] = {}
        batch_records = []

        for f in md_files:
            tags = self._parse_tags(f)
            if not tags:
                tags = ["untagged"]

            for tag in tags:
                target_dir = dst_p / tag
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f.name

                if move and tag == tags[-1]:
                    # 最後一個 tag 才真正移動（其他 tag 用複製）
                    shutil.move(str(f), str(target))
                    from lobster_porter.core import OperationRecord
                    batch_records.append(OperationRecord("move", str(target), str(f)))
                else:
                    shutil.copy2(str(f), str(target))
                    from lobster_porter.core import OperationRecord
                    batch_records.append(OperationRecord("copy", str(f), str(target)))

                result.setdefault(tag, []).append(target)

        if batch_records:
            porter._history.append(batch_records)

        return result


class ByDateStrategy(BaseStrategy):
    """
    按文件最後修改時間（年/月）分類：
      例如 2024/03/
    """

    name = "by_date"

    def classify(self, file: Path) -> str:
        mtime = file.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        return f"{dt.year}/{dt.month:02d}"


class ByKeywordStrategy(BaseStrategy):
    """
    按文件名（或路徑）中包含的關鍵字分類。

    初始化時傳入 keywords 字典：
      { "子目錄名稱": ["關鍵字1", "關鍵字2"] }

    若文件名匹配某關鍵字，歸入對應子目錄；
    若無匹配，歸入 other/。
    """

    name = "by_keyword"

    def __init__(self, keywords: Dict[str, List[str]]):
        """
        參數
        ----
        keywords : 例如 {"api": ["api", "endpoint"], "guide": ["guide", "tutorial"]}
        """
        self.keywords = {
            subdir: [kw.lower() for kw in kws]
            for subdir, kws in keywords.items()
        }

    def classify(self, file: Path) -> str:
        name_lower = file.name.lower()
        for subdir, kws in self.keywords.items():
            if any(kw in name_lower for kw in kws):
                return subdir
        return "other"
