# Team Communication — BFT Build 118 Delivery Candidate

**Date:** 2026-08-29  
**From:** Paul  
**To:** Ringo, George, John, and the BFT / ConfigHub / PyThermX team  
**Subject:** Build 118 is technically qualified and packaged for release-owner review

Team,

Build 118 is the new governed BFT delivery candidate. It replaces the proposed
Build 117 baseline rather than reusing that historical identity.

The release-blocking Settings issue is resolved: **File → Settings** now invokes
the registered ConfigHub workflow for BFT, reports startup failures, and leaves
the BFT interface responsive. The ConfigHub schema, setup contribution,
validation hook, and governed transaction contract are part of the delivery.

The candidate also integrates the sealed PyThermX `0.5.2` Build 15 wheel and
standardizes the supported desktop matrix on CPython 3.11, 3.12, and 3.13. Each
environment now proves an operational Tk root, PyThermX `0.5.2`, and a clean
dependency graph. The setup script discovers registered per-user interpreters
when explicit paths are not supplied, while retaining explicit parameter and
environment-variable overrides for controlled build hosts.

The governed baseline has been corrected. Developer machine paths were removed
from the shipped configuration, the package identity was advanced to
`2.1.118`, the configuration digest and manifest hash were recalculated from
final bytes, and generated governance references were synchronized. The
previously excluded governance identity assertion is now green and is included
in the binding suite.

Qualification results are consistent across all supported runtimes:

- Python 3.11.9: 1,493 passed, 89.52% coverage.
- Python 3.12.10: 1,493 passed, 89.52% coverage.
- Python 3.13.15: 1,493 passed, 89.52% coverage.

## R2 delivery correction

The initial field stager attempted to snapshot the additional Python
environments and generated `out` tree, including junctions. It stopped safely
with `robocopy` code 9 before retention or installation, but produced a very
large partial same-build snapshot.

R2 replaces that snapshot step with an atomic candidate and excludes `.venv`,
`.venv312`, `.venv313`, `out`, caches, and junctions. The repaired sequence
passed an isolated end-to-end fixture, and the added regression contract raises
the installed suite to 1,494 tests at the same 89.52% production-code coverage.
- `pip check`: clean in all three environments.
- Tk: operational on all three environments.
- PyThermX: `0.5.2` on all three environments.

The Build 118 archive, checksum sidecar, payload manifest, markers, installer,
and build record have been prepared for release-owner review. No automated Git
index, commit, ref, or tag write was attempted; those actions remain assigned
to the authorized interactive account under the repository's separation-of-
duties policy.

**Requested team disposition:** review the delivered candidate and checksum,
then have the authorized release owner perform the governed repository release
action if accepted.

— Paul
