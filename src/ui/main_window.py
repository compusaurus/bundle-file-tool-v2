# BFT_B104_USER_STATE_WIRING - window geometry persists to UserStateStore (R-BFT-01)

"""
Main Application Window for Bundle File Tool v2.1.

Implements the complete dual-mode UI with full Un-bundle and Bundle
interfaces, per specification Section 7.
"""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import ConfigManager
from core.service import BundleToolService
from core.startup import startup_log_directory
from core.user_state import UserStateStore
from core.version import __version__
from railgun_display import DisplayRect, geometry_on_display
from ui.bundle_frame import BundleFrame
from ui.check_preferences import edit_check_preferences
from ui.config_hub_launcher import (
    ConfigHubLaunchError,
    config_hub_startup_error,
    launch_bft_config_hub,
)
from ui.log_viewer import LogViewer
from ui.mode_manager import AppMode, ModeManager
from ui.selection_workspace import SelectionWorkspaceFrame
from ui.startup_preferences import edit_startup_preferences
from ui.text_viewer import TextFileViewer
from ui.tk_progress import run_with_progress
from ui.unbundle_frame import UnbundleFrame
from ui.window_icon import apply_window_icon
from ui.window_placement import (
    apply_startup_window_state,
    monitor_work_area_for_widget,
    observed_window_state,
    reconcile_toplevel_with_displays,
    resolved_startup_state,
    safe_window_geometry,
)


