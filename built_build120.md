# Bundle File Tool v2.1 Build 120 - Build Record

**Prepared:** 2026-08-30  
**Status:** Governed corrective delivery; technical gates passed  
**Release identity:** `2.1.120`

## Outcome

Build 120 corrects BFT's use of the governed PyThermX `0.5.2` wheel. The wheel
was already the latest ratified Build 15 artifact and its bytes matched the
PyThermX project's published distribution. The defects were in BFT's CLI and
Tk adapters, not in the vendored package.

The candidate is technically qualified but is not a Git release commit or tag.
Repository policy reserves index, ref, commit, and tag writes for an authorized
interactive account.

## Root causes and repair

The prior adapter tests mostly proved that objects imported and channel methods
accepted calls. They did not assert the rendered terminal outcome or exercise a
fast producer against the real Tk pump. That allowed five protocol defects to
ship:

- the CLI discarded every `OperationProgress.message`;
- normal exception and plan-cancellation paths finalized an open bar as `OK`;
- BFT polled the cancellation source rather than the worker-owned token and
  never advanced `requested -> cancelling -> cancelled`;
- the Tk loop stopped when the worker finished, without draining commands still
  queued for the 40 ms pump; and
- Tk success and failure paths did not call their true terminal renderers.

Build 120 now passes event messages to the CLI renderer, provides explicit
failed and cancelled terminals, settles cancellation through the worker token,
drains every accepted Tk semantic mutation before finalization, and calls
`finish(ok=True)`, `finish(ok=False)`, or `finish_cancelled()` according to the
actual outcome. Dialog cleanup is protected even if the renderer or pump fails,
and a renderer failure cannot replace the worker's primary error.

There is no BFT web surface in this baseline, so no web PyThermX implementation
was claimed or fabricated. The renderer-neutral core event contract remains the
future web integration seam.

## Environment repair

The three BFT virtual environments initially could not start because their
registered base Python directories had been removed. The exact signed
Python.org distributions were verified, stale registrations were removed, and
the official component MSIs were installed directly after the legacy bundle
cache repeatedly lost `core.msi` during maintenance. The existing BFT virtual
environments then reattached without recreation:

| Environment | Python | Tk | PyThermX | pytest |
|---|---:|---:|---:|---:|
| `.venv` | 3.11.9 | 8.6.12 | 0.5.2 | 9.1.1 |
| `.venv312` | 3.12.10 | 8.6.15 | 0.5.2 | 9.1.1 |
| `.venv313` | 3.13.15 | 8.6.15 | 0.5.2 | 9.1.1 |

## Governed identities

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `439237016a27f874d2945b978e15e3d640c82b6711293ba75e06719519397f66` |
| `.pyprojectmgr/project_manifest.json` | `2eec6469f21638af99a5c013d825b4c8589fb6d54691d8119df1fad92a37c0b8` |
| `vendor/pythermx-0.5.2-py3-none-any.whl` | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |

## Qualification evidence

| Runtime | PyThermX protocol gate | Full suite | Coverage |
|---|---:|---:|---:|
| CPython 3.11.9 | 115 passed | 1,505 passed | matrix pass, no coverage collection |
| CPython 3.12.10 | 115 passed | 1,505 passed | 88.43% |
| CPython 3.13.15 | 115 passed | 1,505 passed | matrix pass, no coverage collection |

The focused before-state produced nine reproducible failures. All nine passed
after repair, and the tenth test covers terminal renderer failure and modal
cleanup. The binding 85% coverage floor passed. Python 3.11 and 3.12 each emit
one pre-existing, non-failing Tk variable-finalizer warning from the unrelated
workspace-dialog teardown test; Python 3.13 is warning-free.

## Delivery controls

The Build 120 archive contains one installer, this build record, the team
communication, and one explicit incoming payload. The installer verifies every
staged byte before mutation, makes a reversible backup, uses resilient
hash-checked placement, installs and verifies PyThermX in every supported
environment present, restores Layer C write protection, and runs the full suite
and coverage gate before success-only teardown.

The archive SHA-256 is published in the adjacent `.sha256` sidecar. The
authorized release owner must still review the candidate and perform any Git
commit or tag action required by repository governance.
