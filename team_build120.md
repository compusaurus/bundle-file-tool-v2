# Team Communication - BFT Build 120 PyThermX Protocol Repair

**Date:** 2026-08-30  
**From:** Paul  
**To:** Ringo, George, John, and the BFT / ConfigHub / PyThermX team  
**Subject:** Build 120 corrects BFT's PyThermX adapters and restores the test matrix

Team,

Build 120 is the qualified corrective candidate for the PyThermX behavior in
Build 119.

The vendored `pythermx-0.5.2` wheel is correct and byte-identical to the latest
ratified PyThermX Build 15 distribution. BFT's adapters were not honoring that
package's protocol. CLI messages were discarded, several error and cancellation
paths closed as `OK`, cancellation never reached its worker-owned terminal
state, and a fast Tk worker could finish before the pump applied its queued
updates. Tk also failed to draw explicit success and failure terminals.

Build 120 corrects those boundaries. CLI now renders service detail and true
OK/FAIL/CANCELLED outcomes. Both CLI and Tk hand the worker a cancellation token
predicate and settle the lifecycle only after core confirms cooperative stop.
Tk drains all accepted commands before finalizing, so its final geometry is the
actual final value rather than the last frame the pump happened to draw. A
renderer failure cannot mask the worker error or leave a modal grab behind.

The test strategy was upgraded from import/mocking checks to observable outcome
contracts against the real wheel and real hidden Tk widget. A focused before
gate reproduced nine failures. The repaired protocol suite passes 115 tests on
each supported interpreter, and the full matrix passes 1,505 tests on each:

- Python 3.11.9 / Tk 8.6.12 / PyThermX 0.5.2: 1,505 passed.
- Python 3.12.10 / Tk 8.6.15 / PyThermX 0.5.2: 1,505 passed, 88.43% coverage.
- Python 3.13.15 / Tk 8.6.15 / PyThermX 0.5.2: 1,505 passed.

The three environment bases were also repaired. Their program directories had
been removed while Windows still considered them installed; the exact signed
Python.org components restored the intended 3.11/3.12/3.13 matrix and the
existing virtual environments now launch normally.

There is not yet a BFT web application, so this delivery makes no web-renderer
claim. The shared `OperationProgress` contract remains renderer-neutral and is
ready for a future web adapter without coupling core to PyThermX or Tk.

**Requested team disposition:** supersede Build 119 with Build 120 for baseline
review. Verify the published archive checksum, install through
`PREP_AND_STAGE_BFT`, and reserve repository commit/tag actions for the
authorized release owner.

- Paul
