# BFT v2.1 Build 100 — WP0 Validation Report

**Record ID:** BFT-WP0-VAL-001
**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Last updated:** 2026-07-24
**Candidate baseline:** Working tree based on `b88d67c36c4f2ff97837a0fbee24e907e691fba5`

## 1. Outcome

The normalized WP0 candidate passes the complete configured automated quality gate:

- **Tests:** 480 passed, 0 failed
- **Coverage:** 88.49%
- **Required coverage:** 85%
- **Runtime:** Python 3.11.5
- **Test runner:** pytest 9.0.2
- **Coverage runner:** pytest-cov 7.1.0
- **Elapsed test time:** 7.90 seconds

This is a green supplemental technical baseline. Ringo's decisions are implemented. John accepted the substantive evidence as represented on 2026-07-24 but kept Gate 1 conditional on a clean canonical QC run or a named, scoped, time-bounded waiver. The authorized interactive commit remains a separate publishing control.

## 2. Entry-state failure baseline

The first complete normalized test run produced:

- 455 passed
- 19 failed

The failures fell into four groups:

1. Tests encoding obsolete behavior or malformed assertions.
2. Duplicate module identities caused by mixing `core`/`cli` imports with `src.core`/`src.cli`.
3. Real structured-logging contract defects.
4. A production `builtins.all` monkeypatch and helper classes added solely to accommodate a bad test assertion.

No failure was suppressed or waived.

### Test-count accounting requested by John

| Step | Collected pytest items | Arithmetic |
|---|---:|---|
| WP0 candidate entry run | 474 | 455 passed + 19 failed |
| Retired legacy verification files | 0 | The 15 files were standalone scripts under `verification/`; `pytest.ini` limits collection to `tests/`. |
| Pytest items added or deleted during normalization | 0 | Existing tests were corrected or had imports normalized; no collected test item was removed or added. |
| Pre-ratification configured run | 474 | 474 entry items - 0 retired pytest items + 0 net-new items |
| Ringo decision contract tests | +6 | Version parity, deny-list parity, project-spec ACL policy, manifest-ID hash parity, non-incrementing stager, and CLI version reporting |
| Post-ratification configured run | 480 | 474 + 6 |

The replacement map refers to executable coverage already collected under `tests/`, not to a claim that each retired standalone script became a newly added pytest item. This preserves the item count while replacing informal/manual diagnostics with governed automated coverage.

## 3. Corrections applied and defect traceability

### Production corrections

- Removed the `builtins.all` monkeypatch and its compatibility-only classes from `src/core/writer.py`.
- Enabled strict Base64 input validation in the writer.
- Restored documented completion and error fields in `src/core/logging.py`.
- Made logging-directory fallback safe when the platform temp-directory lookup fails.
- Enforced non-null, non-empty, non-whitespace paths in `src/core/models.py`.

### Test corrections

- Replaced the malformed `all(boolean)` assertion with the intended length assertion.
- Standardized tests on the canonical `core` and `cli` import paths.
- Updated obsolete exception expectations to the actual public contracts.
- Updated empty-path tests to assert the model invariant at construction time.
- Aligned the blank Markdown-fence encoding expectation with UTF-8 normalization.

### Three functional source corrections

| Defect ID | Source | Before WP0 | After WP0 | Executable evidence |
|---|---|---|---|---|
| `BFT-WP0-DEF-001` | `src/core/writer.py` | Production code replaced process-wide `builtins.all`, wrapped `files_written` in test-only proxy classes, and decoded Base64 without strict alphabet validation. | Uses a normal `list[Path]`, never mutates Python builtins, corrects the malformed assertion, and decodes string payloads with `validate=True`. | `tests/unit/test_writer.py::TestExtractManifest::test_extract_tracks_operations`; `tests/coverage_extra/test_writer_failures.py::test_write_entry_binary_bad_base64_raises`; writer contract suite. |
| `BFT-WP0-DEF-002` | `src/core/logging.py` | Log setup could exhaust its filesystem fallbacks when platform temp discovery failed; completion/error call forms did not consistently emit the documented nested counts and canonical error fields. | Guards every fallback including temp discovery, permits memory-only logging, and always emits `counts`, `checksumsVerified`, `elapsedMs`, `errorMessage`, `errorType`, and `filePath` while retaining reader compatibility fields. | `tests/coverage_extra/test_logging_edge_cases.py`; `tests/unit/test_logging.py::TestOperationLogging::test_log_operation_complete`; logging error-schema and full-cycle tests. |
| `BFT-WP0-DEF-003` | `src/core/models.py` | `BundleEntry` could be constructed with a null, empty, or whitespace-only path, deferring failure and weakening manifest invariants. | Construction raises `ValueError("path cannot be empty")` before normalization or manifest use. | `tests/unit/test_models.py::TestBundleEntry::test_empty_path_raises_error`; `tests/coverage_extra/test_base_abstract_enforcement.py::TestManifestValidationEdgeCases::test_validate_manifest_with_missing_required_fields`. |

## 4. Source and legacy-asset preservation

The attached Build 101 source artifact contained 21 source files, and all 21 matched the live tree at WP0 entry. After normalization:

- 12 files remain identical to the attachment after line-ending and terminal-newline normalization.
- 9 files have intentional, recorded WP0 changes: three functional corrections and six whitespace-only cleanups.
- The pre-ratification catalog still contained all 21 entry source files.
- Ringo's decision implementation added `src/core/version.py`, bringing the governed source set to 22 files.
- Product callables were preserved.
- The only removed callables were 13 functions/methods belonging to the writer's production test-compatibility shims.

