"""Owned, monitor-aware viewer for Bundle File Tool session logs."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ui.window_placement import place_toplevel_on_parent_monitor


def discover_log_files(log_dir: str | Path) -> list[Path]:
    """Return supported log files newest-first without traversing subfolders."""

    directory = Path(log_dir)
    if not directory.is_dir():
        return []
    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.casefold() in {".json", ".log", ".txt"}
        and path.stat().st_size > 0
    ]
    return sorted(candidates, key=lambda path: path.stat().st_mtime_ns, reverse=True)


class LogViewer(tk.Toplevel):
    """Browse persistent BFT logs without exposing an unfinished command."""

    def __init__(self, parent: tk.Misc, log_dir: str | Path) -> None:
        super().__init__(parent)
        self.parent_window = parent.winfo_toplevel()
        self.log_dir = Path(log_dir)
        self.files: list[Path] = []
        self.withdraw()
        self.title("Bundle File Tool Logs")
        self.geometry("1000x650")
        self.minsize(720, 440)
        self.transient(self.parent_window)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        shell = ttk.Frame(self, padding=10)
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(1, weight=1)
        shell.columnconfigure(1, weight=1)

        ttk.Label(shell, text=f"Log folder: {self.log_dir}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.file_list = tk.Listbox(shell, width=36, exportselection=False)
        self.file_list.grid(row=1, column=0, sticky="ns", padx=(0, 8))
        self.file_list.bind("<<ListboxSelect>>", self._show_selected)

        text_frame = ttk.Frame(shell)
        text_frame.grid(row=1, column=1, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.text = tk.Text(text_frame, wrap="none", state="disabled", undo=False)
        vertical = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        horizontal = ttk.Scrollbar(text_frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

        controls = ttk.Frame(shell)
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        controls.columnconfigure(0, weight=1)
        self.status = ttk.Label(controls, text="", anchor="w")
        self.status.grid(row=0, column=0, sticky="ew")
        ttk.Button(controls, text="Refresh", command=self.refresh).grid(
            row=0, column=1, padx=(8, 4)
        )
        ttk.Button(controls, text="Close", command=self.destroy).grid(row=0, column=2)

        self.refresh()
        place_toplevel_on_parent_monitor(self, self.parent_window)
        self.deiconify()
        self.lift()

    def refresh(self) -> None:
        try:
            self.files = discover_log_files(self.log_dir)
        except OSError as exc:
            self.files = []
            messagebox.showerror(
                "Logs unavailable",
                f"Could not inspect {self.log_dir}:\n\n{exc}",
                parent=self,
            )
        self.file_list.delete(0, "end")
        for path in self.files:
            self.file_list.insert("end", path.name)
        if self.files:
            self.file_list.selection_set(0)
            self._show_selected()
        else:
            self._set_text("No persistent BFT log files were found.")
            self.status.configure(text="No log files")

    def _show_selected(self, _event: object | None = None) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        path = self.files[int(selection[0])]
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            messagebox.showerror(
                "Log unavailable",
                f"Could not read {path}:\n\n{exc}",
                parent=self,
            )
            return
        self._set_text(content)
        self.status.configure(text=path.name)

    def _set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")


__all__ = ["LogViewer", "discover_log_files"]
