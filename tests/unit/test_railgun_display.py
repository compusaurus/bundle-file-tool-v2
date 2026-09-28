"""Reusable signed-coordinate display selection and placement contracts."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from railgun_display import (
    ActiveDisplayResolver,
    DisplayInfo,
    DisplayRect,
    DisplayTopology,
    ResolutionStrategy,
    Win32DisplayDriver,
    geometry_on_display,
    parse_tk_geometry,
    parse_work_area,
    place_process_tree_windows,
    place_process_windows,
    process_tree_ids,
    display_for_window,
    other_display,
)


LEFT = DisplayInfo(
    "left",
    DisplayRect(-1920, 0, 0, 1080),
    DisplayRect(-1920, 0, 0, 1040),
)
RIGHT = DisplayInfo(
    "right",
    DisplayRect(0, 0, 1920, 1080),
    DisplayRect(0, 0, 1920, 1040),
    primary=True,
)


def test_other_display_uses_window_location_and_cycles_spatially():
    above = DisplayInfo("above", DisplayRect(0, -1080, 1920, 0), DisplayRect(0, -1080, 1920, 0))
    topology = DisplayTopology((RIGHT, LEFT, above))
    assert other_display(topology, DisplayRect(-1000, 100, -100, 900)) == above
    assert other_display(topology, DisplayRect(100, -900, 1000, -100)) == RIGHT
    assert other_display(topology, DisplayRect(100, 100, 1000, 900)) == LEFT
    assert display_for_window(topology, DisplayRect(-300, 50, 700, 900)) == RIGHT
    assert display_for_window(topology, DisplayRect(-5000, 50, -4000, 900)) == LEFT


def test_other_display_handles_single_empty_and_mirrored_topologies():
    rect = DisplayRect(100, 100, 700, 900)
    mirror = DisplayInfo("mirror", RIGHT.bounds, RIGHT.work_area)
    invalid = DisplayInfo("invalid", DisplayRect(0, 0, 0, 0), DisplayRect(0, 0, 0, 0))
    assert other_display(DisplayTopology(()), rect) is None
    assert display_for_window(DisplayTopology(()), rect) is None
    assert other_display(DisplayTopology((RIGHT,)), rect) is None
    assert other_display(DisplayTopology((RIGHT, mirror, invalid)), rect) is None


class VirtualDriver:
    def __init__(self, *, cursor=None, foreground=None):
        self._cursor = cursor
        self._foreground = foreground

    def topology(self):
        return DisplayTopology((LEFT, RIGHT))

    def cursor_point(self):
        return self._cursor

    def foreground_rect(self):
        return self._foreground


def test_geometry_models_preserve_negative_virtual_coordinates():
    geometry = parse_tk_geometry("1200x800-1800+120")

    assert geometry is not None and geometry.positioned
    assert geometry.rect == DisplayRect(-1800, 120, -600, 920)
    assert geometry.rect.center == (-1200, 520)
    assert geometry.rect.area == 960_000
    assert LEFT.bounds.contains((-1, 500))
    assert LEFT.bounds.intersection_area(geometry.rect) == 960_000
    assert parse_tk_geometry("broken") is None
    assert parse_tk_geometry("0x700+0+0") is None


def test_saved_app_display_wins_so_splash_and_window_share_one_target():
    resolver = ActiveDisplayResolver(VirtualDriver(cursor=(400, 300)))

    target = resolver.resolve_application_launch(
        saved_geometry="1200x800-1800+120",
        saved_work_area="-1920,0,0,1040",
    )

    assert target is not None
    assert target.display == LEFT
    assert target.reason == "saved-window"


def test_removed_saved_display_falls_back_to_current_attention():
    resolver = ActiveDisplayResolver(VirtualDriver(cursor=(500, 300)))

    target = resolver.resolve_application_launch(
        saved_geometry="1200x800-5000+120",
        saved_work_area="-5000,0,-3000,1040",
    )

    assert target is not None
    assert target.display == RIGHT
    assert target.reason == "cursor"


def test_foreground_and_primary_fallbacks_are_explicit():
    foreground = DisplayRect(-1500, 100, -500, 900)
    resolver = ActiveDisplayResolver(VirtualDriver(cursor=None, foreground=foreground))

    assert resolver.resolve().reason == "foreground-window"
    assert resolver.resolve(ResolutionStrategy.FOREGROUND_WINDOW).display == LEFT
    assert resolver.resolve(ResolutionStrategy.PRIMARY).display == RIGHT


def test_cursor_outside_topology_uses_the_nearest_signed_display():
    target = ActiveDisplayResolver(VirtualDriver(cursor=(-2500, 100))).resolve()

    assert target is not None and target.display == LEFT


def test_geometry_is_centered_or_clamped_inside_the_resolved_work_area():
    assert geometry_on_display("1000x700", LEFT.work_area) == "1000x700-1460+170"
    assert geometry_on_display("1000x700-1900+900", LEFT.work_area) == (
        "1000x700-1900+340"
    )
    assert geometry_on_display("broken", RIGHT.work_area) == "1000x700+460+170"
    assert parse_work_area("-1920,0,0,1040") == LEFT.work_area
    assert parse_work_area("bad") is None
    assert parse_work_area("0,0,0,0") is None
    assert LEFT.work_area.centered_window(4000, 3000) == LEFT.work_area


class FakeUser32:
    def __init__(self):
        self.moves = []

    def EnumWindows(self, callback, data):
        callback(101, data)
        callback(102, data)
        return True

    def GetWindowThreadProcessId(self, handle, pointer):
        ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD)).contents.value = (
            77 if handle == 101 else 88
        )
        return 1

    def IsWindowVisible(self, handle):
        return handle == 101

    def GetWindowRect(self, _handle, pointer):
        rect = ctypes.cast(pointer, ctypes.POINTER(wintypes.RECT)).contents
        rect.left, rect.top, rect.right, rect.bottom = 10, 20, 410, 220
        return True

    def SetWindowPos(self, handle, _after, x, y, _width, _height, flags):
        self.moves.append((handle, x, y, flags))
        return True


def test_process_window_adapter_centers_only_the_target_process(monkeypatch):
    # The fake API does not use the Windows calling convention. Let this
    # adapter contract run on Linux/macOS without claiming a native Win32 test.
    if not hasattr(ctypes, "WINFUNCTYPE"):
        monkeypatch.setattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, raising=False)
    api = FakeUser32()

    assert place_process_windows(77, RIGHT.work_area, user32=api) == 1
    assert api.moves == [(101, 760, 420, 0x0001 | 0x0004 | 0x0010)]


class FakeKernel32:
    def __init__(self):
        self.entries = iter(((10, 0), (20, 10), (30, 20), (40, 99)))
        self.closed = []

    def CreateToolhelp32Snapshot(self, _flags, _process_id):
        return 501

    def _next(self, _snapshot, pointer):
        try:
            process_id, parent_process_id = next(self.entries)
        except StopIteration:
            return False
        entry = pointer._obj
        entry.th32ProcessID = process_id
        entry.th32ParentProcessID = parent_process_id
        return True

    Process32FirstW = _next
    Process32NextW = _next

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


def test_process_tree_follows_launcher_descendants_and_closes_the_snapshot():
    kernel = FakeKernel32()

    assert process_tree_ids(10, kernel32=kernel) == {10, 20, 30}
    assert kernel.closed == [501]


def test_process_tree_window_adapter_includes_launcher_descendants(monkeypatch):
    import railgun_display.windows as windows
    if not hasattr(ctypes, "WINFUNCTYPE"):
        monkeypatch.setattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, raising=False)

    api = FakeUser32()
    api.IsWindowVisible = lambda _handle: True
    monkeypatch.setattr(
        windows,
        "process_tree_ids",
        lambda _root, *, kernel32=None: {77, 88},
    )

    assert place_process_tree_windows(77, RIGHT.work_area, user32=api) == 2
    assert [move[0] for move in api.moves] == [101, 102]


def test_empty_topology_has_no_target():
    class EmptyDriver(VirtualDriver):
        def topology(self):
            return DisplayTopology(())

    assert ActiveDisplayResolver(EmptyDriver()).resolve() is None
