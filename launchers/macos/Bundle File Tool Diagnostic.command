#!/bin/sh
set -eu

LAUNCHER_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BFT_ROOT=$(CDPATH= cd -- "$LAUNCHER_DIR/../.." && pwd)
RUNTIME_DIR=".bft-uninstalled"
if [ -f "$BFT_ROOT/.bft-runtime.txt" ]; then RUNTIME_DIR=$(sed -n '1p' "$BFT_ROOT/.bft-runtime.txt"); fi
PYTHON=""
for candidate in \
    "$BFT_ROOT/$RUNTIME_DIR/bin/python" \
    "$BFT_ROOT/.venv313/bin/python3" \
    "$BFT_ROOT/.venv313/bin/python" \
    "$BFT_ROOT/.venv312/bin/python3" \
    "$BFT_ROOT/.venv311/bin/python3"
do
    if [ -x "$candidate" ]; then PYTHON="$candidate"; break; fi
done
if [ -z "$PYTHON" ]; then PYTHON=$(command -v python3 || true); fi
if [ -z "$PYTHON" ]; then echo "[FAIL] Python 3 was not found."; exit 1; fi

export BFT_DIAGNOSTIC=1
export PYTHONPATH="$BFT_ROOT/src"
cd "$BFT_ROOT"
exec "$PYTHON" "$BFT_ROOT/src/main.py"
