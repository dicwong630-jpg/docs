"""
lobster_porter.cli — 完整命令列介面
=====================================

提供 LobsterPorter 的所有 CLI 子命令：

    copy    — 批量複製檔案/目錄
    move    — 批量移動檔案/目錄
    delete  — 批量刪除檔案/目錄
    rename  — 批量重命名（正規表達式替換）
    sort    — 使用策略分類並搬運整個目錄
    undo    — 撤銷最近一次操作（基於日誌檔案）
    log     — 顯示或匯出操作日誌

使用範例
--------
::

    # 批量複製（保留層級）
    python -m lobster_porter copy /src/docs /src/images --dest /tmp/backup --base /src/

    # 批量移動
    python -m lobster_porter move /src/docs --dest /tmp/archive --base /src/

    # 批量刪除（建議先 dry-run 確認）
    python -m lobster_porter delete /tmp/old/*.txt --dry-run

    # 批量重命名（正規表達式）
    python -m lobster_porter rename /docs/ --pattern "report_(\\d+)\\.txt" --replacement "annual_\\1.txt"

    # 依副檔名分類搬運整個目錄
    python -m lobster_porter sort /inbox/ --dest /organised/ --strategy extension

    # 使用自定義規則檔分類搬運
    python -m lobster_porter sort /inbox/ --dest /organised/ --strategy user --rules ~/.my_rules.json

    # 匯出操作日誌
    python -m lobster_porter sort /inbox/ --dest /organised/ --log-out /var/log/porter.json
"""

from __future__ import annotations

import argparse
import glob as _glob
import logging
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI 解析器建立
# ---------------------------------------------------------------------------


def build_cli_parser() -> argparse.ArgumentParser:
    """建立 LobsterPorter 完整 CLI 的 argparse 解析器。

    Returns
    -------
    argparse.ArgumentParser
        已設定所有子命令的解析器物件。
    """
    parser = argparse.ArgumentParser(
        prog="lobster_porter",
        description="🦞 LobsterPorter — 批量檔案搬運、分類、刪除與重命名工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令：
  copy    批量複製檔案/目錄（保留層級結構）
  move    批量移動檔案/目錄（保留層級結構）
  delete  批量刪除檔案/目錄
  rename  批量重命名（正規表達式替換）
  sort    使用策略分類並搬運整個目錄
  log     顯示或匯出操作日誌

使用 `python -m lobster_porter <子命令> --help` 查看子命令說明。
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_copy_parser(subparsers)
    _add_move_parser(subparsers)
    _add_delete_parser(subparsers)
    _add_rename_parser(subparsers)
    _add_sort_parser(subparsers)
    _add_log_parser(subparsers)
    return parser


def _common_args(p: argparse.ArgumentParser) -> None:
    """為子命令添加共用選項。"""
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="模擬執行，不實際修改任何檔案",
    )
    p.add_argument(
        "--log-out",
        metavar="PATH",
        default=None,
        help="操作完成後將日誌匯出至指定路徑（.json 或 .csv）",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="輸出詳細日誌",
    )


def _add_copy_parser(subparsers) -> None:
    p = subparsers.add_parser("copy", help="批量複製檔案/目錄")
    p.add_argument("sources", nargs="+", help="來源檔案或目錄路徑（可多個，支援 glob）")
    p.add_argument("--dest", required=True, help="目標根目錄")
    p.add_argument("--base", default=None, help="來源根目錄（用於保留層級結構）")
    _common_args(p)


def _add_move_parser(subparsers) -> None:
    p = subparsers.add_parser("move", help="批量移動檔案/目錄")
    p.add_argument("sources", nargs="+", help="來源檔案或目錄路徑（可多個，支援 glob）")
    p.add_argument("--dest", required=True, help="目標根目錄")
    p.add_argument("--base", default=None, help="來源根目錄（用於保留層級結構）")
    _common_args(p)


