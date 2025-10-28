# ============================================================================
# SOURCEFILE: main.py
# RELPATH: bundle_file_tool_v2/src/main.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Command-line interface - thin controller over headless core
# ARCHITECT: George (Phase 3 guidance document)
# ============================================================================
#!/usr/bin/env python3
"""
Single entry point for Bundle File Tool v2.1
Handles both CLI and GUI modes.
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path
from core.logging import configure_utf8_logging

configure_utf8_logging()

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--cli', action='store_true', help='Launch CLI mode (default)')
    
    # Parse just our mode flag
    args, remaining = parser.parse_known_args()
    
    if args.gui or (not args.cli and not remaining):
        # GUI mode
        from ui.main_window import main as gui_main
        gui_main()
    else:
        # CLI mode
        from cli import main as cli_main
        sys.argv = [sys.argv[0]] + remaining  # Pass remaining args to CLI
        cli_main()

if __name__ == "__main__":
    main()