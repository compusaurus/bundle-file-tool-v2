#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -d "$ROOT/_bundletool_incoming" ]; then ROOT="$ROOT/_bundletool_incoming"; fi
PYTHON=${BFT_PYTHON:-}
if [ -z "$PYTHON" ]; then
    for candidate in /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
        python3.13 python3.12 python3.11 python3
    do
        if "$candidate" -c 'import sys, tkinter, ensurepip; assert (3,11) <= sys.version_info[:2] < (3,14)' 2>/dev/null; then
            PYTHON=$candidate
            break
        fi
    done
fi
if [ -z "$PYTHON" ]; then
    echo 'Install Python 3.11, 3.12, or 3.13 with Tk and venv, then run this installer again.' >&2
    exit 1
fi
exec "$PYTHON" "$ROOT/scripts/install_bft.py" "$@"
