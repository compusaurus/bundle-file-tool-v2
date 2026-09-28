"""Per-user integrity-check automation preferences."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from ui.window_placement import place_toplevel_on_parent_monitor


class CheckPreferencesDialog(tk.Toplevel):
    """Choose when checks start automatically, outside governed config."""

    _OPTIONS = (
        (
            "check_selection_before_create",
            "Check the source selection before creating a bundle",
            "Reads selected content early so actionable findings appear before publication.",
        ),
        (
            "check_bundle_on_load",
            "Check bundles when they are opened or pasted",
            "A parsed bundle is not marked ready for extraction until the check passes.",
        ),
        (
            "check_before_extract",
            "Require a current passing check before extraction",
            "Hard safety blockers remain mandatory even when automatic loading is disabled.",
        ),
        (
            "verify_output_after_create",
            "Verify a saved bundle after creation",
            "Reports Created and verified only after the written artifact reopens cleanly.",
        ),
    )

    def __init__(self, parent: Any, user_state: Any) -> None:
        super().__init__(parent)
        self.user_state = user_state
        self.saved = False
        self.title("Integrity Check Preferences")
        self.resizable(False, False)
        self.transient(parent)
        self.variables = {
            key: tk.BooleanVar(value=bool(user_state.get(key, True)))
            for key, _label, _description in self._OPTIONS
        }

        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")
        ttk.Label(
            body,
            text="Choose when Bundle File Tool checks automatically:",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        for row, (key, label, description) in enumerate(self._OPTIONS, start=1):
            ttk.Checkbutton(
                body,
                text=label,
                variable=self.variables[key],
            ).grid(row=row, column=0, sticky="w", pady=(6, 0))
            ttk.Label(
                body,
                text=description,
                foreground="#555555",
                wraplength=560,
                justify="left",
            ).grid(row=row, column=1, sticky="w", padx=(12, 0), pady=(6, 0))

        ttk.Label(
            body,
            text=(
                "These preferences control convenience automation. Unsafe paths, "
                "invalid checksums, and confirmed unsafe nesting are never bypassed."
            ),
            wraplength=680,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(16, 0))

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
        for key, variable in self.variables.items():
            self.user_state.set(key, bool(variable.get()))
        if not self.user_state.save():
            messagebox.showerror(
                "Integrity preferences not saved",
                "Bundle File Tool could not write the per-user state file.",
                parent=self,
            )
            return
        self.saved = True
        self.destroy()


def edit_check_preferences(parent: Any, user_state: Any) -> bool:
    dialog = CheckPreferencesDialog(parent, user_state)
    parent.wait_window(dialog)
    return dialog.saved


__all__ = ["CheckPreferencesDialog", "edit_check_preferences"]
