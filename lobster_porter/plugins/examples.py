"""
plugins/examples.py — 範例插件
================================
提供四個開箱即用的示範插件：

1. IndexGeneratorPlugin  — 掃描目錄，生成 Markdown 索引文件
2. TagExporterPlugin     — 按標籤篩選並複製 Markdown 文件
3. BulkRenamePlugin      — 批量重命名文件（前綴 / 後綴 / 替換）
4. FormatScannerPlugin   — 統計各格式文件數量並報告
"""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlugin


# ── 1. 索引生成插件 ─────────────────────────────────────────────────────────

class IndexGeneratorPlugin(BasePlugin):
    """
    掃描指定目錄，生成 Markdown 索引文件（INDEX.md）。

    使用方式（程式碼）
    ------------------
    >>> from lobster_porter import LobsterPorter
    >>> from lobster_porter.plugins import IndexGeneratorPlugin
    >>> porter = LobsterPorter("/docs")
    >>> porter.register_plugin(IndexGeneratorPlugin())
    >>> porter.run_plugin("index_generator", path="/docs/api-reference", output="/docs/api-reference/INDEX.md")

    CLI 使用方式
    ------------
    lobster plugin index_generator --path /docs/api-reference --output /docs/api-reference/INDEX.md
    """

    name = "index_generator"
    description = "掃描目錄，生成 Markdown 格式索引文件"

    def run(
        self,
        porter,
        path: Optional[str] = None,
        output: Optional[str] = None,
        formats: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """
        參數
        ----
        path    : 要索引的目錄（預設 porter.root）
        output  : 輸出索引文件路徑（預設 <path>/INDEX.md）
        formats : 限制格式，例如 ["markdown"]
        """
        base = Path(path).resolve() if path else porter.root
        out_path = Path(output).resolve() if output else base / "INDEX.md"

        index_md = porter.generate_index(
            path=str(base),
            output=str(out_path),
            formats=formats,
        )

        print(f"[index_generator] 索引已生成：{out_path}")
        return index_md


# ── 2. 標籤導出插件 ─────────────────────────────────────────────────────────

class TagExporterPlugin(BasePlugin):
    """
    按標籤批量篩選 Markdown 文件並複製到指定目錄。

    使用方式（程式碼）
    ------------------
    >>> porter.register_plugin(TagExporterPlugin())
    >>> porter.run_plugin("tag_exporter", tag="quickstart", dst="/docs/export/quickstart")

    CLI 使用方式
    ------------
    lobster plugin tag_exporter --tag quickstart --dst /docs/export/quickstart
    """

    name = "tag_exporter"
    description = "按標籤篩選 Markdown 文件並批量導出"

    def run(
        self,
        porter,
        tag: str = "",
        dst: str = "./export",
        path: Optional[str] = None,
        **kwargs,
    ) -> List[Path]:
        """
        參數
        ----
        tag  : 要篩選的標籤（必填）
        dst  : 匯出目錄
        path : 搜尋起點（預設 porter.root）
        """
        if not tag:
            raise ValueError("tag_exporter 需要提供 tag 參數。")

        exported = porter.export_by_tag(tag=tag, dst=dst, path=path)
        print(f"[tag_exporter] 標籤「{tag}」：共導出 {len(exported)} 個文件 → {dst}")
        return exported


# ── 3. 批量重命名插件 ────────────────────────────────────────────────────────

class BulkRenamePlugin(BasePlugin):
    """
    批量重命名文件，支援三種模式：
      - prefix  : 在文件名前加前綴
      - suffix  : 在文件名（副檔名之前）加後綴
      - replace : 替換文件名中的指定字串

    使用方式（程式碼）
    ------------------
    >>> porter.register_plugin(BulkRenamePlugin())
    >>> porter.run_plugin(
    ...     "bulk_rename",
    ...     path="/docs/essentials",
    ...     mode="prefix",
    ...     value="2024_",
    ...     pattern="*.md",
    ... )

    CLI 使用方式
    ------------
    lobster plugin bulk_rename --path /docs/essentials --mode prefix --value 2024_ --pattern "*.md"
    """

    name = "bulk_rename"
    description = "批量重命名文件（prefix / suffix / replace 模式）"

    def run(
        self,
        porter,
        path: Optional[str] = None,
        mode: str = "prefix",
        value: str = "",
        old: str = "",
        new: str = "",
        pattern: str = "*",
        dry_run: bool = False,
        **kwargs,
    ) -> List[Dict[str, str]]:
        """
        參數
        ----
        path    : 目標目錄（預設 porter.root）
        mode    : "prefix" | "suffix" | "replace"
        value   : prefix / suffix 模式的字串
        old     : replace 模式的舊字串
        new     : replace 模式的新字串
        pattern : 文件名 glob 篩選（預設 "*"）
        dry_run : True = 只顯示預覽，不實際重命名
        """
        base = Path(path).resolve() if path else porter.root
        files = [f for f in base.glob(pattern) if f.is_file()]

        renames: List[Dict[str, str]] = []
        batch_records = []

        for f in files:
            stem = f.stem
            suffix = f.suffix

            if mode == "prefix":
                new_name = f"{value}{stem}{suffix}"
            elif mode == "suffix":
                new_name = f"{stem}{value}{suffix}"
            elif mode == "replace":
                new_name = f.name.replace(old, new)
            else:
                raise ValueError(f"未知模式：{mode}。請選擇 prefix / suffix / replace。")

            target = f.parent / new_name
            renames.append({"from": str(f), "to": str(target)})

            if not dry_run:
                f.rename(target)
                # 重命名記錄為移動（可撤銷）
                from lobster_porter.core import OperationRecord
                batch_records.append(OperationRecord("move", str(target), str(f)))

        if batch_records:
            porter._history.append(batch_records)

        mode_tag = "[DRY RUN] " if dry_run else ""
        print(f"[bulk_rename] {mode_tag}重命名 {len(renames)} 個文件（模式：{mode}）")
        for r in renames:
            print(f"  {Path(r['from']).name!r}  →  {Path(r['to']).name!r}")

        return renames


# ── 4. 格式掃描插件 ─────────────────────────────────────────────────────────

class FormatScannerPlugin(BasePlugin):
    """
    統計倉庫內各格式文件的數量，並列印報告。

    使用方式（程式碼）
    ------------------
    >>> porter.register_plugin(FormatScannerPlugin())
    >>> report = porter.run_plugin("format_scanner", path="/docs")

    CLI 使用方式
    ------------
    lobster plugin format_scanner --path /docs
    """

    name = "format_scanner"
    description = "統計並報告各格式文件的數量"

    def run(
        self,
        porter,
        path: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, int]:
        """
        參數
        ----
        path : 掃描起點（預設 porter.root）

        回傳副檔名 → 文件數的字典。
        """
        base = Path(path).resolve() if path else porter.root
        files = [f for f in base.rglob("*") if f.is_file()]

        counts: Dict[str, int] = {}
        for f in files:
            ext = f.suffix.lower() or "(無副檔名)"
            counts[ext] = counts.get(ext, 0) + 1

        # 按數量倒序打印
        print(f"\n[format_scanner] 掃描目錄：{base}")
        print(f"{'副檔名':<15} {'數量':>6}")
        print("-" * 22)
        for ext, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"{ext:<15} {count:>6}")
        print(f"\n合計 {len(files)} 個文件，{len(counts)} 種格式。\n")

        return counts
