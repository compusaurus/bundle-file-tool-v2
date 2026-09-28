# Team Communication — BFT Build 119 Responsiveness Repair

**Date:** 2026-08-29  
**From:** Paul  
**To:** Ringo, George, John, and the BFT / ConfigHub / PyThermX team  
**Subject:** Build 119 repairs the Build 118 native-workspace freeze

Team,

Build 119 is the qualified repair candidate for the Build 118 native Selection
Workspace responsiveness regression.

The regression was in the Tk presentation layer, not the selection engine,
ConfigHub Settings integration, or PyThermX. Build 118 measured every Treeview
cell to activate horizontal scrolling and populated every decision below
collapsed folders. Against BFT's remembered self-source—79,538 decisions after
generated QA output accumulated under `out`—each interaction crossed the
Python/Tcl boundary hundreds of thousands of times. That is why Windows showed
Not Responding even though the underlying I/O-free plan was valid.

Build 119 bounds column measurement, virtualizes large decision trees by folder,
limits synchronous branch rendering, and reuses the scan topology across
replans. A literal file checkbox now uses an exact-path fast path and the UI's
canonical `folder/**` checkbox scope uses an exact prefix fast path; genuinely
wildcarded overrides continue through the glob engine. Small projects retain
the complete folded tree and normal Expand all behavior. No selection or
bundle-output semantics changed.

On the exact problematic source, the post-toggle redraw fell from 1.717 seconds
to 0.104 seconds. Checkbox replan plus redraw is now about 0.49 seconds. The
initial scan remains proportional to the 79,538-path source and stays behind the
existing PyThermX progress/cancel dialog; local generated output was not silently
excluded or deleted.

Qualification is consistent across the supported matrix:

- Python 3.11.9 / Tk 8.6.12: 1,497 passed, 88.66% coverage.
- Python 3.12.10 / Tk 8.6.15: 1,497 passed, 88.66% coverage.
- Python 3.13.15 / Tk 8.6.15: 1,497 passed, 88.66% coverage.
- PyThermX 0.5.2 and `pip check`: verified clean in all three environments.

The package identity, governed configuration digest, manifest hash, and
generated governance references now agree on `2.1.119`. The delivery retains
the Build 118 ConfigHub Settings and standardized progress/environment work.

The R2 installer also handles transient Windows mapped-file copy failures. It
retries placement and may continue after a nonzero copy result only when the
installed SHA-256 already matches the staged file; otherwise it still stops
with a complete rollback. This corrects the first live staging interruption at
manifest entry 99 without weakening payload verification.

The resumed installer also did its job as a release gate: it caught an
accumulated-folder benchmark at 901 ms. The remaining cost was repeated regex
evaluation of canonical `folder/**` scopes. R2 now uses exact prefix checks for
that UI-native form, and the final live install plus the complete 3.11, 3.12,
and 3.13 matrices passed. The failed runs' recovery sets remain preserved in
the project archives for audit.

**Requested team disposition:** replace Build 118 with the Build 119 repair
candidate for baseline review. The authorized release owner should verify the
published archive checksum, install through `PREP_AND_STAGE_BFT`, and perform
the governed repository commit/tag action if accepted.

— Paul
