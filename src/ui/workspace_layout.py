"""Keep live workspace views while switching between tabs, tiles and windows."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from railgun_display import (
    DisplayRect, DisplayTopology, create_display_driver, display_for_window, other_display,
)
from ui.window_icon import apply_window_icon
from ui.window_placement import _move_tk_window, place_toplevel_on_parent_monitor


VIEWS = (("selections", "Selections", True), ("rules", "Rules", False),
         ("result_set", "Result set", False), ("guidance", "Operational Guidance", True))
LAYOUTS = ("Tabs", "Side by side", "Stacked", "Grid")


class WorkspacePage(tk.Frame, tk.Wm):
    """Tk frames can become managed windows without rebuilding their children."""


def tile_shape(count: int, layout: str) -> tuple[int, int]:
    if layout == "Stacked":
        return max(1, count), 1
    if layout == "Grid" and count == 4:
        return 2, 2
    return 1, max(1, count)


class WorkspaceLayout(ttk.Frame):
    def __init__(self, parent, *, user_state=None, report=lambda message: None, driver=None):
        super().__init__(parent)
        self.user_state, self.report = user_state, report
        self.driver = driver if driver is not None else create_display_driver()
        self.topology = DisplayTopology(())
        self.detached: set[str] = set()
        self.pages, self.content, self.visible, self.checks = {}, {}, {}, {}
        self.window_buttons, self.display_buttons = {}, {}
        self._active = True
        self._poll_id = None
        self._closed = False
        saved = user_state.get("workspace_layout", "Tabs") if user_state else "Tabs"
        self.layout_var = tk.StringVar(self, saved if saved in LAYOUTS else "Tabs")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        choices = ttk.Frame(self)
        choices.grid(row=0, column=0, sticky="ew", pady=(2, 4))
        ttk.Label(choices, text="Show views:").pack(side="left", padx=(0, 6))
        for key, label, default in VIEWS:
            saved = user_state.get("workspace_show_" + key, default) if user_state else default
            self.visible[key] = tk.BooleanVar(self, saved if isinstance(saved, bool) else default)
            button = ttk.Checkbutton(choices, text=label, variable=self.visible[key],
                                    command=lambda key=key: self.toggle_view(key))
            button.pack(side="left", padx=(0, 8))
            self.checks[key] = button
        ttk.Button(choices, text="Show all", command=self.show_all).pack(side="left")

        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(actions, text="Layout").pack(side="left", padx=(0, 6))
        self.layout_box = ttk.Combobox(actions, textvariable=self.layout_var,
                                       values=LAYOUTS, state="readonly", width=13)
        self.layout_box.pack(side="left")
        self.layout_box.bind("<<ComboboxSelected>>", lambda event: self.change_layout())
        ttk.Button(actions, text="Return all to workspace", command=self.dock_all).pack(side="left", padx=8)
        self.move_workspace_button = ttk.Button(actions, text="Move workspace to other display",
                                                command=self.move_workspace)
        self.display_label = ttk.Label(actions, text="")
        self.display_label.pack(side="right")

        self.deck = ttk.Frame(self)
        self.deck.grid(row=2, column=0, sticky="nsew")
        self.deck.grid_rowconfigure(0, weight=1)
        self.deck.grid_columnconfigure(0, weight=1)
        self.notebook = ttk.Notebook(self.deck)
        self.notebook.enable_traversal()
        # Detached-capable pages are siblings of the notebook. Tk's built-in
        # Ctrl+Tab handler only recognizes notebook descendants, so route keys
        # from these pages explicitly while preserving other notebook bindings.
        self._top = self.winfo_toplevel()
        self._traversal_bindings = []
        for sequence, direction in (("<Control-Tab>", 1), ("<Control-Shift-Tab>", -1),
                                    ("<Control-ISO_Left_Tab>", -1)):
            command = self._top.bind(sequence, lambda event, step=direction:
                                     self._cycle_tab(event, step), add="+")
            self._traversal_bindings.append((sequence, command))
        self.tiles = ttk.Frame(self.deck)
        self.empty = ttk.Label(self.deck, text="Choose a view above or return a window to the workspace.",
                               anchor="center", wraplength=460)
        for key, label, _ in VIEWS:
            page = WorkspacePage(self.deck, borderwidth=0)
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(1, weight=1)
            header = ttk.Frame(page, padding=(6, 3))
            header.grid(row=0, column=0, sticky="ew")
            header.grid_columnconfigure(0, weight=1)
            ttk.Label(header, text=label).grid(row=0, column=0, sticky="w")
            window_button = ttk.Button(header, text="New window",
                                       command=lambda key=key: self.toggle_window(key))
            window_button.grid(row=0, column=1, padx=(6, 0))
            display_button = ttk.Button(header, text="Other display",
                                        command=lambda key=key: self.move_view(key))
            display_button.grid(row=0, column=2, padx=(6, 0))
            content = ttk.Frame(page, padding=6)
            content.grid(row=1, column=0, sticky="nsew")
            self.pages[key], self.content[key] = page, content
            self.window_buttons[key], self.display_buttons[key] = window_button, display_button
        self.arrange()
        self.refresh_displays()
        self._poll_id = self.after(2000, self._poll_displays)

    def _save(self, key, value):
        if self.user_state:
            self.user_state.set_and_save(key, value)

    def toggle_view(self, key):
        self._save("workspace_show_" + key, self.visible[key].get())
        self.arrange(select=key if self.visible[key].get() else None)

    def change_layout(self):
        if self.layout_var.get() not in LAYOUTS:
            self.layout_var.set("Tabs")
        self._save("workspace_layout", self.layout_var.get())
        self.arrange()

    def show_all(self):
        for key in self.visible:
            self.visible[key].set(True)
            self._save("workspace_show_" + key, True)
        self.layout_var.set("Grid")
        self.change_layout()

    def arrange(self, select=None):
        selected = self.notebook.select()
        for name in self.notebook.tabs():
            self.notebook.forget(name)
        for key, page in self.pages.items():
            if key not in self.detached:
                page.grid_forget()
            else:
                (page.deiconify if self.visible[key].get() and self._active else page.withdraw)()
        self.notebook.grid_remove()
        self.tiles.grid_remove()
        self.empty.grid_remove()
        keys = [key for key in self.pages if key not in self.detached and self.visible[key].get()]
        if self.layout_var.get() == "Tabs":
            # Keep hidden tabs registered so normal tab traversal/state works.
            self.notebook.grid(row=0, column=0, sticky="nsew")
            for key, label, _ in VIEWS:
                if key not in self.detached:
                    self.notebook.add(self.pages[key], text=label)
                    if not self.visible[key].get():
                        self.notebook.hide(self.pages[key])
            chosen = str(self.pages[select]) if select in keys else selected
            if chosen in [str(self.pages[key]) for key in keys]:
                self.notebook.select(chosen)
        elif keys:
            self.tiles.grid(row=0, column=0, sticky="nsew")
            rows, columns = tile_shape(len(keys), self.layout_var.get())
            for index in range(len(VIEWS)):
                self.tiles.grid_rowconfigure(index, weight=int(index < rows),
                                             uniform="rows" if index < rows else "", minsize=0)
                self.tiles.grid_columnconfigure(index, weight=int(index < columns),
                                                uniform="columns" if index < columns else "", minsize=0)
            for index, key in enumerate(keys):
                page = self.pages[key]
                page.grid(in_=self.tiles, row=index // columns, column=index % columns,
                          sticky="nsew", padx=2, pady=2)
                # Equal allocations must not be dominated by a table's requested width.
                page.grid_propagate(False)
        if not keys:
            self.empty.grid(row=0, column=0, sticky="nsew")

    def toggle_window(self, key):
        self.dock(key) if key in self.detached else self.detach(key)

    def _cycle_tab(self, event, direction):
        if self.layout_var.get() != "Tabs":
            return None
        pages = [page for key, page in self.pages.items()
                 if key not in self.detached and self.visible[key].get()]
        origin = str(event.widget)
        if not any(origin == str(page) or origin.startswith(str(page) + ".") for page in pages):
            return None
        selected = self.notebook.select()
        current = next(index for index, page in enumerate(pages) if str(page) == selected)
        page = pages[(current + direction) % len(pages)]
        self.notebook.select(page)
        page.focus_set()
        return "break"

    def detach(self, key):
        if key in self.detached:
            return True
        page = self.pages[key]
        size = (max(600, min(900, page.winfo_width())), max(420, min(700, page.winfo_height())))
        if str(page) in self.notebook.tabs():
            self.notebook.forget(page)
        page.grid_forget()
        try:
            self.tk.call("wm", "manage", page)
        except tk.TclError as error:
            self.arrange(select=key)
            self.report(f"This window manager could not open a separate view: {error}")
            return False
        self.detached.add(key)
        label = next(label for name, label, _ in VIEWS if name == key)
        page.title(f"Bundle File Tool — {label}")
        page.protocol("WM_DELETE_WINDOW", lambda: self.dock(key))
        page.geometry(f"{size[0]}x{size[1]}")
        page.minsize(320, 240)
        apply_window_icon(page)
        self.window_buttons[key].configure(text="Return to workspace")
        self.visible[key].set(True)
        self._save("workspace_show_" + key, True)
        page.update_idletasks()
        place_toplevel_on_parent_monitor(page, self)
        self.arrange()
        page.lift()
        return True

    def dock(self, key):
        if key not in self.detached:
            return
        page = self.pages[key]
        self.tk.call("wm", "forget", page)
        self.detached.remove(key)
        self.window_buttons[key].configure(text="New window")
        self.visible[key].set(True)
        self._save("workspace_show_" + key, True)
        self.arrange(select=key)

    def dock_all(self):
        for key in tuple(self.detached):
            self.dock(key)

    @staticmethod
    def _rect(window):
        window.update_idletasks()
        x, y = window.winfo_rootx(), window.winfo_rooty()
        return DisplayRect(x, y, x + window.winfo_width(), y + window.winfo_height())

    @staticmethod
    def _place(window, display):
        area = display.work_area
        # Leave room for the OS frame/title bar as well as taskbar/dock space.
        safe = DisplayRect(area.left + 12, area.top + 12, area.right - 12, area.bottom - 48)
        window.state("normal")
        rect = safe.centered_window(window.winfo_width(), window.winfo_height())
        window.geometry(f"{rect.width}x{rect.height}")
        window.update_idletasks()
        if not _move_tk_window(window, rect.left, rect.top):
            raise OSError("The operating system did not move the window")
        window.lift()

    def move_view(self, key):
        self.refresh_displays()
        anchor = self.pages[key] if key in self.detached else self.winfo_toplevel()
        target = other_display(self.topology, self._rect(anchor))
        if target is None:
            self.report("Connect another display to move this view automatically.")
            return False
        if not self.detach(key):
            return False
        try:
            self._place(self.pages[key], target)
        except (OSError, tk.TclError) as error:
            self.report(f"Could not move the view: {error}. It remains available as a separate window.")
            return False
        self.report("View moved to the other display. Close it or choose Return to workspace to bring it back.")
        return True

    def move_workspace(self):
        self.refresh_displays()
        window = self.winfo_toplevel()
        target = other_display(self.topology, self._rect(window))
        if target:
            try:
                self._place(window, target)
            except (OSError, tk.TclError) as error:
                self.report(f"Could not move the workspace: {error}")

    def refresh_displays(self):
        try:
            topology = self.driver.topology() if self.driver else DisplayTopology(())
        except (OSError, ValueError, AttributeError):
            return  # A transient enumeration failure must not relocate live views.
        changed = topology != self.topology
        self.topology = topology
        count = len({display.work_area for display in topology.displays if display.work_area.area})
        for button in self.display_buttons.values():
            button.grid() if count > 1 else button.grid_remove()
        if count > 1:
            self.move_workspace_button.pack(side="left")
        else:
            self.move_workspace_button.pack_forget()
        self.display_label.configure(text=f"{count} display{'s' if count != 1 else ''}" if count else "")
        if changed and count:
            for key in tuple(self.detached):
                page = self.pages[key]
                rect = self._rect(page)
                display = display_for_window(topology, rect)
                if display and rect.intersection_area(display.work_area) < rect.area * 0.75:
                    try:
                        self._place(page, display)
                        if not self.visible[key].get() or not self._active:
                            page.withdraw()
                        self.report("A display changed; a separate view was brought back onto an available display.")
                    except (OSError, tk.TclError):
                        self.dock(key)

    def _poll_displays(self):
        self._poll_id = None
        if not self._closed:
            self.refresh_displays()
            self._poll_id = self.after(2000, self._poll_displays)

    def set_active(self, active):
        self._active = active
        for key in self.detached:
            page = self.pages[key]
            (page.deiconify if active and self.visible[key].get() else page.withdraw)()

    def destroy(self):
        self._closed = True
        for sequence, command in self._traversal_bindings:
            self._top.unbind(sequence, command)
        self._traversal_bindings.clear()
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        super().destroy()