def _add_delete_parser(subparsers) -> None:
    p = subparsers.add_parser("delete", help="批量刪除檔案/目錄（不可復原，建議先 --dry-run）")
    p.add_argument("sources", nargs="+", help="要刪除的檔案或目錄路徑（可多個，支援 glob）")
    p.add_argument("--force", action="store_true", default=False,
                   help="跳過確認提示直接刪除（預設需要確認）")
    _common_args(p)


def _add_rename_parser(subparsers) -> None:
    p = subparsers.add_parser("rename", help="批量重命名（正規表達式替換）")
    p.add_argument("sources", nargs="+", help="要重命名的檔案路徑（可多個，支援 glob）")
    p.add_argument("--pattern", required=True, help="正規表達式模式（匹配檔名）")
    p.add_argument("--replacement", required=True, help="替換字串（支援反向參照，如 \\\\1）")
    p.add_argument("--case-sensitive", action="store_true", default=False,
                   help="啟用大小寫敏感匹配（預設大小寫不敏感）")
    _common_args(p)


def _add_sort_parser(subparsers) -> None:
    p = subparsers.add_parser("sort", help="使用策略分類並搬運整個目錄")
    p.add_argument("src", help="來源目錄")
    p.add_argument("--dest", required=True, help="目標根目錄")
    p.add_argument(
        "--strategy",
        choices=["extension", "date", "size", "flat", "typegroup", "regex", "user"],
        default="extension",
        help="分類策略（預設：extension）",
    )
    p.add_argument("--rules", metavar="PATH",
                   help="用戶自定義規則 JSON 檔路徑（strategy=user 時必填）")
    p.add_argument("--regex-rules", nargs="+", metavar="PATTERN:CATEGORY",
                   help="正規表達式規則（strategy=regex 時使用），格式：'pattern:category'")
    p.add_argument("--copy", action="store_true", default=False,
                   help="複製而非移動（預設：移動）")
    p.add_argument("--overwrite", action="store_true", default=False,
                   help="覆寫已存在的目標檔案")
    p.add_argument("--include", nargs="+", metavar="PATTERN",
                   help="只處理符合此 glob 模式的檔案（可多個），例如：*.md *.pdf")
    p.add_argument("--exclude", nargs="+", metavar="PATTERN",
                   help="排除符合此 glob 模式的檔案（可多個）")
    _common_args(p)


def _add_log_parser(subparsers) -> None:
    p = subparsers.add_parser("log", help="顯示或匯出操作日誌（需指定現有日誌檔）")
    p.add_argument("log_file", help="現有日誌 JSON 檔路徑")
    p.add_argument("--export", metavar="PATH", help="匯出日誌至指定路徑（.json 或 .csv）")
    p.add_argument("--filter-action", metavar="ACTION",
                   help="只顯示特定操作類型（copy/move/delete/rename/undo_move/undo_rename）")
    p.add_argument("--filter-failed", action="store_true", default=False,
                   help="只顯示失敗的操作")


# ---------------------------------------------------------------------------
# 輔助函式
# ---------------------------------------------------------------------------


def _expand_sources(raw: List[str]) -> List[str]:
    """展開 glob 模式，返回實際存在的路徑列表。"""
    expanded = []
    for item in raw:
        matches = _glob.glob(item, recursive=True)
        if matches:
            expanded.extend(matches)
        else:
            expanded.append(item)  # 保留原始路徑（讓後續操作報錯）
    return expanded


def _progress_callback(log):
    """每次操作完成後列印進度至 stdout。"""
    from lobster_porter.operations import OperationLog
    status = "✅ OK" if log.success else f"❌ FAIL: {log.error}"
    print(f"  [{log.action.upper()}] {log.src}  →  {log.dst}  [{status}]")


def _maybe_export(porter_or_logs, log_out: Optional[str]) -> None:
    """若指定了 log_out，匯出操作日誌。"""
    if not log_out:
        return
    fmt = "csv" if log_out.lower().endswith(".csv") else "json"
    porter_or_logs.export_log(log_out, fmt=fmt)
    print(f"\n📄 操作日誌已匯出至：{log_out}")


