# ============================================================================
# SOURCEFILE: main_window.py
# RELPATH: bundle_file_tool_v2/src/ui/main_window.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# STATUS: NEW - Phase 4 foundation per George's architectural guidance
# DESCRIPTION: Main application window with dual-mode UI framework
# ============================================================================

"""
Main Application Window for Bundle File Tool v2.1.

Implements the dual-mode UI structure with mode switcher and dynamic frame
management. This is the foundation for Phase 5 GUI refactoring work.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.mode_manager import ModeManager, AppMode


class BundleFileToolApp(tk.Tk):
    """
    Main application window for Bundle File Tool v2.1.
    
    This class implements the dual-mode UI architecture, with separate
    interfaces for Un-bundle and Bundle modes. The ModeManager handles
    state transitions and notifies this window to swap UI frames.
    
    Architecture:
    - Mode switcher in toolbar for instant mode changes
    - Separate frames for each mode (swapped on demand)
    - ModeManager observer pattern for state coordination
    - Foundation for Phase 5 full GUI implementation
    """
    
    def __init__(self):
        """Initialize main application window."""
        super().__init__()
        
        # Window configuration
        self.title("Bundle File Tool v2.1 - Un-bundle Mode")
        self.geometry("900x700")
        self.minsize(760, 520)
        
        # Initialize mode manager
        self.mode_manager = ModeManager(initial_mode=AppMode.UNBUNDLE)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        
        # Create UI components
        self._create_toolbar()
        self._create_mode_frames()
        self._create_statusbar()
        
        # NOW register the listener; it will fire immediately and succeed
        self.mode_manager.add_listener(self.on_mode_change)

        # Initial mode setup is handled by mode_manager listener
    
    def _create_toolbar(self):
        """Create top toolbar with mode switcher."""
        toolbar = ttk.Frame(self, padding=5)
        toolbar.grid(row=0, column=0, sticky="ew")
        
        # Mode switcher label
        ttk.Label(toolbar, text="Mode:").pack(side="left", padx=(0, 5))
        
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
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)
        
        # Mode-specific actions will be added in Phase 5
        self.action_frame = ttk.Frame(toolbar)
        self.action_frame.pack(side="left", fill="x", expand=True)
        
        # Placeholder action buttons
        self.action_label = ttk.Label(self.action_frame, text="Actions:")
        self.action_label.pack(side="left", padx=(0, 5))
    
    def _create_mode_frames(self):
        """Create placeholder frames for each mode."""
        # Container for mode-specific content
        content_container = ttk.Frame(self)
        content_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        content_container.grid_columnconfigure(0, weight=1)
        content_container.grid_rowconfigure(0, weight=1)
        
        # Un-bundle mode frame (placeholder)
        self.unbundle_frame = ttk.LabelFrame(
            content_container,
            text="Un-bundle Mode - Extract Files from Bundle",
            padding=10
        )
        
        # Placeholder content for un-bundle mode
        unbundle_content = ttk.Label(
            self.unbundle_frame,
            text="Un-bundle Mode UI\n\n"
                 "This frame will contain:\n"
                 "• File list tree view\n"
                 "• Configuration panel\n"
                 "• Log output\n"
                 "• Extract controls\n\n"
                 "(Phase 5 implementation)",
            justify="center",
            font=("TkDefaultFont", 10)
        )
        unbundle_content.pack(expand=True)
        
        # Bundle mode frame (placeholder)
        self.bundle_frame = ttk.LabelFrame(
            content_container,
            text="Bundle Mode - Create Bundle from Files",
            padding=10
        )
        
        # Placeholder content for bundle mode
        bundle_content = ttk.Label(
            self.bundle_frame,
            text="Bundle Mode UI\n\n"
                 "This frame will contain:\n"
                 "• Source file tree view\n"
                 "• Live bundle preview\n"
                 "• Profile selector\n"
                 "• Create bundle controls\n\n"
                 "(Phase 5 implementation)",
            justify="center",
            font=("TkDefaultFont", 10)
        )
        bundle_content.pack(expand=True)
        
        # Store container reference
        self.content_container = content_container
    
    def _create_statusbar(self):
        """Create bottom status bar."""
        statusbar = ttk.Frame(self, relief="sunken")
        statusbar.grid(row=2, column=0, sticky="ew")
        
        self.status_label = ttk.Label(
            statusbar,
            text="Ready - Phase 4 Foundation Implementation",
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=5, pady=2)
        
        self.mode_indicator = ttk.Label(
            statusbar,
            text="Mode: Un-bundle",
            anchor="e"
        )
        self.mode_indicator.pack(side="right", padx=5, pady=2)
    
    def on_mode_change(self, new_mode: AppMode):
        """
        Callback for mode changes from ModeManager.
        
        This method is called whenever the application mode changes.
        It updates the UI to show the appropriate frame and updates
        window title, button states, and status indicators.
        
        Args:
            new_mode: The new application mode
        """
        # Hide all frames first
        self.unbundle_frame.grid_forget()
        self.bundle_frame.grid_forget()
        
        # Show appropriate frame and update UI
        if new_mode == AppMode.UNBUNDLE:
            self._setup_unbundle_mode()
        elif new_mode == AppMode.BUNDLE:
            self._setup_bundle_mode()
    
    def _setup_unbundle_mode(self):
        """Configure UI for un-bundle mode."""
        # Update window title
        self.title("Bundle File Tool v2.1 - Un-bundle Mode")
        
        # Show un-bundle frame
        self.unbundle_frame.grid(row=0, column=0, sticky="nsew")
        
        # Update button states (visual feedback)
        self.unbundle_btn.state(['pressed'])
        self.bundle_btn.state(['!pressed'])
        
        # Update status bar
        self.mode_indicator.config(text="Mode: Un-bundle")
        self.status_label.config(text="Ready to parse bundle files")
        
        # Phase 5: Enable/disable appropriate menu items and actions
        # Phase 5: Load last used configuration for un-bundle mode
    
    def _setup_bundle_mode(self):
        """Configure UI for bundle mode."""
        # Update window title
        self.title("Bundle File Tool v2.1 - Bundle Mode")
        
        # Show bundle frame
        self.bundle_frame.grid(row=0, column=0, sticky="nsew")
        
        # Update button states (visual feedback)
        self.bundle_btn.state(['pressed'])
        self.unbundle_btn.state(['!pressed'])
        
        # Update status bar
        self.mode_indicator.config(text="Mode: Bundle")
        self.status_label.config(text="Ready to create bundle files")
        
        # Phase 5: Enable/disable appropriate menu items and actions
        # Phase 5: Load last used configuration for bundle mode
    
    def set_status(self, message: str):
        """
        Update status bar message.
        
        Args:
            message: Status message to display
        """
        self.status_label.config(text=message)


def main():
    """Application entry point."""
    app = BundleFileToolApp()
    app.mainloop()


if __name__ == "__main__":
    main()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# ARCHITECTURE: Dual-mode UI foundation per George's Phase 4 guidance
# DEPENDENCIES: ui/mode_manager.py
# TESTS: Manual testing of mode switching, UI state updates
# PHASE 5 INTEGRATION: Placeholder frames will be replaced with full implementations
# NEXT STEPS: Refactor v1.1.5 UI components into unbundle_frame and bundle_frame
# NOTES: Current implementation is foundation only - full features in Phase 5
# ============================================================================
