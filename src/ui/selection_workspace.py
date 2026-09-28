# BFT_B115_SELECTION_WORKSPACE - the desktop Selection Workspace frame
# ===================================================================================================
# SOURCEFILE: selection_workspace.py
# RELPATH: bundle_file_tool_v2/src/ui/selection_workspace.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_SELECTION_WORKSPACE
# DESCRIPTION: Tk binding for WorkspaceModel. Renders; decides nothing.
# Relative Path: src/ui/selection_workspace.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""The window from `BFT_SELECTION_WORKSPACE_DESIGN_SPEC` §7.1, bound to a model.

The source and operation controls remain visible above independently selectable
Selections, Rules, Result set, and Operational Guidance views. Their visibility
and layout are remembered in per-user state; Rules and Result set start hidden.
WorkspaceLayout keeps the same live widgets in tabs, equal panes or separate
windows and provides RailGun display placement where a driver is available.

    action bar     source, preset, Rescan, Create bundle
    summary band   counts, pruned roots, estimate, overrides
    folders        tri-state tree with per-folder reason badges
    rules          the active ladder, governed layers marked locked
    decisions      All / Included / Excluded / Blocked, search, bulk actions
    inspector      winning rule, full chain, override action
    footer         what the tool actually did

This module holds no selection logic. Every question is answered by
`WorkspaceModel`, which in turn asks `BundleToolService`; SEL-X-002 forbids a
second implementation of precedence and this is where one would otherwise creep
in. What lives here is widget construction, event binding and formatting.

**Tri-state is drawn as text.** `[x]`, `[-]` and `[ ]` prefix each row rather
than a colour or an icon. §7.2 requires that colour never carry meaning alone,
and a text glyph is also what makes the tree assertable in a headless test.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Mapping, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cancellation import OperationCancelled
from core.checking import CheckResult, SUBJECT_OUTPUT
from core.exceptions import BundleFileToolError
from core.service import BundleToolService
from ui.check_results import show_check_results
from ui.tk_progress import run_with_progress
from ui.workspace_layout import WorkspaceLayout
from ui.workspace_model import (
    VIEW_ALL,
    VIEW_BLOCKED,
    VIEW_EXCLUDED,
    VIEW_INCLUDED,
    TriState,
    WorkspaceModel,
    human_bytes,
)

#: Tri-state glyphs. Text, not colour - see the module docstring.
GLYPH = {
    TriState.CHECKED: "[x]",
    TriState.PARTIAL: "[-]",
    TriState.UNCHECKED: "[ ]",
}

VIEW_LABELS = (("All", VIEW_ALL), ("Included", VIEW_INCLUDED),
               ("Excluded", VIEW_EXCLUDED), ("Blocked", VIEW_BLOCKED))

# Tk Treeview is not a virtual control: every inserted item is a Tcl object.
# Materialising tens of thousands of collapsed descendants makes Windows quite
# correctly report the process as unresponsive. Small plans keep the complete
# tree (and its familiar Expand all behaviour); large plans expose one branch
# at a time. A broad branch is bounded as well -- typing part of a path in the
# Filter presents the matching rows without changing the selection plan.
DECISION_EAGER_LIMIT = 1_000
DECISION_BRANCH_LIMIT = 1_000
TREE_COLUMN_SAMPLE_LIMIT = 256


def scrolled_tree(parent, **options):
    """A Treeview with both scroll bars, in its own grid-managed container.

    BFT_B116_PANEL_SCROLLBARS. Every pane shipped without them in Build 115.
    On a 1,100-file project that is not a cosmetic problem: the rows below the
    fold are simply unreachable, and long paths run off the right edge with no
    way to see the end of them.
    """
    holder = ttk.Frame(parent)
    holder.grid_rowconfigure(0, weight=1)
    holder.grid_columnconfigure(0, weight=1)

    tree = ttk.Treeview(holder, **options)
    tree.grid(row=0, column=0, sticky="nsew")

    vertical = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
    horizontal.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    tree.scroll_x = horizontal
    tree.scroll_y = vertical
    tree.holder = holder
    return tree


def fit_tree_columns(
    tree,
    maximum: int = 1600,
    sample_limit: int = TREE_COLUMN_SAMPLE_LIMIT,
    value_hints: Optional[Mapping[str, str]] = None,
) -> None:
    """Size columns without synchronously measuring an unbounded tree.

    ``tkfont.measure`` crosses the Python/Tcl boundary. Build 118 called it for
    every cell after every interaction, which turns a folded 80,000-file plan
    into hundreds of thousands of synchronous GUI calls. A fixed sample keeps
    the cost independent of project size. Renderers may supply a representative
    longest value so an off-screen long path still activates horizontal scroll.
    """

    font = tkfont.nametofont("TkDefaultFont")
    columns = ("#0", *tree.cget("columns"))
    minimums = getattr(tree, "_minimum_column_widths", None)
    if minimums is None:
        minimums = {
            column: int(tree.column(column, "width"))
            for column in columns
        }
        tree._minimum_column_widths = minimums

    items = []
    stack = [(item, 0) for item in tree.get_children()]
    while stack and len(items) < max(0, sample_limit):
        item, depth = stack.pop()
        items.append((item, depth))
        remaining = sample_limit - len(items)
        if remaining > 0:
            children = tree.get_children(item)
            stack.extend((child, depth + 1) for child in children[:remaining])

    for index, column in enumerate(columns):
        heading = str(tree.heading(column, "text"))
        measured = font.measure(heading) + 28
        hint = str((value_hints or {}).get(column, ""))
        if hint:
            measured = max(measured, font.measure(hint) + 28)
        for item, depth in items:
            if column == "#0":
                value = str(tree.item(item, "text"))
                indent = depth * 20
            else:
                values = tree.item(item, "values")
                value_index = index - 1
                value = str(values[value_index]) if value_index < len(values) else ""
                indent = 0
            measured = max(measured, font.measure(value) + indent + 28)
        tree.column(
            column,
            width=min(maximum, max(minimums[column], measured)),
            stretch=False,
        )


