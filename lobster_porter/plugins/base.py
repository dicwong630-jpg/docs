"""
lobster_porter.plugins.base — 插件基礎類 / 接口
================================================

All Lobster Porter plugins must inherit from ``BasePlugin``.

The base class provides no-op implementations of every lifecycle hook so
concrete plugins only need to override the hooks they care about.

Implementing a plugin
---------------------
1. Subclass ``BasePlugin``.
2. Override the hooks you need (see the method docstrings below).
3. Pass an instance to ``Porter(plugins=[MyPlugin()])``.

Minimal example::

    from lobster_porter.plugins.base import BasePlugin

    class EchoPlugin(BasePlugin):
        def on_start(self, porter, **kwargs):
            print(f"Starting porter: {porter.src} → {porter.dest}")

        def on_finish(self, porter, results, **kwargs):
            ok = sum(r.success for r in results)
            print(f"Done. {ok}/{len(results)} files transported.")

TODO
----
- Add a ``priority`` attribute so plugins can be auto-sorted.
- Add a plugin registry / discovery mechanism (e.g. via entry points).
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from pathlib import Path

    from lobster_porter.core import Porter, TransportResult


class BasePlugin(ABC):
    """Abstract base class for all Lobster Porter plugins.

    Every hook has a default no-op implementation so you only need to
    override the hooks your plugin actually uses.

    Parameters
    ----------
    name : str, optional
        Human-readable name for this plugin instance.  Used in log messages.
        Defaults to the class name.
    enabled : bool
        When ``False`` the porter skips this plugin entirely.
        Defaults to ``True``.
    """

    def __init__(self, name: str | None = None, enabled: bool = True) -> None:
        self.name: str = name or self.__class__.__name__
        self.enabled: bool = enabled

    # ------------------------------------------------------------------
    # Lifecycle hooks — override as needed
    # ------------------------------------------------------------------

    def on_start(self, porter: "Porter", **kwargs: Any) -> None:
        """Called once before the porter begins file discovery.

        Parameters
        ----------
        porter : Porter
            The ``Porter`` instance that is about to run.
        """

    def on_before_transport(self, file_path: "Path", **kwargs: Any) -> None:
        """Called immediately before a single file is transported.

        Parameters
        ----------
        file_path : Path
            The source file about to be transported.
        """

    def on_after_transport(self, result: "TransportResult", **kwargs: Any) -> None:
        """Called immediately after a single file transport attempt.

        Parameters
        ----------
        result : TransportResult
            The outcome of the transport.  Check ``result.success`` and
            ``result.error`` for details.
        """

    def on_finish(self, porter: "Porter", results: "List[TransportResult]", **kwargs: Any) -> None:
        """Called once after all files have been processed.

        Parameters
        ----------
        porter : Porter
            The ``Porter`` instance that just finished.
        results : list[TransportResult]
            Complete list of transport results (one per discovered file).
        """

    def __repr__(self) -> str:  # pragma: no cover
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__} name={self.name!r} [{status}]>"
