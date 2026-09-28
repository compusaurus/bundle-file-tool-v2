#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BFT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SOURCE_APP="$BFT_ROOT/launchers/macos/Bundle File Tool.app"
SOURCE_WEB_APP="$BFT_ROOT/launchers/macos/Bundle File Tool Web.app"
APPLICATIONS_DIR="$HOME/Applications"
TARGET_APP="$APPLICATIONS_DIR/Bundle File Tool.app"
TARGET_WEB_APP="$APPLICATIONS_DIR/Bundle File Tool Web.app"

case "${1:-install}" in
    uninstall)
        if [ "$(dirname -- "$TARGET_APP")" != "$APPLICATIONS_DIR" ] || \
           [ "$(basename -- "$TARGET_APP")" != "Bundle File Tool.app" ]; then
            echo "Refusing unexpected uninstall target: $TARGET_APP" >&2
            exit 1
        fi
        if [ "$(dirname -- "$TARGET_WEB_APP")" != "$APPLICATIONS_DIR" ] || \
           [ "$(basename -- "$TARGET_WEB_APP")" != "Bundle File Tool Web.app" ]; then
            echo "Refusing unexpected uninstall target: $TARGET_WEB_APP" >&2
            exit 1
        fi
        rm -rf -- "$TARGET_APP"
        rm -rf -- "$TARGET_WEB_APP"
        echo "Removed $TARGET_APP and $TARGET_WEB_APP"
        echo "Per-user state and logs were retained under ~/.config/bundle_file_tool."
        exit 0
        ;;
    install|upgrade) ;;
    *) echo "Usage: $0 [install|upgrade|uninstall]" >&2; exit 2 ;;
esac

mkdir -p -- "$APPLICATIONS_DIR"
if [ -e "$TARGET_APP" ]; then
    rm -rf -- "$TARGET_APP"
fi
cp -R -- "$SOURCE_APP" "$TARGET_APP"
if [ -e "$TARGET_WEB_APP" ]; then
    rm -rf -- "$TARGET_WEB_APP"
fi
cp -R -- "$SOURCE_WEB_APP" "$TARGET_WEB_APP"
mkdir -p -- "$TARGET_APP/Contents/Resources"
mkdir -p -- "$TARGET_WEB_APP/Contents/Resources"
printf '%s\n' "$BFT_ROOT" > "$TARGET_APP/Contents/Resources/bft-root.txt"
printf '%s\n' "$BFT_ROOT" > "$TARGET_WEB_APP/Contents/Resources/bft-root.txt"
chmod 755 "$TARGET_APP/Contents/MacOS/bft-gui"
chmod 755 "$TARGET_WEB_APP/Contents/MacOS/bft-web"
chmod 755 "$BFT_ROOT/launchers/macos/Bundle File Tool Diagnostic.command" 2>/dev/null || true
echo "Installed $TARGET_APP and $TARGET_WEB_APP"
echo "Normal launch is windowless; use the Diagnostic launcher for Terminal output."
