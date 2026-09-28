# BFT v2.1 Build 100 — WP0 Baseline Catalog

**Record ID:** BFT-WP0-CAT-001
**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Baseline HEAD:** `b88d67c36c4f2ff97837a0fbee24e907e691fba5`
**Candidate source:** `BFT_v2_src_build_101.txt`

## 1. Repository state at WP0 entry

- Branch: `master`
- Tracked changes: 65 files
  - 48 modified
  - 17 deleted
- Untracked files: 168
- Candidate source files matching the attached Build 101 bundle: 21 of 21

No existing changed or untracked file was deleted, overwritten, staged, or committed during the inventory.

## 2. Classification rules

| Classification | Meaning |
|---|---|
| KEEP-PRODUCT | Required production source or runtime configuration |
| KEEP-TEST | Required automated validation |
| KEEP-GOVERNANCE | Required specification, policy, manifest, catalog, or delivery control |
| MOVE | Retained content whose canonical path changed |
| RETIRE-AFTER-COVERAGE | Legacy diagnostic retained by Git history after its replacement test is proved |
| EXCLUDE-LOCAL | Local runtime state that must not enter the governed baseline |
| EXCLUDE-BACKUP | Backup copy retained locally but not committed |
| REVIEW | Cannot be committed until ownership or purpose is approved |

## 3. Tracked modified files

### KEEP-PRODUCT

- `bundle_config.json` — schema-compatible portable defaults; machine-specific recent paths and window geometry were removed during WP0.
- `src\cli.py`
- `src\core\config.py`
- `src\core\exceptions.py`
- `src\core\logging.py`
- `src\core\models.py`
- `src\core\parser.py`
- `src\core\profiles\base.py`
- `src\core\profiles\markdown_fence.py`
- `src\core\profiles\plain_marker.py`
- `src\core\validators.py`
- `src\core\writer.py`
- `src\main.py`
- `src\ui\bundle_frame.py`
- `src\ui\main_window.py`
- `src\ui\mode_manager.py`
- `src\ui\unbundle_frame.py`

The listed source files began as the Build 101 consolidated versions. WP0 then made three functional corrections in `logging.py`, `models.py`, and `writer.py` and removed trailing whitespace from six additional source files. Every delta is recorded in `WP0_SOURCE_RECONCILIATION.md`. The production test-compatibility monkeypatch in `writer.py` has been removed.

### KEEP-TEST

- `tests\conftest.py`
- all modified files under `tests\coverage_extra`
- `tests\integration\test-cli.py`
- all modified files under `tests\unit`

Most observed test diffs add governance headers or align tests with the consolidated source. Their functional correctness remains subject to the full-suite gate.

## 4. Tracked deleted files

### MOVE

- `code_catalogger_v3.py` → `scripts\code_catalogger_v3.py`
- `code_catalog_comparison_v3_3.py` → `scripts\code_catalog_comparison_v3_3.py`

The `scripts` copies include canonical-path header changes and require a functional comparison before the move is committed.

### RETIRED — REPLACEMENT COVERAGE PROVED

- `verification\harness_Binary_Safe_Roundtrip_v1.py`
- `verification\harness_Binary_Safe_Roundtrip_v2.py`
- `verification\harness_binary_detection.py`
- `verification\harness_discover_files_v1.py`
- `verification\harness_glob_filter.py`
- `verification\harness_glob_filter_v2.py`
- `verification\harness_glob_filter_v3.py`
- `verification\harness_glob_filter_v4.py`
- `verification\harness_glob_filter_v5.py`
- `verification\harness_glob_filter_v6.py`
- `verification\harness_glob_filter_v7.py`
- `verification\harness_glob_filter_v8.py`
- `verification\harness_sanitize_filename.py`
- `verification\manifest_diagnostic.py`
- `verification\manifest_diagnostic_v2.py`

These deletions are accepted for the WP0 candidate baseline. The replacement map in section 8 passed in the 474-test configured suite, and the code-catalog comparison found no lost product source.

## 5. Untracked production and test candidates

### KEEP-PRODUCT

- `src\core\bundle_integrity.py`
- `src\core\config_ids.py`
- `src\core\module_ids.py`
- `src\core\static_ids.py`
- `src\core\version.py`
- `src\database\schema_ids.py`

### KEEP-TEST

- `tests\coverage_extra\test_base_abstract_enforcement.py`
- `tests\coverage_extra\test_cli_exception_handling.py`
- `tests\coverage_extra\test_logging_edge_cases.py`
- `tests\coverage_extra\test_parser_type_errors.py`
- `tests\unit\test_bundle_integrity.py`
- `tests\unit\test_release_contract.py`

### EXCLUDE-BACKUP

- `tests\coverage_extra\test_logging_edge_cases - Copy.py.bak`

## 6. Untracked governance candidates

### KEEP-GOVERNANCE

