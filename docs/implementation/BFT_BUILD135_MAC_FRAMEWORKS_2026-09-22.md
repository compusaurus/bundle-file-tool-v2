# Build 135: Mac framework aliases and bundle producer tags

Ringo supplied a Mac Build 134 traceback from Python 3.13.15 on macOS 26.6.2.
Create Bundle failed in the pre-save integrity check with duplicate paths for
Mantle, Squirrel and ReactiveObjC frameworks. `BundleCreator.create_manifest`
resolved each symlink before calculating the stored name, converting the alias
and its target into the same manifest path. The native Save As dialog was never
reached. Earlier Linux tests used ordinary files and did not cover aliases.

## Repair and regression coverage

Discovery and manifest construction preserve lexical file names. Manifest
construction separately checks that the resolved target stays inside the base
before reading it. A symlinked source root is supported. Framework-style
`Versions/Current` links, file aliases, binary payloads and outside-root links
are exercised in `tests/integration/test_framework_aliases.py`.

The regression reproduced the supplied duplicate-path exception before the
repair. After the repair, check/create/read/extract retain all selected paths
and bytes. File aliases are stored as separate regular file payloads; this
transport does not recreate filesystem symlinks or promise an executable clone
of a Mac application package. Directory symlink traversal is unchanged.

`test_native_save_dialog_tk.py` adds a 466-file case with an additional file
alias and drives the real Linux Save As dialog through creation and verification.
It also covers small selections, required review and cancellation. Linux Tk
tests use Xvfb on Ubuntu; the separate WSLg host graphics issue is unchanged.

## Producer identification and reading diagnostics

New plain-marker and Markdown-fence headers include `bft_version=2.1.135`.
Tags are transport metadata, not extracted source content. Formatting remains
deterministic. Parsed manifests expose the producing versions, and Un-bundle
shows them after loading and integrity checking. Untagged historical bundles
remain readable and display “Producer build not recorded.” Tags are descriptive
metadata, not a signature or proof of authenticity.

Bounded-payload errors now report the entry path, declared and available byte
counts and recorded producer build. Open Bundle logs the input pathname before
reading and retains the failure traceback in startup diagnostics.

Ringo could not identify the old file that failed at line 872. Its original
bytes are unavailable, so no cause or repair is claimed for that file. Strict
payload-size checks are retained. Native Mac acceptance of Build 135 remains
pending Ringo's retest.

## Delivery

Version 2.1.135 uses the existing offline Windows/Mac fresh-folder and upgrade
installers and versioned Linux installation. Build 134 archives are retained.
Validation results and final checksums are recorded in
`dist/BUILD_135_VERIFICATION.md`.
