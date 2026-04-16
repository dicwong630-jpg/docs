"""
core.py — 龍蝦搬運工核心模組
==============================
提供 LobsterPorter 主類，負責：
  - 搜尋文件 (search)
  - 單一 / 批量移動、複製 (move / copy / batch_*)
  - 撤銷最近一次操作 (undo)
  - 生成索引 (generate_index)
  - 按標籤導出 (export_by_tag)
  - 載入並執行插件 (run_plugin)
"""

import os
import shutil
import json
import fnmatch
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


# ── 支援的文件格式（可擴充） ─────────────────────────────────────────────────
# 要新增格式，直接在此字典加入條目即可，例如：
#   SUPPORTED_FORMATS["rst"] = [".rst"]
SUPPORTED_FORMATS = {
    "markdown": [".md", ".mdx"],
    "pdf":      [".pdf"],
    "word":     [".docx", ".doc"],
    "text":     [".txt"],
    "json":     [".json"],
}

# 所有支援副檔名的扁平列表
ALL_EXTENSIONS: List[str] = [
    ext for exts in SUPPORTED_FORMATS.values() for ext in exts
]


class OperationRecord:
    """記錄單次操作，用於撤銷。"""

    def __init__(self, op_type: str, src: str, dst: str):
        # op_type: "move" | "copy"
        self.op_type = op_type
        self.src = src
        self.dst = dst

    def __repr__(self) -> str:
        return f"<OperationRecord {self.op_type}: {self.src!r} → {self.dst!r}>"


