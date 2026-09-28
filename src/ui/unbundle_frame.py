# BFT_B104_USER_STATE_WIRING - accepts the UserStateStore handle (R-BFT-01)

"""
Un-bundle Mode Frame for Bundle File Tool v2.1.

This frame implements the complete Un-bundle mode interface, mirroring the
v1.1.5 layout with file list, configuration panel, and log output.
"""

import base64
import binascii
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List
import sys
import os
import traceback

# Add parent directory for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.parser import BundleParser
from core.writer import BundleWriter
from core.models import BundleManifest
from core.cancellation import OperationCancelled
from core.checking import CheckResult
from core.exceptions import BundleFileToolError
from core.service import BundleToolService
from ui.check_results import show_check_results
from ui.tk_progress import run_with_progress


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
    
    def __init__(self, parent, config_manager=None, user_state=None,
                 service: Optional[BundleToolService] = None):
        """
        Initialize Un-bundle frame.
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance for settings
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.user_state = user_state
        self.current_manifest: Optional[BundleManifest] = None
        self.current_check: Optional[CheckResult] = None
        self.current_source_label = "bundle"
        self.service = service or BundleToolService(config=config_manager)
        # Kept as a public adapter seam for the existing parser-focused tests.
        self.parser = self.service.parser
        
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

        self.check_btn = ttk.Button(
            action_frame,
            text="✓ Check Bundle",
            command=self.check_current_bundle,
            width=20,
            state="disabled",
        )
        self.check_btn.pack(side="left", padx=(0, 5))
        
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

    def _preference(self, key: str, default: bool = True) -> bool:
        if self.user_state is None:
            return default
        return bool(self.user_state.get(key, default))
    
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
        
        self.file_tree.column("#0", width=300, minwidth=200, stretch=False)
        self.file_tree.column("size", width=100, minwidth=80, anchor="e",
                              stretch=False)
        self.file_tree.column("encoding", width=100, minwidth=80,
                              stretch=False)
        self.file_tree.column("eol", width=60, minwidth=50, anchor="center",
                              stretch=False)
        self.file_tree.column("binary", width=60, minwidth=50,
                              anchor="center", stretch=False)
        
        # Scrollbars
        self.file_vscroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_tree.yview)
        self.file_hscroll = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(
            yscrollcommand=self.file_vscroll.set,
            xscrollcommand=self.file_hscroll.set)
        
        # Grid layout
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        self.file_vscroll.grid(row=0, column=1, sticky="ns")
        self.file_hscroll.grid(row=1, column=0, sticky="ew")
    
    def _create_config_panel(self):
        """Create configuration panel."""
        config_frame = ttk.LabelFrame(self, text="Extraction Options", padding=5)
        config_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        # Output directory
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(dir_frame, text="Output Directory:").pack(side="left")
        
        self.output_dir_var = tk.StringVar(
            master=self,
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
            master=self,
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
            master=self,
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
            master=self,
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
        log_frame.grid_rowconfigure(0, weight=1)
        
        # Log text widget
        self.log_text = tk.Text(
            log_frame,
            height=6,
            wrap="none",
            state="disabled",
            background="#f5f5f5"
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        self.log_vscroll = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview
        )
        self.log_hscroll = ttk.Scrollbar(
            log_frame,
            orient="horizontal",
            command=self.log_text.xview
        )
        self.log_vscroll.grid(row=0, column=1, sticky="ns")
        self.log_hscroll.grid(row=1, column=0, sticky="ew")
        self.log_text.configure(
            yscrollcommand=self.log_vscroll.set,
            xscrollcommand=self.log_hscroll.set)
    
    def _browse_output_dir(self):
        """Open directory browser for output directory."""
        directory = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Select Output Directory",
            initialdir=self.output_dir_var.get() or Path.cwd()
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def open_bundle(self):
        """Open and parse a bundle file."""
        remembered = (
            self.user_state.get("last_bundle_open_dir", "")
            if self.user_state else ""
        )
        fallback = (
            self.config_manager.get("global_settings.input_dir", "")
            if self.config_manager else ""
        )
        initial_directory = remembered or fallback
        if initial_directory and not Path(initial_directory).is_dir():
            initial_directory = fallback if fallback and Path(fallback).is_dir() else ""

        file_path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Open Bundle File",
            initialdir=initial_directory,
            filetypes=[
                ("Bundle files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self._log(f"Opening bundle file: {file_path}")

            # Build 111: Open Bundle reports through PyThermX like every other
            # long operation. The entry count cannot gate this - it is not known
            # until parsing finishes - so the threshold is the file size, which
            # stat() gives us before any work starts.
            bundle_path = Path(file_path)
            if self._parse_progress_enabled(bundle_path):
                # BFT_B115_OPEN_BUNDLE_CANCEL_ARITY.
                #
                # This lambda took only `progress` until Build 115, while
                # Build 112 had taught `run_with_progress` to pass `cancel` as
                # well. Every bundle over the 2 MB threshold therefore died on
                # a TypeError before a byte was parsed, surfaced to the user as
                # "Failed to parse bundle" - so Open Bundle worked on small
                # files and failed on exactly the large ones the progress bar
                # existed to serve. Build 112 updated three of the four work
                # callables and missed this one.
                #
                # `allow_cancel=False` because `parse_file` has no cancellation
                # seam yet. Rendering a Cancel button that does nothing would be
                # worse than rendering none.
                self.current_manifest = run_with_progress(
                    self,
                    "Opening bundle",
                    lambda progress=None, cancel=None: self.parser.parse_file(
                        bundle_path, progress=progress),
                    allow_cancel=False,
                )
            else:
                self.current_manifest = self.parser.parse_file(bundle_path)

            if self.user_state:
                self.user_state.set_and_save(
                    "last_bundle_open_dir",
                    str(bundle_path.parent),
                )

            self.current_check = None
            self._accept_manifest(str(bundle_path))
            if self._preference("check_bundle_on_load"):
                self.check_current_bundle(show_results=False, show_problems=True)
            
        except Exception as e:
            self._log(f"✗ Error parsing bundle {file_path}: {e}")
            print(f"Error opening bundle: {file_path}", file=sys.stderr, flush=True)
            traceback.print_exc()
            sys.stderr.flush()
            messagebox.showerror(
                "Parse Error",
                f"Failed to parse bundle:\n{file_path}\n\n{e}",
                parent=self.winfo_toplevel(),
            )

    def load_bundle_text(self, bundle_text: str, *, source_label: str = "Text") -> None:
        """Parse bundle text supplied by another owned surface, such as Clipboard."""

        try:
            self._log(f"Opening bundle from {source_label.lower()}...")
            threshold = self.PARSE_PROGRESS_MIN_MB * 1024 * 1024
            if len(bundle_text.encode("utf-8")) >= threshold:
                self.current_manifest = run_with_progress(
                    self,
                    f"Opening bundle from {source_label.lower()}",
                    lambda progress=None, cancel=None: self.parser.parse(
                        bundle_text,
                        progress=progress,
                    ),
                    allow_cancel=False,
                )
            else:
                self.current_manifest = self.parser.parse(bundle_text)
            self.current_check = None
            self._accept_manifest(source_label)
            # Lightweight test doubles used by adapter tests intentionally do
            # not carry the service/user-state surface.
            if getattr(self, "service", None) is not None \
                    and self._preference("check_bundle_on_load"):
                self.check_current_bundle(show_results=False, show_problems=True)
        except Exception as exc:
            self._log(f"✗ Error parsing bundle from {source_label.lower()}: {exc}")
            messagebox.showerror(
                "Parse Error",
                f"Failed to parse bundle text from {source_label.lower()}:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )

    def _accept_manifest(self, source_label: str) -> None:
        """Publish a successfully parsed manifest to the visible unbundle surface."""

        self.current_source_label = source_label
        self._populate_file_list()
        self._update_ui_state()
        profile = self.current_manifest.profile
        file_count = self.current_manifest.get_file_count()
        self._log("✓ Bundle parsed successfully")
        self._log(f"  Source: {source_label}")
        self._log(f"  Profile: {profile}")
        self._log(f"  Files: {file_count}")
        self._log(f"  Producer: {self._producer_label()}")
        self.status_label.config(
            text=f"Loaded: {file_count} files ({profile} format) · not checked\n{self._producer_label()}"
        )

    def _producer_label(self) -> str:
        metadata = self.current_manifest.metadata if self.current_manifest else {}
        versions = metadata.get("bft_versions", [])
        return ("Created with BFT " + ", ".join(versions)
                if versions else "Producer build not recorded")

    def _publish_check_result(self, result: CheckResult, *, show: bool) -> bool:
        self.current_check = result
        profile = self.current_manifest.profile if self.current_manifest else "unknown"
        if result.status == "blocked":
            state = f"BLOCKED ({len(result.blockers)} finding(s))"
        elif result.status == "warnings":
            state = f"checked with {len(result.warnings)} warning(s)"
        else:
            state = "checked — ready to extract"
        self.status_label.config(
            text=f"Loaded: {result.file_count} files ({profile} format) · {state}\n{self._producer_label()}")
        self._log(
            f"{'✓' if result.valid else '✗'} Integrity check {result.status}: "
            f"{len(result.blockers)} blocking, {len(result.warnings)} warning(s)")
        self._update_ui_state()
        if show:
            show_check_results(self.winfo_toplevel(), result)
        return result.valid

    def check_current_bundle(
        self, *, show_results: bool = True, show_problems: bool = False
    ) -> bool:
        """Check the loaded manifest without reparsing or writing anything."""
        if not self.current_manifest:
            return False
        manifest = self.current_manifest
        entry_count = len(manifest.entries)

        def work(progress=None, cancel=None):
            return self.service.check_manifest(
                manifest,
                label=self.current_source_label,
                progress=progress,
                cancel=cancel,
            )

        try:
            if self._progress_enabled(entry_count):
                result = run_with_progress(
                    self, "Checking bundle", work, allow_cancel=True)
            else:
                result = work()
        except OperationCancelled:
            self._log("Integrity check cancelled")
            self.status_label.config(text="Bundle loaded · check cancelled")
            return False
        except BundleFileToolError as error:
            self._log(f"✗ Integrity check failed: {error}")
            messagebox.showerror(
                "Bundle check failed", str(error), parent=self.winfo_toplevel())
            return False
        show = show_results or (show_problems and bool(
            result.blockers or result.warnings))
        return self._publish_check_result(result, show=show)

    def _ensure_bundle_checked(self) -> bool:
        if self._preference("check_before_extract"):
            return self.check_current_bundle(
                show_results=False, show_problems=True)
        if self.current_check is not None:
            if not self.current_check.valid:
                show_check_results(self.winfo_toplevel(), self.current_check)
            return self.current_check.valid
        # Hard extraction safety is not bypassable. The preference controls
        # when the convenience check runs, not whether unsafe paths may write.
        return self.check_current_bundle(show_results=False, show_problems=True)
    
    def extract_files(self):
        """Extract files from current manifest."""
        if not self.current_manifest:
            return
        if not self._ensure_bundle_checked():
            self._log("✗ Extraction blocked by the integrity check")
            return
        
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showwarning(
                "No Output Directory",
                "Please select an output directory.",
                parent=self.winfo_toplevel(),
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
            
            # Extract files. Build 108: extraction knows its size up front, so
            # the thermometer is determinate from the first frame.
            entry_count = len(self.current_manifest.entries)
            if self._progress_enabled(entry_count):
                stats = run_with_progress(
                    self,
                    f"Extracting {entry_count} files",
                    lambda progress=None, cancel=None: writer.extract_manifest(
                        self.current_manifest,
                        Path(output_dir),
                        progress=progress, cancel=cancel),
                )
            else:
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
                    f"Errors: {stats['errors']}",
                    parent=self.winfo_toplevel(),
                )
            else:
                messagebox.showinfo(
                    "Dry Run Complete",
                    f"Preview: {stats['processed']} files would be extracted.\n"
                    f"(No files were actually written)",
                    parent=self.winfo_toplevel(),
                )
                
        except Exception as e:
            self._log(f"✗ Error during extraction: {str(e)}")
            messagebox.showerror(
                "Extraction Error",
                f"Failed to extract files:\n\n{str(e)}",
                parent=self.winfo_toplevel(),
            )
    
    def _populate_file_list(self):
        """Populate file tree with manifest entries."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        if not self.current_manifest:
            return

        # A Treeview scroll range is based on column widths, not rendered text.
        # Size the path column to its content so long paths create a real,
        # reachable horizontal range instead of being silently clipped.
        font = tkfont.nametofont("TkDefaultFont")
        path_width = max(
            300,
            max((font.measure(entry.path) + 36
                 for entry in self.current_manifest.entries), default=300),
        )
        self.file_tree.column("#0", width=min(path_width, 8192), stretch=False)
        
        # Add entries
        for entry in self.current_manifest.entries:
            size = self._entry_size_bytes(entry)
            size_str = f"{size:,}" if size is not None else "?"
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

    @staticmethod
    def _entry_size_bytes(entry) -> Optional[int]:
        """Return original metadata size or infer the extractable payload size."""
        if entry.file_size_bytes is not None:
            return entry.file_size_bytes

        if entry.is_binary:
            try:
                if isinstance(entry.content, (bytes, bytearray)):
                    return len(entry.content)
                return len(base64.b64decode(
                    str(entry.content).strip(), validate=True))
            except (binascii.Error, ValueError, TypeError):
                return None

        content = entry.content if isinstance(entry.content, str) \
            else str(entry.content)
        encoding = entry.encoding or "utf-8"
        if encoding.lower() in ("auto",):
            encoding = "utf-8"
        elif encoding.lower() in ("utf-8-bom", "utf8-bom", "utf-8_sig"):
            encoding = "utf-8-sig"
        try:
            return len(content.encode(encoding, errors="replace"))
        except LookupError:
            return None
    
    def _update_ui_state(self):
        """Update UI element states based on current state."""
        has_manifest = self.current_manifest is not None
        
        # Enable/disable extract button
        can_extract = has_manifest and (
            self.current_check is None or self.current_check.valid)
        self.extract_btn.config(state="normal" if can_extract else "disabled")
        self.check_btn.config(
            state="normal" if has_manifest else "disabled"
        )
    
    #: Bundles at or above this size get a progress dialog when opened.
    #: Below it, parsing finishes faster than a dialog would be readable.
    PARSE_PROGRESS_MIN_MB = 2.0

    def _parse_progress_enabled(self, bundle_path) -> bool:
        """Whether opening this bundle gets a progress dialog.

        BFT_B111_PARSE_THRESHOLD. The bundle-side rule keys off a file count,
        which is unavailable here: the number of entries is the *result* of the
        work being measured. File size is the honest proxy and is known before
        the read begins.
        """
        if not self.config_manager:
            return True
        if not self.config_manager.get("ui.progress.enabled", True):
            return False
        try:
            size_mb = bundle_path.stat().st_size / (1024 * 1024)
        except OSError:
            return False
        floor = self.config_manager.get(
            "ui.progress.min_parse_mb", self.PARSE_PROGRESS_MIN_MB)
        return size_mb >= floor

    def _progress_enabled(self, file_count=None) -> bool:
        """Whether an operation of this size gets a progress dialog.

        BFT_B108_PROGRESS_THRESHOLD - the same rule the bundle side applies.
        """
        if not self.config_manager:
            return True
        if not self.config_manager.get("ui.progress.enabled", True):
            return False
        if file_count is None:
            return True
        return file_count >= self.config_manager.get("ui.progress.min_files", 200)

    def _log(self, message: str):
        """Add message to log panel."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