The mapped replacement tests for the retired legacy verification harnesses pass as part of the 480-test suite. Their removal therefore has a documented, executable replacement rather than relying on absence alone.

## 5. Configuration and governance validation

- Machine-specific recent directories and saved window geometry were removed from `bundle_config.json`.
- The governed first-launch state was restored to `true`.
- The active header-policy filename now matches `.pyprojectmgr/project_manifest.json`.
- Duplicate values were removed from the header policy's `status_values` list, and its recognized keywords now agree with its governed `DESCRIPTION` and transition `LIFECYCLE` keys.
- Local backups, logs, sessions, generated output, and emergency scripts are excluded by `.gitignore`.
- The EDSS-specific validation batch file remains a local exclusion.
- `deny_additions.json` is governed traceability evidence. Its five archive/bundle patterns are synchronized in `ConfigManager.DEFAULT_CONFIG` and shipped `bundle_config.json`.
- The alternate proposed header policy is retained as non-active design evidence; only the manifest-selected policy governs WP0.
- `git check-ignore --no-index` confirms that `.pyprojectmgr/assets.db`, `.pyprojectmgr/project_manifest.json`, `.pyprojectmgr/project_spec.json`, and a probe beneath `updates/` are not excluded.
- Required `.pyprojectmgr/project_spec.json` follows the family-app structure and records the intentional host-ACL separation-of-duties policy.
- Package metadata, `VERSION.txt`, shipped configuration, project spec, manifest metadata, UI, CLI, and generated headers resolve to installed version `2.1.102`.
- The stager no longer increments `VERSION.txt`; the package owns the installed value.

## 6. QC vocabulary and canonical-QC disposition

The WP0 checks below are supplemental evidence. They are not renamed substitutes for the four canonical pyprojectmgr QC checks.

| WP0 evidence name | Canonical relationship | Classification |
|---|---|---|
| Governed JSON parsing | Supports contract adherence by proving governed JSON is syntactically loadable. | Supplemental preflight |
| Active header-policy path | Supports lifecycle compliance and contract adherence by proving the manifest-selected policy resolves. | Supplemental preflight |
| Code-catalog source preservation | Supports signature drift and orphan detection by comparing source/module inventories. | Supplemental catalog evidence |
| Product callable preservation | Supports signature drift and contract adherence by comparing callable identities/signatures. | Supplemental catalog evidence |
| pytest and coverage gate | Exercises product behavior; it is not a pyprojectmgr governance rule. | Supplemental product validation |

Canonical `pyprojmgr qc --strict` was attempted on 2026-07-23. The live invocation attempted auto-remediation and rewrote generated `schema_ids.py` before failing on Windows console encoding. The exact pre-invocation WP0 file was immediately restored and verified by SHA256: `b2db1b55cc0e12d9822805c75c0616b0f9df1712bebc0b881a4ed1a0ed82fe57`.

QC was then rerun against a disposable mirror with UTF-8 forced. Artifact generation completed, but pyprojectmgr still reported non-stabilizing schema drift and aborted before returning lifecycle compliance, signature drift, contract adherence, or orphan-detection results. Therefore:

- canonical QC is **TOOL-BLOCKED**, not passed;
- no canonical rule result is inferred from the supplemental WP0 evidence;
- the live BFT source was restored and the mutating QC path will not be rerun against it;
- the pyprojectmgr remediation/idempotence defect requires a separate correction or an approved waiver before authoritative WP0 closure.

The blocker is tracked as `BFT-WP0-QC-001` in `WP0_CANONICAL_QC_BLOCKER_BFT-WP0-QC-001.md`. The earlier execution environment did not persist the full July 23 console transcript or installed-distribution version. Those omissions are now explicit evidence gaps; neither is reconstructed or represented as captured output.

## 7. Coverage observation

Overall coverage passes the gate. `src/main.py` remains uncovered by unit tests because it is a thin application entry point; this is not a WP0 failure, but later UI/application bootstrap testing should address it.

## 8. Reproduction command

From the repository root, with the project environment packages and `src` on `PYTHONPATH`:

```powershell
C:\ProgramData\Anaconda3\python.exe -m pytest
```

The repository's configured pytest options perform the coverage measurement and enforce the 85% threshold.

## 9. Exit status

| Gate | Status |
|---|---|
| Candidate source reconciled | PASS |
| No production test shim | PASS |
| Full configured suite | PASS |
| Coverage threshold | PASS |
| Legacy harness replacement map | PASS |
| Portable governed configuration | PASS |
| Active header-policy path | PASS |
| Local/generated exclusions | PASS |
| Governed-path ignore check | PASS; required `.pyprojectmgr/project_spec.json` present and not ignored |
| Canonical pyprojectmgr QC | TOOL-BLOCKED before rule results |
| Gate 1 baseline acceptance | GEORGE RATIFIED; JOHN CONDITIONAL — REQUIRES CLEAN CANONICAL QC OR BOUNDED WAIVER |
| Gates 2–4 | CLOSED BY RINGO; IMPLEMENTED |
| Gates 5–6 | CLOSED |
| Required project specification | PASS |
| Package-owned `2.1.102` contract | PASS |
| Safety deny-list synchronization | PASS |
| Protected WP0 branch and commit | REQUIRES AUTHORIZED INTERACTIVE ACCOUNT BY POLICY |
