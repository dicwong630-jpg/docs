"""
cli.py — 龍蝦搬運工命令行介面（CLI）
使用 argparse 提供完整的命令行操作介面，支援批量移動、複製、撤銷等操作。
"""

import argparse
import sys
from pathlib import Path
from typing import List

from .core import LobsterPorter


def parse_args(argv: List[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lobster-porter",
        description="🦞 龍蝦搬運工 — 批量檔案搬運與分類工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 批量移動所有 PDF 到 劇本/ 資料夾
  lobster-porter move *.pdf --dest 劇本/

  # 批量複製並模擬（不實際執行）
  lobster-porter copy *.psd --dest 美術/ --dry-run

  # 撤銷最近 3 步操作
  lobster-porter undo --steps 3
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── move ──────────────────────────────────────────────────────────
    move_parser = subparsers.add_parser("move", help="批量移動檔案")
    move_parser.add_argument("files", nargs="+", help="來源檔案路徑（支援 glob）")
    move_parser.add_argument("--dest", required=True, help="目標資料夾路徑")
    move_parser.add_argument("--overwrite", action="store_true", help="覆蓋已存在的同名檔案")
    move_parser.add_argument("--dry-run", action="store_true", help="模擬模式（不實際執行）")

    # ── copy ──────────────────────────────────────────────────────────
    copy_parser = subparsers.add_parser("copy", help="批量複製檔案")
    copy_parser.add_argument("files", nargs="+", help="來源檔案路徑（支援 glob）")
    copy_parser.add_argument("--dest", required=True, help="目標資料夾路徑")
    copy_parser.add_argument("--overwrite", action="store_true", help="覆蓋已存在的同名檔案")
    copy_parser.add_argument("--dry-run", action="store_true", help="模擬模式（不實際執行）")

    # ── delete ────────────────────────────────────────────────────────
    delete_parser = subparsers.add_parser("delete", help="批量刪除檔案")
    delete_parser.add_argument("files", nargs="+", help="要刪除的檔案路徑")
    delete_parser.add_argument("--dry-run", action="store_true", help="模擬模式（不實際執行）")

    # ── undo ──────────────────────────────────────────────────────────
    undo_parser = subparsers.add_parser("undo", help="撤銷最近操作")
    undo_parser.add_argument(
        "--steps", type=int, default=1, help="要撤銷的步驟數（預設：1）"
    )
    undo_parser.add_argument("--dry-run", action="store_true", help="模擬模式（不實際執行）")

    # ── history ───────────────────────────────────────────────────────
    subparsers.add_parser("history", help="顯示操作歷史記錄")

    return parser.parse_args(argv)


def expand_files(patterns: List[str]) -> List[str]:
    """展開 glob 模式，回傳實際存在的檔案路徑列表。"""
    import glob as glob_module

    result = []
    for pattern in patterns:
        expanded = glob_module.glob(pattern, recursive=True)
        result.extend(expanded if expanded else [pattern])
    return result


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)
    porter = LobsterPorter(dry_run=getattr(args, "dry_run", False))

    if args.command == "move":
        files = expand_files(args.files)
        moved = porter.batch_move(files, args.dest, overwrite=args.overwrite)
        print(f"✅ 已移動 {len(moved)} 個檔案到 {args.dest}")

    elif args.command == "copy":
        files = expand_files(args.files)
        copied = porter.batch_copy(files, args.dest, overwrite=args.overwrite)
        print(f"✅ 已複製 {len(copied)} 個檔案到 {args.dest}")

    elif args.command == "delete":
        files = expand_files(args.files)
        deleted = porter.batch_delete(files)
        print(f"🗑️  已刪除 {len(deleted)} 個檔案")

    elif args.command == "undo":
        undone = porter.undo(steps=args.steps)
        print(f"↩️  已撤銷 {len(undone)} 步操作")
        for record in undone:
            print(f"   {record}")

    elif args.command == "history":
        records = porter.history.all_records()
        if not records:
            print("（尚無操作歷史記錄）")
        else:
            for record in records:
                print(f"  {record}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
