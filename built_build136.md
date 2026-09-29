# Bundle File Tool Build 136

Release identity: `2.1.136`.

Repairs the macOS "PyProjectMgr is unavailable" failure reported against Build
135. An app opened from Finder or the Dock inherits a minimal `PATH`, so the
pip-installed `pyprojmgr` console script was invisible to the app although the
same command resolved from Terminal. Governed settings now also search the
running interpreter's own directory, `~/.local/bin`, `/usr/local/bin`,
Homebrew, and the per-version framework and user Python `bin` directories. The
app launchers export `PATH`, so a double-clicked app behaves as a Terminal
launch does, for the app and anything it starts.

Discovery order is unchanged where it already worked: an explicit
`PYPROJECTMGR_EXECUTABLE` still wins, `PATH` is still consulted first, and the
new search runs only after `PATH` misses. Windows resolution is untouched.

When PyProjectMgr genuinely is not installed, the message now reports every
location that was searched instead of naming three remedies alone.

This build also repairs governed digest verification on macOS and Linux. The
byte-hashed project manifest and governed config were end-of-line normalised
into the repository, so their recorded SHA256 values only validated on a
Windows checkout. Both now carry the line endings their digests were computed
over and are excluded from normalisation. On macOS and Linux this removes a
tamper finding reported against an untouched delivery.

Install with `INSTALL_BFT.command` on Mac or `INSTALL_BFT.cmd` on Windows.
Both offer a fresh folder or upgrade with backups. Linux delivery and the
stable WSL browser launcher are retained.

Native Mac retesting is required. The launch-path defect was reproduced and
repaired against a simulated minimal `PATH`, not on macOS hardware.

See [the implementation record](docs/implementation/BFT_BUILD136_MACOS_CONFIGHUB_LAUNCH_2026-09-29.md).
