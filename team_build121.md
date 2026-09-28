# Team Communication - BFT Build 121 Repaired Baseline Candidate

**Date:** 2026-08-30  
**From:** Paul  
**To:** Ringo, George, John, and the BFT / ConfigHub / PyThermX team  
**Subject:** Build 121 restores responsive preset changes and correct multi-display placement

Team,

Build 121 is the qualified repaired candidate for the BFT baseline.

The severe native-workspace pause was traced to preset changes performing a
complete replan synchronously on Tk's UI thread. On a real project tree that
blocked Windows message handling long enough for the application to be marked
Not Responding. Preset replanning now crosses the same worker/progress boundary
as other long operations, preserves the current plan on cancellation, and
reports its discovery and planning phases. The core replan path also reuses
resolved safety evidence, removing repeated path-resolution work.

Build 121 retains the corrected PyThermX `0.5.2` protocol from Build 120: service
messages render, progress closes with the real OK/FAIL/CANCELLED result,
cancellation is settled through the worker-owned token, and Tk drains accepted
commands before finalizing. The vendored wheel was not replaced because it was
already the current ratified artifact; the defects were in BFT's adapters.

Review Selection, Rule Editor, Review Report, the PyThermX dialog, and ConfigHub
Settings now open on the display containing the BFT window that invoked them.
The shared placement rule supports negative monitor coordinates, respects the
selected monitor's work area, and clamps oversized child windows instead of
allowing them to straddle or disappear beyond a display edge.

The complete supported matrix is green:

- Python 3.11.9 / Tk 8.6.12 / PyThermX 0.5.2: 1,520 passed, 87.74% branch coverage.
- Python 3.12.10 / Tk 8.6.15 / PyThermX 0.5.2: 1,520 passed.
- Python 3.13.15 / Tk 8.6.15 / PyThermX 0.5.2: 1,520 passed.

The three environments retain standardized activation and deactivation batch
scripts. There is still no BFT web application in this baseline; Build 121 does
not claim a web surface.

Delivery handling is also tightened. A Build ZIP is now accepted only with its
matching verified `.sha256` sidecar, and the stager moves the pair into the
archive together. The loose Build 119 and 120 checksum files can therefore be
moved from Downloads beside their already-archived ZIPs; they do not need to
remain as Downloads clutter.

**Requested team disposition:** supersede Builds 119 and 120 with Build 121 for
baseline review. Verify the adjacent checksum, install through
`PREP_AND_STAGE_BFT`, and reserve repository commit/tag actions for the
authorized release owner.

- Paul
