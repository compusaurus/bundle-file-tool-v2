#!/bin/sh
# Install into a versioned user directory; no sudo or network access required.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${BFT_PYTHON:-python3}" "$SCRIPT_DIR/install_linux.py" "$@"
