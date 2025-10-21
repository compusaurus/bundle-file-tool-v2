# ============================================================================
# SOURCEFILE: bundle_frame.py
# RELPATH: bundle_file_tool_v2/src/ui/bundle_frame.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# STATUS: In Development
# DESCRIPTION: Bundle mode UI frame (split pane: file tree + preview)
# ============================================================================

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

from core.writer import BundleCreator
from core.models import BundleManifest
from core.parser import ProfileRegistry


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
    
    def __init__(self, parent, config_manager=None):
        """
        Initialize Bundle frame.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for settings
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.source_path: Optional[Path] = None
        self.current_manifest: Optional[BundleManifest] = None
        self.creator = BundleCreator()
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
        self.auto_preview_var = tk.BooleanVar(value=True)
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
    
    def select_source(self):
        """Open directory browser to select source."""
        directory = filedialog.askdirectory(
            title="Select Source Directory",
            initialdir=self.config_manager.get("global_settings.input_dir", "")
            if self.config_manager else ""
        )
        
        if not directory:
            return
        
        try:
            self.source_path = Path(directory)
            
            # Discover files
            files = self.creator.discover_files(
                self.source_path,
                self.source_path
            )
            
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
            messagebox.showerror("Error", f"Failed to scan directory:\n\n{str(e)}")
    
    def create_bundle(self):
        """Create bundle file from selected files."""
        if not self.source_path or not self.current_manifest:
            return
        
        # Get save location
        file_path = filedialog.asksaveasfilename(
            title="Save Bundle As",
            defaultextension=".txt",
            filetypes=[
                ("Bundle files", "*.txt"),
                ("All files", "*.*")
            ],
            initialfile=f"{self.source_path.name}_bundle.txt"
        )
        
        if not file_path:
            return
        
        try:
            # Get profile
            profile = self.registry.get(self.profile_var.get())
            
            # Format manifest using profile
            bundle_text = profile.format_manifest(self.current_manifest)
            
            # Write to file
            Path(file_path).write_text(bundle_text, encoding='utf-8')
            
            messagebox.showinfo(
                "Bundle Created",
                f"Bundle file created successfully:\n\n{file_path}\n\n"
                f"Files: {self.current_manifest.get_file_count()}\n"
                f"Profile: {self.profile_var.get()}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create bundle:\n\n{str(e)}")
    
    def copy_to_clipboard(self):
        """Copy bundle preview to clipboard."""
        try:
            preview_content = self.preview_text.get("1.0", "end-1c")
            
            if not preview_content.strip():
                messagebox.showwarning("Empty Preview", "No content to copy.")
                return
            
            self.clipboard_clear()
            self.clipboard_append(preview_content)
            self.update()
            
            messagebox.showinfo(
                "Copied",
                f"Bundle copied to clipboard!\n\n"
                f"Files: {self.current_manifest.get_file_count()}\n"
                f"Size: {len(preview_content):,} characters"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard:\n\n{str(e)}")
    
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
            
            # Create manifest from selected files
            self.current_manifest = self.creator.create_manifest(
                selected_files,
                self.source_path,
                self.profile_var.get()
            )
            
            # Get profile and format
            profile = self.registry.get(self.profile_var.get())
            bundle_text = profile.format_manifest(self.current_manifest)
            
            # Update preview
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", bundle_text)
            
            # Update stats
            total_size = self.current_manifest.get_total_size_bytes()
            size_str = self._format_size(total_size)
            
            self.stats_label.config(
                text=f"Preview: {len(selected_files)} files, {size_str} "
                     f"({len(bundle_text):,} chars)"
            )
            
            # Enable action buttons
            self._update_ui_state()
            
        except Exception as e:
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"Error generating preview:\n\n{str(e)}")
            self.stats_label.config(text="Preview error")
            self.current_manifest = None
            self._update_ui_state()
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size as human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _update_ui_state(self):
        """Update UI element states based on current state."""
        has_manifest = self.current_manifest is not None
        
        # Enable/disable action buttons
        self.create_btn.config(
            state="normal" if has_manifest else "disabled"
        )
        self.copy_btn.config(
            state="normal" if has_manifest else "disabled"
        )


# ============================================================================
# LIFECYCLE STATUS: Proposed
# PHASE: Phase 5 GUI Implementation
# DEPENDENCIES: core/writer.py, core/models.py, core/parser.py (ProfileRegistry)
# TESTS: Manual UI testing, integration with ModeManager
# NEXT STEPS: Integration with main_window.py, clipboard functionality testing
# ============================================================================