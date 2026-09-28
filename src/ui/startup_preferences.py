"""Per-user startup-window preferences for the Tk desktop adapter."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from ui.window_placement import place_toplevel_on_parent_monitor


class StartupPreferencesDialog(tk.Toplevel):
    """Edit launch state without modifying governed product configuration."""

    _OPTIONS = (
        ("Restore Last", "restore",
         "Restore the last visible state; Normal is used on first launch."),
        ("Normal", "normal", "Open as a standard resizable window."),
        ("Maximized", "maximized",
         "Fill the monitor work area without entering macOS fullscreen."),
        ("Minimized", "minimized",
         "Start in the Dock or taskbar. This can make launch look invisible."),
    )

    def __init__(self, parent: Any, user_state: Any) -> None:
        super().__init__(parent)
        self.user_state = user_state
        self.saved = False
        self.title("Startup Window")
        self.resizable(False, False)
        self.transient(parent)

        self.mode_var = tk.StringVar(value=user_state.startup_mode())
        self.remember_var = tk.BooleanVar(
            value=bool(user_state.get("remember_window_geometry", True)))

        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            body, text="Choose how Bundle File Tool opens:",
            font=("TkDefaultFont", 10, "bold")).grid(
                row=0, column=0, sticky="w", pady=(0, 8))

        for row, (label, value, description) in enumerate(
                self._OPTIONS, start=1):
            ttk.Radiobutton(
                body, text=label, value=value, variable=self.mode_var).grid(
                    row=row, column=0, sticky="w", pady=(4, 0))
            ttk.Label(
                body, text=description, foreground="#555555",
                wraplength=440, justify="left").grid(
                    row=row, column=1, sticky="w", padx=(10, 0), pady=(4, 0))

        ttk.Checkbutton(
            body, text="Remember normal window size and position",
            variable=self.remember_var).grid(
                row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(
            side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save", command=self._save).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        place_toplevel_on_parent_monitor(self, parent)
        self.grab_set()

    def _save(self) -> None:
        self.user_state.set("startup_mode", self.mode_var.get())
        self.user_state.set(
            "remember_window_geometry", bool(self.remember_var.get()))
        if not self.user_state.save():
            messagebox.showerror(
                "Startup preference not saved",
                "Bundle File Tool could not write the per-user state file.",
                parent=self)
            return
        self.saved = True
        self.destroy()


def edit_startup_preferences(parent: Any, user_state: Any) -> bool:
    """Show the modal editor and report whether preferences were saved."""
    dialog = StartupPreferencesDialog(parent, user_state)
    parent.wait_window(dialog)
    return dialog.saved


__all__ = ["StartupPreferencesDialog", "edit_startup_preferences"]