# ---------------------------------------------------------------------------
# 子命令處理函式
# ---------------------------------------------------------------------------


def _handle_copy(args) -> int:
    from lobster_porter.operations import LobsterPorter
    sources = _expand_sources(args.sources)
    print(f"🦞 批量複製 {len(sources)} 個項目 → {args.dest}")
    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式，不實際修改任何檔案。")
    porter = LobsterPorter(dry_run=args.dry_run)
    porter.batch_copy(
        sources=sources,
        dest_dir=args.dest,
        base_src=args.base,
        on_progress=_progress_callback,
    )
    print("\n--- 操作摘要 ---")
    porter.print_logs()
    _maybe_export(porter, args.log_out)
    failed = [log for log in porter.logs if not log.success]
    if failed:
        print(f"\n⚠️  {len(failed)} 個操作失敗。")
        return 1
    return 0


def _handle_move(args) -> int:
    from lobster_porter.operations import LobsterPorter
    sources = _expand_sources(args.sources)
    print(f"🦞 批量移動 {len(sources)} 個項目 → {args.dest}")
    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式，不實際修改任何檔案。")
    porter = LobsterPorter(dry_run=args.dry_run)
    porter.batch_move(
        sources=sources,
        dest_dir=args.dest,
        base_src=args.base,
        on_progress=_progress_callback,
    )
    print("\n--- 操作摘要 ---")
    porter.print_logs()
    _maybe_export(porter, args.log_out)
    failed = [log for log in porter.logs if not log.success]
    if failed:
        print(f"\n⚠️  {len(failed)} 個操作失敗。")
        return 1
    return 0


