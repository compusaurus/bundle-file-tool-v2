"""Native-safe fatal error reporting for windowless GUI launch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, TextIO


def show_startup_failure(error: BaseException, log_path: Path,
                         fallback_stream: Optional[TextIO] = None) -> None:
    """Surface a launch failure without assuming Tk can create a root."""
    message = (
        "Bundle File Tool could not start.\n\n"
        f"{type(error).__name__}: {error}\n\n"
        f"Startup log:\n{log_path}")
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, message, "Bundle File Tool startup failure", 0x10)
            return
        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e",
                 'display dialog ' + _apple_script_string(message)
                 + ' with title "Bundle File Tool startup failure" buttons {"OK"}'],
                check=False, timeout=10, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            return
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        try:
            messagebox.showerror(
                "Bundle File Tool startup failure", message, parent=root)
        finally:
            root.destroy()
        return
    except Exception:
        pass
    if fallback_stream is not None:
        try:
            fallback_stream.write(message + "\n")
            fallback_stream.flush()
        except Exception:
            pass


def _apple_script_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r", "").replace("\n", "\\n")
    return f'"{escaped}"'


__all__ = ["show_startup_failure"]