- `.pyprojectmgr\assets.db`
- `.pyprojectmgr\project_manifest.json`
- `.pyprojectmgr\project_spec.json`
- `CP-2026-002_Change_Proposal.pdf`
- `PREP_AND_STAGE_BFT.bat` — retained as the delivery entry point; its option parser uses `%~1` with `shift`, so the previously suspected `%0` defect is not present in this candidate
- `SELECTION_MANIFEST.txt` — retained as historical selection evidence; a new WP0 reconciliation record supersedes its stale hashes
- `VERSION.txt` — package-owned installed version `2.1.102`
- `config\policies\headers\header_config_v1_0_0.json`
- `config\policies\headers\header_config_v1_1_0.json`
- `scripts\code_catalogger_v3.py`
- `scripts\code_catalog_comparison_v3_3.py`

### KEEP AS LEGACY HISTORY

- `BUILT.md`
- `TEAM.md`

These are not valid names for a new delivery.

### KEEP-GOVERNANCE — NON-ACTIVE PROPOSAL

- `config\policies\headers\proposed_header_config_v_1_1_0.json` — retained as design evidence only. It is not referenced by the project manifest and is not the active policy.
- `deny_additions.json` — retained as traceability evidence. Gate 4 is closed and all five bundle/archive patterns are synchronized in code and shipped configuration.

### EXCLUDE-LOCAL — OUT-OF-SCOPE TRANSITION AIDS

- `VALIDATE_regenerated_bundle.bat` — hard-coded to an EDSS Build 198 bundle and unsuitable as a reusable BFT baseline gate.

## 7. Local/generated exclusions

The following must not enter the governed baseline:

- `.governance_backups\`
- `.pyprojectmgr\*.bak`
- `.pyprojectmgr\project_manifest_backup_*.json`
- `.pyprojectmgr\qc_report_*.html`
- `bundle_config.json.bak`
- `config\policies\headers\*.bak`
- `logs\`
- `sessions\`
- `outputs\FIX_EVERYTHING.py`
- `tests.zip`
- `bftV2_dir.txt`
- caches, coverage output, virtual environments, and build output already covered by `.gitignore`

`outputs\FIX_EVERYTHING.py` is an emergency/one-off script and conflicts with the team's no-shims/no-one-off-delivery rule.

## 8. Legacy verification replacement map

| Retired candidate | Replacement coverage required |
|---|---|
| Binary-safe round-trip harnesses | `tests\unit\test_roundtrip.py`, profile round-trip tests, binary payload test |
| Binary detection harness | writer/binary detection unit tests |
| File discovery harness | `tests\unit\test_discovery_globfilter.py` |
| Glob-filter harnesses v1–v8 | discovery, validator, and precedence unit tests |
| Filename sanitizer harness | path/filename validator unit tests |
| Manifest diagnostics | `test_bundle_integrity.py`, parser validation tests, duplicate/nested-bundle tests |

The mapped tests pass in the configured suite. The pre-ratification comparison catalog contained all 21 entry source files and reported only the intentional removal of 13 production test-shim callables from `writer.py`; no product requirement or product callable was lost. Ringo's ratification added the governed `core/version.py`, bringing the current source set to 22 files.

## 9. Discovered governance defects

1. **Resolved:** The active header-policy file now uses the manifest path `config/policies/headers/header_config_v1_1_0.json`.
2. **Resolved:** `SELECTION_MANIFEST.txt` is retained as historical evidence; `WP0_SOURCE_RECONCILIATION.md` is the authoritative current reconciliation.
3. **Resolved:** `bundle_config.json` now contains portable recent-directory and window defaults.
4. **Resolved for validation:** The configured suite runs with the accessible Python 3.11 runtime and the project environment packages.
5. **Intentional control:** Git metadata is read-only to automated agents. An authorized interactive account must create the protected WP0 branch and baseline commit.
6. **Resolved after John and Ringo review:** `deny_additions.json` is governed traceability evidence; its five patterns are synchronized in both defaults.
7. **Verified after John review:** `.gitignore` does not exclude `.pyprojectmgr/assets.db`, `.pyprojectmgr/project_manifest.json`, `project_spec.json`, or a probe beneath `updates/`.
8. **Resolved by Ringo:** `.pyprojectmgr/project_spec.json` is required and follows the family-app governance structure.
9. **Resolved by Ringo:** Repository-awareness deferral, package-owned `2.1.102`, the deny-list default, and intentional Git separation of duties are recorded and implemented.

## 10. Catalog exit gate

The catalog, exclusion rules, active policy path, validation environment, replacement-test mapping, and full-suite gate are complete. The candidate is technically normalized and test-ready. The authoritative commit remains blocked until:

- John directly audits the routed primary records, and Gate 1 closes only after clean canonical QC or an approved bounded waiver;
- canonical pyprojectmgr QC is repaired or receives an approved written waiver;
- an authorized interactive account creates the protected branch and commit without weakening the intentional ACL.
