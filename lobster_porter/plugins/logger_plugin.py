"""
lobster_porter.plugins.logger_plugin
Writes a human-readable transfer log to a text file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import BasePlugin


class LoggerPlugin(BasePlugin):
    """Append a line to *log_file* after every successful transfer."""

    def __init__(self, log_file: str | Path = "porter_transfer.log") -> None:
        self.log_file = Path(log_file)

    def on_after_transfer(self, action: str, src: Path, dst: Path, record) -> None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{timestamp}] {action.upper():5s}  {src}  →  {dst}\n"
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(line)
