# ============================================================================
# SOURCEFILE: unbundle_frame.py
# RELPATH: bundle_file_tool_v2/src/ui/unbundle_frame.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# STATUS: In Development
# DESCRIPTION: Un-bundle mode UI frame (mirrors v1.1.5 layout)
# ============================================================================

"""
Un-bundle Mode Frame for Bundle File Tool v2.1.

This frame implements the complete Un-bundle mode interface, mirroring the
v1.1.5 layout with file list, configuration panel, and log output.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List
import sys
import os

# Add parent directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.parser import BundleParser
from core.writer import BundleWriter
from core.models import BundleManifest


class UnbundleFrame(ttk.Frame):
    """
    Un-bundle mode interface frame.
    
    Provides UI for:
    - Opening and parsing bundle files
    - Displaying extracted file list
    - Configuring extraction options
    - Extracting files to disk
    - Viewing operation logs
    """
    
    def __init__(self, parent, config_manager=None):
        """
        Initialize Un-bundle frame.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for settings
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.current_manifest: Optional[BundleManifest] = None
        self.parser = BundleParser()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # File list expands
        
        # Create UI sections
        self._create_action_bar()
        self._create_file_list()
        self._create_config_panel()
        self._create_log_panel()
        
        # Initialize state
        self._update_ui_state()
    
    def _create_action_bar(self):
        """Create top action button bar."""
        action_frame = ttk.Frame(self)
        action_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Open Bundle button
        self.open_btn = ttk.Button(
            action_frame,
            text="📂 Open Bundle...",
            command=self.open_bundle,
            width=20
        )
        self.open_btn.pack(side="left", padx=(0, 5))
        
        # Extract Files button
        self.extract_btn = ttk.Button(
            action_frame,
            text="⬇️ Extract Files",
            command=self.extract_files,
            width=20,
            state="disabled"
        )
        self.extract_btn.pack(side="left", padx=(0, 5))
        
        # Separator
        ttk.Separator(action_frame, orient="vertical").pack(
            side="left", fill="y", padx=10
        )
        
        # Status label
        self.status_label = ttk.Label(
            action_frame,
            text="No bundle loaded",
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True)
    
    def _create_file_list(self):
        """Create file list treeview (main content area)."""
        list_frame = ttk.LabelFrame(self, text="Bundle Contents", padding=5)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # Create treeview with columns
        columns = ("size", "encoding", "eol", "binary")
        self.file_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="tree headings",
            selectmode="extended"
        )
        
        # Configure columns
        self.file_tree.heading("#0", text="File Path", anchor="w")
        self.file_tree.heading("size", text="Size", anchor="e")
        self.file_tree.heading("encoding", text="Encoding", anchor="w")
        self.file_tree.heading("eol", text="EOL", anchor="center")
        self.file_tree.heading("binary", text="Binary", anchor="center")
        
        self.file_tree.column("#0", width=300, minwidth=200)
        self.file_tree.column("size", width=100, minwidth=80, anchor="e")
        self.file_tree.column("encoding", width=100, minwidth=80)
        self.file_tree.column("eol", width=60, minwidth=50, anchor="center")
        self.file_tree.column("binary", width=60, minwidth=50, anchor="center")
        
        # Scrollbars
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
    
    def _create_config_panel(self):
        """Create configuration panel."""
        config_frame = ttk.LabelFrame(self, text="Extraction Options", padding=5)
        config_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        # Output directory
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(dir_frame, text="Output Directory:").pack(side="left")
        
        self.output_dir_var = tk.StringVar(
            value=self.config_manager.get("global_settings.output_dir", "")
            if self.config_manager else ""
        )
        
        output_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var)
        output_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Button(
            dir_frame,
            text="Browse...",
            command=self._browse_output_dir,
            width=10
        ).pack(side="left")
        
        # Options row
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill="x")
        
        # Add headers checkbox
        self.add_headers_var = tk.BooleanVar(
            value=self.config_manager.get("app_defaults.add_headers", True)
            if self.config_manager else True
        )
        ttk.Checkbutton(
            options_frame,
            text="Add file headers",
            variable=self.add_headers_var
        ).pack(side="left", padx=(0, 15))
        
        # Dry run checkbox
        self.dry_run_var = tk.BooleanVar(
            value=self.config_manager.get("app_defaults.dry_run_default", True)
            if self.config_manager else True
        )
        ttk.Checkbutton(
            options_frame,
            text="Dry run (preview only)",
            variable=self.dry_run_var
        ).pack(side="left", padx=(0, 15))
        
        # Overwrite policy
        ttk.Label(options_frame, text="If file exists:").pack(side="left", padx=(0, 5))
        
        self.overwrite_var = tk.StringVar(
            value=self.config_manager.get("app_defaults.overwrite_policy", "prompt")
            if self.config_manager else "prompt"
        )
        
        overwrite_combo = ttk.Combobox(
            options_frame,
            textvariable=self.overwrite_var,
            values=["prompt", "skip", "rename", "overwrite"],
            state="readonly",
            width=10
        )
        overwrite_combo.pack(side="left")
    
    def _create_log_panel(self):
        """Create log output panel."""
        log_frame = ttk.LabelFrame(self, text="Operation Log", padding=5)
        log_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 5))
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Log text widget
        self.log_text = tk.Text(
            log_frame,
            height=6,
            wrap="word",
            state="disabled",
            background="#f5f5f5"
        )
        self.log_text.grid(row=0, column=0, sticky="ew")
        
        # Scrollbar
        log_scroll = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview
        )
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)
    
    def _browse_output_dir(self):
        """Open directory browser for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get() or Path.cwd()
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def open_bundle(self):
        """Open and parse a bundle file."""
        file_path = filedialog.askopenfilename(
            title="Open Bundle File",
            initialdir=self.config_manager.get("global_settings.input_dir", "")
            if self.config_manager else "",
            filetypes=[
                ("Bundle files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self._log("Opening bundle file...")
            
            # Parse bundle
            self.current_manifest = self.parser.parse_file(Path(file_path))
            
            # Update UI
            self._populate_file_list()
            self._update_ui_state()
            
            profile = self.current_manifest.profile
            file_count = self.current_manifest.get_file_count()
            
            self._log(f"✓ Bundle parsed successfully")
            self._log(f"  Profile: {profile}")
            self._log(f"  Files: {file_count}")
            
            self.status_label.config(
                text=f"Loaded: {file_count} files ({profile} format)"
            )
            
        except Exception as e:
            self._log(f"✗ Error parsing bundle: {str(e)}")
            messagebox.showerror("Parse Error", f"Failed to parse bundle:\n\n{str(e)}")
    
    def extract_files(self):
        """Extract files from current manifest."""
        if not self.current_manifest:
            return
        
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showwarning(
                "No Output Directory",
                "Please select an output directory."
            )
            return
        
        try:
            self._log(f"Extracting to: {output_dir}")
            
            # Create writer with current settings
            writer = BundleWriter(
                base_path=Path(output_dir),
                overwrite_policy=self.overwrite_var.get(),
                dry_run=self.dry_run_var.get(),
                add_headers=self.add_headers_var.get()
            )
            
            # Extract files
            stats = writer.extract_manifest(
                self.current_manifest,
                Path(output_dir)
            )
            
            # Report results
            mode = "DRY RUN - " if self.dry_run_var.get() else ""
            self._log(f"✓ {mode}Extraction complete")
            self._log(f"  Processed: {stats['processed']}")
            self._log(f"  Skipped: {stats['skipped']}")
            self._log(f"  Errors: {stats['errors']}")
            
            if not self.dry_run_var.get():
                messagebox.showinfo(
                    "Extraction Complete",
                    f"Successfully extracted {stats['processed']} files.\n"
                    f"Skipped: {stats['skipped']}\n"
                    f"Errors: {stats['errors']}"
                )
            else:
                messagebox.showinfo(
                    "Dry Run Complete",
                    f"Preview: {stats['processed']} files would be extracted.\n"
                    f"(No files were actually written)"
                )
                
        except Exception as e:
            self._log(f"✗ Error during extraction: {str(e)}")
            messagebox.showerror("Extraction Error", f"Failed to extract files:\n\n{str(e)}")
    
    def _populate_file_list(self):
        """Populate file tree with manifest entries."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        if not self.current_manifest:
            return
        
        # Add entries
        for entry in self.current_manifest.entries:
            size_str = f"{entry.file_size_bytes:,}" if entry.file_size_bytes else "?"
            binary_str = "✓" if entry.is_binary else ""
            
            self.file_tree.insert(
                "",
                "end",
                text=entry.path,
                values=(
                    size_str,
                    entry.encoding,
                    entry.eol_style,
                    binary_str
                )
            )
    
    def _update_ui_state(self):
        """Update UI element states based on current state."""
        has_manifest = self.current_manifest is not None
        
        # Enable/disable extract button
        self.extract_btn.config(
            state="normal" if has_manifest else "disabled"
        )
    
    def _log(self, message: str):
        """Add message to log panel."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


# ============================================================================
# LIFECYCLE STATUS: Proposed
# PHASE: Phase 5 GUI Implementation
# DEPENDENCIES: core/parser.py, core/writer.py, core/models.py
# TESTS: Manual UI testing, integration with ModeManager
# NEXT STEPS: Integration with main_window.py, menu bar implementation
# ============================================================================