def _handle_delete(args) -> int:
    from lobster_porter.operations import LobsterPorter
    sources = _expand_sources(args.sources)
    print(f"🦞 批量刪除 {len(sources)} 個項目")
    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式，不實際修改任何檔案。")
    elif not args.force:
        confirm = input(f"⚠️  確定要刪除 {len(sources)} 個項目？此操作不可復原。[y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("已取消。")
            return 0
    porter = LobsterPorter(dry_run=args.dry_run)
    porter.batch_delete(sources=sources, on_progress=_progress_callback)
    print("\n--- 操作摘要 ---")
    porter.print_logs()
    _maybe_export(porter, args.log_out)
    failed = [log for log in porter.logs if not log.success]
    if failed:
        print(f"\n⚠️  {len(failed)} 個操作失敗。")
        return 1
    return 0


def _handle_rename(args) -> int:
    import re as _re
    from lobster_porter.operations import LobsterPorter
    sources = _expand_sources(args.sources)
    flags = 0 if args.case_sensitive else _re.IGNORECASE
    print(f"🦞 批量重命名 {len(sources)} 個項目")
    print(f"   模式：{args.pattern!r}  →  {args.replacement!r}")
    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式，不實際修改任何檔案。")
    porter = LobsterPorter(dry_run=args.dry_run)
    porter.batch_rename(
        sources=sources,
        pattern=args.pattern,
        replacement=args.replacement,
        flags=flags,
        on_progress=_progress_callback,
    )
    print("\n--- 操作摘要 ---")
    porter.print_logs()
    _maybe_export(porter, args.log_out)
    failed = [log for log in porter.logs if not log.success]
    if failed:
        print(f"\n⚠️  {len(failed)} 個操作失敗。")
        return 1
    return 0


def _handle_sort(args) -> int:
    from lobster_porter.core import Porter
    from lobster_porter.strategies import (
        DateStrategy, ExtensionStrategy, FlatStrategy,
        RegexStrategy, SizeStrategy, TypeGroupStrategy, UserRuleStrategy,
    )
    from lobster_porter.plugins.examples import SummaryPlugin, LoggingPlugin

    # 建立策略
    strategy_map = {
        "extension": ExtensionStrategy,
        "date": DateStrategy,
        "size": SizeStrategy,
        "flat": FlatStrategy,
        "typegroup": TypeGroupStrategy,
    }
    if args.strategy in strategy_map:
        strategy = strategy_map[args.strategy]()
    elif args.strategy == "regex":
        if not args.regex_rules:
            print("❌ strategy=regex 時必須提供 --regex-rules。")
            return 1
        rules = []
        for item in args.regex_rules:
            parts = item.rsplit(":", 1)
            if len(parts) != 2:
                print(f"❌ --regex-rules 格式錯誤：{item!r}（應為 'pattern:category'）")
                return 1
            rules.append((parts[0], parts[1]))
        strategy = RegexStrategy(rules)
    elif args.strategy == "user":
        if not args.rules:
            print("❌ strategy=user 時必須提供 --rules 規則 JSON 檔路徑。")
            return 1
        strategy = UserRuleStrategy(args.rules)
    else:
        strategy = ExtensionStrategy()

    plugins = [LoggingPlugin(), SummaryPlugin()]

    porter = Porter(
        src=args.src,
        dest=args.dest,
        strategy=strategy,
        plugins=plugins,
        copy=args.copy,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        include_patterns=args.include or [],
        exclude_patterns=args.exclude or [],
    )

    if args.dry_run:
        print("🔍 [DRY RUN] 模擬模式，不實際修改任何檔案。")

    print(f"🦞 開始分類搬運：{args.src} → {args.dest}（策略：{args.strategy}）")
    results = porter.run()

    if args.log_out:
        # 用 LobsterPorter 記錄器匯出
        from lobster_porter.operations import LobsterPorter, OperationLog
        from datetime import datetime
        tmp_porter = LobsterPorter()
        for r in results:
            action = "copy" if args.copy else "move"
            log = OperationLog(
                action=action,
                src=str(r.src),
                dst=str(r.dest),
                success=r.success,
                error=str(r.error) if r.error else "",
            )
            tmp_porter._logs.append(log)
        _maybe_export(tmp_porter, args.log_out)

    failed = [r for r in results if not r.success]
    return 1 if failed else 0


def _handle_log(args) -> int:
    import json
    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"❌ 找不到日誌檔案：{args.log_file}")
        return 1

    with open(log_path, encoding="utf-8") as fh:
        entries = json.load(fh)

    # 過濾
    if args.filter_action:
        entries = [e for e in entries if e.get("action") == args.filter_action]
    if args.filter_failed:
        entries = [e for e in entries if not e.get("success", True)]

    # 顯示
    print(f"{'ACTION':<14} {'STATUS':<10} {'SRC':<40} {'DST':<40} TIMESTAMP")
    print("-" * 110)
    for e in entries:
        status = "OK" if e.get("success", True) else f"FAIL: {e.get('error', '')[:20]}"
        print(
            f"{e.get('action', ''):<14} {status:<10} "
            f"{e.get('src', ''):<40} {e.get('dst', ''):<40} {e.get('timestamp', '')}"
        )

    # 匯出
    if args.export:
        import csv as _csv
        fmt = "csv" if args.export.lower().endswith(".csv") else "json"
        if fmt == "json":
            with open(args.export, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, ensure_ascii=False, indent=2)
        else:
            with open(args.export, "w", newline="", encoding="utf-8") as fh:
                writer = _csv.DictWriter(
                    fh,
                    fieldnames=["action", "src", "dst", "timestamp", "success", "error"]
                )
                writer.writeheader()
                writer.writerows(entries)
        print(f"\n📄 已匯出至：{args.export}")

    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """LobsterPorter CLI 主入口。

    Args:
        argv (Optional[List[str]]): 命令列參數。若為 None，使用 sys.argv[1:]。

    Returns:
        int: 退出碼（0 成功，1 有操作失敗）。
    """
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    dispatch = {
        "copy": _handle_copy,
        "move": _handle_move,
        "delete": _handle_delete,
        "rename": _handle_rename,
        "sort": _handle_sort,
        "log": _handle_log,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except FileNotFoundError as exc:
        print(f"❌ 錯誤：{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 未預期錯誤：{exc}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
