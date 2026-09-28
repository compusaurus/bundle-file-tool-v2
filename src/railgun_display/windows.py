"""Zero-dependency Win32 driver and child-window placement adapter."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from .models import DisplayInfo, DisplayRect, DisplayTopology


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class _ProcessEntry32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _rect(value: wintypes.RECT) -> DisplayRect:
    return DisplayRect(value.left, value.top, value.right, value.bottom)


def _load_user32():
    """Load private function objects, isolated from toolkit ctypes metadata."""

    return ctypes.WinDLL("user32", use_last_error=True)


def _set_signature(function, argument_types, result_type) -> None:
    """Give private Win32 functions pointer-safe signatures; leave fakes alone."""

    try:
        function.argtypes = argument_types
        function.restype = result_type
    except AttributeError:
        pass


class Win32DisplayDriver:
    """Read monitor, cursor, and foreground-window state from User32."""

    def __init__(self, user32: object | None = None) -> None:
        if os.name != "nt" and user32 is None:
            raise OSError("Win32 display services are unavailable")
        # A private loader prevents another GUI toolkit from leaving argtypes
        # on the process-global ``ctypes.windll.user32`` function objects.
        # PySide6/Qt integrations can otherwise make GetMonitorInfoW reject an
        # equivalent structure created by this small adapter.
        self.user32 = user32 or _load_user32()

    def topology(self) -> DisplayTopology:
        displays: list[DisplayInfo] = []
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )
        _set_signature(
            self.user32.GetMonitorInfoW,
            [wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo)],
            wintypes.BOOL,
        )
        _set_signature(
            self.user32.EnumDisplayMonitors,
            [wintypes.HDC, ctypes.POINTER(wintypes.RECT), callback_type, wintypes.LPARAM],
            wintypes.BOOL,
        )

        def collect(handle, _dc, _rect_pointer, _data):
            info = _MonitorInfo()
            info.cbSize = ctypes.sizeof(_MonitorInfo)
            if self.user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                displays.append(
                    DisplayInfo(
                        info.szDevice,
                        _rect(info.rcMonitor),
                        _rect(info.rcWork),
                        bool(info.dwFlags & 1),
                    )
                )
            return True

        callback = callback_type(collect)
        self.user32.EnumDisplayMonitors(None, None, callback, 0)
        return DisplayTopology(tuple(displays))

    def cursor_point(self) -> tuple[int, int] | None:
        point = wintypes.POINT()
        _set_signature(
            self.user32.GetCursorPos,
            [ctypes.POINTER(wintypes.POINT)],
            wintypes.BOOL,
        )
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            return None
        return int(point.x), int(point.y)

    def foreground_rect(self) -> DisplayRect | None:
        _set_signature(self.user32.GetForegroundWindow, [], wintypes.HWND)
        _set_signature(
            self.user32.GetWindowRect,
            [wintypes.HWND, ctypes.POINTER(wintypes.RECT)],
            wintypes.BOOL,
        )
        handle = self.user32.GetForegroundWindow()
        if not handle:
            return None
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(handle, ctypes.byref(rect)):
            return None
        return _rect(rect)


def create_display_driver() -> Win32DisplayDriver | None:
    """Return the native driver where supported; callers retain fail-open policy."""

    if os.name != "nt":
        return None
    try:
        return Win32DisplayDriver()
    except (AttributeError, OSError):
        return None


def process_tree_ids(
    root_process_id: int,
    *,
    kernel32: object | None = None,
) -> set[int]:
    """Snapshot ``root_process_id`` and all descendants without dependencies."""

    root_process_id = int(root_process_id)
    if os.name != "nt" and kernel32 is None:
        return {root_process_id}
    api = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
    _set_signature(
        api.CreateToolhelp32Snapshot,
        [wintypes.DWORD, wintypes.DWORD],
        wintypes.HANDLE,
    )
    _set_signature(
        api.Process32FirstW,
        [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32)],
        wintypes.BOOL,
    )
    _set_signature(
        api.Process32NextW,
        [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32)],
        wintypes.BOOL,
    )
    _set_signature(api.CloseHandle, [wintypes.HANDLE], wintypes.BOOL)

    snapshot = api.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot in {None, invalid_handle}:
        return {root_process_id}

    parents: dict[int, int] = {}
    entry = _ProcessEntry32()
    entry.dwSize = ctypes.sizeof(_ProcessEntry32)
    try:
        available = bool(api.Process32FirstW(snapshot, ctypes.byref(entry)))
        while available:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            available = bool(api.Process32NextW(snapshot, ctypes.byref(entry)))
    finally:
        api.CloseHandle(snapshot)

    process_ids = {root_process_id}
    changed = True
    while changed:
        changed = False
        for process_id, parent_process_id in parents.items():
            if parent_process_id in process_ids and process_id not in process_ids:
                process_ids.add(process_id)
                changed = True
    return process_ids


def _place_windows(
    process_ids: set[int],
    work_area: DisplayRect,
    *,
    user32: object | None = None,
) -> int:
    if os.name != "nt" and user32 is None:
        return 0
    api = user32 or _load_user32()
    moved = 0
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _set_signature(
        api.GetWindowThreadProcessId,
        [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)],
        wintypes.DWORD,
    )
    _set_signature(api.IsWindowVisible, [wintypes.HWND], wintypes.BOOL)
    _set_signature(
        api.GetWindowRect,
        [wintypes.HWND, ctypes.POINTER(wintypes.RECT)],
        wintypes.BOOL,
    )
    _set_signature(
        api.SetWindowPos,
        [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ],
        wintypes.BOOL,
    )
    _set_signature(api.EnumWindows, [callback_type, wintypes.LPARAM], wintypes.BOOL)

    def place(handle, _data):
        nonlocal moved
        owner = wintypes.DWORD()
        api.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        if owner.value not in process_ids or not api.IsWindowVisible(handle):
            return True
        bounds = wintypes.RECT()
        if not api.GetWindowRect(handle, ctypes.byref(bounds)):
            return True
        target = work_area.centered_window(
            int(bounds.right - bounds.left), int(bounds.bottom - bounds.top)
        )
        flags = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE
        if api.SetWindowPos(handle, 0, target.left, target.top, 0, 0, flags):
            moved += 1
        return True

    callback = callback_type(place)
    api.EnumWindows(callback, 0)
    return moved


def place_process_windows(
    process_id: int,
    work_area: DisplayRect,
    *,
    user32: object | None = None,
) -> int:
    """Center visible top-level windows owned by exactly ``process_id``."""

    return _place_windows({int(process_id)}, work_area, user32=user32)


def place_process_tree_windows(
    root_process_id: int,
    work_area: DisplayRect,
    *,
    user32: object | None = None,
    kernel32: object | None = None,
) -> int:
    """Center windows owned by a process or a launcher-created descendant."""

    process_ids = process_tree_ids(root_process_id, kernel32=kernel32)
    return _place_windows(process_ids, work_area, user32=user32)
