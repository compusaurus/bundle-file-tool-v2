"""Local, session-authorized directory browsing without a desktop display."""
from __future__ import annotations

from itertools import islice
import os
from pathlib import Path

from core.exceptions import BundleFileToolError


def browse_directory(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("path", ""), str):
        raise ValueError("Directory request must contain a text path")
    path = Path(payload.get("path") or Path.home()).expanduser()
    try:
        path = path.resolve()
        if path.is_file():
            path = path.parent
        if not path.is_dir():
            raise ValueError("The selected folder does not exist")
        entries = []
        with os.scandir(path) as children:
            candidates = list(islice(children, 1001))
        for child in candidates[:1000]:
            try:
                directory = child.is_dir()
                if directory or child.is_file():
                    entries.append({"name": child.name, "path": str(path / child.name),
                                    "directory": directory})
            except OSError:
                continue
        entries.sort(key=lambda entry: (not entry["directory"], entry["name"].casefold()))
        return {"path": str(path), "parent": str(path.parent), "entries": entries,
                "truncated": len(candidates) > 1000, "separator": os.sep}
    except OSError as exc:
        raise BundleFileToolError(f"Cannot read folder {path}: {exc.strerror}") from exc
