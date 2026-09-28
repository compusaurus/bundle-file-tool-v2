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

    # Normal desktop launchers have no console. Redirect before importing the
    # Tk surface so import and construction failures are still diagnosable.
    from core.startup import begin_gui_startup
    from ui.startup_failure import show_startup_failure

    session = begin_gui_startup()
    try:
        # Bootstrap logging (best-effort, non-fatal)
        bootstrap_logging()

        # PySplashX uses Qt Multimedia while the BFT desktop uses Tkinter.
        # Its supported Tk-host integration runs the splash in an isolated,
        # short-lived process before Tk owns this process's GUI event loop.
        from core.splash import run_startup_splash
        from core.user_state import UserStateStore
        from railgun_display import ActiveDisplayResolver, create_display_driver

        launch_target = None
        try:
            launch_state = UserStateStore()
            display_driver = create_display_driver()
            if display_driver is not None:
                launch_target = ActiveDisplayResolver(
                    display_driver
                ).resolve_application_launch(
                    saved_geometry=launch_state.get(
                        "last_non_minimized_geometry", ""
                    ),
                    saved_work_area=launch_state.get("window_monitor", ""),
                )
        except (AttributeError, OSError, TypeError, ValueError):
            launch_target = None

        launch_work_area = launch_target.work_area if launch_target else None
        splash_attempt = run_startup_splash(target_work_area=launch_work_area)
        print(f"pysplashx={splash_attempt.status} {splash_attempt.detail}".rstrip())

        # Import and launch GUI. Import here so path and diagnostics exist first.
        from ui.main_window import main as gui_main
        gui_main(launch_work_area=launch_work_area)
    except BaseException as error:
        session.record_exception(error)
        show_startup_failure(
            error, session.log_path, fallback_stream=session.original_stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
