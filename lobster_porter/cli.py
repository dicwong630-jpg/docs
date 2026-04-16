"""
cli.py — 龍蝦搬運工命令列介面
================================
使用 argparse 實作，支援以下指令：

  lobster search   <path> [--pattern PAT] [--formats md,pdf]
  lobster move     <src> <dst>
  lobster copy     <src> <dst>
  lobster batch-move <dst> <file1> [file2 ...]
  lobster batch-copy <dst> <file1> [file2 ...]
  lobster undo
  lobster index    [--path PATH] [--output OUTPUT] [--formats md]
  lobster export-tag <tag> <dst> [--path PATH]
  lobster plugin   <plugin_name> [--path PATH] [--output OUTPUT]
                   [--tag TAG] [--mode MODE] [--value VALUE]
                   [--old OLD] [--new NEW] [--pattern PAT] [--dry-run]
  lobster plugins  （列出所有已載入插件）
  lobster history  （顯示操作歷史）

執行方式
--------
# 直接執行腳本
python -m lobster_porter.cli search ./docs --formats markdown

# 若安裝後（setup.py / pyproject.toml 配置 entry_points）
lobster search ./docs --formats markdown
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .core import LobsterPorter
from .plugins.examples import (
    BulkRenamePlugin,
    FormatScannerPlugin,
    IndexGeneratorPlugin,
    TagExporterPlugin,
)


def _build_porter(root: Optional[str] = None) -> LobsterPorter:
    """建立 LobsterPorter 實例並載入所有內建插件。"""
    porter = LobsterPorter(root=root or ".")
    # 預設載入所有內建插件
    for plugin in [
        IndexGeneratorPlugin(),
        TagExporterPlugin(),
        BulkRenamePlugin(),
        FormatScannerPlugin(),
    ]:
        porter.register_plugin(plugin)
    return porter


def _parse_formats(formats_str: Optional[str]) -> Optional[List[str]]:
    """將逗號分隔的格式字串轉為列表，例如 "markdown,pdf" → ["markdown", "pdf"]。"""
    if not formats_str:
        return None
    return [f.strip() for f in formats_str.split(",") if f.strip()]


# ── 各子命令處理函數 ─────────────────────────────────────────────────────────

def cmd_search(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """搜尋文件並列印結果。"""
    results = porter.search(
        path=args.path,
        pattern=args.pattern,
        formats=_parse_formats(args.formats),
        recursive=not args.no_recursive,
    )
    if results:
        print(f"找到 {len(results)} 個文件：")
        for p in results:
            print(f"  {p}")
    else:
        print("未找到符合條件的文件。")


def cmd_move(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """移動單一文件或目錄。"""
    target = porter.move(args.src, args.dst)
    print(f"已移動：{args.src}  →  {target}")


def cmd_copy(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """複製單一文件或目錄。"""
    target = porter.copy(args.src, args.dst)
    print(f"已複製：{args.src}  →  {target}")


def cmd_batch_move(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """批量移動文件到目標目錄。"""
    moved = porter.batch_move(args.files, args.dst)
    print(f"已批量移動 {len(moved)} 個文件 → {args.dst}")


def cmd_batch_copy(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """批量複製文件到目標目錄。"""
    copied = porter.batch_copy(args.files, args.dst)
    print(f"已批量複製 {len(copied)} 個文件 → {args.dst}")


def cmd_undo(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """撤銷最近一次操作。"""
    porter.undo()


def cmd_index(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """生成 Markdown 索引文件。"""
    porter.generate_index(
        path=args.path,
        output=args.output,
        formats=_parse_formats(args.formats),
    )


def cmd_export_tag(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """按標籤導出文件。"""
    exported = porter.export_by_tag(tag=args.tag, dst=args.dst, path=args.path)
    print(f"已導出 {len(exported)} 個含「{args.tag}」標籤的文件 → {args.dst}")


def cmd_plugin(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """執行指定插件。"""
    kwargs = {
        k: v for k, v in vars(args).items()
        if k not in ("command", "plugin_name") and v is not None
    }
    porter.run_plugin(args.plugin_name, **kwargs)


def cmd_plugins(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """列出已載入插件。"""
    names = porter.list_plugins()
    if names:
        print("已載入插件：")
        for name in names:
            plugin = porter._plugins[name]
            print(f"  {name:<20}  {plugin.description}")
    else:
        print("（無已載入插件）")


def cmd_history(porter: LobsterPorter, args: argparse.Namespace) -> None:
    """顯示操作歷史。"""
    porter.show_history()


# ── 主入口 ──────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """建立並回傳完整 ArgumentParser。"""
    parser = argparse.ArgumentParser(
        prog="lobster",
        description="🦞 龍蝦搬運工 — 知識文件倉庫批量搬運工具",
    )
    parser.add_argument(
        "--root", default=".",
        help="文件倉庫根目錄（預設：當前目錄）",
    )

    sub = parser.add_subparsers(dest="command", metavar="<指令>")
    sub.required = True

    # search
    p_search = sub.add_parser("search", help="搜尋文件")
    p_search.add_argument("path", nargs="?", help="搜尋起點目錄")
    p_search.add_argument("--pattern", default="*", help="文件名 glob 模式（預設：*）")
    p_search.add_argument("--formats", help="格式篩選，逗號分隔，例如 markdown,pdf")
    p_search.add_argument("--no-recursive", action="store_true", help="不遞迴子目錄")

    # move
    p_move = sub.add_parser("move", help="移動單一文件/目錄")
    p_move.add_argument("src", help="來源路徑")
    p_move.add_argument("dst", help="目標路徑")

    # copy
    p_copy = sub.add_parser("copy", help="複製單一文件/目錄")
    p_copy.add_argument("src", help="來源路徑")
    p_copy.add_argument("dst", help="目標路徑")

    # batch-move
    p_bmove = sub.add_parser("batch-move", help="批量移動文件")
    p_bmove.add_argument("dst", help="目標目錄")
    p_bmove.add_argument("files", nargs="+", help="要移動的文件列表")

    # batch-copy
    p_bcopy = sub.add_parser("batch-copy", help="批量複製文件")
    p_bcopy.add_argument("dst", help="目標目錄")
    p_bcopy.add_argument("files", nargs="+", help="要複製的文件列表")

    # undo
    sub.add_parser("undo", help="撤銷最近一次操作")

    # index
    p_index = sub.add_parser("index", help="生成 Markdown 索引文件")
    p_index.add_argument("--path", help="掃描起點目錄")
    p_index.add_argument("--output", help="索引文件輸出路徑")
    p_index.add_argument("--formats", help="格式篩選，逗號分隔")

    # export-tag
    p_etag = sub.add_parser("export-tag", help="按標籤批量導出 Markdown 文件")
    p_etag.add_argument("tag", help="要篩選的標籤")
    p_etag.add_argument("dst", help="導出目標目錄")
    p_etag.add_argument("--path", help="搜尋起點目錄")

    # plugin
    p_plugin = sub.add_parser("plugin", help="執行指定插件")
    p_plugin.add_argument("plugin_name", help="插件名稱")
    p_plugin.add_argument("--path", help="目標目錄")
    p_plugin.add_argument("--output", help="輸出路徑")
    p_plugin.add_argument("--tag", help="標籤（tag_exporter 使用）")
    p_plugin.add_argument("--dst", help="導出目標目錄（tag_exporter 使用）")
    p_plugin.add_argument("--mode", help="模式（bulk_rename：prefix/suffix/replace）")
    p_plugin.add_argument("--value", help="前綴/後綴字串（bulk_rename 使用）")
    p_plugin.add_argument("--old", help="要替換的舊字串（bulk_rename replace 使用）")
    p_plugin.add_argument("--new", help="替換後的新字串（bulk_rename replace 使用）")
    p_plugin.add_argument("--pattern", help="文件名 glob 篩選")
    p_plugin.add_argument("--formats", help="格式篩選，逗號分隔")
    p_plugin.add_argument("--dry-run", action="store_true", help="只預覽，不實際執行")

    # plugins（列表）
    sub.add_parser("plugins", help="列出已載入插件")

    # history
    sub.add_parser("history", help="顯示操作歷史")

    return parser


_COMMAND_MAP = {
    "search":     cmd_search,
    "move":       cmd_move,
    "copy":       cmd_copy,
    "batch-move": cmd_batch_move,
    "batch-copy": cmd_batch_copy,
    "undo":       cmd_undo,
    "index":      cmd_index,
    "export-tag": cmd_export_tag,
    "plugin":     cmd_plugin,
    "plugins":    cmd_plugins,
    "history":    cmd_history,
}


def main(argv: Optional[List[str]] = None) -> None:
    """CLI 主入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    porter = _build_porter(args.root)

    handler = _COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(porter, args)


if __name__ == "__main__":
    main()
