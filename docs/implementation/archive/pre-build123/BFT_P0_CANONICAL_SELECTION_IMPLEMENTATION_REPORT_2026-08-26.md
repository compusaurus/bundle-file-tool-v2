# BFT P0 Canonical Selection Implementation Report — 2026-08-26

**Lead Developer:** Paul  
**For:** Ringo, George, and John  
**Status:** Implemented and full-suite verified  
**Release identity:** Working-tree successor to 2.1.116; no version bump, commit, or release tag was made

## 1. Objective

Close the two critical findings from the Build 115/116 review:

1. every bundle-producing adapter must use the canonical `SelectionService` plan, including default/flagless CLI and classic GUI paths;
2. a successful artifact must match the approved selection plan exactly, with no silent deletion, oversize, read-error, containment, or writer-omission drift.

The work also closes the directly related workspace clipboard integration failure and unreadable-directory warning serialization gap.

## 2. Implemented behavior

### One selection authority

- Removed `_SELECTION_FLAGS` and `_uses_selection_workspace()` from `src/cli.py`.
- Removed the flagless legacy `BundleCreator` branch from the CLI.
- Every `bundle` invocation now plans first and executes that exact plan.
- `BundleToolService.create_bundle(plan=None)` now creates a canonical plan rather than invoking legacy discovery.
- Migrated governed classic `BundleFrame` scanning, preview, file publication, and clipboard publication onto `BundleToolService`.
- Added a structural acceptance gate preventing CLI, classic GUI, or workspace GUI adapters from constructing `BundleCreator`.

### Plan-time emission eligibility

- Added the effective maximum file size to the plan inputs.
- Oversize wanted files become visible `State.SKIPPED` decisions with code `SKIPPED_OVERSIZE`.
- Outside-base, unsafe-relative, unresolved/outside-symlink, missing-metadata, and active-output inputs become non-overridable Priority 0 blocks.
- Added `--max-size` to the `plan` command so an operator can preview the same limit used by `bundle`.
- Kept checkbox replans I/O-free by carrying immutable emission eligibility through incremental Layer 1 replans.

### Strict plan-to-artifact reconciliation

- Added `PlanDriftError`, a typed validation failure that instructs the operator to re-plan.
- Planned creation checks every included file immediately before reading:
  - metadata record exists;
  - normalized path is safely relative;
  - resolved path remains inside the approved base;
  - active output is not also an input;
  - path remains a regular file;
  - size and nanosecond modification time match the reviewed snapshot.
- The same snapshot check runs again after the writer finishes reading.
- Writer skips are forbidden for planned creation.
- Manifest paths, order, and recorded sizes must equal the approved emission list.
- Any mismatch fails before formatting is published.

### Atomic artifact publication

- Bundle output is written to a temporary file in the destination directory.
- Content is flushed and synchronized before `os.replace()` publishes it.
- A failed replacement removes the temporary file and preserves an existing artifact.
- Publication failures are surfaced as `BundleWriteError`.

### Adapter integration

- Implemented `SelectionWorkspaceFrame.copy_to_clipboard()`.
- The main-window Copy Bundle menu now has a valid workspace implementation.
- Clipboard output is re-executed and reconciled through the service instead of copying an unchecked stale preview.

### Metadata error handling

- `os.walk` errors are converted to stable strings rather than storing raw, non-JSON-serializable `OSError` objects.
- An unreadable directory becomes visible `Unknown` plan evidence.
- A single-file stat failure also becomes `Unknown` with a serializable warning.

## 3. Acceptance coverage added

The new/strengthened tests cover:

- flagless default `bundle` manifest equals flagless default `plan` exactly;
- default CLI and direct service calls exclude a signature-detected `.venv312` tree;
- deleted and changed planned files fail without publication;
- an injected writer omission is rejected before publication;
- oversize files are visible `Skipped` decisions and do not surprise the writer;
- outside-base sources are Priority 0 blocks during planning;
- an existing active output is blocked during planning;
- atomic replacement failure preserves the previous artifact and leaves no temporary file;
- unreadable-directory warnings are strings, JSON-serializable, and represented in `unknown`;
- adapters do not construct the legacy creator;
- workspace clipboard output is produced from the reconciled workspace plan;
- the canonical metadata scan's determinate progress total represents files scanned, including excluded files needed for explanation.

## 4. Verification result

Repository virtual environment:

```text
1416 passed in 94.98s
Required coverage: 85.0%
Actual coverage: 90.77%
Skipped tests: 0
```

Additional verification:

```text
python -m compileall -q src tests
compileall=PASS
```

Focused suites also passed:

