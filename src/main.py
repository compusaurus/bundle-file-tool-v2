# ============================================================================
# SOURCEFILE: main.py
# RELPATH: bundle_file_tool_v2/src/main.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Pure GUI entry point - NO CLI coupling
# ARCHITECT: George (Phase 3 guidance document)
# REQUIREMENTS: REQ-MAI-001, REQ-MAI-002, REQ-MAI-003, REQ-MAI-004
# ============================================================================
#!/usr/bin/env python3
"""
Single GUI entry point for Bundle File Tool v2.1.

This module provides ONLY GUI functionality. It does NOT import or reference
the CLI module (cli.py), ensuring clean separation of concerns per REQ-MAI-001.

For CLI usage, invoke cli.py directly:
    python src/cli.py unbundle <bundle_file>
    python src/cli.py bundle <source_paths...>

For GUI usage (this file):
    python src/main.py
"""
import sys
from pathlib import Path


def setup_path():
    """
    Add project root to sys.path for direct script execution.
    
    Ensures 'from core.* imports work when running:
        python src/main.py
    from the project root on Windows 11.
    
    Requirement: REQ-MAI-002
    """
    # Get project root (parent of src/)
    current_file = Path(__file__).resolve()
    src_dir = current_file.parent
    project_root = src_dir.parent
    
    # Add to path if not already present
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


def bootstrap_logging():
    """
    Bootstrap UTF-8 logging with API compatibility.
    
    The configure_utf8_logging() signature varies across versions:
    - Old: configure_utf8_logging()  # no parameters
    - New: configure_utf8_logging(force=False)  # optional parameter
    
    This function adapts to both signatures without crashing.
    
    Requirement: REQ-MAI-003
    """
    try:
        from core.logging import configure_utf8_logging
        
        # Try calling with no args first (old API)
        try:
            configure_utf8_logging()
        except TypeError:
            # Signature requires parameters (new API), try with force=False
            try:
                configure_utf8_logging(force=False)
            except TypeError:
                # Unexpected signature, but don't crash - logging is best-effort
                pass
    except ImportError:
        # If logging module doesn't exist, proceed without it
        # GUI should still launch even if logging fails
        pass


def main():
    """
    Main entry point for GUI mode only.
    
    Launches the Tkinter GUI without any CLI coupling.
    
    Requirements:
        - REQ-MAI-001: No argparse imports or CLI coupling
        - REQ-MAI-002: Path setup for direct execution
        - REQ-MAI-003: Logging bootstrap with API compatibility
        - REQ-MAI-004: Support 'python src/main.py' on Windows 11
    """
    # Setup path for direct execution
    setup_path()
    
    # Bootstrap logging (best-effort, non-fatal)
    bootstrap_logging()
    
    # Import and launch GUI
    # Import here (not at top) so path setup happens first
    from ui.main_window import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# REQUIREMENTS SATISFIED:
#   REQ-MAI-001: No argparse, no CLI imports - pure GUI entry
#   REQ-MAI-002: setup_path() enables direct execution from project root
#   REQ-MAI-003: bootstrap_logging() handles varying API signatures
#   REQ-MAI-004: Supports 'python src\main.py' on Windows 11
# NEXT STEPS: Integration testing with GUI, test on Windows 11
# DEPENDENCIES: ui.main_window (GUI), core.logging (optional)
# ============================================================================