class LobsterPorter:
    """
    龍蝦搬運工主類
    ===============
    所有搬運、整理、索引、插件執行功能的入口點。

    使用範例
    --------
    >>> porter = LobsterPorter(root="/path/to/docs")
    >>> results = porter.search(pattern="*.md")
    >>> porter.batch_move(results[:5], dst="/path/to/docs/archive")
    >>> porter.undo()
    """

    def __init__(self, root: str = "."):
        # 文件倉庫根目錄
        self.root = Path(root).resolve()
        # 操作歷史棧，用於撤銷（每個元素是 List[OperationRecord]）
        self._history: List[List[OperationRecord]] = []
        # 已載入的插件字典：name → plugin instance
        self._plugins: Dict[str, object] = {}

    # ── 搜尋 ────────────────────────────────────────────────────────────────

    def search(
        self,
        path: Optional[str] = None,
        pattern: str = "*",
        formats: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> List[Path]:
        """
        搜尋符合條件的文件。

        參數
        ----
        path      : 搜尋起點目錄（預設倉庫根目錄）
        pattern   : 文件名 glob 模式（如 "*.md"、"intro*"）
        formats   : 限制格式列表，例如 ["markdown", "pdf"]
                    None 表示搜尋所有支援格式
        recursive : 是否遞迴子目錄

        回傳
        ----
        Path 物件列表
        """
        base = Path(path).resolve() if path else self.root

        # 決定允許的副檔名集合
        allowed_exts: Optional[set] = None
        if formats:
            allowed_exts = set()
            for fmt in formats:
                allowed_exts.update(SUPPORTED_FORMATS.get(fmt, []))

        results: List[Path] = []
        walker = base.rglob(pattern) if recursive else base.glob(pattern)
        for p in walker:
            if not p.is_file():
                continue
            # 若有格式限制，檢查副檔名
            if allowed_exts and p.suffix.lower() not in allowed_exts:
                continue
            results.append(p)

        return sorted(results)

    # ── 移動 / 複製 ─────────────────────────────────────────────────────────

    def move(self, src: str, dst: str) -> Path:
        """
        移動單一文件或目錄。

        - 目標若為目錄，文件移至該目錄內。
        - 自動建立不存在的中間目錄。

        回傳移動後的目標路徑。
        """
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()

        if dst_p.is_dir():
            dst_p = dst_p / src_p.name

        # 確保目標父目錄存在
        dst_p.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_p), str(dst_p))

        # 記錄操作（移動的撤銷 = 再移回來）
        self._history.append([OperationRecord("move", str(dst_p), str(src_p))])
        return dst_p

    def copy(self, src: str, dst: str) -> Path:
        """
        複製單一文件或目錄。

        - 目標若為目錄，文件複製至該目錄內。
        - 自動建立不存在的中間目錄。

        回傳複製後的目標路徑。
        """
        src_p = Path(src).resolve()
        dst_p = Path(dst).resolve()

        if dst_p.is_dir():
            dst_p = dst_p / src_p.name

        dst_p.parent.mkdir(parents=True, exist_ok=True)

        if src_p.is_dir():
            shutil.copytree(str(src_p), str(dst_p))
        else:
            shutil.copy2(str(src_p), str(dst_p))

        # 撤銷複製 = 刪除複製出的目標
        self._history.append([OperationRecord("copy", str(src_p), str(dst_p))])
        return dst_p

    def batch_move(self, files: List[str], dst: str) -> List[Path]:
        """
        批量移動文件到同一目標目錄。

        回傳所有目標路徑列表。
        整批操作記錄為一個歷史條目，可一次性撤銷。
        """
        dst_p = Path(dst).resolve()
        dst_p.mkdir(parents=True, exist_ok=True)

        batch_records: List[OperationRecord] = []
        moved: List[Path] = []

        for f in files:
            src_p = Path(f).resolve()
            target = dst_p / src_p.name
            shutil.move(str(src_p), str(target))
            batch_records.append(OperationRecord("move", str(target), str(src_p)))
            moved.append(target)

        if batch_records:
            self._history.append(batch_records)

        return moved

    def batch_copy(self, files: List[str], dst: str) -> List[Path]:
        """
        批量複製文件到同一目標目錄。

        回傳所有目標路徑列表。
        整批操作記錄為一個歷史條目，可一次性撤銷。
        """
        dst_p = Path(dst).resolve()
        dst_p.mkdir(parents=True, exist_ok=True)

        batch_records: List[OperationRecord] = []
        copied: List[Path] = []

        for f in files:
            src_p = Path(f).resolve()
            target = dst_p / src_p.name
            if src_p.is_dir():
                shutil.copytree(str(src_p), str(target))
            else:
                shutil.copy2(str(src_p), str(target))
            batch_records.append(OperationRecord("copy", str(src_p), str(target)))
            copied.append(target)

        if batch_records:
            self._history.append(batch_records)

        return copied

    # ── 撤銷 ────────────────────────────────────────────────────────────────

    def undo(self) -> bool:
        """
        撤銷最近一次操作（支援批量撤銷）。

        回傳 True 表示成功；False 表示歷史為空。
        """
        if not self._history:
            print("（無可撤銷的操作）")
            return False

        last_batch = self._history.pop()
        for record in last_batch:
            src_p = Path(record.src)
            dst_p = Path(record.dst)

            if record.op_type == "move":
                # 把文件移回原位
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_p), str(dst_p))

            elif record.op_type == "copy":
                # 刪除複製出的文件／目錄
                if dst_p.is_dir():
                    shutil.rmtree(str(dst_p))
                elif dst_p.exists():
                    dst_p.unlink()

        print(f"已撤銷 {len(last_batch)} 個操作。")
        return True

    # ── 索引生成 ────────────────────────────────────────────────────────────

    def generate_index(
        self,
        path: Optional[str] = None,
        output: Optional[str] = None,
        formats: Optional[List[str]] = None,
    ) -> str:
        """
        掃描目錄，生成 Markdown 格式的文件索引。

        參數
        ----
        path    : 掃描起點（預設倉庫根目錄）
        output  : 索引文件輸出路徑（None 則只回傳字串，不寫入）
        formats : 限制格式（None 表示所有支援格式）

        回傳 Markdown 字串。
        """
        base = Path(path).resolve() if path else self.root
        files = self.search(path=str(base), formats=formats)

        lines = [f"# 文件索引 — {base.name}\n", ""]
        for f in files:
            rel = f.relative_to(base)
            lines.append(f"- [{rel}]({rel})")
        lines.append("")
        index_md = "\n".join(lines)

        if output:
            out_p = Path(output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(index_md, encoding="utf-8")
            print(f"索引已寫入 {out_p}")

        return index_md

    # ── 按標籤導出 ──────────────────────────────────────────────────────────

    def export_by_tag(
        self,
        tag: str,
        dst: str,
        path: Optional[str] = None,
    ) -> List[Path]:
        """
        搜尋在 YAML frontmatter 或文件內容中含有指定標籤的 Markdown 文件，
        並批量複製到目標目錄。

        參數
        ----
        tag  : 要搜尋的標籤字串（大小寫不敏感）
        dst  : 目標目錄
        path : 搜尋起點（預設倉庫根目錄）

        回傳已複製的文件路徑列表。
        """
        base = Path(path).resolve() if path else self.root
        md_files = self.search(path=str(base), formats=["markdown"])

        matched: List[str] = []
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if tag.lower() in content.lower():
                matched.append(str(f))

        if not matched:
            print(f"未找到含有標籤「{tag}」的文件。")
            return []

        return self.batch_copy(matched, dst)

    # ── 插件系統 ────────────────────────────────────────────────────────────

    def register_plugin(self, plugin: "BasePlugin") -> None:  # type: ignore[name-defined]
        """
        註冊一個插件實例。

        插件必須繼承自 lobster_porter.plugins.base.BasePlugin。
        """
        self._plugins[plugin.name] = plugin
        print(f"插件「{plugin.name}」已載入。")

    def run_plugin(self, name: str, **kwargs) -> object:
        """
        按名稱執行已載入的插件。

        額外 kwargs 會傳遞給插件的 run() 方法。
        """
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(
                f"插件「{name}」未找到。已載入插件：{list(self._plugins)}"
            )
        return plugin.run(self, **kwargs)

    def list_plugins(self) -> List[str]:
        """回傳所有已載入插件名稱的列表。"""
        return list(self._plugins.keys())

    # ── 輔助工具 ────────────────────────────────────────────────────────────

    def show_history(self) -> None:
        """印出操作歷史（用於除錯）。"""
        if not self._history:
            print("（操作歷史為空）")
            return
        for i, batch in enumerate(self._history, 1):
            print(f"[{i}] {len(batch)} 個操作")
            for rec in batch:
                print(f"      {rec}")
