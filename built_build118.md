# Bundle File Tool v2.1 Build 118 — Build Record

**Prepared:** 2026-08-29  
**Status:** Governed delivery candidate; technical gates passed  
**Release identity:** `2.1.118`

## Outcome

Build 118 establishes the corrected BFT baseline after Build 117. It delivers
the repaired **File → Settings** integration with ConfigHub, the governed
PyThermX `0.5.2` wheel, portable configuration defaults, synchronized
governance identities, and standardized Python 3.11/3.12/3.13 environments.

The candidate is technically qualified but is not a Git release commit or tag.
Repository policy reserves index, ref, commit, and tag writes for an authorized
interactive account.

## Delivered changes

- Settings delegates to ConfigHub application `bft` through a non-blocking
  launcher with single-instance focus, early-exit monitoring, diagnostics, and
  an actionable error path.
- ConfigHub registration ships through
  `.pyprojectmgr/setup_contribution.json`,
  `config/bft_settings.schema.json`, and `src/core/config_setup.py`.
- The governed configuration no longer contains workstation paths. Its
  portable `input_dir`, `output_dir`, and `relative_base_path` values are empty,
  and `session.first_launch` is restored for a new installation.
- All package-owned version sources agree on `2.1.118`.
- The manifest records the final governed-config digest, and generated module,
  schema, configuration, and static-asset identity headers reference the final
  manifest.
- PyThermX `0.5.2` Build 15 is vendored and verified from its wheel RECORD.
- Python support is explicit at `>=3.11,<3.14`, with reproducible 3.11, 3.12,
  and 3.13 test environments and a setup script that discovers registered
  interpreters and creates a real Tk root during its postflight.
- Runtime version reporting prefers package-owned `VERSION.txt` in a delivered
  source tree so stale generated egg metadata cannot report an older build.
- Integrity telemetry uses timezone-aware UTC on supported runtimes.

## Governed identities

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `9337bf8217b197e49bc4618ef50d5f334d7976dac7288e4e4181a3822ec2f7bf` |
| `.pyprojectmgr/project_manifest.json` | `362566c844a22bf697477d016e1cdfb5430db3b52d835744efc439cacbfdea53` |
| `vendor/pythermx-0.5.2-py3-none-any.whl` | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |

## Qualification evidence

| Runtime | Tk | PyThermX | Full suite | Coverage |
|---|---:|---:|---:|---:|
| CPython 3.11.9 | 8.6.12 | 0.5.2 | 1,493 passed | 89.52% |
| CPython 3.12.10 | 8.6.15 | 0.5.2 | 1,493 passed | 89.52% |
| CPython 3.13.15 | 8.6.15 | 0.5.2 | 1,493 passed | 89.52% |

## R2 staging correction — 2026-08-29

The first field staging attempt exposed an unbounded snapshot defect in
`PREP_AND_STAGE_BFT.bat`: it copied `.venv312`, `.venv313`, and `out`, then
followed junctions under generated test output. The partial snapshot grew past
206,000 files and `robocopy` returned code 9 before archive retention or
installation.

R2 makes the snapshot atomic, excludes all three supported environments and
generated output/cache trees, uses `/XJ`, and surfaces the `robocopy` diagnostic
log on failure. A real isolated snapshot/archive/stage fixture passed all 13
postconditions. One regression contract was added, so R2's installed whole-suite
gate is 1,494 tests; the production-code coverage result remains 89.52%.

All three environments passed `pip check`. The complete Settings, ConfigHub,
PyThermX, governance-identity, transport-fidelity, workspace, and Tk test
surfaces were active. Python 3.11 emitted one and Python 3.12 emitted two
non-failing Tk variable-finalizer warnings; Python 3.13 was warning-free.

## Delivery controls

The delivery archive contains one Build 118 installer and one explicit incoming
payload. The installer verifies every staged file before mutation, makes a
reversible backup, places the payload, retires superseded PyThermX wheels,
installs and verifies PyThermX in every supported environment that is present,
re-verifies installed hashes and content markers, restores Layer C read-only
protection, and runs the binding acceptance suite.

The archive SHA-256 is published in the adjacent `.sha256` sidecar. The
authorized release owner must still review the candidate and perform any Git
commit/tag action required by repository governance.
