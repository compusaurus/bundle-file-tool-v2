# ============================================================================
# SOURCEFILE: __init__.py
# RELPATH: core/__init__.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Proposed
# DESCRIPTION:
#   (Content extracted from bundle)
# FIXES:
#   (If applicable, list fixes related to this file)
# ============================================================================
r"""bundle_file_tool_v2.core

Regular-package marker. Added deliberately -- do NOT delete.

WHY THIS FILE EXISTS
    Without it, "core" is a PEP 420 implicit namespace package. Python's finder
    treats a directory lacking __init__.py as a namespace PORTION and keeps
    scanning sys.path, so a REGULAR package of the same name found later wins --
    regardless of path order, and regardless of sys.path[0] being this tree.

    Measured on a developer machine (2026-08-18): an editable install
    (__editable__.legacy_video_jukebox-0.1.0.pth in site-packages) placed an
    unrelated project on sys.path. Running

        python <bft>/src/cli.py --version

    under that interpreter resolved "core" to
    C:/Users/mpw/Python/video_jukebox/video_jukebox/core and failed with
    "ModuleNotFoundError: No module named 'core.logging'". The same command under
    a clean venv succeeded. Both interpreters were Python 3.11.

    A delivery tool that can silently load another project's code is a supply
    risk, not a nuisance. Interpreter isolation flags do NOT fix it: -E and -s
    skip environment variables and the USER site directory, but the offending
    .pth lives in the MAIN site-packages; and -I additionally implies -P on
    Python 3.11+, which strips the script directory and breaks the tool outright.
    Both were tested and rejected. Making these regular packages is the only fix
    that works at the source.

NOTE
    This does not enable "python -m src.cli"; that would additionally require
    src/__init__.py and imports rewritten to src.core.*. The supported
    invocation remains:  python "<bft>/src/cli.py"

    This docstring is a RAW string. A plain docstring containing a Windows path
    such as C:\Users\... is a SyntaxError -- \U opens a unicode escape. The first
    draft of this very file hit that and was caught by the post-extraction
    functional check.
"""
