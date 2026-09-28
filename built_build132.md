# Bundle File Tool Build 132

Release identity: `2.1.132`.

Build 132 adds fresh-folder and upgrade installation choices, a macOS installer
entry point, and the PyThermX ConfigHub tab. The Windows Linux shortcut opens
the Ubuntu-hosted browser workspace with an in-browser file chooser.
The web Source row spans the workspace and keeps its folder/file picker buttons
beside the heading. Splash styles are isolated from the workspace controls.

The native Linux application renders inside Ubuntu, but this host's stable
WSLg graphics client fails to present it on Windows. Ringo selected the browser
launcher while retaining stable WSL. No WSL preview upgrade was applied.

Release validation is recorded in
`docs/implementation/BFT_BUILD132_RELIABLE_DELIVERY_AND_SETTINGS_2026-09-20.md`.
Native macOS execution must still be qualified on a Mac; this Windows host can
verify the installer logic, shell syntax, app structure, and archive modes.
