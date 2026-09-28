"""Monitor-aware placement policy for BFT-owned top-level windows."""

from __future__ import annotations

from ui import window_placement as placement


class FakeWindow:
    def __init__(self, state="normal"):
        self.current_state = state
        self.geometries = []
        self.after_idle_calls = []

    def state(self, value=None):
        if value is not None:
            self.current_state = value
        return self.current_state

    def geometry(self, value):
        self.geometries.append(value)

    def iconify(self):
        self.current_state = "iconic"

    def after_idle(self, callback):
        self.after_idle_calls.append(callback)
        callback()


def test_centred_position_preserves_negative_monitor_coordinates():
    area = placement.WorkArea(-1920, 0, 0, 1040)

    position = placement.centred_position(
        (-1800, 100, 1200, 800),
        (500, 300),
        area,
    )

    assert position == (-1450, 350)
    assert area.left <= position[0] <= area.right - 500


def test_centred_position_clamps_an_oversized_window_to_the_work_area_origin():
    area = placement.WorkArea(1920, -900, 3200, 0)

    assert placement.centred_position(
        (3100, -100, 100, 100),
        (1600, 1200),
        area,
    ) == (1920, -900)


def test_clamped_position_recovers_geometry_from_a_removed_display():
    area = placement.WorkArea(0, 0, 1920, 1040)

    assert placement.clamped_position((-1800, 100), (1100, 750), area) == (0, 100)
    assert placement.clamped_position((5000, 3000), (1100, 750), area) == (820, 290)


def test_restore_last_never_restores_an_accidental_minimize():
    assert placement.resolved_startup_state("restore", "maximized") == "maximized"
    assert placement.resolved_startup_state("restore", "minimized") == "normal"
    assert placement.resolved_startup_state("invalid", "invalid") == "normal"


def test_malformed_geometry_falls_back_without_reaching_tk():
    assert placement.safe_window_geometry("not geometry") == "1000x700"
    assert placement.safe_window_geometry("1200x800-1920+20") == "1200x800-1920+20"


def test_macos_maximize_fills_work_area_without_fullscreen():
    window = FakeWindow()
    area = placement.WorkArea(-1920, 24, 0, 1080)

    state = placement.apply_startup_window_state(
        window, "maximized", work_area=area, platform_name="darwin")

    assert state == "maximized"
    assert window.geometries == ["1920x1056-1920+24"]
    assert window.current_state == "normal", "macOS fullscreen was not requested"


def test_minimized_start_is_applied_after_mapping():
    window = FakeWindow()
    assert placement.apply_startup_window_state(
        window, "minimized", platform_name="win32") == "minimized"
    assert len(window.after_idle_calls) == 1
    assert placement.observed_window_state(window) == "minimized"


def test_toplevel_is_placed_from_the_parent_rectangle(monkeypatch):
    class Parent:
        def winfo_toplevel(self):
            return self

        def update_idletasks(self):
            pass

        def winfo_rootx(self):
            return -1800

        def winfo_rooty(self):
            return 100

        def winfo_width(self):
            return 1200

        def winfo_height(self):
            return 800

    class Window:
        def update_idletasks(self):
            pass

        def winfo_width(self):
            return 500

        def winfo_height(self):
            return 300

        def winfo_reqwidth(self):
            return 480

        def winfo_reqheight(self):
            return 280

    moved = []
    area = placement.WorkArea(-1920, 0, 0, 1040)
    monkeypatch.setattr(
        placement,
        "monitor_work_area_for_widget",
        lambda _widget: area,
    )
    monkeypatch.setattr(
        placement,
        "_move_tk_window",
        lambda window, x, y: moved.append((window, x, y)) or True,
    )
    window = Window()

    assert placement.place_toplevel_on_parent_monitor(window, Parent()) is True
    assert moved == [(window, -1450, 350)]


def test_restored_toplevel_is_reconciled_with_the_nearest_display(monkeypatch):
    class Window:
        def update_idletasks(self):
            pass

        def winfo_rootx(self):
            return -1800

        def winfo_rooty(self):
            return 100

        def winfo_width(self):
            return 1100

        def winfo_height(self):
            return 750

    window = Window()
    moved = []
    monkeypatch.setattr(
        placement,
        "monitor_work_area_for_widget",
        lambda _widget: placement.WorkArea(0, 0, 1920, 1040),
    )
    monkeypatch.setattr(
        placement,
        "_move_tk_window",
        lambda item, x, y: moved.append((item, x, y)) or True,
    )

    assert placement.reconcile_toplevel_with_displays(window) is True
    assert moved == [(window, 0, 100)]
