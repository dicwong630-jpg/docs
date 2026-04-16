"""
lobster_porter.plugins.examples
================================
Ready-to-use plugin implementations for LobsterPorter.

Plugins
-------
- :class:`LoggingPlugin`    — logs every file event to the Python logging system
- :class:`TaggingPlugin`    — prepends a YAML frontmatter ``tags`` field to MDX/MD files
- :class:`StatisticsPlugin` — counts moved/copied files and reports a summary
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from lobster_porter.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LoggingPlugin
# ---------------------------------------------------------------------------


class LoggingPlugin(BasePlugin):
    """Log every file operation using the Python :mod:`logging` module.

    Parameters
    ----------
    level:
        Python logging level for event messages (default ``logging.INFO``).

    Example
    -------
    ::

        import logging
        from lobster_porter.plugins.examples import LoggingPlugin

        logging.basicConfig(level=logging.INFO)
        plugin = LoggingPlugin(level=logging.DEBUG)
    """

    name = "logging"

    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__()
        self.level = level

    def on_start(self, **context) -> None:
        """Log the start of a batch operation."""
        logger.log(self.level, "[LoggingPlugin] Operation started: %s", context)

    def on_event(self, event: str, *args) -> None:
        """Log each file event.

        Parameters
        ----------
        event:
            Event name (``"move"``, ``"copy"``, ``"index"``).
        *args:
            Source and destination paths (for move/copy) or index path.
        """
        if not self.enabled:
            return
        logger.log(self.level, "[LoggingPlugin] %s %s", event.upper(), " -> ".join(str(a) for a in args))

    def on_finish(self, **context) -> None:
        """Log the completion of a batch operation."""
        logger.log(self.level, "[LoggingPlugin] Operation finished: %s", context)


# ---------------------------------------------------------------------------
# TaggingPlugin
# ---------------------------------------------------------------------------


class TaggingPlugin(BasePlugin):
    """Prepend or update a ``tags`` field in YAML frontmatter of MD/MDX files.

    If the file already has YAML frontmatter (``---`` delimiters), the tags
    list is added or merged.  Otherwise a minimal frontmatter block is
    prepended.

    Parameters
    ----------
    tags:
        List of tag strings to add to every processed document.

    Example
    -------
    ::

        from lobster_porter.plugins.examples import TaggingPlugin

        plugin = TaggingPlugin(tags=["migrated", "2025-q1"])
    """

    name = "tagging"

    def __init__(self, tags: list[str] | None = None) -> None:
        super().__init__()
        self.tags: list[str] = tags or []

    def on_event(self, event: str, *args) -> None:
        """Tag destination MDX/MD files after a ``"move"`` or ``"copy"`` event.

        Parameters
        ----------
        event:
            Only ``"move"`` and ``"copy"`` events are handled.
        *args:
            ``(source_path, destination_path)``; the destination is tagged.
        """
        if not self.enabled or event not in {"move", "copy"}:
            return
        if len(args) < 2:
            return
        dst: Path = args[1]
        if dst.suffix not in {".md", ".mdx"}:
            return
        self._tag_file(dst)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tag_file(self, path: Path) -> None:
        """Add :attr:`tags` to the YAML frontmatter of *path*."""
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        fm_pattern = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
        match = fm_pattern.match(content)
        if match:
            fm_body = match.group(1)
            tags_pattern = re.compile(r"^tags:\s*\[(.*?)\]", re.MULTILINE)
            tags_match = tags_pattern.search(fm_body)
            if tags_match:
                existing = [t.strip().strip("\"'") for t in tags_match.group(1).split(",") if t.strip()]
                merged = list(dict.fromkeys(existing + self.tags))
                new_tags_line = "tags: [{}]".format(", ".join(f'"{t}"' for t in merged))
                new_fm = tags_pattern.sub(new_tags_line, fm_body)
            else:
                new_tags_line = "tags: [{}]".format(", ".join(f'"{t}"' for t in self.tags))
                new_fm = fm_body + f"\n{new_tags_line}"
            new_content = f"---\n{new_fm}\n---\n" + content[match.end():]
        else:
            tags_line = "tags: [{}]".format(", ".join(f'"{t}"' for t in self.tags))
            new_content = f"---\n{tags_line}\n---\n" + content
        path.write_text(new_content, encoding="utf-8")
        logger.debug("[TaggingPlugin] Tagged %s with %s", path, self.tags)


# ---------------------------------------------------------------------------
# StatisticsPlugin
# ---------------------------------------------------------------------------


class StatisticsPlugin(BasePlugin):
    """Collect and report statistics about file operations.

    After a batch run, call :meth:`report` to get a formatted summary, or
    access :attr:`counts` directly.

    Example
    -------
    ::

        from lobster_porter.plugins.examples import StatisticsPlugin

        stats = StatisticsPlugin()
        porter.register_plugin(stats)
        porter.move("old/", "new/")
        print(stats.report())
    """

    name = "statistics"

    def __init__(self) -> None:
        super().__init__()
        #: Mapping of ``event_name → count``.
        self.counts: dict[str, int] = defaultdict(int)
        #: Total bytes transferred (move + copy operations only).
        self.bytes_transferred: int = 0

    def on_start(self, **context) -> None:
        """Reset counters when a new batch starts."""
        self.counts.clear()
        self.bytes_transferred = 0

    def on_event(self, event: str, *args) -> None:
        """Increment the counter for *event* and accumulate byte count.

        Parameters
        ----------
        event:
            Event name.
        *args:
            For ``"move"``/``"copy"``: ``(source_path, destination_path)``.
        """
        if not self.enabled:
            return
        self.counts[event] += 1
        if event in {"move", "copy"} and len(args) >= 2:
            dst: Path = args[1]
            if dst.exists():
                self.bytes_transferred += dst.stat().st_size

    def on_finish(self, **context) -> None:
        """Log the statistics summary when the batch finishes."""
        logger.info("[StatisticsPlugin] %s", self.report())

    def report(self) -> str:
        """Return a human-readable statistics summary.

        Returns
        -------
        str
            Multi-line summary string.
        """
        lines = ["=== LobsterPorter Statistics ==="]
        for event, count in sorted(self.counts.items()):
            lines.append(f"  {event}: {count} file(s)")
        kb = self.bytes_transferred / 1024
        lines.append(f"  bytes transferred: {kb:.1f} KB")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.counts.clear()
        self.bytes_transferred = 0
