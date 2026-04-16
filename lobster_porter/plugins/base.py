"""
lobster_porter.plugins.base
============================
Abstract base class for all LobsterPorter plugins.

Every plugin must subclass :class:`BasePlugin` and implement
:meth:`on_event`.  Optionally override :meth:`on_start` and :meth:`on_finish`
for setup and teardown logic.

Example
-------
::

    from lobster_porter.plugins.base import BasePlugin

    class MyPlugin(BasePlugin):
        name = "my_plugin"

        def on_event(self, event: str, *args) -> None:
            print(f"[MyPlugin] event={event}, args={args}")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class BasePlugin(ABC):
    """Abstract base class that every LobsterPorter plugin must inherit from.

    Lifecycle
    ---------
    1. :meth:`on_start`  — called once when the porter operation begins.
    2. :meth:`on_event`  — called after each individual file operation.
    3. :meth:`on_finish` — called once when the porter operation ends.

    Attributes
    ----------
    name:
        A unique, human-readable identifier for the plugin (class attribute).
    enabled:
        Whether the plugin should receive events.  Set to ``False`` to
        temporarily disable a plugin without removing it.
    """

    #: Unique name for this plugin type (override in subclasses).
    name: ClassVar[str] = "base"

    def __init__(self) -> None:
        self.enabled: bool = True

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_start(self, **context) -> None:
        """Called once before a batch operation starts.

        Parameters
        ----------
        **context:
            Arbitrary keyword arguments passed from the core engine,
            e.g. ``operation="move"``, ``dry_run=False``.
        """

    @abstractmethod
    def on_event(self, event: str, *args) -> None:
        """Called after each file operation.

        Parameters
        ----------
        event:
            The name of the event, e.g. ``"move"``, ``"copy"``, ``"index"``.
        *args:
            Event-specific positional arguments.

            For ``"move"`` and ``"copy"`` events:
                ``args == (source_path, destination_path)``
            For ``"index"`` events:
                ``args == (index_file_path,)``
        """

    def on_finish(self, **context) -> None:
        """Called once after a batch operation completes.

        Parameters
        ----------
        **context:
            Arbitrary keyword arguments with summary information,
            e.g. ``processed=42``, ``skipped=3``.
        """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__} name={self.name!r} {status}>"