class SelectionWorkspaceFrame(ttk.Frame):
    """Bundle mode as a plan you can inspect, not a checklist you must trust."""

    def __init__(self, parent, config_manager=None, user_state=None,
                 service: Optional[BundleToolService] = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.user_state = user_state
        self.service = service or BundleToolService()
        self.model: Optional[WorkspaceModel] = None
        self.check_result: Optional[CheckResult] = None

        self.source_var = tk.StringVar(master=self)
        self.preset_var = tk.StringVar(master=self, value="")
        self._preset_explicit = False
        self.search_var = tk.StringVar(master=self)
        self.view_var = tk.StringVar(master=self, value=VIEW_INCLUDED)
        self.list_rule_matches_var = tk.BooleanVar(
            master=self, value=(self.user_state.get("workspace_list_rule_matches", True)
                                if self.user_state else True))
        self.summary_var = tk.StringVar(master=self, value="No source selected")
        self.check_status_var = tk.StringVar(
            master=self, value="Integrity: not checked")
        self.status_var = tk.StringVar(
            master=self,
            value="Select a source to plan a bundle",
        )
        self.scope_var = tk.StringVar(master=self, value="")
        self.hide_blocked_var = tk.BooleanVar(master=self, value=False)

        self._expanded: set = set()
        self._tree_rows: Dict[str, str] = {}
        self._selected_path: str = ""
        self._decision_expanded: set = set()
        self._decision_children: Dict[str, List[Tuple[str, bool]]] = {}
        self._decision_rows: Dict[str, object] = {}
        self._decision_lazy = False
        self._decision_virtual_model = False
        self._decision_view = VIEW_INCLUDED
        self._decision_hide_blocked = False
        self._visible_count = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_action_bar()
        self._build_summary_band()
        self._build_panes()
        self._build_footer()
        self._bind_keys()
        self._update_enabled()

    # -- construction ----------------------------------------------------

    def _build_action_bar(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        bar.grid_columnconfigure(1, weight=1)

        ttk.Label(bar, text="Source").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.source_entry = ttk.Entry(bar, textvariable=self.source_var)
        self.source_entry.grid(row=0, column=1, sticky="ew")

        ttk.Button(bar, text="Browse...", command=self.select_source).grid(
            row=0, column=2, padx=4)

        actions = ttk.Frame(bar)
        actions.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        actions.grid_columnconfigure(1, weight=1)
        ttk.Label(actions, text="Selection preset").grid(row=0, column=0, padx=(0, 6))
        self.preset_box = ttk.Combobox(actions, textvariable=self.preset_var,
                                       state="readonly", width=22,
                                       values=self._preset_values())
        self.preset_box.grid(row=0, column=1, sticky="ew")
        self.preset_box.bind("<<ComboboxSelected>>", self._on_preset_selected)

        self.rescan_btn = ttk.Button(actions, text="Rescan", command=self.rescan)
        self.rescan_btn.grid(row=0, column=2, padx=4)
        self.check_btn = ttk.Button(
            actions, text="Check selection", command=self.check_selection)
        self.check_btn.grid(row=0, column=3, padx=(0, 4))
        self.create_btn = ttk.Button(actions, text="Create bundle...",
                                     command=self.create_bundle)
        self.create_btn.grid(row=0, column=4)

    def _preset_values(self) -> List[str]:
        return ["(none)"] + sorted(self.service.presets())

    def _build_summary_band(self) -> None:
        band = ttk.Frame(self)
        band.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        self.summary_label = ttk.Label(band, textvariable=self.summary_var,
                                       anchor="w")
        self.summary_label.pack(side="left", fill="x", expand=True)
        ttk.Label(
            band, textvariable=self.check_status_var, anchor="e"
        ).pack(side="right", padx=(12, 0))

    def _build_panes(self) -> None:
        self.workspace_layout = WorkspaceLayout(
            self, user_state=self.user_state, report=self.status_var.set)
        self.workspace_layout.grid(row=2, column=0, sticky="nsew", padx=8)
        self.notebook = self.workspace_layout.notebook
        self.workspace_tabs = self.workspace_layout.pages
        self.tab_visibility = self.workspace_layout.visible
        self.tab_buttons = self.workspace_layout.checks

        left = self.workspace_layout.content["selections"]
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ttk.Label(left, text="Folders & groups").grid(row=0, column=0, sticky="w")
        self.folder_tree = scrolled_tree(left, columns=("count", "badge"),
                                         show="tree headings", selectmode="browse")
        self.folder_tree.heading("#0", text="Folder")
        self.folder_tree.heading("count", text="Files")
        self.folder_tree.heading("badge", text="Reason")
        self.folder_tree.column("count", width=110, anchor="e")
        self.folder_tree.column("badge", width=110, anchor="w")
        self.folder_tree.holder.grid(row=1, column=0, sticky="nsew", pady=(2, 6))
        self.folder_tree.bind("<<TreeviewSelect>>", self._on_folder_select)
        self.folder_tree.bind("<<TreeviewOpen>>", self._on_folder_open)
        self.folder_tree.bind("<<TreeviewClose>>", self._on_folder_close)
        self.folder_tree.bind("<Button-1>", self._on_folder_click)
        self.folder_tree.bind("<Double-1>", self._on_folder_double_click)
        self.folder_tree.bind("<space>", self._on_space)

        rules = self.workspace_layout.content["rules"]
        rules.grid_rowconfigure(1, weight=1)
        rules.grid_columnconfigure(0, weight=1)
        rules_head = ttk.Frame(rules)
        rules_head.grid(row=0, column=0, sticky="ew")
        ttk.Label(rules_head, text="Rules in effect").pack(side="left")
        self.list_rule_matches_check = ttk.Checkbutton(
            rules_head, text="List matches", variable=self.list_rule_matches_var,
            command=self._toggle_rule_matches)
        self.list_rule_matches_check.pack(side="left", padx=12)
        self.edit_rules_btn = ttk.Button(rules_head, text="Edit rules...",
                                         command=self.edit_rules)
        self.edit_rules_btn.pack(side="right")

        self.rules_tree = scrolled_tree(rules, columns=("patterns",),
                                        show="tree headings", selectmode="browse")
        self.rules_tree.heading("#0", text="Rule")
        self.rules_tree.heading("patterns", text="Matches")
        self.rules_tree.column("patterns", width=240)
        self.rules_tree.holder.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        right = self.workspace_layout.content["result_set"]
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        filters = ttk.Frame(right)
        filters.grid(row=0, column=0, sticky="ew")
        filters.grid_columnconfigure(1, weight=1)
        ttk.Label(filters, text="Search").grid(row=0, column=0, padx=(0, 4))
        self.search_entry = ttk.Entry(filters, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.search_var.trace_add("write", lambda *_: self.refresh_decisions())
        view_choices = ttk.Frame(filters)
        view_choices.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.view_buttons = {}
        for index, (label, value) in enumerate(VIEW_LABELS):
            button = ttk.Radiobutton(
                view_choices, text=label, value=value, variable=self.view_var,
                command=self.refresh_decisions)
            button.grid(row=0, column=index, padx=2)
            self.view_buttons[value] = button
        self.hide_blocked_check = ttk.Checkbutton(
            right, text="Hide blocked", variable=self.hide_blocked_var,
            command=self.refresh_decisions)
        self.hide_blocked_check.grid(
            in_=view_choices, row=1, column=0, columnspan=4, sticky="w", padx=2)

        bulk = ttk.Frame(right)
        bulk.grid(row=1, column=0, sticky="ew", pady=4)
        self.scope_label = ttk.Label(bulk, textvariable=self.scope_var)
        self.scope_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 3))
        self.include_visible_btn = ttk.Button(
            bulk, text="Include visible", command=lambda: self.apply_bulk(True))
        self.include_visible_btn.grid(row=1, column=0, sticky="w", padx=2, pady=1)
        self.exclude_visible_btn = ttk.Button(
            bulk, text="Exclude visible", command=lambda: self.apply_bulk(False))
        self.exclude_visible_btn.grid(row=1, column=1, sticky="w", padx=2, pady=1)
        self.clear_btn = ttk.Button(bulk, text="Clear overrides",
                                    command=self.clear_overrides)
        self.clear_btn.grid(row=1, column=2, sticky="w", padx=2, pady=1)
        self.collapse_btn = ttk.Button(bulk, text="Collapse all",
                                       command=self.collapse_decisions)
        self.collapse_btn.grid(row=2, column=1, sticky="w", padx=2, pady=1)
        self.expand_btn = ttk.Button(bulk, text="Expand all",
                                     command=self.expand_decisions)
        self.expand_btn.grid(row=2, column=0, sticky="w", padx=2, pady=1)
        self.result_actions_button = ttk.Menubutton(bulk, text="Actions…")
        self.result_actions_menu = tk.Menu(self.result_actions_button, tearoff=False)
        self.result_actions_button.configure(menu=self.result_actions_menu)
        for label, command in (("Include visible", lambda: self.apply_bulk(True)),
                               ("Exclude visible", lambda: self.apply_bulk(False)),
                               ("Clear overrides", self.clear_overrides),
                               ("Expand all", self.expand_decisions),
                               ("Collapse all", self.collapse_decisions)):
            self.result_actions_menu.add_command(label=label, command=command)

        def update_action_menu():
            for index, button in enumerate((self.include_visible_btn, self.exclude_visible_btn,
                                             self.clear_btn, self.expand_btn, self.collapse_btn)):
                self.result_actions_menu.entryconfigure(
                    index, state="disabled" if button.instate(["disabled"]) else "normal")

        self.result_actions_menu.configure(postcommand=update_action_menu)

        self.decision_tree = scrolled_tree(
            right, columns=("state", "reason"), show="tree headings",
            selectmode="browse")
        self.decision_tree.heading("#0", text="Path")
        self.decision_tree.heading("state", text="State")
        self.decision_tree.heading("reason", text="Reason")
        self.decision_tree.column("state", width=90, anchor="w")
        self.decision_tree.column("reason", width=180, anchor="w")
        self.decision_tree.holder.grid(row=2, column=0, sticky="nsew")
        self.decision_tree.bind("<<TreeviewSelect>>", self._on_decision_select)
        self.decision_tree.bind("<<TreeviewOpen>>", self._on_decision_open)
        self.decision_tree.bind("<<TreeviewClose>>", self._on_decision_close)
        self.decision_tree.bind("<space>", self._on_decision_space)

        inspector = ttk.LabelFrame(right, text="Why")
        inspector.grid(row=4, column=0, sticky="nsew", pady=(6, 0))
        inspector.grid_columnconfigure(0, weight=1)
        self.inspector_path = ttk.Label(inspector, text="", anchor="w")
        self.inspector_path.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 0))
        self.inspector_text = ttk.Label(
            inspector, text="Select a file or folder to see why it is included, excluded, or blocked.", anchor="w",
                                        wraplength=520, justify="left")
        self.inspector_text.grid(row=1, column=0, sticky="ew", padx=6)
        self.override_btn = ttk.Button(inspector, text="Override for session",
                                       command=self.override_selected,
                                       state="disabled")
        self.override_btn.grid(row=0, column=1, rowspan=2, padx=6, pady=4)
        inspector.bind("<Configure>", lambda event: self.inspector_text.configure(
            wraplength=max(100, event.width - self.override_btn.winfo_reqwidth() - 30)))
        self.show_explanation_var = tk.BooleanVar(self, True)
        explanation_choice = {"manual": False}

        def show_explanation(manual=False):
            if manual:
                explanation_choice["manual"] = True
            if self.show_explanation_var.get():
                inspector.grid()
            else:
                inspector.grid_remove()

        self.explanation_check = ttk.Checkbutton(
            right, text="Show explanation", variable=self.show_explanation_var,
            command=lambda: show_explanation(manual=True))
        self.explanation_check.grid(row=3, column=0, sticky="w", pady=(4, 0))

        def fit_result_controls(event):
            # Wrap action rows only when needed, preserving space for the results
            # and their explanation when four views share a modest-sized window.
            width, height = right.winfo_width(), right.winfo_height()
            def fitting_columns(buttons, choices):
                # A grid column takes the widest control in any of its rows.
                # Linux themes can have wider minimum button sizes than Windows.
                for count in choices:
                    required = sum(max(button.winfo_reqwidth() + 4
                                       for button in buttons[column::count])
                                   for column in range(min(count, len(buttons))))
                    if required <= width:
                        return count
                return 1

            radio_buttons = tuple(self.view_buttons.values())
            filters_width = sum(button.winfo_reqwidth() + 4 for button in radio_buttons)
            columns = fitting_columns(radio_buttons, (4, 2, 1))
            for index, button in enumerate(self.view_buttons.values()):
                button.grid_configure(row=index // columns, column=index % columns, sticky="w")
            filters_width += self.hide_blocked_check.winfo_reqwidth() + 12
            self.hide_blocked_check.grid_configure(in_=view_choices,
                row=0 if width >= filters_width else (4 // columns),
                column=4 if width >= filters_width else 0,
                columnspan=1 if width >= filters_width else columns)
            action_buttons = (
                self.include_visible_btn, self.exclude_visible_btn, self.clear_btn,
                self.expand_btn, self.collapse_btn)
            action_columns = fitting_columns(action_buttons, (5, 3, 2, 1))
            for index, button in enumerate(action_buttons):
                button.grid(row=1 + index // action_columns, column=index % action_columns)
            if height < 230:
                # The complete app includes menus and mode controls above the
                # workspace. In a short grid pane retain every action through
                # a compact menu and keep checkboxes beside it, leaving rows visible.
                for button in action_buttons:
                    button.grid_remove()
                compact = (self.result_actions_button, self.hide_blocked_check,
                           self.explanation_check, self.scope_label)
                self.hide_blocked_check.lift()
                compact_columns = fitting_columns(compact, (4, 2, 1))
                for index, control in enumerate(compact):
                    control.grid(in_=bulk, row=index // compact_columns,
                                 column=index % compact_columns, columnspan=1,
                                 sticky="w", padx=2, pady=1)
            else:
                self.result_actions_button.grid_remove()
                self.scope_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 3))
                self.explanation_check.grid(in_=right, row=3, column=0, columnspan=1,
                                            sticky="w", pady=(4, 0))
            if not explanation_choice["manual"]:
                self.show_explanation_var.set(height >= 360)
                show_explanation()

        right.bind("<Configure>", fit_result_controls)
        view_choices.bind("<Configure>", fit_result_controls)
        self.scope_label.bind("<Configure>", fit_result_controls)
        self._build_operational_guidance()

    def _toggle_workspace_tab(self, key: str) -> None:
        """Hide/show an existing page without losing its plan or selection."""
        self.workspace_layout.toggle_view(key)

    def _build_operational_guidance(self) -> None:
        page = self.workspace_layout.content["guidance"]
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        text = tk.Text(page, wrap="word", width=40, height=10, font="TkDefaultFont",
                       padx=16, pady=12, relief="flat", borderwidth=0)
        scroll = ttk.Scrollbar(page, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        text.insert("1.0", (
            "Create a bundle\n\n"
            "1. Choose a source folder with Browse, or paste a path into Source "
            "and click Rescan. The source field uses the full window width.\n\n"
            "2. Choose a selection preset if needed. Rescan refreshes the plan "
            "after source files change.\n\n"
            "3. In Selections, expand folders to review the source. Click a "
            "checkbox marker or press Space to include or exclude a folder. "
            "[x] means included, [-] means partly included, and [ ] means excluded. "
            "Safety-blocked paths cannot be included.\n\n"
            "4. Click Check selection to review integrity findings, then "
            "Create bundle to choose an output file and write the bundle. "
            "Review selection report explains the current plan.\n\n"
            "Understand and refine the plan\n\n"
            "Turn on Rules above to inspect the active rules or open Edit rules. "
            "Governed rules are locked; session overrides apply only to this plan.\n\n"
            "Turn on Result set to search paths and view All, Included, Excluded, "
            "or Blocked entries. Select a row to read Why. Include visible and "
            "Exclude visible affect the displayed scope. Clear overrides resets "
            "session changes; Ctrl+Z and Ctrl+Y undo and redo selection changes.\n\n"
            "Compare views and use another display\n\n"
            "Use Show views to choose one or more views. Layout can show them as "
            "Tabs, Side by side, Stacked, or an evenly spaced Grid. Show all opens "
            "all four views in a grid. Your layout and visible views are remembered.\n\n"
            "New window opens a view separately without losing its contents. "
            "When a second display is detected, Other display opens or moves that "
            "view there. Close the separate window or choose Return to workspace "
            "to bring it back. Return all to workspace brings every view back.\n\n"
            "For example, choose Selections and Result set with Side by side, "
            "then turn on Operational Guidance and choose its Other display "
            "button. Both selections and results stay live as you change the plan. "
            "Hiding a view does not change the plan.\n\n"
            "Extract or validate a bundle\n\n"
            "Switch to Un-bundle, open a bundle (or use File > Un-bundle from "
            "Clipboard), review its contents, and choose an extraction folder. "
            "Tools > Validate Bundle checks an existing bundle.\n\n"
            "Paths on Linux and WSL\n\n"
            "Use Linux paths such as /home/mpw/project. Windows drives appear "
            "under /mnt, for example /mnt/c/Users/mpw/Python. Browse selects "
            "paths in the operating system running BFT.\n"
        ))
        text.configure(state="disabled")
        self.guidance_text = text

    def _build_footer(self) -> None:
        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew", padx=8, pady=6)
        ttk.Label(footer, textvariable=self.status_var, anchor="w").pack(
            side="left", fill="x", expand=True)
        self.report_btn = ttk.Button(footer, text="Review selection report...",
                                     command=self.review_report)
        self.report_btn.pack(side="right")

    def _bind_keys(self) -> None:
        """§7.2: arrows move focus, Space toggles, Ctrl+Z/Y walk the history."""
        self.bind_all("<Control-z>", lambda _e: self.undo())
        self.bind_all("<Control-y>", lambda _e: self.redo())

    # -- planning --------------------------------------------------------

    def _get_last_dir(self, key: str, fallback_key: str) -> str:
        """Return a usable remembered dialog folder without mutating config."""
        remembered = self.user_state.get(key, "") if self.user_state else ""
        fallback = (self.config_manager.get(fallback_key, "")
                    if self.config_manager else "")
        directory = remembered or fallback
        if directory and not Path(directory).is_dir():
            return ""
        return str(directory)

    def _remember_last_dir(self, key: str, directory: str) -> None:
        """Persist non-critical dialog state outside the governed config."""
        if not self.user_state or not directory:
            return
        try:
            self.user_state.set_and_save(key, str(directory))
        except Exception:
            # Folder memory is a convenience and must not block the operation.
            pass

    def _suggested_bundle_name(self) -> str:
        """Suggest the classic ``<source>_bundle.txt`` filename."""
        if self.model is not None:
            source = self.model.result.base_path
        else:
            source = Path(self.source_var.get().strip())
        source_name = source.name or "project"
        return f"{source_name}_bundle.txt"

    def select_source(self) -> None:
        directory = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Select source folder",
            initialdir=self._get_last_dir(
                "last_source_dir", "global_settings.input_dir"))
        if directory:
            self._remember_last_dir("last_source_dir", directory)
            self._preset_explicit = False
            self.preset_var.set("")
            self.source_var.set(directory)
            self.rescan()

    def _on_preset_selected(self, _event=None) -> None:
        self._preset_explicit = True
        self.apply_preset()

    def _progress_enabled(self, file_count=None) -> bool:
        """Whether an operation of this size gets a progress dialog.

        BFT_B108_PROGRESS_THRESHOLD, carried over from the classic frame. A
        modal dialog for eleven files is worse than none, so small work stays
        inline. A scan passes None because it cannot know its size until it has
        finished - which is exactly why it reports indeterminate progress.
        """
        if not self.config_manager:
            return True
        if not self.config_manager.get("ui.progress.enabled", True):
            return False
        if file_count is None:
            return True
        return file_count >= self.config_manager.get("ui.progress.min_files", 200)

    def rescan(self) -> None:
        """Full re-scan: the only action here that touches the filesystem.

        BFT_B115_WORKSPACE_PROGRESS. Runs behind the PyThermX dialog with a
        Cancel button, like every other long operation since Build 112. A
        4,000-file tree takes seconds to walk, and without this the window
        would simply stop repainting with no bar and no way to stop it.
        """
        source = self.source_var.get().strip()
        if not source:
            return
        presets = self._selected_presets()
        preset_argument = presets if self._preset_explicit else None

        def work(progress=None, cancel=None):
            return self.service.plan_bundle([Path(source)], preset=preset_argument,
                                            progress=progress, cancel=cancel)

        try:
            if self._progress_enabled():
                result = run_with_progress(self, "Scanning source", work,
                                           allow_cancel=True)
            else:
                result = work()
        except OperationCancelled:
            self.status_var.set("Scan cancelled - the previous plan is unchanged")
            return
        except BundleFileToolError as error:
            messagebox.showerror(
                "Cannot plan this source",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        self.model = WorkspaceModel(self.service, result)
        self._invalidate_check()
        if not self._preset_explicit and result.presets_applied:
            self.preset_var.set(result.presets_applied[0])
        self._expanded = set()
        self.refresh_all()

    def apply_preset(self) -> None:
        """Changing the preset re-decides without reading content (§7.1)."""
        if self.model is None:
            self.rescan()
            return
        previous = self.model.result
        selected = self._selected_presets()
        previous_presets = list(previous.inputs.get("preset", []))

        def work(progress=None, cancel=None):
            # Capture the immutable plan result, not the UI-owned WorkspaceModel.
            # The service can re-decide off-thread; model mutation stays on Tk.
            return self.service.replan(
                previous, preset=selected, progress=progress, cancel=cancel)

        try:
            if self._progress_enabled(len(previous.plan.decisions)):
                result = run_with_progress(
                    self, "Applying selection preset", work,
                    allow_cancel=True)
            else:
                result = work()
        except OperationCancelled:
            self.preset_var.set(
                previous_presets[0] if previous_presets else "(none)")
            self.status_var.set(
                "Preset change cancelled - the previous plan is unchanged")
            return
        except BundleFileToolError as error:
            self.preset_var.set(
                previous_presets[0] if previous_presets else "(none)")
            messagebox.showerror(
                "Cannot apply selection preset",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return

        self.model.adopt_result(result)
        self.refresh_all()

    def _selected_presets(self) -> List[str]:
        value = self.preset_var.get()
        return [] if not value or value == "(none)" else [value]

    # -- rendering -------------------------------------------------------

    def refresh_all(self) -> None:
        if (
            self.model is not None
            and self.check_result is not None
            and self.check_result.generation != self.model.result.plan.generation
        ):
            self._invalidate_check(stale=True)
        self.refresh_summary()
        self.refresh_folders()
        self.refresh_rules()
        self.refresh_decisions()
        self._update_enabled()

    def refresh_summary(self) -> None:
        if self.model is None:
            self.summary_var.set("No source selected")
            self._refresh_view_labels({})
            return
        self.summary_var.set(self.model.summary().headline())
        self._refresh_view_labels(self.model.counts_for_views())
        self.status_var.set(self.model.status_text())

    def _refresh_view_labels(self, counts: Mapping[str, int]) -> None:
        """Keep the filter choices honest about the size of each scope."""
        for label, value in VIEW_LABELS:
            button = getattr(self, "view_buttons", {}).get(value)
            if button is not None:
                button.configure(text=f"{label} ({counts.get(value, 0):,})")

    def refresh_folders(self) -> None:
        self.folder_tree.delete(*self.folder_tree.get_children())
        self._tree_rows = {}
        if self.model is None:
            return
        parents = {"": ""}
        selected_item = ""
        for node in self.model.tree(expanded=self._expanded):
            parent_path = node.path.rsplit("/", 1)[0] if "/" in node.path else ""
            parent_item = parents.get(parent_path, "")
            item = self.folder_tree.insert(
                parent_item, "end",
                text=f"{GLYPH[node.state]} {node.label}",
                values=(node.count_text, node.badge),
                open=node.path in self._expanded)
            parents[node.path] = item
            self._tree_rows[item] = node.path
            if (
                node.is_dir
                and node.path not in self._expanded
                and self.model.has_children(node.path)
            ):
                self.folder_tree.insert(item, "end", text="")
            if node.path == self._selected_path:
                selected_item = item
        if selected_item:
            self.folder_tree.selection_set(selected_item)
            self.folder_tree.focus(selected_item)
        fit_tree_columns(self.folder_tree)

    def refresh_rules(self) -> None:
        self.rules_tree.delete(*self.rules_tree.get_children())
        if self.model is None:
            return
        for rule in self.model.rules_in_effect():
            sign = "+" if rule.action == "include" else "-"
            lock = "  (governed, locked)" if rule.locked else ""
            listed = self.list_rule_matches_var.get()
            item = self.rules_tree.insert(
                "", "end", text=f"{sign} [{rule.layer}] {rule.label}{lock}",
                values=(f"{len(rule.patterns)} patterns" if listed else rule.pattern_text,),
                open=listed)
            if listed:
                for pattern in rule.patterns:
                    self.rules_tree.insert(item, "end", values=(pattern,))
        fit_tree_columns(self.rules_tree)

    def _toggle_rule_matches(self) -> None:
        if self.user_state:
            self.user_state.set_and_save("workspace_list_rule_matches", self.list_rule_matches_var.get())
        self.refresh_rules()

    def refresh_decisions(self) -> None:
        """Render the decision list as a folded tree, not 1,100 flat rows.

        BFT_B116_FOLDED_DECISIONS. A flat list is unreadable on a real project:
        the pane opened on a thousand identical-looking backup files with no way
        to see the shape of the selection. Files now sit under their folders,
        collapsed by default, so the pane opens on a handful of rows.

        A search expands automatically - hiding a match inside a collapsed
        folder would make the filter look broken.
        """
        self.decision_tree.delete(*self.decision_tree.get_children())
        if self.model is None:
            self.scope_var.set("")
            self._visible_count = 0
            self._update_enabled()
            return

        view = self.view_var.get()
        search = self.search_var.get().strip()
        hide_blocked = self.hide_blocked_var.get()
        self._decision_view = view
        self._decision_hide_blocked = hide_blocked

        # The native WorkspaceModel can expose its already-built scan topology.
        # Use it for broad, unsearched views instead of allocating every folded
        # DecisionRow and rebuilding the same 80,000-path index in this widget.
        supports_virtual = all(hasattr(self.model, name) for name in (
            "decision_count", "decision_children", "decision_row",
            "decision_width_hints"))
        count = (self.model.decision_count(view=view, hide_blocked=hide_blocked)
                 if supports_virtual and not search else None)
        self._decision_virtual_model = bool(
            supports_virtual and not search and count is not None
            and count > DECISION_EAGER_LIMIT)

        if self._decision_virtual_model:
            rows = []
            self._decision_rows = {}
            self._decision_children = {}
            row_count = int(count)
        else:
            rows = self.model.rows(view=view, search=search,
                                   hide_blocked=hide_blocked)
            self._decision_rows = {row.path: row for row in rows}
            self._decision_children = self._index_decision_children(rows)
            row_count = len(rows)
        self._decision_lazy = row_count > DECISION_EAGER_LIMIT
        self._visible_count = row_count

        if self._decision_lazy:
            self._populate_decision_branch("")
        else:
            # Preserve Build 116's complete folded tree for ordinary projects.
            # It is useful for accessibility traversal and makes Expand all
            # literal when the row count is small enough for Tk to handle.
            self._populate_complete_decision_tree(
                open_folders=bool(search), expanded=self._decision_expanded)

        if row_count == 0:
            hint = (
                "Clear Search or choose another filter"
                if search
                else "Choose another filter or revise the selection rules"
            )
            self.decision_tree.insert(
                "", "end", iid="empty::scope",
                text="No files match this view", values=("", hint))

        noun = "file" if row_count == 1 else "files"
        hidden = ""
        if self.hide_blocked_var.get():
            blocked = self.model.counts_for_views().get(VIEW_BLOCKED, 0)
            if blocked and view != VIEW_BLOCKED:
                hidden = f"  ({blocked} blocked hidden)"
        virtual = "  (folders load on demand)" if self._decision_lazy else ""
        self.scope_var.set(f"{row_count} visible {noun}{hidden}{virtual}")

        if self._decision_virtual_model:
            width_hints = self.model.decision_width_hints()
        else:
            longest_name = max(
                (row.path.rsplit("/", 1)[-1] for row in rows),
                key=len,
                default="",
            )
            width_hints = {
                "#0": f"[x] {longest_name}",
                "state": max((row.state for row in rows), key=len, default=""),
                "reason": max((row.reason for row in rows), key=len, default=""),
            }
        fit_tree_columns(
            self.decision_tree,
            value_hints=width_hints,
        )
        self._update_enabled()

    def _decision_entries(self, path: str) -> List[Tuple[str, bool]]:
        if self._decision_virtual_model:
            return self.model.decision_children(
                path, view=self._decision_view,
                hide_blocked=self._decision_hide_blocked)
        return self._decision_children.get(path, [])

    @staticmethod
    def _index_decision_children(rows) -> Dict[str, List[Tuple[str, bool]]]:
        """Index each filtered path once for on-demand Treeview population."""

        indexed: Dict[str, Dict[str, bool]] = {}
        for row in rows:
            parts = row.path.split("/")
            for depth in range(len(parts)):
                parent = "/".join(parts[:depth])
                child = "/".join(parts[:depth + 1])
                is_dir = depth < len(parts) - 1
                bucket = indexed.setdefault(parent, {})
                bucket[child] = bucket.get(child, False) or is_dir

        children: Dict[str, List[Tuple[str, bool]]] = {}
        for parent, entries in indexed.items():
            ordered = list(entries.items())
            ordered.sort(key=lambda entry: (not entry[1], entry[0].lower()))
            children[parent] = ordered
        return children

    def _insert_decision_entry(self, parent_item: str, path: str,
                               is_dir: bool, *, open_folder: bool = False) -> str:
        if is_dir:
            item = self.decision_tree.insert(
                parent_item, "end", iid=f"dir::{path}",
                text=path.rsplit("/", 1)[-1], values=("", ""),
                open=open_folder,
            )
            return str(item)

        row = (self.model.decision_row(path) if self._decision_virtual_model
               else self._decision_rows[path])
        mark = "[x]" if row.included else "[ ]"
        item = self.decision_tree.insert(
            parent_item, "end", iid=path,
            text=f"{mark} {path.rsplit('/', 1)[-1]}",
            values=(row.state, row.reason),
        )
        return str(item)

    def _populate_complete_decision_tree(self, *, open_folders: bool,
                                         expanded: set) -> None:
        """Materialise a small filtered tree, preserving the legacy UX."""

        def populate(parent_path: str, parent_item: str) -> None:
            for path, is_dir in self._decision_children.get(parent_path, ()):
                is_open = open_folders or path in expanded
                item = self._insert_decision_entry(
                    parent_item, path, is_dir, open_folder=is_open)
                if is_dir:
                    populate(path, item)

        populate("", "")

    def _populate_decision_branch(self, path: str) -> None:
        """Populate one large-plan folder, with a hard synchronous bound."""

        parent_item = f"dir::{path}" if path else ""
        existing = self.decision_tree.get_children(parent_item)
        for item in existing:
            if str(item).startswith("lazy::"):
                self.decision_tree.delete(item)
        if any(not str(item).startswith("lazy::") for item in existing):
            return

        entries = self._decision_entries(path)
        shown = entries[:DECISION_BRANCH_LIMIT]
        for child, is_dir in shown:
            item = self._insert_decision_entry(parent_item, child, is_dir)
            if is_dir and self._decision_entries(child):
                self.decision_tree.insert(
                    item, "end", iid=f"lazy::{child}", text="Loading…")

        remaining = len(entries) - len(shown)
        if remaining:
            marker = f"more::{path or 'root'}"
            self.decision_tree.insert(
                parent_item, "end", iid=marker,
                text=f"… {remaining:,} more rows; refine Filter to view",
                values=("", ""),
            )
            self.status_var.set(
                f"Large branch bounded at {DECISION_BRANCH_LIMIT:,} rows; "
                "refine Filter to inspect the remaining paths")

    def expand_decisions(self) -> None:
        if self._decision_lazy:
            # Opening every descendant is precisely the Build 118 failure mode.
            # Expand what is already materialised; individual branches remain
            # available through their native expander and broad sets via Filter.
            for item in self._decision_folders():
                self.decision_tree.item(item, open=True)
            self.status_var.set(
                "Expand all is bounded for large plans; open a branch or refine "
                "Filter to inspect more paths")
            return
        for item in self._decision_folders():
            self.decision_tree.item(item, open=True)

    def collapse_decisions(self) -> None:
        for item in self._decision_folders():
            self.decision_tree.item(item, open=False)

    def _decision_folders(self) -> List[str]:
        found: List[str] = []
        stack = list(self.decision_tree.get_children())
        while stack:
            item = stack.pop()
            if str(item).startswith("dir::"):
                found.append(item)
                stack.extend(self.decision_tree.get_children(item))
        return found

    # -- events ----------------------------------------------------------

    def _on_folder_select(self, _event=None) -> None:
        """Select a folder for inspection without changing its open state."""
        selected = self.folder_tree.selection()
        if not selected:
            return
        path = self._tree_rows.get(selected[0], "")
        self._selected_path = path
        self.show_inspector(path)

    def _on_folder_open(self, _event=None) -> None:
        """Remember expansion initiated through the native tree indicator."""
        path = self._tree_rows.get(self.folder_tree.focus(), "")
        if path:
            self._expanded.add(path)
            self.after_idle(self.refresh_folders)

    def _on_folder_close(self, _event=None) -> None:
        """Remember collapse initiated through the native tree indicator."""
        path = self._tree_rows.get(self.folder_tree.focus(), "")
        if path:
            self._expanded.discard(path)

    def _on_folder_click(self, event) -> Optional[str]:
        """Toggle a folder row while leaving the native expander independent."""
        item = self.folder_tree.identify_row(event.y)
        if not item:
            return None
        element = self.folder_tree.identify_element(event.x, event.y)
        if "indicator" in str(element).lower():
            # Continue to the Treeview class binding, which opens/closes only.
            return None

        path = self._tree_rows.get(item, "")
        if not path or self.model is None:
            return None
        self.folder_tree.selection_set(item)
        self.folder_tree.focus(item)
        self._selected_path = path
        self.model.toggle(path)
        self.refresh_all()
        self.show_inspector(path)
        # Do not let the Treeview class binding reinterpret this as expansion.
        return "break"

    def _on_folder_double_click(self, _event=None) -> str:
        """A double-click is one toggle, not two toggles plus expansion."""
        return "break"

    def _on_space(self, _event=None) -> str:
        selected = self.folder_tree.selection()
        if selected and self.model is not None:
            path = self._tree_rows.get(selected[0], "")
            if path:
                self.model.toggle(path)
                self.refresh_all()
        return "break"

    def _on_decision_select(self, _event=None) -> None:
        selected = self.decision_tree.selection()
        if not selected:
            return
        path = str(selected[0])
        if path.startswith(("lazy::", "more::", "empty::")):
            return
        if path.startswith("dir::"):
            path = path[5:]
        self._selected_path = path
        self.show_inspector(path)

    def _on_decision_space(self, _event=None) -> str:
        selected = self.decision_tree.selection()
        if selected and self.model is not None:
            path = str(selected[0])
            if path.startswith(("lazy::", "more::", "empty::")):
                return "break"
            path = path[5:] if path.startswith("dir::") else path
            try:
                self.model.toggle(path)
            except KeyError:
                return "break"
            self.refresh_all()
        return "break"

    def _on_decision_open(self, _event=None) -> None:
        item = str(self.decision_tree.focus())
        if not item.startswith("dir::"):
            return
        path = item[5:]
        self._decision_expanded.add(path)
        if self._decision_lazy:
            self._populate_decision_branch(path)

    def _on_decision_close(self, _event=None) -> None:
        item = str(self.decision_tree.focus())
        if item.startswith("dir::"):
            self._decision_expanded.discard(item[5:])

    def show_inspector(self, path: str) -> None:
        if self.model is None or not path:
            return
        view = self.model.inspector(path)
        if view is None:
            self.inspector_path.configure(text=path)
            self.inspector_text.configure(
                text="Not in this plan. If it sits under a pruned directory, "
                     "use Rescan with that root included.")
            self.override_btn.configure(state="disabled")
            return
        self.inspector_path.configure(text=view.path)
        self.inspector_text.configure(text=view.headline)
        self.override_btn.configure(
            text=view.override_action,
            state="normal" if view.can_override else "disabled")

    # -- commands --------------------------------------------------------

    def _preference(self, key: str, default: bool = True) -> bool:
        if self.user_state is None:
            return default
        return bool(self.user_state.get(key, default))

    def _invalidate_check(self, *, stale: bool = False) -> None:
        had_result = self.check_result is not None
        self.check_result = None
        self.check_status_var.set(
            "Integrity: stale — check again"
            if stale and had_result
            else "Integrity: not checked"
        )

    def _check_is_current(self) -> bool:
        return bool(
            self.model is not None
            and self.check_result is not None
            and self.check_result.generation == self.model.result.plan.generation
        )

    def _publish_check_result(
        self, result: CheckResult, *, show_results: bool
    ) -> bool:
        self.check_result = result
        if result.status == "blocked":
            self.check_status_var.set(
                f"Integrity: BLOCKED ({len(result.blockers)})")
        elif result.status == "warnings":
            self.check_status_var.set(
                f"Integrity: passed with {len(result.warnings)} warning(s)")
        else:
            self.check_status_var.set(
                f"Integrity: passed ({result.file_count:,} files)")
        if show_results:
            show_check_results(
                self.winfo_toplevel(),
                result,
                on_exclude=self._exclude_check_paths,
            )
        return result.valid

    def _exclude_check_paths(self, paths: List[str]) -> None:
        """Apply only remediations that map to real paths in this plan."""
        if self.model is None:
            return
        changed = False
        for path in paths:
            try:
                if self.model.node_for(path) is not None:
                    self.model.set_file(path, False)
                    changed = True
            except (BundleFileToolError, KeyError):
                continue
        if changed:
            self.refresh_all()
            self.status_var.set(
                "Blocking paths excluded for this session; check the revised selection again")

    def check_selection(self, *, show_results: bool = True) -> bool:
        """Read and check the selected content without creating an artifact."""
        if self.model is None:
            return False
        plan = self.model.result

        def work(progress=None, cancel=None):
            return self.service.check_selection(
                plan, progress=progress, cancel=cancel)

        try:
            if self._progress_enabled(plan.file_count):
                result = run_with_progress(
                    self, "Checking selection", work, allow_cancel=True)
            else:
                result = work()
        except OperationCancelled:
            self.status_var.set("Selection check cancelled")
            return False
        except BundleFileToolError as error:
            messagebox.showerror(
                "Cannot check selection",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return False
        return self._publish_check_result(result, show_results=show_results)

    def _ensure_selection_checked(self) -> bool:
        if self._check_is_current():
            if self.check_result is not None and not self.check_result.valid:
                self._publish_check_result(self.check_result, show_results=True)
            return bool(self.check_result and self.check_result.valid)
        valid = self.check_selection(show_results=False)
        if self.check_result is not None and (
            not valid or self.check_result.warnings
        ):
            self._publish_check_result(self.check_result, show_results=True)
        return valid

    def override_selected(self) -> None:
        if self.model is None or not self._selected_path:
            return
        view = self.model.inspector(self._selected_path)
        if view is None or not view.can_override:
            return

        # Both questions are the model's to answer. Asking the inspector's
        # state string was wrong twice over: a folder reports a tri-state
        # rather than a decision state, and `confirm_required` describes a
        # decision an override has *already* won, so it was always False here.
        try:
            include = self.model.desired_state(self._selected_path)
        except KeyError:
            return
        if self.model.needs_confirmation(self._selected_path, include) \
                and not messagebox.askyesno(
                    "Confirm override",
                    f"{self._selected_path} is excluded by a default safety "
                    f"rule.\n\nInclude it in this session anyway?",
                    parent=self.decision_tree.winfo_toplevel(),
                ):
            return

        node = self.model.node_for(self._selected_path)
        if node is not None and node.is_dir:
            self.model.set_folder(self._selected_path, include)
        else:
            self.model.set_file(self._selected_path, include)
        self.refresh_all()
        self.show_inspector(self._selected_path)

    def apply_bulk(self, include: bool) -> None:
        if self.model is None:
            return
        action = "Include" if include else "Exclude"
        scope = self.model.bulk_scope(action, view=self.view_var.get(),
                                      search=self.search_var.get())
        if scope.count == 0:
            return
        if not messagebox.askyesno(
            "Confirm bulk action",
            scope.describe() + "?",
            parent=self.decision_tree.winfo_toplevel(),
        ):
            return
        self.model.apply_bulk(include, view=self.view_var.get(),
                              search=self.search_var.get())
        self.refresh_all()

    def clear_overrides(self) -> None:
        if self.model is None:
            return
        self.model.clear_all_overrides()
        self.refresh_all()

    def undo(self) -> None:
        if self.model is not None and self.model.can_undo:
            self.model.undo()
            self.refresh_all()

    def redo(self) -> None:
        if self.model is not None and self.model.can_redo:
            self.model.redo()
            self.refresh_all()

    def edit_rules(self) -> None:
        from ui.rule_editor import RuleEditorDialog

        if self.model is None:
            return
        RuleEditorDialog(self.rules_tree, self.model, on_apply=self._on_rules_applied)

    def _on_rules_applied(self) -> None:
        self.refresh_all()

    def review_report(self) -> None:
        if self.model is None:
            return
        from ui.rule_editor import ReviewReportDialog

        ReviewReportDialog(self, self.model)

    def confirm_review(self) -> bool:
        """The §7.2 final review. True to proceed.

        Three outcomes, not two: blocked paths can be explicitly set aside so
        the warning is settled rather than repeated on every Create Bundle.
        """
        from ui.rule_editor import ReviewSelectionDialog

        reasons = self.model.needs_review()
        if not reasons:
            return True

        dialog = ReviewSelectionDialog(self, reasons,
                                       self.model.unacknowledged_blocked())
        self.wait_window(dialog)

        if dialog.choice == "cancel":
            return False
        if dialog.choice == "exclude_blocked":
            self.model.acknowledge_blocked()
            self.refresh_all()
        return True

    def confirm_capacity(self, *, clipboard: bool = False) -> bool:
        """Require an explicit decision before expensive or unsafe output."""
        if self.model is None:
            return False
        estimate = self.model.result.estimate()
        if clipboard and estimate.output_bytes > 16 * 1024 * 1024:
            messagebox.showwarning(
                "Bundle too large for clipboard",
                "This bundle may exceed 16 MiB. Save it as an artifact instead "
                "of placing it on the system clipboard.",
                parent=self.winfo_toplevel(),
            )
            return False
        if not estimate.requires_confirmation:
            return True
        return bool(messagebox.askyesno(
            "Large bundle plan",
            f"This {estimate.level} plan contains {estimate.file_count:,} files "
            f"and {estimate.raw_bytes / (1024 * 1024):,.1f} MiB of source data.\n\n"
            f"Estimated output: up to {estimate.output_bytes / (1024 * 1024):,.1f} MiB\n"
            f"Temporary space: {estimate.temporary_bytes / (1024 * 1024):,.1f} MiB\n\n"
            "Continue?",
            parent=self.winfo_toplevel(),
        ))

    def create_bundle(self) -> None:
        """Create Bundle, with the final review §7.2 requires."""
        if self.model is None:
            return
        if not self.confirm_review():
            return
        if not self.confirm_capacity():
            return
        if (
            self._preference("check_selection_before_create")
            and not self._ensure_selection_checked()
        ):
            self.status_var.set(
                "Bundle creation blocked by the selection integrity check")
            return

        target = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Create bundle", defaultextension=".txt",
            filetypes=[("Bundle files", "*.txt"), ("All files", "*.*")],
            initialdir=self._get_last_dir(
                "last_bundle_save_dir", "global_settings.output_dir"),
            initialfile=self._suggested_bundle_name())
        if not target:
            return
        self._remember_last_dir(
            "last_bundle_save_dir", str(Path(target).parent))
        plan = self.model.result

        def work(progress=None, cancel=None):
            return self.service.create_bundle(
                sources=plan.sources, base_path=plan.base_path,
                output_path=Path(target), plan=plan,
                progress=progress, cancel=cancel)

        try:
            if self._progress_enabled(plan.file_count):
                outcome = run_with_progress(self, "Creating bundle", work,
                                            allow_cancel=True)
            else:
                outcome = work()
        except OperationCancelled as cancelled:
            # A cancelled run is its own outcome, not a failure - Build 112.
            written = len(getattr(cancelled, "partial_paths", ()) or ())
            self.status_var.set(
                f"Bundle cancelled after {cancelled.completed} of "
                f"{cancelled.total or plan.file_count} files"
                + (f"; {written} file(s) left in place" if written else ""))
            return
        except BundleFileToolError as error:
            messagebox.showerror(
                "Bundle creation blocked",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        created = (
            f"Bundle created: {outcome.output_path} "
            f"({outcome.file_count} files, {human_bytes(outcome.byte_count)})")
        if self._preference("verify_output_after_create") and outcome.output_path:
            def verify(progress=None, cancel=None):
                return self.service.check_bundle(
                    Path(outcome.output_path), subject=SUBJECT_OUTPUT,
                    progress=progress, cancel=cancel)

            try:
                if self._progress_enabled(outcome.file_count):
                    verified = run_with_progress(
                        self, "Verifying created bundle", verify,
                        allow_cancel=True)
                else:
                    verified = verify()
            except OperationCancelled:
                self.status_var.set(created + "; output verification cancelled")
                return
            except BundleFileToolError as error:
                messagebox.showerror(
                    "Bundle created; verification failed",
                    f"{created}\n\n{error}",
                    parent=self.winfo_toplevel(),
                )
                return
            if not verified.valid or verified.warnings:
                show_check_results(self.winfo_toplevel(), verified)
            if not verified.valid:
                self.status_var.set(created + "; output integrity check BLOCKED")
                return
            created += "; output verified"
        self.status_var.set(created)

    def copy_to_clipboard(self) -> None:
        """Execute the reviewed plan and copy the reconciled artifact.

        The main-window menu exposes this capability in workspace mode.  It
        must execute through the service just like file publication; copying a
        stale preview would reintroduce a second, unchecked artifact path.
        """
        if self.model is None:
            return
        if not self.confirm_review():
            return
        if not self.confirm_capacity(clipboard=True):
            return
        if (
            self._preference("check_selection_before_create")
            and not self._ensure_selection_checked()
        ):
            self.status_var.set(
                "Clipboard bundle blocked by the selection integrity check")
            return
        plan = self.model.result

        def work(progress=None, cancel=None):
            return self.service.create_bundle(
                sources=plan.sources,
                base_path=plan.base_path,
                plan=plan,
                progress=progress,
                cancel=cancel,
            )

        try:
            if self._progress_enabled(plan.file_count):
                outcome = run_with_progress(
                    self, "Preparing clipboard bundle", work,
                    allow_cancel=True)
            else:
                outcome = work()
        except OperationCancelled as cancelled:
            self.status_var.set(
                f"Clipboard bundle cancelled after {cancelled.completed} of "
                f"{cancelled.total or plan.file_count} files")
            return
        except BundleFileToolError as error:
            messagebox.showerror(
                "Copy failed",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return

        self.clipboard_clear()
        self.clipboard_append(outcome.text)
        self.update()
        self.status_var.set(
            f"Copied reconciled bundle to clipboard "
            f"({outcome.file_count} files, {human_bytes(len(outcome.text))})")

    # -- state -----------------------------------------------------------

    def _update_enabled(self) -> None:
        ready = self.model is not None
        state = "normal" if ready else "disabled"
        for widget in (self.create_btn, self.check_btn, self.clear_btn,
                       self.edit_rules_btn, self.report_btn):
            widget.configure(state=state)
        visible_state = "normal" if ready and self._visible_count else "disabled"
        self.include_visible_btn.configure(state=visible_state)
        self.exclude_visible_btn.configure(state=visible_state)
        self.expand_btn.configure(state=visible_state)
        self.collapse_btn.configure(state=visible_state)
        self.clear_btn.configure(
            state=("normal" if ready and getattr(self.model, "overrides", ())
                   else "disabled"))
