# Build 136: macOS ConfigHub launch and governed digest verification

John reported that Build 135 on macOS showed "PyProjectMgr is unavailable.
Install its 'pyprojmgr' command, set PYPROJECTMGR_EXECUTABLE, or set
PYPROJECTMGR_PROJECT_ROOT." when opening governed settings, on an installation
where the same action had previously worked.

## Why the same installation succeeded and failed

`Bundle File Tool.app/Contents/MacOS/bft-gui` exported `PYTHONPATH` but never
`PATH`. An app launched from Finder or the Dock inherits launchd's minimal
`PATH` of `/usr/bin:/bin:/usr/sbin:/sbin`, so `shutil.which("pyprojmgr")` could
not see a console script installed by pip into Homebrew, `/usr/local/bin`,
`~/.local/bin`, a framework build or the app's own virtual environment. The
identical command resolves from Terminal, which inherits the full user `PATH`.
The launch method, not the installation, decided the outcome.

The filesystem fallback could not compensate. `config_hub_launcher` had no
macOS awareness: every branch tested `os.name == "nt"` against everything else,
and its only home-relative checkout root was the Windows-shaped
`~/Python/pyprojectmgr_project/pyprojectmgrV2`.

## Repair

After a `PATH` lookup misses, discovery now searches the conventional console
script locations: the directory of the running interpreter, which covers
`pyprojmgr` installed into BFT's own environment; `~/.local/bin`;
`/usr/local/bin`; and on macOS `/opt/homebrew/bin` together with the enumerated
per-version `bin` directories under `~/Library/Python` and
`/Library/Frameworks/Python.framework/Versions`. Versions are enumerated rather
than guessed. The fallback runs only after `PATH` misses, so Terminal and
Windows launches keep their existing resolution order, and an explicit
`PYPROJECTMGR_EXECUTABLE` still wins outright.

The sibling checkout is probed at `parents[3]` as well as `parents[4]`, mirroring
the `%ROOT%\..\..` probe the Windows installer already performs. A supplied
`HOME` is honoured so the home-relative root is testable. A POSIX virtual
environment providing `python3` without `python` is now accepted.

The failure message reports every location that was searched. The previous text
named three remedies without saying where it had looked, which is unactionable
when the command is installed but invisible.

Both app launchers prepend the runtime bin, Homebrew, `/usr/local/bin` and
`~/.local/bin` to `PATH`, so a double-clicked app matches a Terminal launch for
the process and anything it starts.

## Governed digest verification on macOS and Linux

Investigating the above surfaced a second platform defect. `module_ids`
recorded a `MANIFEST_HASH` that `.pyprojectmgr/project_manifest.json` did not
produce, and `bundle_config.json` disagreed with the `governed_config_sha256`
the manifest records.

Both files are generated on Windows with CRLF and verified byte-for-byte, but
`.gitattributes` applied `* text=auto` and excluded `*.jsonl` without excluding
`*.json`. Git normalised both to LF. A Windows checkout restores CRLF through
`core.autocrlf` and the digests validate, which is why this was invisible there.
macOS and Linux check out LF, so `ConfigManager` reported a tamper finding
against an untouched delivery on the platform under test.

Both artifacts are now marked `-text`, matching the existing `*.txt` and
`*.jsonl` rules, and carry the CRLF their digests were computed over. Line
endings do not affect JSON parsing, and the governed config is installed
read-only, so nothing rewrites either file at runtime.

The manifest contains a mis-encoded em-dash in `project_meta.description`.
Those bytes are part of the hashed content, so repairing them here would break
the recorded digest. It belongs upstream in `manifest_manager.py`, with the
hash regenerated in the same step.

## Building the delivery where PowerShell is blocked

`scripts/build_build136_delivery.ps1` follows the established per-build
generator convention. Where machine policy blocks PowerShell execution,
`scripts/build_build136_delivery.py` produces an equivalent kit using only the
standard library:

    python scripts\build_build136_delivery.py

Both write the same tree, the same `_delivery` manifests and markers (UTF-8
without BOM, CRLF, Windows path separators), and the same two-space sidecar,
so either may be staged by `PREP_AND_STAGE_BFT.bat`. `--suite-root` locates the
sibling projects if the suite is not two levels above the project root, and
`--output-directory` redirects the zip.

The Python generator was exercised end to end against stub sibling projects:
298 payload files and 9 integration files, every delivery manifest digest
verified against the archive members, no `__pycache__` or `.pyc` present, and a
sidecar whose recorded digest matches the zip.

## Regression coverage

`tests/unit/test_config_hub_launcher.py` adds seven cases: the Finder-launch
regression under a minimal `PATH`, `PATH`-first precedence, explicit-executable
precedence, the macOS directory set, exclusion of macOS paths on other
platforms, the diagnostic message naming what was searched, and a `python3`-only
virtual environment. The Finder-launch case reproduced the reported dialog
before the repair.

The digest repair is covered by the existing `test_layer_a_integrity.py` and
`test_release_contract.py` contracts, which were red on LF platforms and pass
on all platforms after the change.

Native macOS retesting is required. The launch-path defect was reproduced and
repaired against a simulated minimal `PATH` rather than on macOS hardware.
