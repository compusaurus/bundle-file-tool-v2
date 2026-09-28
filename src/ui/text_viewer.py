"""Owned, monitor-aware read-only text document viewer."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ui.window_placement import place_toplevel_on_parent_monitor


class TextFileViewer(tk.Toplevel):
    """Display a UTF-8 text file without sending users into internal folders."""

    def __init__(self, parent: tk.Misc, path: str | Path, *, title: str) -> None:
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.path = Path(path)
        self.withdraw()
        self.title(title)
        self.geometry("900x650")
        self.minsize(640, 420)
        self.transient(self.parent_window)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        shell = ttk.Frame(self, padding=10)
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        self.text = tk.Text(shell, wrap="word", state="disabled", undo=False)
        scroll = ttk.Scrollbar(shell, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        footer = ttk.Frame(shell)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        self.status = ttk.Label(footer, text=str(self.path), anchor="w")
        self.status.grid(row=0, column=0, sticky="ew")
        ttk.Button(footer, text="Reload", command=self.reload).grid(
            row=0, column=1, padx=(8, 4)
        )
        ttk.Button(footer, text="Close", command=self.destroy).grid(row=0, column=2)

        self.reload()
        place_toplevel_on_parent_monitor(self, self.parent_window)
        self.deiconify()
        self.lift()

    def reload(self) -> None:
        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Documentation unavailable",
                f"Could not read {self.path}:\n\n{exc}",
                parent=self,
            )
            content = ""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")


__all__ = ["TextFileViewer"]
