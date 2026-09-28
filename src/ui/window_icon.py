"""Bundle File Tool window-branding helpers."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any


WINDOW_ICON_PATH = Path(__file__).resolve().parent / "assets" / "bft-icon.png"


def apply_window_icon(window: Any) -> bool:
    """Apply BFT's packaged icon to a Tk window and future child windows.

    Tk must retain the ``PhotoImage`` for as long as the native window exists,
    so the reference deliberately lives on the window instance.  A missing or
    undecodable branding asset is non-fatal; the application remains usable.
    """

    try:
        image = tk.PhotoImage(master=window, file=str(WINDOW_ICON_PATH))
        window.iconphoto(True, image)
        window._bft_window_icon = image
    except (OSError, tk.TclError):
        return False
    return True


__all__ = ["WINDOW_ICON_PATH", "apply_window_icon"]
