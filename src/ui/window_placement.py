"""Place BFT-owned windows on the display that contains their caller."""

from __future__ import annotations

import os
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkArea:
    """A monitor work area in virtual-desktop coordinates."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(1, self.right - self.left)

    @property
    def height(self) -> int:
        return max(1, self.bottom - self.top)

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


STARTUP_STATES = frozenset({"restore", "normal", "maximized", "minimized"})
VISIBLE_STATES = frozenset({"normal", "maximized"})
DEFAULT_GEOMETRY = "1000x700"
_GEOMETRY_RE = re.compile(r"^\d+x\d+(?:[+-]\d+[+-]\d+)?$")


def safe_window_geometry(value: Any, default: str = DEFAULT_GEOMETRY) -> str:
    """Return valid Tk geometry or a known-safe size-only fallback."""
    candidate = str(value or "").strip()
    if not _GEOMETRY_RE.fullmatch(candidate):
        return default
    size = candidate.split("+", 1)[0].split("-", 1)[0]
    try:
        width, height = (int(part) for part in size.split("x", 1))
    except (TypeError, ValueError):
        return default
    return candidate if width >= 1 and height >= 1 else default


def resolved_startup_state(mode: Any, last_non_minimized: Any) -> str:
    """Resolve Restore Last without ever restoring an accidental minimize."""
    requested = str(mode or "restore").strip().lower()
    if requested not in STARTUP_STATES:
        requested = "restore"
    if requested != "restore":
        return requested
    remembered = str(last_non_minimized or "normal").strip().lower()
    return remembered if remembered in VISIBLE_STATES else "normal"


def apply_startup_window_state(
        window: Any,
        state: str,
        *,
        work_area: WorkArea | None = None,
        platform_name: str | None = None) -> str:
    """Apply a launch state with macOS maximize distinct from fullscreen."""
    target = state if state in {"normal", "maximized", "minimized"} else "normal"
    platform_name = platform_name or sys.platform

    if target == "normal":
        return target
    if target == "minimized":
        # Iconifying an unmapped Tk root is inconsistent across window
        # managers. Queue it so the application maps normally first.
        window.after_idle(window.iconify)
        return target

    if platform_name == "darwin":
        area = work_area or monitor_work_area_for_widget(window)
        if area is not None:
            window.geometry(
                f"{area.width}x{area.height}{area.left:+d}{area.top:+d}")
            return target

    try:
        window.state("zoomed")
        return target
    except (AttributeError, tk.TclError, TypeError, ValueError):
        area = work_area or monitor_work_area_for_widget(window)
        if area is not None:
            window.geometry(
                f"{area.width}x{area.height}{area.left:+d}{area.top:+d}")
        return target


def observed_window_state(window: Any, effective_state: str = "") -> str:
    """Classify Tk's platform-specific state into BFT's state vocabulary."""
    try:
        current = str(window.state()).lower()
    except (AttributeError, tk.TclError, TypeError, ValueError):
        current = "normal"
    if current in {"iconic", "withdrawn"}:
        return "minimized"
    if current == "zoomed" or effective_state == "maximized":
        return "maximized"
    return "normal"


def centred_position(
    anchor_rect: tuple[int, int, int, int],
    size: tuple[int, int],
    work_area: WorkArea,
) -> tuple[int, int]:
    """Centre ``size`` over an anchor and keep it inside ``work_area``."""

    anchor_x, anchor_y, anchor_width, anchor_height = anchor_rect
    width, height = max(1, size[0]), max(1, size[1])
    x = anchor_x + (anchor_width - width) // 2
    y = anchor_y + (anchor_height - height) // 2
    max_x = max(work_area.left, work_area.right - width)
    max_y = max(work_area.top, work_area.bottom - height)
    return (
        min(max(x, work_area.left), max_x),
        min(max(y, work_area.top), max_y),
    )


def clamped_position(
    position: tuple[int, int],
    size: tuple[int, int],
    work_area: WorkArea,
) -> tuple[int, int]:
    """Keep an existing top-left position inside the selected work area."""

    x, y = position
    width, height = max(1, size[0]), max(1, size[1])
    max_x = max(work_area.left, work_area.right - width)
    max_y = max(work_area.top, work_area.bottom - height)
    return (
        min(max(x, work_area.left), max_x),
        min(max(y, work_area.top), max_y),
    )


def monitor_work_area_for_widget(widget: Any) -> WorkArea | None:
    """Return the work area of the monitor containing the widget's top level."""

    try:
        top = widget.winfo_toplevel()
        top.update_idletasks()
        if os.name == "nt":
            area = _windows_monitor_work_area(top)
            if area is not None:
                return area

        left = int(top.winfo_vrootx())
        top_edge = int(top.winfo_vrooty())
        return WorkArea(
            left,
            top_edge,
            left + int(top.winfo_vrootwidth()),
            top_edge + int(top.winfo_vrootheight()),
        )
    except (AttributeError, OSError, tk.TclError, TypeError, ValueError):
        return None