- 112 canonical CLI/service/planning tests;
- 199 expanded metadata/parity/classic-adapter tests;
- 129 reconciliation/atomic-publication/workspace tests;
- SEL-PERF-005 passed after removing filesystem resolution from incremental checkbox replans.

## 5. Files changed in this implementation slice

Production:

- `src/cli.py`
- `src/cli_plan.py`
- `src/core/exceptions.py`
- `src/core/metadata_scan.py`
- `src/core/service.py`
- `src/ui/bundle_frame.py`
- `src/ui/selection_workspace.py`

Tests:

- `tests/integration/test_cli_plan.py`
- `tests/integration/test_cross_surface_parity.py`
- `tests/integration/test_service_facade.py`
- `tests/integration/test_workspace_dialogs_tk.py`
- `tests/unit/test_metadata_scan.py`
- `tests/unit/test_service_planning.py`

Documentation:

- `docs/implementation/BFT_P0_IMPLEMENTATION_BASELINE_2026-08-26.md`
- this report

No source or test file outside this list was edited during the P0 slice. No user changes were staged, committed, reverted, or deleted.

## 6. Post-change SHA-256 ledger

| SHA-256 | File |
|---|---|
| `A2BD66F81FC98FE3F6ACA23A89B727629DF30D13190FF6C824BC786902D4047A` | `src/cli.py` |
| `A1BEADCECD0B8E6F87E9F380367ADDE942D542B48CECF1C1BB0DE2F9FDC4369B` | `src/cli_plan.py` |
| `6D178992A188265C8708E285A99DEC006B6C73273F4CB96243F1AE918B9A97E5` | `src/core/service.py` |
| `883284EAFC0395320AF6C407D069375716B9AF1358E8322793ED54AF85C35657` | `src/core/metadata_scan.py` |
| `C1CD4BD210BE49792303330B749E71B6950DD6DE05DB2512D1B665429E139474` | `src/core/exceptions.py` |
| `CF2EBB5ECC0B942AC50C8CF5E8E62D0A108B1D1C210F829C73E07B35E31377D7` | `src/ui/bundle_frame.py` |
| `6CDF81754E66E2078DB8B84C96815ADC2815920F0B66FDFEC6F80A5BAC2430ED` | `src/ui/selection_workspace.py` |
| `C974AC804173D6F115662109E38572ED0F7FCB7F16BA1A342D5613814787BCD5` | `tests/integration/test_cli_plan.py` |
| `383444C7BE3C9A0856BE9220940DC858BCAD39A07475DE949778A83B50873000` | `tests/integration/test_cross_surface_parity.py` |
| `F1969CDC25F8431B8712AB043DEBCDAA0859825C4EA6BBFBE9BCC6CA3927CBFA` | `tests/integration/test_service_facade.py` |
| `74D5DB382A8AD4B3627E9A6A683662573B234BADB8204DB0794C4DDB20E06AB4` | `tests/integration/test_workspace_dialogs_tk.py` |
| `6F728CCFA55E49F66044D42328B4B74361DC1FC16152A84CBB81C53421EF8FA7` | `tests/unit/test_metadata_scan.py` |
| `9F4286B851719510FE25FB675F5012E0589E3B7C43518F907ED384723A0B99E0` | `tests/unit/test_service_planning.py` |

## 7. Closed and remaining review findings

Closed by this slice:

- `BFT115-GAP-001` — default bundle bypassed canonical selection;
- `BFT115-GAP-002` — plan/artifact drift from deletion, oversize, and silent writer skips;
- `BFT115-GAP-008` — outside-base/active-output safety was deferred to the writer;
- `BFT115-GAP-014` — workspace Copy Bundle menu called a missing method;
- `BFT115-GAP-015` — unreadable-directory warning could break JSON serialization.

Partially improved:

- release provenance now has pre/post checksum ledgers, but the dirty working tree is still not an immutable release;
- artifact publication is atomic, but a clean release artifact/tag is still required;
- the model performance gate remains green, but the separate real-Tk whole-widget refresh issue remains open.

Next implementation priorities:

1. make the governed configuration pass full schema validation and add installer/startup validation;
2. publish and implement the formal Revision 1.1 rule schema and migration;
3. complete accessibility/focus retention and incremental/virtualized Tk rendering;
4. close the nested-header basename edge;
5. establish a clean tagged release candidate before any deployment.

## 8. Review links

- [Pre-change baseline](BFT_P0_IMPLEMENTATION_BASELINE_2026-08-26.md)
- [Original GAP register](../analysis/build115/BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Recommendations](../analysis/build115/BFT_BUILD115_RECOMMENDATIONS.md)
