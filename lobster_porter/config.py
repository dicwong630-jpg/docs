"""
lobster_porter.config
=====================

All tuneable parameters for a Porter run live in :class:`Config`.

Keeping configuration in a single dataclass (rather than scattered keyword
arguments) makes it easy to:

* Serialise / deserialise a run definition (JSON, TOML, CLI flags).
* Pass the same config object to every strategy and plugin without coupling
  them to each other.
* Add new options in one place without changing any strategy or plugin
  signatures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Config:
    """Runtime configuration for a Porter session.

    Parameters
    ----------
    source:
        Root directory whose contents will be processed.
    destination:
        Root directory where processed files will land.
    file_patterns:
        Glob patterns that select which files to process.
        Defaults to common document formats.
    dry_run:
        When *True* the porter logs every action it *would* take but does
        not modify any files.  Useful for previewing a run.
    overwrite:
        When *True* existing files in *destination* are silently replaced.
        When *False* (default) a collision raises :class:`FileExistsError`.
    recursive:
        When *True* (default) the source tree is walked recursively.
    extra:
        Arbitrary key/value pairs forwarded to strategies and plugins that
        need domain-specific settings, without polluting the core dataclass.
    """

    source: str | Path = "."
    destination: str | Path = "output"
    file_patterns: List[str] = field(
        default_factory=lambda: ["*.md", "*.mdx", "*.pdf", "*.docx", "*.txt"]
    )
    dry_run: bool = False
    overwrite: bool = False
    recursive: bool = True
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = Path(self.source)
        self.destination = Path(self.destination)