def place_toplevel_on_parent_monitor(window: Any, parent: Any) -> bool:
    """Centre a Tk top level over its parent on the parent's current display."""

    try:
        parent_top = parent.winfo_toplevel()
        parent_top.update_idletasks()
        window.update_idletasks()
        work_area = monitor_work_area_for_widget(parent_top)
        if work_area is None:
            return False

        anchor = (
            int(parent_top.winfo_rootx()),
            int(parent_top.winfo_rooty()),
            max(1, int(parent_top.winfo_width())),
            max(1, int(parent_top.winfo_height())),
        )
        size = (
            max(int(window.winfo_width()), int(window.winfo_reqwidth()), 1),
            max(int(window.winfo_height()), int(window.winfo_reqheight()), 1),
        )
        x, y = centred_position(anchor, size, work_area)
        return _move_tk_window(window, x, y)
    except (AttributeError, OSError, tk.TclError, TypeError, ValueError):
        return False


def reconcile_toplevel_with_displays(window: Any) -> bool:
    """Clamp restored geometry to the nearest currently available display."""

    try:
        window.update_idletasks()
        work_area = monitor_work_area_for_widget(window)
        if work_area is None:
            return False
        current = (int(window.winfo_rootx()), int(window.winfo_rooty()))
        size = (max(1, int(window.winfo_width())), max(1, int(window.winfo_height())))
        target = clamped_position(current, size, work_area)
        if target == current:
            return True
        return _move_tk_window(window, *target)
    except (AttributeError, OSError, tk.TclError, TypeError, ValueError):
        return False


def _windows_monitor_work_area(top: Any) -> WorkArea | None:
    import ctypes
    from ctypes import wintypes

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    user32 = ctypes.windll.user32
    hwnd = _native_toplevel_handle(top, user32)
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    if not monitor:
        return None
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return WorkArea(
        int(info.rcWork.left),
        int(info.rcWork.top),
        int(info.rcWork.right),
        int(info.rcWork.bottom),
    )


def _native_toplevel_handle(window: Any, user32: Any) -> int:
    from ctypes import wintypes

    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    hwnd = int(window.winfo_id())
    wrapper = user32.GetParent(hwnd)
    return int(wrapper) if wrapper else hwnd


def _move_tk_window(window: Any, x: int, y: int) -> bool:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = _native_toplevel_handle(window, user32)
            flags = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE
            user32.SetWindowPos.argtypes = [
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL
            return bool(user32.SetWindowPos(hwnd, 0, x, y, 0, 0, flags))
        except (AttributeError, OSError, TypeError, ValueError):
            pass

    # On non-Windows platforms Tk accepts signed virtual-desktop coordinates.
    window.geometry(f"{x:+d}{y:+d}")
    return True


__all__ = [
    "DEFAULT_GEOMETRY",
    "WorkArea",
    "apply_startup_window_state",
    "clamped_position",
    "centred_position",
    "monitor_work_area_for_widget",
    "observed_window_state",
    "place_toplevel_on_parent_monitor",
    "reconcile_toplevel_with_displays",
    "resolved_startup_state",
    "safe_window_geometry",
]
