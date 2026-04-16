"""
lobster_porter.plugins
======================

Plugin interface and built-in implementations.

Plugins are called at three lifecycle hooks:

* :meth:`BasePlugin.on_start` — once, before any files are processed.
* :meth:`BasePlugin.on_file` — once per file, after the strategy has run.
* :meth:`BasePlugin.on_finish` — once, after all files have been processed.

Extension guide
---------------
To add a new plugin:

1. Create a class that inherits from :class:`BasePlugin`.
2. Override whichever lifecycle hooks you need.
3. Pass an instance to :class:`~lobster_porter.core.Porter` via the
   ``plugins`` list.

Example::

    from lobster_porter.plugins import BasePlugin

    class TagPlugin(BasePlugin):
        \"\"\"Append tag metadata to each processed Markdown file.\"\"\"

        name = "tag"

        def on_file(self, source_file, destination_file, config):
            tag = config.extra.get("tag", "untagged")
            if destination_file.suffix in (".md", ".mdx") and not config.dry_run:
                with destination_file.open("a") as fh:
                    fh.write(f"\\n<!-- tag: {tag} -->\\n")

Multiple plugins can be composed freely; they are called in the order
provided to :class:`~lobster_porter.core.Porter`.
"""

from __future__ import annotations

import datetime
import json
from abc import ABC
from pathlib import Path
from typing import List

from lobster_porter.config import Config


class BasePlugin(ABC):
    """Abstract base class for all Porter plugins.

    All lifecycle methods are *no-ops* by default so that concrete plugins
    only need to override the hooks they actually use.

    Attributes
    ----------
    name:
        A short, human-readable identifier.  Override in subclasses.
    """

    name: str = "base"

    def on_start(self, files: List[Path], config: Config) -> None:
        """Called once before any files are processed.

        Parameters
        ----------
        files:
            The full list of source files that will be processed in this run.
        config:
            The active :class:`~lobster_porter.config.Config` instance.
        """

    def on_file(
        self,
        source_file: Path,
        destination_file: Path,
        config: Config,
    ) -> None:
        """Called once per file, immediately after the strategy has run.

        Parameters
        ----------
        source_file:
            The file that was just transported.
        destination_file:
            Where it landed (or would have landed in a dry run).
        config:
            The active :class:`~lobster_porter.config.Config` instance.
        """

    def on_finish(self, files: List[Path], config: Config) -> None:
        """Called once after all files have been processed.

        Parameters
        ----------
        files:
            The same list that was passed to :meth:`on_start`.
        config:
            The active :class:`~lobster_porter.config.Config` instance.
        """


class IndexPlugin(BasePlugin):
    """Write a ``_index.json`` manifest in the destination directory.

    The manifest lists every transported file with its relative path and
    the timestamp of the run, making it easy to build navigation trees or
    search indexes on top of the output.
    """

    name = "index"

    def on_finish(self, files: List[Path], config: Config) -> None:
        if config.dry_run:
            return
        index = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source": str(config.source),
            "destination": str(config.destination),
            "files": [
                str(f.relative_to(config.source)) for f in files
            ],
        }
        index_path = config.destination / "_index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2))


class LogPlugin(BasePlugin):
    """Print a one-line status message for every processed file.

    This plugin is intentionally simple and is meant to serve as both a
    useful default and a reference implementation for custom plugins.
    """

    name = "log"

    def on_start(self, files: List[Path], config: Config) -> None:
        prefix = "[dry-run] " if config.dry_run else ""
        print(f"{prefix}lobster_porter: starting — {len(files)} file(s) to process")

    def on_file(
        self,
        source_file: Path,
        destination_file: Path,
        config: Config,
    ) -> None:
        prefix = "[dry-run] " if config.dry_run else ""
        print(f"{prefix}  {source_file} → {destination_file}")

    def on_finish(self, files: List[Path], config: Config) -> None:
        prefix = "[dry-run] " if config.dry_run else ""
        print(f"{prefix}lobster_porter: done — {len(files)} file(s) processed")
