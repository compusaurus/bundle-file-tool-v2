"""Native path chooser used by the loopback web workspace.

Browsers deliberately do not reveal absolute local paths.  Running the chooser
in a short-lived process also keeps Tk on that process's main thread, which is
required by macOS and avoids coupling the HTTP worker threads to a GUI loop.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog


def _initial_directory(value: str) -> str:
    if not value:
        return ""
    path = Path(value).expanduser()
    candidate = path if path.is_dir() else path.parent
    while candidate != candidate.parent and not candidate.is_dir():
        candidate = candidate.parent
    return str(candidate) if candidate.is_dir() else ""


def choose(kind: str, *, title: str, initial_path: str = "",
           default_name: str = "") -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    options = {"title": title}
    initial = _initial_directory(initial_path)
    if initial:
        options["initialdir"] = initial
    try:
        if kind == "folder":
            return filedialog.askdirectory(parent=root, mustexist=True, **options)
        if kind == "file":
            return filedialog.askopenfilename(parent=root, **options)
        if kind == "save":
            if default_name:
                options["initialfile"] = default_name
            return filedialog.asksaveasfilename(
                parent=root, defaultextension=".txt",
                filetypes=(("Bundle text", "*.txt"), ("All files", "*.*")),
                **options)
        raise ValueError(f"Unknown chooser kind: {kind}")
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("folder", "file", "save"))
    parser.add_argument("--title", default="Select a path")
    parser.add_argument("--initial-path", default="")
    parser.add_argument("--default-name", default="")
    args = parser.parse_args()
    selected = choose(
        args.kind, title=args.title, initial_path=args.initial_path,
        default_name=args.default_name)
    print(json.dumps({"path": selected or ""}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
