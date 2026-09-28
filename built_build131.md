# Bundle File Tool Build 131

Release identity: `2.1.131`.

The native workspace gives Source its own full-width row and places Selections,
Rules, Result set, and Operational Guidance on separate tabs. Show tabs controls
persist per user. Selections and Operational Guidance start visible; Rules and
Result set start hidden. Hiding a page preserves the current plan.

ConfigHub launch now probes candidate PyProjectMgr environments and isolates its
Python imports. An incomplete numbered environment no longer masks a working
legacy environment. The release also restores the governed BFT configuration
checksum required by ConfigHub validation.

Linux delivery includes a checksum-verifying, offline user installer, native
application-menu entry, and Windows-to-WSL desktop-shortcut installer. Releases
are installed separately, retaining prior installations.

Windows Python 3.13: 1,667 passed, 85.76% coverage. Ubuntu 24.04 Python 3.12:
1,667 passed, 85.15% coverage. ConfigHub and ConfigEditor: 30 passed.
Existing Tk teardown warnings remain non-failing (one on Windows, two on Linux).

Qualification details and machine installation paths are recorded in
`docs/implementation/BFT_BUILD131_WORKSPACE_TABS_AND_LINUX_2026-09-20.md`.

This remains a restricted internal delivery under the existing BFT license and
Crex media terms. No Git commit, tag, or external publication is part of this build.
