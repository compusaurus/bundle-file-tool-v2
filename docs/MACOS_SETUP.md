# Bundle File Tool on macOS

Build 135 includes a complete source installer for Python 3.11, 3.12, or 3.13
with Tk and venv. Use the macOS tar.gz delivery; its app executables and command
launcher have POSIX executable permissions. No physical Mac was available for
Build 133 acceptance: installation logic and shell structure are checked here,
but native Mac execution remains to be verified on the destination Mac.

Extract the archive and open INSTALL_BFT.command. If opening it does not start
Terminal, run `sh INSTALL_BFT.command` from the extracted folder. Choose a new
folder or an existing BFT folder in the installer. On macOS, Python.org framework
installations are checked before other python3 commands. A Homebrew installation
must include its matching Tk package. The base installation uses bundled wheels
without network access and automatically registers both apps in ~/Applications.

See [Installation](INSTALLATION.md) for upgrade backups, governed-settings
replacement, command-line options, and optional native video dependencies.
PyProjectMgr/ConfigEditor remain separate suite installations for ConfigHub.

Opening Bundle File Tool.app launches the native Tk workspace. Bundle File Tool
Web.app launches a local browser workspace. Both use the new installation's
.bft-runtime.txt pointer. The diagnostic launcher is in launchers/macos.

## Locations

- Native wrapper: ~/Applications/Bundle File Tool.app
- Browser wrapper: ~/Applications/Bundle File Tool Web.app
- Per-user preferences: ~/.config/bundle_file_tool/user_state.json
- Startup logs: ~/.config/bundle_file_tool/logs/startup_*.log
- Portable state: .bft_user_state.json when BFT_PORTABLE=1

`sh scripts/install_macos.sh uninstall` removes the app wrappers and retains
preferences and logs. The governed bundle_config.json stays read-only and is
not used for window geometry or startup preferences.