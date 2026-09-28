# Team Communication - BFT Build 122 Qualified for Delivery

**Date:** 2026-08-30  
**From:** Paul  
**To:** BFT, PyProjectMgr, ConfigEditor, and PyThermX team  
**Subject:** Build 122 closes the ConfigHub, public-surface, and environment baseline defects

Team,

The ratified Build 122 scope is implemented and qualified for delivery.

The ConfigHub launch is now a governed three-product contract. BFT determines
the work area of the display containing its window and identifies itself as the
requester. PyProjectMgr validates that requester against its registry and
passes a versioned payload. ConfigEditor validates the payload, places itself
before display, and shows the accurate provenance: “Requested by Bundle File
Tool • governed by PyProjectMgr.” The delivery includes and hashes all three
products' participating files; it does not assume that the sibling projects
were updated separately.

The public native UI is also complete for this baseline. Documentation,
validation, log viewing, and clipboard unbundling are functional rather than
phase placeholders. Dialogs have owners, `Ctrl+O` is real, restored geometry is
clamped to the current display topology, and public notices no longer expose
internal development promises or individual roles.

The damaged `.venv` was replaced, not repaired in place. The supported BFT
environments are now exactly `.venv311`, `.venv312`, and `.venv313`; all three
have working activation/deactivation scripts, pass dependency and compile
checks, create real Tk roots, and load PyThermX 0.5.2.

Final strict matrix:

- Python 3.11.9 / Tk 8.6.12: 1,537 passed, 87.37% branch coverage.
- Python 3.12.10 / Tk 8.6.15: 1,537 passed.
- Python 3.13.15 / Tk 8.6.15: 1,537 passed.

Warnings were treated as errors. A late Tk cleanup warning found during the
first binding run was repaired and the full matrix was rerun cleanly. The real
cross-product ConfigHub test also passed on both attached 1920×1080 displays,
including the secondary display at positive virtual-desktop coordinates.

The Build 122 installer verifies the BFT payload and seven cross-product files,
creates recovery ledgers before placement, verifies installed hashes, restores
governed configuration protection, executes the BFT binding suite, and executes
the PyProjectMgr and ConfigEditor ConfigHub acceptance tests. The ZIP is paired
with a filename-bound SHA-256 sidecar for `PREP_AND_STAGE_BFT`.

Please supersede Builds 119–121 with Build 122 for baseline review. Verify the
adjacent checksum and install through `PREP_AND_STAGE_BFT`. Git commit/tag
actions remain with the authorized interactive release owner.

— Paul
