"""Actionable rendering of the shared integrity-check result."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from core.checking import CheckResult
from ui.window_placement import place_toplevel_on_parent_monitor


def check_result_text(result: CheckResult) -> str:
    """Copyable text form for diagnostics and issue reports."""
    lines = [
        f"Status: {result.status.upper()}",
        f"Subject: {result.subject}",
        f"Label: {result.label}",
        f"Format: {result.profile or 'not detected'}",
        f"Files checked: {result.file_count}",
        f"Blocking findings: {len(result.blockers)}",
        f"Warnings: {len(result.warnings)}",
    ]
    for finding in result.findings:
        location = f" — {finding.path}" if finding.path else ""
        lines.append(
            f"[{finding.severity.upper()}] {finding.code}{location}: "
            f"{finding.summary}"
        )
        if finding.detail:
            lines.append(f"  {finding.detail}")
        if finding.remediation:
            lines.append(f"  Suggested action: {finding.remediation}")
    return "\n".join(lines)


class CheckResultsDialog(tk.Toplevel):
    """Show findings and offer safe, context-specific remediation."""

    def __init__(
        self,
        parent: Any,
        result: CheckResult,
        *,
        on_exclude: Optional[Callable[[list[str]], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.result = result
        self.on_exclude = on_exclude
        self.title("Integrity Check Results")
        self.geometry("900x500")
        self.minsize(720, 380)
        self.transient(parent)

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        status = {
            "passed": "Passed — ready to continue",
            "warnings": "Passed with warnings",
            "blocked": "Blocked — resolve the findings before continuing",
        }[result.status]
        ttk.Label(
            body,
            text=status,
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            body,
            text=(
                f"{result.file_count:,} files checked · "
                f"{len(result.blockers)} blocking · {len(result.warnings)} warnings"
            ),
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        tree_frame = ttk.Frame(body)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("severity", "path", "finding"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("severity", text="Severity")
        self.tree.heading("path", text="Path")
        self.tree.heading("finding", text="Finding")
        self.tree.column("severity", width=90, stretch=False)
        self.tree.column("path", width=340)
        self.tree.column("finding", width=360)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._show_selected)

        for index, finding in enumerate(result.findings):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(finding.severity.title(), finding.path, finding.summary),
            )

        self.detail_var = tk.StringVar(
            value=("No findings." if not result.findings
                   else "Select a finding to see its explanation and suggested action."))
        ttk.Label(
            body,
            textvariable=self.detail_var,
            wraplength=840,
            justify="left",
        ).grid(row=3, column=0, sticky="ew", pady=(8, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Copy details", command=self._copy).pack(
            side="left", padx=(0, 8))
        blocker_paths = sorted({item.path for item in result.blockers if item.path})
        if on_exclude is not None and blocker_paths:
            ttk.Button(
                buttons,
                text="Exclude blocking paths for this session",
                command=lambda: self._exclude(blocker_paths),
            ).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        place_toplevel_on_parent_monitor(self, parent)

    def _show_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        finding = self.result.findings[int(selected[0])]
        pieces = [finding.detail or finding.summary]
        if finding.remediation:
            pieces.append(f"Suggested action: {finding.remediation}")
        self.detail_var.set("\n".join(pieces))

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(check_result_text(self.result))
        self.update()

    def _exclude(self, paths: list[str]) -> None:
        if self.on_exclude is not None:
            self.on_exclude(paths)
        self.destroy()


def show_check_results(
    parent: Any,
    result: CheckResult,
    *,
    on_exclude: Optional[Callable[[list[str]], None]] = None,
) -> CheckResultsDialog:
    return CheckResultsDialog(parent, result, on_exclude=on_exclude)


__all__ = ["CheckResultsDialog", "check_result_text", "show_check_results"]
