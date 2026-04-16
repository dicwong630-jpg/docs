"""
lobster_porter.core
===================
批量移動、複製與分類的核心邏輯，以及 CLI 入口點。

CLI 使用方式
------------
移動::

    python -m lobster_porter move <src_dir> <dst_dir> [--pattern GLOB]

複製::

    python -m lobster_porter copy <src_dir> <dst_dir> [--pattern GLOB]

分類::

    python -m lobster_porter classify <src_dir> <out_dir> [--strategy <name>] [--keywords k1,k2]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from .strategies import (
    ClassificationResult,
    DirectoryStrategy,
    KeywordStrategy,
    MetaStrategy,
    StrategyBase,
)


# ---------------------------------------------------------------------------
# Batch move / copy helpers
# ---------------------------------------------------------------------------

def batch_move(
    src_dir: str | Path,
    dst_dir: str | Path,
    pattern: str = "**/*",
) -> List[Path]:
    """批量移動 *src_dir* 中符合 *pattern* 的檔案到 *dst_dir*。

    Parameters
    ----------
    src_dir:
        來源目錄路徑。
    dst_dir:
        目的目錄路徑（不存在時自動建立）。
    pattern:
        glob 樣式，預設為所有檔案 ``**/*``。

    Returns
    -------
    list[Path]
        已移動的目的檔案路徑列表。
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    moved: List[Path] = []
    for src_file in src_dir.glob(pattern):
        if src_file.is_file():
            # 保留相對路徑結構
            rel = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_file), str(dst_file))
            moved.append(dst_file)
    return moved


def batch_copy(
    src_dir: str | Path,
    dst_dir: str | Path,
    pattern: str = "**/*",
) -> List[Path]:
    """批量複製 *src_dir* 中符合 *pattern* 的檔案到 *dst_dir*。

    Parameters
    ----------
    src_dir:
        來源目錄路徑。
    dst_dir:
        目的目錄路徑（不存在時自動建立）。
    pattern:
        glob 樣式，預設為所有檔案 ``**/*``。

    Returns
    -------
    list[Path]
        已複製的目的檔案路徑列表。
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    copied: List[Path] = []
    for src_file in src_dir.glob(pattern):
        if src_file.is_file():
            rel = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dst_file))
            copied.append(dst_file)
    return copied


# ---------------------------------------------------------------------------
# Batch classify
# ---------------------------------------------------------------------------

def batch_classify(
    src_dir: str | Path,
    out_dir: str | Path,
    strategy: Optional[StrategyBase] = None,
    pattern: str = "**/*",
    copy: bool = True,
) -> List[ClassificationResult]:
    """使用指定 *strategy* 批量分類 *src_dir* 中的檔案並輸出到 *out_dir*。

    每個檔案依策略取得分類標籤，並按標籤子目錄複製（或移動）到 *out_dir*
    下對應的子目錄。

    Parameters
    ----------
    src_dir:
        來源目錄路徑。
    out_dir:
        分類輸出根目錄（不存在時自動建立）。
    strategy:
        :class:`~lobster_porter.strategies.StrategyBase` 的實例。
        若為 ``None`` 則使用 :class:`~lobster_porter.strategies.DirectoryStrategy`。
    pattern:
        glob 樣式，預設為所有檔案 ``**/*``。
    copy:
        ``True`` 表示複製檔案（保留原始），``False`` 表示移動（刪除原始）。

    Returns
    -------
    list[ClassificationResult]
        每個已處理檔案的分類結果。
    """
    src_dir = Path(src_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 預設策略：按目錄層次分類
    if strategy is None:
        strategy = DirectoryStrategy()

    results: List[ClassificationResult] = []
    for src_file in src_dir.glob(pattern):
        if not src_file.is_file():
            continue

        # 取得分類結果
        result = strategy.classify(src_file)
        # 目標路徑：out_dir / category / filename
        dst_file = out_dir / result.category / src_file.name
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        if copy:
            shutil.copy2(str(src_file), str(dst_file))
        else:
            shutil.move(str(src_file), str(dst_file))

        result.dst_path = dst_file
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """建立並回傳 CLI 解析器。"""
    parser = argparse.ArgumentParser(
        prog="python -m lobster_porter",
        description="龍蝦搬運工 — 批量檔案搬運、分類工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # move 子命令
    mv = sub.add_parser("move", help="批量移動檔案")
    mv.add_argument("src", help="來源目錄")
    mv.add_argument("dst", help="目的目錄")
    mv.add_argument("--pattern", default="**/*", help="glob 樣式 (預設: **/*)")

    # copy 子命令
    cp = sub.add_parser("copy", help="批量複製檔案")
    cp.add_argument("src", help="來源目錄")
    cp.add_argument("dst", help="目的目錄")
    cp.add_argument("--pattern", default="**/*", help="glob 樣式 (預設: **/*)")

    # classify 子命令
    cl = sub.add_parser("classify", help="批量分類並輸出到指定路徑")
    cl.add_argument("src", help="來源目錄")
    cl.add_argument("out", help="分類輸出根目錄")
    cl.add_argument(
        "--strategy",
        choices=["directory", "keyword", "meta"],
        default="directory",
        help="分類策略 (預設: directory)",
    )
    cl.add_argument(
        "--keywords",
        default="",
        help="逗號分隔關鍵字列表，搭配 keyword 策略使用",
    )
    cl.add_argument("--pattern", default="**/*", help="glob 樣式 (預設: **/*)")
    cl.add_argument(
        "--move",
        action="store_true",
        help="移動檔案而非複製 (預設為複製)",
    )

    return parser


def _make_strategy(args: argparse.Namespace) -> StrategyBase:
    """根據 CLI 參數建立對應策略。"""
    if args.strategy == "keyword":
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        return KeywordStrategy(keywords=keywords)
    if args.strategy == "meta":
        return MetaStrategy()
    # 預設 directory
    return DirectoryStrategy()


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口，回傳 exit code。"""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "move":
        files = batch_move(args.src, args.dst, pattern=args.pattern)
        print(f"已移動 {len(files)} 個檔案 → {args.dst}")

    elif args.command == "copy":
        files = batch_copy(args.src, args.dst, pattern=args.pattern)
        print(f"已複製 {len(files)} 個檔案 → {args.dst}")

    elif args.command == "classify":
        strategy = _make_strategy(args)
        results = batch_classify(
            args.src,
            args.out,
            strategy=strategy,
            pattern=args.pattern,
            copy=not args.move,
        )
        # 列印分類摘要
        from collections import Counter
        counts = Counter(r.category for r in results)
        print(f"已分類 {len(results)} 個檔案 → {args.out}")
        for cat, cnt in sorted(counts.items()):
            print(f"  [{cat}] {cnt} 個")

    return 0


if __name__ == "__main__":
    sys.exit(main())
