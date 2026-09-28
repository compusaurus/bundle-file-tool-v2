# BFT_B104_USER_STATE_WIRING - remembered folders persist to UserStateStore (R-BFT-01)

"""
Bundle Mode Frame for Bundle File Tool v2.1.

This frame implements the complete Bundle mode interface with source file
selection tree, live preview, and bundle creation controls.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Set
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import BundleManifest
from core.parser import ProfileRegistry
from core.service import BundleToolService, PlanResult
from core.user_state import UserStateStore
from ui.tk_progress import run_with_progress


class BundleFrame(ttk.Frame):
    """
    Bundle mode interface frame.

    Provides UI for:
    - Selecting source directory/files
    - Filtering files with tree selection
    - Choosing bundle profile
    - Live preview of bundle output
    - Creating bundle file or copying to clipboard
    """

    def __init__(self, parent, config_manager=None, user_state=None):
        """
        Initialize Bundle frame.

        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for settings
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.user_state = user_state
        self.source_path: Optional[Path] = None
        self.current_manifest: Optional[BundleManifest] = None
        self.source_plan: Optional[PlanResult] = None
        self.current_plan: Optional[PlanResult] = None
        self.current_bundle_text: str = ""
        self.service = BundleToolService(config=config_manager)
        self.registry = ProfileRegistry()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Content area expands

        # Create UI sections
        self._create_action_bar()
        self._create_split_pane()
        self._create_options_bar()

        # Initialize state
        self._update_ui_state()

    def _create_action_bar(self):
        """Create top action button bar."""
        action_frame = ttk.Frame(self)
        action_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Select Source button
        self.select_btn = ttk.Button(
            action_frame,
            text="📁 Select Source...",
            command=self.select_source,
            width=20
        )
        self.select_btn.pack(side="left", padx=(0, 5))

        # Create Bundle button
        self.create_btn = ttk.Button(
            action_frame,
            text="📦 Create Bundle...",
            command=self.create_bundle,
            width=20,
            state="disabled"
        )
        self.create_btn.pack(side="left", padx=(0, 5))

        # Copy to Clipboard button
        self.copy_btn = ttk.Button(
            action_frame,
            text="📋 Copy to Clipboard",
            command=self.copy_to_clipboard,
            width=20,
            state="disabled"
        )
        self.copy_btn.pack(side="left", padx=(0, 5))

        # Separator
        ttk.Separator(action_frame, orient="vertical").pack(
            side="left", fill="y", padx=10
        )

        # Status label
        self.status_label = ttk.Label(
            action_frame,
            text="No source selected",
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True)

    def _create_split_pane(self):
        """Create split pane with file tree and preview."""
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        # Left pane: Source file tree
        self._create_file_tree(paned)

        # Right pane: Bundle preview
        self._create_preview_pane(paned)

    def _create_file_tree(self, parent):
        """Create source file selection tree."""
        tree_frame = ttk.LabelFrame(parent, text="Source Files", padding=5)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Create treeview
        self.file_tree = ttk.Treeview(
            tree_frame,
            selectmode="extended",
            show="tree"
        )

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Selection controls
        btn_frame = ttk.Frame(tree_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        ttk.Button(
            btn_frame,
            text="Select All",
            command=self._select_all_files,
            width=12
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="Deselect All",
            command=self._deselect_all_files,
            width=12
        ).pack(side="left")

        ttk.Label(
            btn_frame,
            text="Tip: Check files to include in bundle",
            foreground="gray"
        ).pack(side="right")

        # Bind selection event for preview update
        self.file_tree.bind("<<TreeviewSelect>>", self._on_selection_change)

        parent.add(tree_frame, weight=1)

    def _create_preview_pane(self, parent):
        """Create live bundle preview pane."""
        preview_frame = ttk.LabelFrame(parent, text="Bundle Preview", padding=5)
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)

        # Preview text widget
        self.preview_text = tk.Text(
            preview_frame,
            wrap="none",
            background="#f5f5f5",
            font=("Consolas", 9)
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        vsb = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
            command=self.preview_text.yview
        )
        hsb = ttk.Scrollbar(
            preview_frame,
            orient="horizontal",
            command=self.preview_text.xview
        )
        self.preview_text.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Stats label
        self.stats_label = ttk.Label(
            preview_frame,
            text="Preview: 0 files, 0 bytes",
            anchor="w"
        )
        self.stats_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        parent.add(preview_frame, weight=2)

    def _create_options_bar(self):
        """Create bottom options bar."""
        options_frame = ttk.Frame(self)
        options_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

        # Profile selector
        ttk.Label(options_frame, text="Bundle Profile:").pack(side="left", padx=(0, 5))

        self.profile_var = tk.StringVar(
            master=self,
            value=self.config_manager.get("app_defaults.bundle_profile", "plain_marker")
            if self.config_manager else "plain_marker"
        )

        profile_combo = ttk.Combobox(
            options_frame,
            textvariable=self.profile_var,
            values=self.registry.list_profiles(),
            state="readonly",
            width=15
        )
        profile_combo.pack(side="left", padx=(0, 15))
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        # Auto-preview checkbox
        self.auto_preview_var = tk.BooleanVar(master=self, value=True)
        ttk.Checkbutton(
            options_frame,
            text="Auto-update preview",
            variable=self.auto_preview_var
        ).pack(side="left", padx=(0, 15))

        # Manual refresh button
        ttk.Button(
            options_frame,
            text="🔄 Refresh Preview",
            command=self._update_preview,
            width=15
        ).pack(side="left")

    def _get_last_dir(self, key: str, fallback_key: str) -> str:
        """
        Return the remembered directory for a dialog, or a sensible fallback.

        Args:
            key: Per-action config key (e.g. 'global_settings.last_source_dir')
            fallback_key: Legacy/global key used when the per-action key is
                unset (e.g. 'global_settings.input_dir')

        Returns:
            Directory path string, or "" if nothing usable is stored.
        """
        remembered = self.user_state.get(key, "") if self.user_state else ""
        fallback = self.config_manager.get(fallback_key, "") if self.config_manager else ""
        directory = remembered or fallback
        # Stale paths (deleted/renamed folders) fall back to Tk default.
        if directory and not Path(directory).is_dir():
            return ""
        return directory

    def _remember_last_dir(self, key: str, directory: str):
        """
        Persist a successfully used dialog directory to config.

        Persistence failures are non-critical and must never interrupt the
        user's workflow, mirroring ConfigManager backup semantics.

        Args:
            key: Per-action config key to store under
            directory: Directory path to remember
        """
        if not self.user_state or not directory:
            return
        try:
            self.user_state.set_and_save(key, str(directory))
        except Exception:
            # Non-critical: remembering the folder is a convenience only.
            pass

    def _progress_enabled(self, file_count=None) -> bool:
        """Whether an operation of this size gets a progress dialog.

        BFT_B108_PROGRESS_THRESHOLD. A modal dialog for eleven files is worse
        than no dialog, so small work stays inline and instant. Discovery passes
        None because it cannot know its size until it has finished - which is
        the whole reason it reports indeterminate progress.
        """
        if not self.config_manager:
            return True
        if not self.config_manager.get("ui.progress.enabled", True):
            return False
        if file_count is None:
            return True
        return file_count >= self.config_manager.get("ui.progress.min_files", 200)

    def select_source(self):
        """Open directory browser to select source."""
        directory = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Select Source Directory",
            initialdir=self._get_last_dir(
                "last_source_dir",
                "global_settings.input_dir"
            )
        )

        if not directory:
            return

        # CP-2026-002: remember this folder for the next Select Source only.
        self._remember_last_dir("last_source_dir", directory)

        try:
            self.source_path = Path(directory)

            # P0: classic mode is a presentation over the same plan as the
            # Selection Workspace.  It no longer owns a second discovery path.
            if self._progress_enabled():
                self.source_plan = run_with_progress(
                    self,
                    f"Scanning {self.source_path.name}",
                    lambda progress=None, cancel=None: self.service.plan_bundle(
                        [self.source_path], base_path=self.source_path,
                        progress=progress, cancel=cancel),
                )
            else:
                self.source_plan = self.service.plan_bundle(
                    [self.source_path], base_path=self.source_path)

            self.current_plan = self.source_plan
            files = self.source_plan.absolute_paths()

            # Populate tree
            self._populate_file_tree(files)

            # Update status
            self.status_label.config(
                text=f"Source: {len(files)} files from {directory}"
            )

            # Update preview
            self._update_preview()

            # Enable controls
            self._update_ui_state()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to scan directory:\n\n{str(e)}",
                parent=self.winfo_toplevel(),
            )

    def create_bundle(self):
        """Create bundle file from selected files."""
        if not self.source_path or self.current_plan is None:
            return
        if not self._confirm_capacity():
            return

        # Get save location
        # CP-2026-002: open in the last bundle-save folder, NOT wherever the
        # process-global Tk dialog memory happens to point (previously this
        # inherited the Select Source folder because no initialdir was given).
        file_path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Save Bundle As",
            defaultextension=".txt",
            filetypes=[
                ("Bundle files", "*.txt"),
                ("All files", "*.*")
            ],
            initialdir=self._get_last_dir(
                "last_bundle_save_dir",
                "global_settings.output_dir"
            ),
            initialfile=f"{self.source_path.name}_bundle.txt"
        )

        if not file_path:
            return

        # CP-2026-002: remember this folder for the next Create Bundle only.
        self._remember_last_dir(
            "last_bundle_save_dir",
            str(Path(file_path).parent)
        )

        try:
            if self.current_plan is None:
                return
            outcome = self.service.create_bundle(
                sources=self.current_plan.sources,
                base_path=self.current_plan.base_path,
                profile=self.profile_var.get(),
                output_path=Path(file_path),
                plan=self.current_plan,
            )
            self.current_manifest = outcome.manifest
            self.current_bundle_text = outcome.text

            messagebox.showinfo(
                "Bundle Created",
                f"Bundle file created successfully:\n\n{file_path}\n\n"
                f"Files: {outcome.file_count}\n"
                f"Profile: {self.profile_var.get()}",
                parent=self.winfo_toplevel(),
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to create bundle:\n\n{str(e)}",
                parent=self.winfo_toplevel(),
            )

    def copy_to_clipboard(self):
        """Copy bundle preview to clipboard."""
        try:
            if self.current_plan is None:
                return
            if not self._confirm_capacity(clipboard=True):
                return
            outcome = self.service.create_bundle(
                sources=self.current_plan.sources,
                base_path=self.current_plan.base_path,
                profile=self.profile_var.get(),
                plan=self.current_plan,
            )
            preview_content = outcome.text

            if not preview_content.strip():
                messagebox.showwarning(
                    "Empty Preview",
                    "No content to copy.",
                    parent=self.winfo_toplevel(),
                )
                return

            self.clipboard_clear()
            self.clipboard_append(preview_content)
            self.update()

            messagebox.showinfo(
                "Copied",
                f"Bundle copied to clipboard!\n\n"
                f"Files: {outcome.file_count}\n"
                f"Size: {len(preview_content):,} characters",
                parent=self.winfo_toplevel(),
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to copy to clipboard:\n\n{str(e)}",
                parent=self.winfo_toplevel(),
            )

    def _populate_file_tree(self, files: List[Path]):
        """Populate file tree with discovered files."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        if not files or not self.source_path:
            return

        # Add files as tree items
        for file_path in sorted(files):
            try:
                rel_path = file_path.relative_to(self.source_path)
                display_path = str(rel_path).replace('\\', '/')

                self.file_tree.insert(
                    "",
                    "end",
                    text=f"☑ {display_path}",
                    values=(str(file_path),),
                    tags=("checked",)
                )
            except ValueError:
                # Skip files outside source path
                continue

    def _get_selected_files(self) -> List[Path]:
        """Get list of currently selected (checked) files."""
        selected = []

        for item in self.file_tree.get_children():
            item_text = self.file_tree.item(item, "text")
            if item_text.startswith("☑"):
                values = self.file_tree.item(item, "values")
                if values:
                    selected.append(Path(values[0]))

        return selected

    def _select_all_files(self):
        """Select (check) all files in tree."""
        for item in self.file_tree.get_children():
            item_text = self.file_tree.item(item, "text")
            if item_text.startswith("☐"):
                new_text = "☑" + item_text[1:]
                self.file_tree.item(item, text=new_text)

        self._on_selection_change()

    def _deselect_all_files(self):
        """Deselect (uncheck) all files in tree."""
        for item in self.file_tree.get_children():
            item_text = self.file_tree.item(item, "text")
            if item_text.startswith("☑"):
                new_text = "☐" + item_text[1:]
                self.file_tree.item(item, text=new_text)

        self._on_selection_change()

    def _on_selection_change(self, event=None):
        """Handle file selection changes."""
        # Toggle check state on double-click
        if event:
            selection = self.file_tree.selection()
            for item in selection:
                item_text = self.file_tree.item(item, "text")
                if item_text.startswith("☑"):
                    new_text = "☐" + item_text[1:]
                else:
                    new_text = "☑" + item_text[1:]
                self.file_tree.item(item, text=new_text)

        # Update preview if auto-preview is enabled
        if self.auto_preview_var.get():
            self._update_preview()

    def _update_preview(self):
        """Update bundle preview with current selection."""
        if not self.source_path:
            return

        try:
            # Get selected files
            selected_files = self._get_selected_files()

            if not selected_files:
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", "No files selected.\n\nSelect files from the tree to preview.")
                self.stats_label.config(text="Preview: 0 files, 0 bytes")
                self.current_manifest = None
                self._update_ui_state()
                return

            if self.source_plan is None:
                return
            selected_patterns = [
                str(path.relative_to(self.source_path)).replace("\\", "/")
                for path in selected_files
            ]
            self.current_plan = self.service.replan(
                self.source_plan, include=selected_patterns)

            estimate = self.current_plan.estimate()
            if estimate.output_bytes > 16 * 1024 * 1024:
                self.current_manifest = None
                self.current_bundle_text = ""
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert(
                    "1.0",
                    "Preview suppressed because the planned bundle may exceed "
                    "16 MiB. Use Create Bundle to stream it safely to a file.")
                self.stats_label.config(
                    text=f"Plan: {estimate.file_count:,} files, up to "
                         f"{self._format_size(estimate.output_bytes)}")
                self._update_ui_state()
                return

            # Execute the canonical plan for the content preview. Creation will
            # execute and reconcile the same plan again before publication.
            if self._progress_enabled(len(selected_files)):
                outcome = run_with_progress(
                    self,
                    "Reading files",
                    lambda progress=None, cancel=None: self.service.create_bundle(
                        sources=self.current_plan.sources,
                        base_path=self.current_plan.base_path,
                        profile=self.profile_var.get(), plan=self.current_plan,
                        progress=progress, cancel=cancel),
                )
            else:
                outcome = self.service.create_bundle(
                    sources=self.current_plan.sources,
                    base_path=self.current_plan.base_path,
                    profile=self.profile_var.get(), plan=self.current_plan,
                )
            self.current_manifest = outcome.manifest
            self.current_bundle_text = outcome.text
            bundle_text = outcome.text

            # Build 110 (UX-BFT-001): oversized files are skipped, not fatal.
            # Lead with the notice so it is visible above the bundle text, and
            # say what to do about it - the old error named the file but left
            # the user to work out the remedy.
            skipped = getattr(self.current_manifest, "skipped_entries", []) or []
            banner = self._format_skipped_banner(skipped)

            # Update preview
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", banner + bundle_text)

            # Update stats
            total_size = self.current_manifest.get_total_size_bytes()
            size_str = self._format_size(total_size)

            stats = (f"Preview: {len(self.current_manifest.entries)} files, {size_str} "
                     f"({len(bundle_text):,} chars)")
            if skipped:
                stats += f" - {len(skipped)} skipped"
            self.stats_label.config(text=stats)

            # Enable action buttons
            self._update_ui_state()

        except Exception as e:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"Error generating preview:\n\n{str(e)}")
            self.stats_label.config(text="Preview error")
            self.current_manifest = None
            self._update_ui_state()

    def _format_skipped_banner(self, skipped: list) -> str:
        """Render the non-blocking notice for files left out of the payload.

        Build 110 (UX-BFT-001). Returns an empty string when nothing was
        skipped, so the preview is byte-identical to previous builds in the
        ordinary case.
        """
        if not skipped:
            return ""

        oversize = [s for s in skipped if s.get("reason") == "oversize"]
        if not oversize:
            return ""

        limit = oversize[0].get("limit_mb", 0.0)
        lines = [
            f"NOTE: Skipped {len(oversize)} oversized "
            f"file{'s' if len(oversize) != 1 else ''} (> {limit:.2f} MB):"
        ]
        for item in oversize[:5]:
            lines.append(f"  - {item.get('path')} ({item.get('size_mb'):.2f} MB)")
        if len(oversize) > 5:
            lines.append(f"  ... and {len(oversize) - 5} more")
        lines.append("Raise the size limit or deselect these files to clear this notice.")
        lines.append("The bundle below contains every other selected file.")
        return "\n".join(lines) + "\n\n" + ("-" * 72) + "\n\n"

    def _format_size(self, size_bytes: int) -> str:
        """Format byte size as human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _confirm_capacity(self, *, clipboard: bool = False) -> bool:
        if self.current_plan is None:
            return False
        estimate = self.current_plan.estimate()
        if clipboard and estimate.output_bytes > 16 * 1024 * 1024:
            messagebox.showwarning(
                "Bundle too large for clipboard",
                "This bundle may exceed 16 MiB. Save it as an artifact instead.",
                parent=self.winfo_toplevel())
            return False
        if not estimate.requires_confirmation:
            return True
        return bool(messagebox.askyesno(
            "Large bundle plan",
            f"This {estimate.level} plan contains {estimate.file_count:,} files "
            f"and {estimate.raw_bytes / (1024 * 1024):,.1f} MiB of source data.\n\n"
            "Continue?",
            parent=self.winfo_toplevel()))

    def _update_ui_state(self):
        """Update UI element states based on current state."""
        has_plan = self.current_plan is not None
        has_manifest = self.current_manifest is not None

        # Enable/disable action buttons
        self.create_btn.config(
            state="normal" if has_plan else "disabled"
        )
        self.copy_btn.config(
            state="normal" if has_manifest else "disabled"
        )
