# BFT_B115_RULE_EDITOR - focused rule editor and selection review
# ===================================================================================================
# SOURCEFILE: rule_editor.py
# RELPATH: bundle_file_tool_v2/src/ui/rule_editor.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_RULE_EDITOR
# DESCRIPTION: The §7.3 rule editor and §7.4 review surface. Both preview
#              their effect before applying, and neither writes governed policy.
# Relative Path: src/ui/rule_editor.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Two dialogs, and one rule they both obey: never write governed policy.

§7.3 is explicit - *"The editor must never write bundle_config.json. Governed
policy is rendered as a locked layer."* So the editor edits **session
overrides** only, at Layer 1, and shows every governed rule read-only with the
reason it cannot be touched. SEL-GOV-001 is enforced by a test that hashes the
governed config before and after a full editor session.

The other shared rule is preview-before-apply. §7.3 asks for a live
*"matches N paths / changes M decisions"* readout, which matters more than it
sounds: a pattern that matches 900 paths but changes 0 decisions is doing
nothing, and one that changes 900 is about to reshape the bundle. Both are
worth knowing before pressing Apply, and both are computed by re-planning
in memory - no file is read to answer either.

`RuleEditorPreview` holds that arithmetic and imports no toolkit, so the
counting is testable without a display.
"""

from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.selection import Action, State, matches, normalise
from ui.window_placement import place_toplevel_on_parent_monitor
from ui.workspace_model import WorkspaceModel


# ---------------------------------------------------------------------------
# Preview arithmetic - no toolkit, so it can be tested headless
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RulePreview:
    """What adding one override would do."""

    pattern: str
    action: str
    matched: int
    changed: int
    valid: bool = True
    error: str = ""

    def describe(self) -> str:
        if not self.valid:
            return self.error
        noun = "path" if self.matched == 1 else "paths"
        verb = "decision" if self.changed == 1 else "decisions"
        return f"matches {self.matched} {noun} / changes {self.changed} {verb}"


class RuleEditorPreview:
    """Computes the live readout for a candidate override."""

    def __init__(self, model: WorkspaceModel) -> None:
        self.model = model

    def preview(self, pattern: str, include: bool) -> RulePreview:
        """Count matches and *changes*, which are not the same number.

        A pattern matching 900 already-included files changes nothing. Showing
        only the match count would make a no-op look decisive.
        """
        action = Action.INCLUDE.value if include else Action.EXCLUDE.value
        cleaned = (pattern or "").strip()
        if not cleaned:
            return RulePreview(cleaned, action, 0, 0, False,
                               "Enter a pattern, for example docs/**")
        try:
            matches(cleaned, "probe.txt")
        except Exception as error:                       # pragma: no cover
            return RulePreview(cleaned, action, 0, 0, False,
                               f"Invalid pattern: {error}")

        wanted = State.INCLUDED if include else State.EXCLUDED
        matched = changed = 0
        for decision in self.model.result.plan.decisions:
            if not matches(cleaned, decision.path):
                continue
            matched += 1
            if decision.state is State.BLOCKED:
                continue          # priority 0 cannot be moved, so it cannot change
            if decision.state is not wanted:
                changed += 1
        return RulePreview(cleaned, action, matched, changed)


# ---------------------------------------------------------------------------
# The rule editor dialog
# ---------------------------------------------------------------------------

class RuleEditorDialog(tk.Toplevel):
    """A focused dialog, not a second application (§7.3)."""

    def __init__(self, parent, model: WorkspaceModel,
                 on_apply: Optional[Callable[[], None]] = None) -> None:
        super().__init__(parent)
        self.title("Rules in effect")
        self.model = model
        self.previewer = RuleEditorPreview(model)
        self.on_apply = on_apply
        self.transient(parent)

        self.pattern_var = tk.StringVar(master=self)
        self.action_var = tk.StringVar(master=self, value="exclude")
        self.preview_var = tk.StringVar(master=self, value="")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build()
        self.refresh()
        place_toplevel_on_parent_monitor(self, parent)

    def _build(self) -> None:
        ttk.Label(self, text="Governed policy is shown locked and cannot be "
                             "edited here.").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.rules = ttk.Treeview(self, columns=("layer", "patterns"),
                                  show="tree headings", height=10)
        self.rules.heading("#0", text="Rule")
        self.rules.heading("layer", text="Priority")
        self.rules.heading("patterns", text="Matches")
        self.rules.column("layer", width=80, anchor="center")
        self.rules.column("patterns", width=320)
        self.rules.grid(row=1, column=0, sticky="nsew", padx=10)

        editor = ttk.LabelFrame(self, text="Add a session override")
        editor.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="Pattern").grid(row=0, column=0, padx=6, pady=6)
        entry = ttk.Entry(editor, textvariable=self.pattern_var)
        entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.pattern_var.trace_add("write", lambda *_: self.refresh_preview())

        ttk.Radiobutton(editor, text="Include", value="include",
                        variable=self.action_var,
                        command=self.refresh_preview).grid(row=0, column=2, padx=4)
        ttk.Radiobutton(editor, text="Exclude", value="exclude",
                        variable=self.action_var,
                        command=self.refresh_preview).grid(row=0, column=3, padx=4)

        self.preview_label = ttk.Label(editor, textvariable=self.preview_var)
        self.preview_label.grid(row=1, column=0, columnspan=3, sticky="w",
                                padx=6, pady=(0, 6))
        self.apply_btn = ttk.Button(editor, text="Apply",
                                    command=self.apply_rule, state="disabled")
        self.apply_btn.grid(row=1, column=3, padx=6, pady=(0, 6))

        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Export project rule file...",
                   command=self.export_rules).pack(side="left")
        ttk.Button(buttons, text="Clear session overrides",
                   command=self.clear_overrides).pack(side="left", padx=6)
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right")

    def refresh(self) -> None:
        self.rules.delete(*self.rules.get_children())
        for rule in self.model.rules_in_effect():
            sign = "+" if rule.action == "include" else "-"
            lock = "  (locked)" if rule.locked else ""
            self.rules.insert("", "end",
                              text=f"{sign} {rule.label}{lock}",
                              values=(rule.layer, rule.pattern_text))
        self.refresh_preview()

    def refresh_preview(self) -> None:
        preview = self.previewer.preview(self.pattern_var.get(),
                                         self.action_var.get() == "include")
        self.preview_var.set(preview.describe())
        self.apply_btn.configure(
            state="normal" if preview.valid and preview.matched else "disabled")

    def apply_rule(self) -> None:
        include = self.action_var.get() == "include"
        pattern = self.pattern_var.get().strip()
        if not pattern:
            return
        self.model.set_file(pattern, include)
        self.pattern_var.set("")
        self.refresh()
        if self.on_apply:
            self.on_apply()

    def clear_overrides(self) -> None:
        self.model.clear_all_overrides()
        self.refresh()
        if self.on_apply:
            self.on_apply()

    def export_rules(self) -> None:
        """Write a project rule file - the one explicit, opted-in export.

        SEL-GOV-003: a project rule file is inactive until someone opts in, so
        writing one here arms nothing. It is an export, not an install.
        """
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Export project rule file", defaultextension=".json",
            filetypes=[("Rule files", "*.json")])
        if not target:
            return
        payload = {
            "version": 1,
            "rules": [{"action": action, "pattern": pattern}
                      for action, pattern in self.model.overrides],
        }
        Path(target).write_text(json.dumps(payload, indent=2) + "\n",
                                encoding="utf-8")
        messagebox.showinfo(
            "Exported",
            f"Wrote {len(payload['rules'])} rule(s) to {target}.\n\n"
            f"It is inactive until passed with --rules or opened here.",
            parent=self,
        )


# ---------------------------------------------------------------------------
# The review surface (§7.4)
# ---------------------------------------------------------------------------

class ReviewReportDialog(tk.Toplevel):
    """The transparency contract, rendered and exportable."""

    def __init__(self, parent, model: WorkspaceModel) -> None:
        super().__init__(parent)
        self.title("Selection report")
        self.model = model
        self.transient(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = tk.Text(self, wrap="none", height=24, width=96)
        self.text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.text.insert("1.0", self.render())
        self.text.configure(state="disabled")

        buttons = ttk.Frame(self)
        buttons.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Export JSON...",
                   command=self.export_json).pack(side="left")
        ttk.Button(buttons, text="Export text...",
                   command=self.export_text).pack(side="left", padx=6)
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right")
        place_toplevel_on_parent_monitor(self, parent)

    def render(self) -> str:
        return render_review(self.model)

    def export_json(self) -> None:
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Export selection report", defaultextension=".json",
            filetypes=[("JSON", "*.json")])
        if target:
            Path(target).write_text(
                json.dumps(self.model.result.to_dict(), indent=2) + "\n",
                encoding="utf-8")

    def export_text(self) -> None:
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Export selection report", defaultextension=".txt",
            filetypes=[("Text", "*.txt")])
        if target:
            Path(target).write_text(self.render(), encoding="utf-8")


def render_review(model: WorkspaceModel) -> str:
    """The §7.4 review, as text. No toolkit, so it is testable and exportable.

    Reports a pruned environment as one excluded root with its evidence and an
    explicit "not enumerated" descendant count - never a fabricated file total.
    """
    summary = model.summary()
    lines: List[str] = []
    lines.append("SELECTION REPORT")
    lines.append("=" * 64)
    lines.append(f"Base path      {model.result.base_path}")
    lines.append(f"Generation     {summary.generation}")
    lines.append(f"Base action    {model.result.base_action}")
    lines.append(f"Rule digest    {model.result.plan.rule_stack_digest[:16]}")
    lines.append("")
    lines.append("COUNTS BY STATE")
    for state, count in model.result.plan.counts().items():
        lines.append(f"  {state:10} {count}")
    lines.append(f"  {'estimated':10} {summary.estimated_bytes} bytes")
    lines.append("")

    if model.result.presets_applied:
        lines.append("PRESETS APPLIED")
        for name in model.result.presets_applied:
            lines.append(f"  {name}")
        lines.append("")

    pruned = [row for row in model.result.scan.ledger.to_report()
              if row.get("result") == "detected"]
    lines.append(f"PRUNED DIRECTORIES ({len(pruned)})")
    if not pruned:
        lines.append("  none")
    for row in pruned:
        lines.append(f"  {row['path']}  [{row['family']}] {row['code']}")
        lines.append(f"      evidence: {', '.join(str(e) for e in row['evidence'])}")
        lines.append("      descendants: not enumerated (never walked)")
    lines.append("")

    ambiguous = model.result.scan.ledger.ambiguous
    lines.append(f"AMBIGUOUS, TRAVERSED AND KEPT ({len(ambiguous)})")
    if not ambiguous:
        lines.append("  none")
    for path in sorted(ambiguous):
        lines.append(f"  {path}  {ambiguous[path].code}")
    lines.append("")

    overrides = model.overrides
    lines.append(f"MANUAL OVERRIDES ({len(overrides)})")
    if not overrides:
        lines.append("  none")
    for action, pattern in overrides:
        lines.append(f"  {action:8} {pattern}")
    lines.append("")

    confirm = [d.path for d in model.result.plan.included() if d.confirm_required]
    lines.append(f"OVERRIDES AWAITING CONFIRMATION ({len(confirm)})")
    for path in confirm or ():
        lines.append(f"  {path}")
    if not confirm:
        lines.append("  none")
    lines.append("")

    blocked = model.result.plan.by_state(State.BLOCKED)
    lines.append(f"BLOCKED AT PRIORITY 0 ({len(blocked)})")
    for decision in blocked:
        lines.append(f"  {decision.path}  {decision.code}")
    if not blocked:
        lines.append("  none")
    lines.append("")

    warnings = model.result.plan.warnings
    lines.append(f"SCAN WARNINGS ({len(warnings)})")
    for warning in warnings:
        lines.append(f"  {warning}")
    if not warnings:
        lines.append("  none")
    lines.append("")

    lines.append("EMISSION ORDER")
    for path in model.result.plan.ordered_paths():
        lines.append(f"  {path}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The final selection review (§7.2)
# ---------------------------------------------------------------------------

class ReviewSelectionDialog(tk.Toplevel):
    """The stop-and-look before Create Bundle, with a way to settle it.

    This was a bare Yes/No messagebox reading "This selection still has open
    items ... Create the bundle anyway?", which was wrong twice over. It framed
    an omission as a risk - blocked paths are held at Priority 0 and were never
    going into the bundle, so "anyway" implied a danger that does not exist -
    and it offered no way to resolve the warning, so the same dialog appeared on
    every Create Bundle forever.

    Three outcomes now, because there are genuinely three things an operator
    might mean:

        exclude_blocked   "I know, leave them out"  - records the choice
        continue          "proceed as-is"           - warning stands
        cancel            "let me look again"

    `choice` holds the outcome after the dialog closes.
    """

    def __init__(self, parent, reasons, blocked_paths=()) -> None:
        super().__init__(parent)
        self.title("Review selection")
        self.transient(parent)
        self.resizable(False, False)
        self.choice = "cancel"
        self.blocked_paths = list(blocked_paths)

        body = ttk.Frame(self, padding=16)
        body.grid(row=0, column=0, sticky="nsew")

        ttk.Label(body, text="This selection has items worth a look:",
                  font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        for index, reason in enumerate(reasons, start=1):
            ttk.Label(body, text=f"•  {reason}", wraplength=460,
                      justify="left").grid(row=index, column=0, sticky="w")

        row = len(reasons) + 1
        if self.blocked_paths:
            ttk.Label(
                body,
                text="Blocked paths are recursion hazards. They cannot be "
                     "included, and the bundle will be created without them "
                     "either way.",
                wraplength=460, justify="left", foreground="#555555").grid(
                row=row, column=0, sticky="w", pady=(10, 0))
            row += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=row, column=0, sticky="e", pady=(16, 0))

        if self.blocked_paths:
            self.exclude_btn = ttk.Button(
                buttons, text="Exclude blocked and continue",
                command=lambda: self._choose("exclude_blocked"))
            self.exclude_btn.pack(side="left", padx=4)

        self.continue_btn = ttk.Button(buttons, text="Continue",
                                       command=lambda: self._choose("continue"))
        self.continue_btn.pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(buttons, text="Cancel",
                                     command=lambda: self._choose("cancel"))
        self.cancel_btn.pack(side="left", padx=4)

        self.bind("<Escape>", lambda _e: self._choose("cancel"))
        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("cancel"))
        place_toplevel_on_parent_monitor(self, parent)

    def _choose(self, choice: str) -> None:
        self.choice = choice
        self.destroy()
