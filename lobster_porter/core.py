"""
lobster_porter.core — 核心 Porter 協調器
==========================================

提供 ``Porter`` 類別，作為 Lobster Porter 系統的主協調器，負責：

1. **Discovery** — 掃描來源目錄，收集符合條件的檔案。
2. **Classification** — 透過 ``Strategy`` 決定每個檔案的目標子目錄。
3. **Transport** — 複製或移動檔案至目標路徑。
4. **Plugin hooks** — 在每個生命週期階段通知已註冊的插件。

使用範例
--------
最簡單的用法::

    from lobster_porter import Porter
    from lobster_porter.strategies import ExtensionStrategy

    porter = Porter(
        src="./inbox",
        dest="./organised",
        strategy=ExtensionStrategy(),
    )
    porter.run()

乾跑模式（dry_run），不實際移動任何檔案::

    porter = Porter(src="./inbox", dest="./organised", dry_run=True)
    results = porter.run()
    for r in results:
        print(r)

架構說明
--------
- ``Porter`` 刻意保持精簡；繁重工作分散至 strategy 和 plugin，
  使核心易於閱讀和測試。
- 所有檔案系統副作用都集中在 ``_transport`` 方法，可在子類別中
  只覆寫該方法（例如用於單元測試）。
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

from lobster_porter.strategies import BaseStrategy, ExtensionStrategy

logger = logging.getLogger(__name__)


class TransportResult:
    """記錄單次檔案搬運操作的結果。

    Attributes
    ----------
    src : Path
        原始檔案路徑。
    dest : Path
        目標檔案路徑（檔案實際放置的位置）。
    success : bool
        若搬運成功則為 ``True``。
    error : Optional[Exception]
        當 ``success`` 為 ``False`` 時，此欄位記錄例外資訊。
    """

    def __init__(
        self,
        src: Path,
        dest: Path,
        success: bool,
        error: Optional[Exception] = None,
    ) -> None:
        self.src = src
        self.dest = dest
        self.success = success
        self.error = error

    def __repr__(self) -> str:  # pragma: no cover
        status = "OK" if self.success else f"ERR({self.error})"
        return f"<TransportResult {self.src} → {self.dest} [{status}]>"


class Porter:
    """Lobster Porter 主協調器。

    Parameters
    ----------
    src : str | Path
        來源目錄，用於掃描檔案。
    dest : str | Path
        目標根目錄。子目錄根據策略的分類結果自動建立。
    strategy : BaseStrategy, optional
        分類/路由策略。預設使用 ``ExtensionStrategy``（依副檔名分組）。
    plugins : list, optional
        插件實例的有序列表，在每個生命週期掛鉤時收到通知。
    copy : bool
        為 ``True`` 時複製檔案而非移動。預設為 ``False``（移動）。
    overwrite : bool
        為 ``True`` 時靜默覆寫已存在的目標檔案。預設為 ``False``（跳過並警告）。
    dry_run : bool
        為 ``True`` 時只記錄日誌而不實際修改任何檔案。預設為 ``False``。
    include_patterns : list of str, optional
        Glob 模式白名單。僅處理符合至少一個模式的檔案。
        例如：``["*.md", "*.pdf"]``。
    exclude_patterns : list of str, optional
        Glob 模式黑名單。符合任一模式的檔案將被略過。
        例如：``[".git", "__pycache__"]``。

    Examples
    --------
    >>> porter = Porter(src="inbox", dest="organised")
    >>> results = porter.run()
    >>> print(f"Transported {sum(r.success for r in results)} files.")
    """

    def __init__(
        self,
        src: "str | Path",
        dest: "str | Path",
        strategy: Optional[BaseStrategy] = None,
        plugins: Optional[list] = None,
        copy: bool = False,
        overwrite: bool = False,
        dry_run: bool = False,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        self.src = Path(src)
        self.dest = Path(dest)
        self.strategy = strategy or ExtensionStrategy()
        self.plugins: list = plugins or []
        self.copy = copy
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.include_patterns: List[str] = include_patterns or []
        self.exclude_patterns: List[str] = exclude_patterns or ["__pycache__", ".git", ".DS_Store"]

    # ------------------------------------------------------------------
    # 公開介面
    # ------------------------------------------------------------------

    def run(self) -> List[TransportResult]:
        """發現、分類並搬運所有符合條件的檔案。

        Returns
        -------
        list[TransportResult]
            每個發現的檔案對應一個條目；檢查 ``.success`` 確認搬運是否成功。
        """
        self._notify_plugins("on_start", porter=self)

        files = list(self._discover())
        logger.info("Discovered %d files in %s", len(files), self.src)

        results: List[TransportResult] = []
        for file_path in files:
            result = self._handle_file(file_path)
            results.append(result)

        self._notify_plugins("on_finish", porter=self, results=results)

        successes = sum(r.success for r in results)
        logger.info("Transport complete: %d/%d successful", successes, len(results))
        return results

    # ------------------------------------------------------------------
    # 內部輔助方法
    # ------------------------------------------------------------------

    def _discover(self) -> Iterable[Path]:
        """遞迴列舉 ``self.src`` 中所有符合條件的檔案。"""
        if not self.src.exists():
            raise FileNotFoundError(f"Source directory not found: {self.src}")
        for root, dirs, files in os.walk(self.src):
            # 移除被排除的目錄（就地修改，防止遞迴進入）
            dirs[:] = [
                d for d in dirs
                if not any(Path(d).match(ex) for ex in self.exclude_patterns)
            ]
            for fname in files:
                file_path = Path(root) / fname
                if self._should_include(file_path):
                    yield file_path

    def _should_include(self, file_path: Path) -> bool:
        """判斷檔案是否應被處理。"""
        name = file_path.name
        # 排除黑名單
        if any(file_path.match(ex) for ex in self.exclude_patterns):
            return False
        # 若有白名單，只收錄符合的檔案
        if self.include_patterns:
            return any(file_path.match(inc) for inc in self.include_patterns)
        return True

    def _handle_file(self, file_path: Path) -> TransportResult:
        """分類並搬運單一檔案。"""
        self._notify_plugins("on_before_transport", file_path=file_path)

        category = self.strategy.classify(file_path)
        dest_dir = self.dest / category
        dest_path = dest_dir / file_path.name

        result = self._transport(file_path, dest_path)
        self._notify_plugins("on_after_transport", result=result)
        return result

    def _transport(self, src: Path, dest: Path) -> TransportResult:
        """執行實際的檔案系統操作（移動或複製）。

        此方法刻意獨立，方便子類別在不觸及其他邏輯的情況下覆寫
        （例如用於不應接觸真實檔案系統的單元測試）。
        """
        try:
            if self.dry_run:
                logger.info("[DRY RUN] would %s %s → %s",
                            "copy" if self.copy else "move", src, dest)
                return TransportResult(src=src, dest=dest, success=True)

            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and not self.overwrite:
                logger.warning("Skipping %s — destination already exists: %s", src, dest)
                return TransportResult(
                    src=src, dest=dest, success=False,
                    error=FileExistsError(str(dest))
                )

            if self.copy:
                shutil.copy2(src, dest)
                logger.debug("Copied %s → %s", src, dest)
            else:
                shutil.move(str(src), dest)
                logger.debug("Moved %s → %s", src, dest)

            return TransportResult(src=src, dest=dest, success=True)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to transport %s: %s", src, exc)
            return TransportResult(src=src, dest=dest, success=False, error=exc)

    def _notify_plugins(self, hook: str, **kwargs) -> None:
        """呼叫每個已註冊插件的 ``hook`` 方法（若插件有實作該方法）。"""
        for plugin in self.plugins:
            method = getattr(plugin, hook, None)
            if callable(method):
                try:
                    method(**kwargs)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Plugin %s raised in %s: %s", plugin, hook, exc)
