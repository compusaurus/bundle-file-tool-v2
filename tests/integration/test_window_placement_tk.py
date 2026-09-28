"""Real-Tk verification of the monitor-aware placement adapter."""

from __future__ import annotations

import tkinter as tk

from ui.window_placement import (
    monitor_work_area_for_widget,
    place_toplevel_on_parent_monitor,
)


def test_real_tk_dialog_stays_on_its_parent_monitor(tk_root):
    parent_area = monitor_work_area_for_widget(tk_root)
    assert parent_area is not None

    dialog = tk.Toplevel(tk_root)
    dialog.geometry("420x220")
    try:
        assert place_toplevel_on_parent_monitor(dialog, tk_root) is True
        dialog.update_idletasks()
        assert monitor_work_area_for_widget(dialog) == parent_area
    finally:
        dialog.destroy()