class BundleFileToolApp(tk.Tk):
    """
    Main application window for Bundle File Tool v2.1.
    
    This class implements the complete dual-mode UI architecture with
    separate fully-functional interfaces for Un-bundle and Bundle modes.
    
    Features:
    - Mode switcher with instant mode changes
    - Complete Un-bundle UI (mirrors v1.1.5)
    - Complete Bundle UI (split pane with preview)
    - Menu bar with mode-aware items
    - Settings dialog
    - Help/About dialog
    """
    
    def __init__(self, *, launch_work_area: DisplayRect | None = None):
        """Initialize main application window."""
        super().__init__()
        apply_window_icon(self)
        # Avoid showing a default-size flash while state and geometry are
        # restored. Minimized startup is queued only after the final map.
        self.withdraw()

        # Load configuration. Build 104, R-BFT-01: the governed document is
        # read-only at runtime; mutable per-user state lives in UserStateStore.
        #
        # BFT_B109_GUI_CONFIG_ANCHORING (F-02). No argument, deliberately. An
        # explicit path is developer/test scope in ConfigManager: it resolves
        # against the process working directory and may create the file, so the
        # GUI could address - and bring into existence - a different document
        # from the one the CLI reads and the installer governs. That also has to
        # be true before Layer C means anything, because a read-only flag on the
        # installed file protects nothing if the app is using another one.
        try:
            self.config_manager = ConfigManager()
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            self.config_manager = None

        try:
            self.user_state = UserStateStore()
            # One-time seed from a pre-104 config that still carries these keys.
            if self.config_manager:
                self.user_state.seed_from_config(self.config_manager.config)
        except Exception as e:
            print(f"Warning: Could not load user state: {e}")
            self.user_state = None
        
        # Window configuration
        self.title(f"Bundle File Tool v{__version__} - Un-bundle Mode")
        
        # Restore window geometry if available
        startup_mode = (
            self.user_state.startup_mode() if self.user_state else "restore")
        remembered_state = (
            self.user_state.last_non_minimized_state()
            if self.user_state else "normal")
        self._startup_effective_state = resolved_startup_state(
            startup_mode, remembered_state)
        remember_geometry = bool(
            self.user_state.get("remember_window_geometry", True)
            if self.user_state else True)
        saved_geometry = (
            self.user_state.get("last_non_minimized_geometry", "")
            if self.user_state and remember_geometry else "")
        
        restored_geometry = safe_window_geometry(saved_geometry)
        if launch_work_area is not None:
            restored_geometry = geometry_on_display(
                restored_geometry, launch_work_area)
        try:
            self.geometry(restored_geometry)
        except tk.TclError:
            self.geometry("1000x700")
        self.minsize(800, 600)
        reconcile_toplevel_with_displays(self)
        
        # Initialize mode manager
        initial_mode_str = (
            self.config_manager.get("app_defaults.default_mode", "unbundle")
            if self.config_manager else "unbundle"
        )
        initial_mode = (
            AppMode.BUNDLE if initial_mode_str == "bundle" else AppMode.UNBUNDLE
        )
        self.mode_manager = ModeManager(initial_mode=initial_mode)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Content area expands
        
        # Create UI components
        self._create_menu_bar()
        self._create_toolbar()
        self._create_mode_frames()
        self._create_statusbar()
        self.bind_all("<Control-o>", self._open_bundle_shortcut)

        # BFT_B109_LAYER_A_INTEGRITY. The alert must be high-visibility on the
        # UI as well as the CLI, so it goes to three
        # places: stderr for the record, the status bar so it stays visible for
        # the whole session, and one dialog so it cannot be missed. Reported
        # after the widgets exist, because the status bar is one of them.
        self._report_config_integrity()

        # Register mode listener AFTER frames exist
        self.mode_manager.add_listener(self.on_mode_change)
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.deiconify()
        self.after_idle(self._apply_configured_startup_state)
        
        #self.max_file_mb = max_file_mb
        #self.treat_binary_as_base64 = treat_binary_as_base64
    
    def _create_menu_bar(self):
        """Create application menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        file_menu.add_command(
            label="Open Bundle...",
            command=self.menu_open_bundle,
            accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Un-bundle from Clipboard",
            command=self.menu_unbundle_clipboard
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Select Source Directory...",
            command=self.menu_select_source,
            state="disabled"  # Enabled in Bundle mode
        )
        file_menu.add_command(
            label="Save Bundle As...",
            command=self.menu_save_bundle,
            state="disabled"  # Enabled in Bundle mode
        )
        file_menu.add_command(
            label="Copy Bundle to Clipboard",
            command=self.menu_copy_bundle,
            state="disabled"  # Enabled in Bundle mode
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Settings...",
            command=self.show_settings
        )
        file_menu.add_command(
            label="Startup Window...",
            command=self.show_startup_preferences
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Exit",
            command=self.on_close,
            accelerator="Alt+F4"
        )
        
        # Store menu references for state updates
        self.file_menu = file_menu
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        tools_menu.add_command(
            label="Validate Bundle...",
            command=self.menu_validate_bundle
        )
        tools_menu.add_command(
            label="Integrity Check Preferences...",
            command=self.show_check_preferences,
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Open Web Workspace...",
            command=self.menu_open_web_workspace,
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="View Logs...",
            command=self.menu_view_logs
        )
        tools_menu.add_command(
            label="View Startup Logs...",
            command=self.menu_view_startup_logs
        )
        
        self.tools_menu = tools_menu
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        help_menu.add_command(
            label="Documentation",
            command=self.show_documentation
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="About Bundle File Tool",
            command=self.show_about
        )
    
    def _create_toolbar(self):
        """Create top toolbar with mode switcher."""
        toolbar = ttk.Frame(self, padding=5)
        toolbar.grid(row=0, column=0, sticky="ew")
        
        # Mode switcher label
        ttk.Label(toolbar, text="Mode:", font=("TkDefaultFont", 9, "bold")).pack(
            side="left", padx=(0, 5)
        )
        
        # Mode switcher buttons (segmented control style)
        mode_frame = ttk.Frame(toolbar)
        mode_frame.pack(side="left")
        
        self.unbundle_btn = ttk.Button(
            mode_frame,
            text="Un-bundle",
            command=lambda: self.mode_manager.set_mode(AppMode.UNBUNDLE),
            width=12
        )
        self.unbundle_btn.pack(side="left", padx=(0, 2))
        
        self.bundle_btn = ttk.Button(
            mode_frame,
            text="Bundle",
            command=lambda: self.mode_manager.set_mode(AppMode.BUNDLE),
            width=12
        )
        self.bundle_btn.pack(side="left")
        
        # Separator
        ttk.Separator(toolbar, orient="vertical").pack(
            side="left", fill="y", padx=10
        )
        
        # Mode description label
        self.mode_desc_label = ttk.Label(
            toolbar,
            text="Extract files from bundle text",
            foreground="gray"
        )
        self.mode_desc_label.pack(side="left")
    
    def _create_mode_frames(self):
        """Create frame instances for each mode."""
        # Container for mode-specific content
        content_container = ttk.Frame(self)
        content_container.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        content_container.grid_columnconfigure(0, weight=1)
        content_container.grid_rowconfigure(0, weight=1)
        
        # Create Un-bundle frame
        self.unbundle_frame = UnbundleFrame(
            content_container,
            config_manager=self.config_manager,
            user_state=self.user_state
        )
        
        # BFT_B115_BUNDLE_MODE_WORKSPACE. Spec 7.1: "Bundle mode becomes a
        # Selection Workspace." The classic flat checklist is retained and
        # selectable, because replacing the most-used surface outright leaves
        # no way back if something is wrong in the field; release policy keeps
        # that behaviour configurable.
        style = self._bundle_mode_style()
        if style == "classic":
            self.bundle_frame = BundleFrame(
                content_container,
                config_manager=self.config_manager,
                user_state=self.user_state
            )
        else:
            self.bundle_frame = SelectionWorkspaceFrame(
                content_container,
                config_manager=self.config_manager,
                user_state=self.user_state
            )
        self.bundle_mode_style = style
        
        # Store container reference
        self.content_container = content_container
    
    def _bundle_mode_style(self) -> str:
        """'workspace' (default) or 'classic', from governed configuration."""
        try:
            value = self.config_manager.get("ui.bundle_mode", "workspace")
        except Exception:
            return "workspace"
        return "classic" if str(value).lower() == "classic" else "workspace"

    def _report_config_integrity(self) -> None:
        """Layer A on the desktop surface. Never raises; never blocks startup."""
        self.config_integrity_finding = None
        self.integrity_banner = None
        try:
            manager = self.config_manager
            if manager is None:
                return
            finding = manager.check_config_integrity()
            if not finding:
                return
            self.config_integrity_finding = finding
            lines = ConfigManager.format_integrity_alert(finding)

            for line in lines:
                print(line, file=sys.stderr)

            try:
                self.status_label.config(
                    text="WARNING: governed configuration failed its integrity check "
                         "- reinstall the delivery kit"
                )
            except Exception:
                pass

            # BFT_B115_NONMODAL_INTEGRITY_ALERT.
            #
            # This was messagebox.showwarning(), directly beneath a docstring
            # promising it "never blocks startup". A modal dialog blocks until
            # someone clicks it, so an unattended launch - a kiosk, a scripted
            # smoke test, a CI probe - waited forever. One test run spent 265
            # seconds sitting on this dialog before it was noticed, and in the
            # field it would have been a hang rather than a slow test.
            #
            # The Build 109 policy requires the alert to reach the GUI. A
            # persistent banner honours that better than a modal: it cannot be
            # dismissed and forgotten while the drift is still present.
            self._show_integrity_banner(lines)
        except Exception:
            # A diagnostic must never stop the application from starting.
            self.config_integrity_finding = None

    def _show_integrity_banner(self, lines) -> None:
        """A persistent, non-blocking alert row across the top of the window."""
        try:
            if getattr(self, "integrity_banner", None) is not None:
                return
            banner = tk.Frame(self, background="#7A2E24")
            banner.grid(row=99, column=0, sticky="ew")
            banner.grid_columnconfigure(0, weight=1)
            tk.Label(
                banner,
                text="WARNING: the governed configuration does not match its "
                     "recorded digest. Reinstall the delivery kit to restore it.",
                background="#7A2E24", foreground="#FFFFFF",
                anchor="w", justify="left", padx=10, pady=6,
            ).grid(row=0, column=0, sticky="ew")
            detail = "\n".join(lines)
            tk.Button(banner, text="Details",
                      command=lambda: messagebox.showwarning(
                          "Governed configuration modified",
                          detail,
                          parent=self,
                      )).grid(
                row=0, column=1, padx=8)
            self.integrity_banner = banner
        except Exception:
            self.integrity_banner = None

    def _create_statusbar(self):
        """Create bottom status bar."""
        statusbar = ttk.Frame(self, relief="sunken")
        statusbar.grid(row=3, column=0, sticky="ew")
        
        self.status_label = ttk.Label(
            statusbar,
            text="Ready",
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=5, pady=2)
        
        self.mode_indicator = ttk.Label(
            statusbar,
            text="Mode: Un-bundle",
            anchor="e"
        )
        self.mode_indicator.pack(side="right", padx=5, pady=2)
        
        # Version label
        ttk.Label(
            statusbar,
            text=f"v{__version__}",
            foreground="gray",
            anchor="e"
        ).pack(side="right", padx=5, pady=2)
    
    def on_mode_change(self, new_mode: AppMode):
        """
        Callback for mode changes from ModeManager.
        
        Updates UI to show appropriate frame and adjusts window title,
        button states, menu items, and status indicators.
        
        Args:
            new_mode: The new application mode
        """
        # Hide all frames first
        self.unbundle_frame.grid_forget()
        self.bundle_frame.grid_forget()
        if hasattr(self.bundle_frame, "workspace_layout"):
            self.bundle_frame.workspace_layout.set_active(new_mode == AppMode.BUNDLE)
        
        # Show appropriate frame and update UI
        if new_mode == AppMode.UNBUNDLE:
            self._setup_unbundle_mode()
        elif new_mode == AppMode.BUNDLE:
            self._setup_bundle_mode()
    
    def _setup_unbundle_mode(self):
        """Configure UI for un-bundle mode."""
        # Update window title
        self.title(f"Bundle File Tool v{__version__} - Un-bundle Mode")
        
        # Show un-bundle frame
        self.unbundle_frame.grid(row=0, column=0, sticky="nsew")
        
        # Update button states (visual feedback)
        self.unbundle_btn.state(['pressed'])
        self.bundle_btn.state(['!pressed'])
        
        # Update mode description
        self.mode_desc_label.config(text="Extract files from bundle text")
        
        # Update status bar
        self.mode_indicator.config(text="Mode: Un-bundle")
        self.status_label.config(text="Ready to parse bundle files")
        
        # Update menu item states (per spec Section 7.3)
        self.file_menu.entryconfig("Select Source Directory...", state="disabled")
        self.file_menu.entryconfig("Save Bundle As...", state="disabled")
        self.file_menu.entryconfig("Copy Bundle to Clipboard", state="disabled")
        self.tools_menu.entryconfig("Validate Bundle...", state="normal")
    
    def _setup_bundle_mode(self):
        """Configure UI for bundle mode."""
        # Update window title
        self.title(f"Bundle File Tool v{__version__} - Bundle Mode")
        
        # Show bundle frame
        self.bundle_frame.grid(row=0, column=0, sticky="nsew")
        
        # Update button states (visual feedback)
        self.bundle_btn.state(['pressed'])
        self.unbundle_btn.state(['!pressed'])
        
        # Update mode description
        if getattr(self, "bundle_mode_style", "workspace") == "workspace":
            self.title(f"Bundle File Tool v{__version__} - Selection Workspace")
            self.mode_desc_label.config(
                text="Plan a bundle: see what is included, excluded, and why")
        else:
            self.mode_desc_label.config(text="Create bundle from source files")
        
        # Update status bar
        self.mode_indicator.config(text="Mode: Bundle")
        self.status_label.config(text="Ready to create bundle files")
        
        # Update menu item states (per spec Section 7.3)
        self.file_menu.entryconfig("Select Source Directory...", state="normal")
        self.file_menu.entryconfig("Save Bundle As...", state="normal")
        self.file_menu.entryconfig("Copy Bundle to Clipboard", state="normal")
        self.tools_menu.entryconfig("Validate Bundle...", state="disabled")
    
    def set_status(self, message: str):
        """
        Update status bar message.
        
        Args:
            message: Status message to display
        """
        self.status_label.config(text=message)
    
# ===================================================================================================
    # Menu Command Handlers
# ===================================================================================================
    
    def menu_open_bundle(self):
        """File -> Open Bundle..."""
        if self.mode_manager.is_unbundle_mode():
            self.unbundle_frame.open_bundle()
        else:
            # Switch to unbundle mode first
            self.mode_manager.set_mode(AppMode.UNBUNDLE)
            self.after(100, self.unbundle_frame.open_bundle)

    def _open_bundle_shortcut(self, _event=None):
        self.menu_open_bundle()
        return "break"
    
    def menu_unbundle_clipboard(self):
        """File -> Un-bundle from Clipboard."""
        try:
            bundle_text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(
                "Clipboard is empty",
                "The clipboard does not contain text that can be opened as a bundle.",
                parent=self,
            )
            return
        if not bundle_text.strip():
            messagebox.showwarning(
                "Clipboard is empty",
                "The clipboard does not contain text that can be opened as a bundle.",
                parent=self,
            )
            return
        if not self.mode_manager.is_unbundle_mode():
            self.mode_manager.set_mode(AppMode.UNBUNDLE)
        self.after(
            0,
            lambda: self.unbundle_frame.load_bundle_text(
                bundle_text,
                source_label="Clipboard",
            ),
        )
    
    def menu_select_source(self):
        """File -> Select Source Directory..."""
        if self.mode_manager.is_bundle_mode():
            self.bundle_frame.select_source()
    
    def menu_save_bundle(self):
        """File -> Save Bundle As..."""
        if self.mode_manager.is_bundle_mode():
            self.bundle_frame.create_bundle()
    
    def menu_copy_bundle(self):
        """File -> Copy Bundle to Clipboard."""
        if self.mode_manager.is_bundle_mode():
            self.bundle_frame.copy_to_clipboard()
    
    def menu_validate_bundle(self):
        """Tools -> Validate Bundle..."""
        remembered = (
            self.user_state.get("last_bundle_open_dir", "")
            if self.user_state else ""
        )
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Validate Bundle",
            initialdir=remembered if remembered and Path(remembered).is_dir() else "",
            filetypes=[("Bundle files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return
        bundle_path = Path(file_path)
        try:
            service = BundleToolService(config=self.config_manager)
            result = run_with_progress(
                self,
                "Validating bundle",
                lambda progress=None, cancel=None: service.validate_bundle(
                    bundle_path,
                    progress=progress,
                ),
                allow_cancel=False,
            )
        except Exception as exc:
            messagebox.showerror(
                "Validation failed",
                f"Could not validate the selected bundle:\n\n{exc}",
                parent=self,
            )
            self.set_status("Bundle validation failed")
            return

        if self.user_state:
            self.user_state.set_and_save("last_bundle_open_dir", str(bundle_path.parent))
        details = [
            "Status: VALID" if result.valid else "Status: INVALID",
            f"Format: {result.profile or 'not detected'}",
            f"Files: {result.file_count}",
        ]
        if result.warnings:
            details.extend(("", "Warnings:", *[f"• {item}" for item in result.warnings]))
        if result.errors:
            details.extend(("", "Errors:", *[f"• {item}" for item in result.errors]))
        dialog = messagebox.showinfo if result.valid else messagebox.showerror
        dialog("Bundle Validation", "\n".join(details), parent=self)
        self.set_status("Bundle is valid" if result.valid else "Bundle is invalid")
    
    def menu_view_logs(self):
        """Tools -> View Logs..."""
        configured = (
            self.config_manager.get("global_settings.log_dir", "logs")
            if self.config_manager else "logs"
        )
        log_dir = Path(str(configured)).expanduser()
        if not log_dir.is_absolute():
            log_dir = ConfigManager.governed_config_path().parent / log_dir
        LogViewer(self, log_dir)

    def menu_open_web_workspace(self):
        """Launch the loopback-only third member of the CLI/Tk/web triad."""
        current = getattr(self, "web_workspace_process", None)
        if current is not None and current.poll() is None:
            self.set_status("The web workspace is already running")
            return

        project_root = Path(__file__).resolve().parents[2]
        entry_point = project_root / "src" / "web_main.py"
        environment = os.environ.copy()
        source_root = str(project_root / "src")
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            source_root + (os.pathsep + inherited if inherited else ""))
        try:
            self.web_workspace_process = subprocess.Popen(
                [sys.executable, str(entry_point)],
                cwd=str(project_root),
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            messagebox.showerror(
                "Web workspace unavailable",
                "Could not start the local web workspace:\n\n"
                f"{exc}\n\nYou can still use the Tkinter and CLI interfaces.",
                parent=self,
            )
            self.set_status("Could not open the web workspace")
            return
        self.set_status("Opening the local web workspace in your browser...")

    def menu_view_startup_logs(self):
        """Open the per-user logs written before the GUI can report errors."""
        LogViewer(self, startup_log_directory())

    def _apply_configured_startup_state(self):
        """Apply the saved choice after Tk has mapped the completed window."""
        area = monitor_work_area_for_widget(self)
        self._startup_effective_state = apply_startup_window_state(
            self,
            getattr(self, "_startup_effective_state", "normal"),
            work_area=area,
        )

    def show_startup_preferences(self):
        """Edit mutable launch preferences, never governed configuration."""
        if not self.user_state:
            messagebox.showerror(
                "Startup preferences unavailable",
                "The per-user state store is unavailable for this session.",
                parent=self,
            )
            return
        if edit_startup_preferences(self, self.user_state):
            self.set_status("Startup window preference saved for the next launch")

    def show_check_preferences(self):
        """Edit per-user automation choices for the shared check service."""
        if not self.user_state:
            messagebox.showerror(
                "Integrity preferences unavailable",
                "The per-user state store is unavailable for this session.",
                parent=self,
            )
            return
        if edit_check_preferences(self, self.user_state):
            self.set_status("Integrity check preferences saved")
    
    def show_settings(self):
        """Open a BFT-scoped ConfigHub session through PyProjectMgr."""
        work_area = monitor_work_area_for_widget(self)
        target_monitor = work_area.as_tuple() if work_area is not None else None
        current = getattr(self, "config_hub_process", None)
        if current is not None and current.process.poll() is None:
            self.set_status("Governed Settings is already open")
            return
        try:
            launched = (
                launch_bft_config_hub(target_monitor=target_monitor)
                if target_monitor is not None
                else launch_bft_config_hub()
            )
        except ConfigHubLaunchError as exc:
            messagebox.showerror(
                "Governed Settings unavailable",
                str(exc),
                parent=self,
            )
            self.set_status("Could not open governed settings")
            return
        self.config_hub_process = launched
        self.set_status("Opening governed settings in ConfigHub...")
        self.after(
            500,
            lambda: self._check_config_hub_startup(
                launched,
                checks_remaining=12,
            ),
        )

    def _check_config_hub_startup(self, instance, checks_remaining: int):
        """Surface child-process failures that occur after ``Popen`` returns."""

        if getattr(self, "config_hub_process", None) is not instance:
            return

        startup_error = config_hub_startup_error(instance)
        if startup_error is not None:
            self.config_hub_process = None
            messagebox.showerror(
                "Governed Settings failed to open",
                startup_error,
                parent=self,
            )
            self.set_status("Could not open governed settings")
            return

        if checks_remaining > 1:
            self.after(
                500,
                lambda: self._check_config_hub_startup(
                    instance,
                    checks_remaining=checks_remaining - 1,
                ),
            )
            return

        self.set_status("Opened governed settings in ConfigHub")
    
    def show_documentation(self):
        """Help -> Documentation."""
        guide = ConfigManager.governed_config_path().parent / "USER_GUIDE.md"
        if not guide.is_file():
            messagebox.showerror(
                "Documentation unavailable",
                f"The installed user guide is missing:\n\n{guide}\n\n"
                "Repair or reinstall Bundle File Tool.",
                parent=self,
            )
            return
        TextFileViewer(self, guide, title="Bundle File Tool User Guide")
    
    def show_about(self):
        """Help -> About."""
        messagebox.showinfo(
            "About Bundle File Tool",
            f"Bundle File Tool v{__version__}\n\n"
            "Create, inspect, validate, and extract portable text bundles.\n\n"
            "© 2026 CompusaurusRex Engineering Team.\n"
            "All rights reserved.",
            parent=self,
        )
    
    def on_close(self):
        """Handle window close event."""
        # Save visible-state evidence to the user store, never to governed
        # configuration. Closing while minimized records the observation but
        # deliberately preserves the last visible state and geometry.
        if self.user_state:
            try:
                current_state = observed_window_state(
                    self, getattr(self, "_startup_effective_state", ""))
                self.user_state.set("last_window_state", current_state)
                if current_state != "minimized":
                    self.user_state.set(
                        "last_non_minimized_state", current_state)
                    if (current_state == "normal"
                            and bool(self.user_state.get(
                                "remember_window_geometry", True))):
                        geometry = safe_window_geometry(self.geometry())
                        self.user_state.set("window_geometry", geometry)
                        self.user_state.set(
                            "last_non_minimized_geometry", geometry)
                work_area = monitor_work_area_for_widget(self)
                if work_area is not None:
                    self.user_state.set(
                        "window_monitor",
                        ",".join(str(value) for value in work_area.as_tuple()))
                self.user_state.set("first_launch", False)
                self.user_state.save()
            except Exception as e:
                print(f"Warning: Could not save user state: {e}")
        
        # Close application
        self.quit()
        self.destroy()


def main(*, launch_work_area: DisplayRect | None = None):
    """Application entry point."""
    app = BundleFileToolApp(launch_work_area=launch_work_area)
    print("status=gui-created", flush=True)
    app.mainloop()


if __name__ == "__main__":
    main()
