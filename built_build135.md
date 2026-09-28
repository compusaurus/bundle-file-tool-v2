# Bundle File Tool Build 135

Release identity: `2.1.135`.

Repairs the Mac Create Bundle failure reported against Build 134. Framework
file aliases retain their selected relative names while their resolved targets
are checked for containment and read. Distinct aliases no longer collapse into
duplicate manifest paths during the integrity check before Save As.

New plain-marker and Markdown-fence bundles record `bft_version` in their
transport metadata. Un-bundle shows the producing build; older bundles whose
build was not recorded are labeled accordingly. Read errors identify the input
file, failing entry and declared/available byte counts, and persist a traceback
in the startup log.

The reported old bundle with a size error at line 872 was not identifiable, so
its cause remains unverified. Size validation remains strict; this build does
not silently repair or truncate damaged input.

Install with `INSTALL_BFT.command` on Mac or `INSTALL_BFT.cmd` on Windows.
Both offer a fresh folder or upgrade with backups. Linux delivery and the stable
WSL browser launcher are retained. Native Mac retesting is required; the same
framework-link failure has been reproduced and repaired on Windows and Ubuntu.

See [the implementation record](docs/implementation/BFT_BUILD135_MAC_FRAMEWORKS_2026-09-22.md).
