# Team Communication — BFT Build 117 Release-Gate Disposition

**Date:** 2026-08-27  
**From:** Paul, Lead Analyst  
**To:** Ringo, George, John, and the BFT / ConfigHub team  
**Subject:** Engineering corrections complete; Build 117 remains on governance hold

Team,

I treated John's release-gate review as evidence to investigate, not as authority to change governed release state. I reproduced the reported failures, corrected the engineering defects and fragile tests that were in scope, and left the governed configuration and generated governance IDs untouched because their final state requires an explicit owner/architect decision.

## Disposition

**Build 117 remains HOLD.** The application and UAT corrections are now in good shape, including the Settings launch repair, but the live governed baseline no longer matches the approved Build 117 identity. We should prepare an RC2/hotfix candidate only after the baseline is explicitly restored or revised and approved.

## Actions completed

1. **Settings / ConfigHub launch repaired.** BFT's **File → Settings** command now delegates to the governed ConfigHub workflow for application `bft`, launches it without blocking the BFT UI, focuses an already-running instance, monitors early startup failure, writes a diagnostic log, and shows an actionable error instead of failing silently. The launcher and Settings command tests pass.

2. **Source byte fidelity closed end to end.** Source files are read once as bytes and classified against the complete stream. Valid UTF-8 is decoded strictly; NUL-bearing or non-UTF-8 data is losslessly base64-transported when policy permits and fails closed otherwise. LF, CRLF, CR, mixed endings, empty files, missing final newlines, trailing blank lines, UTF-8 boundary characters, and late non-UTF-8 bytes are covered.

3. **Bundle transport no longer rewrites payload newlines.** Bundle ingress preserves decoded transport characters instead of applying universal-newline translation. Bounded plain-marker blocks use their source-size metadata to remove only formatter padding. CLI bundle output is written as raw UTF-8 bytes so Windows stdout translation cannot corrupt CRLF payloads.

4. **Build 117 desktop UAT gaps corrected.** Nested folder expanders now populate lazily; all workspace horizontal scrollbars activate under overflow; window identity derives from `2.1.117`; and Open Bundle remembers its own last folder in per-user state without writing operator paths into governed configuration.

5. **Tests made independent of workstation configuration.** Layer A copies governed files as bytes. The CLI missing-output test now supplies an empty-output fixture instead of inheriting the shipped config. File-artifact comparisons use bytes where text-mode newline translation would invalidate the assertion. The Open Bundle UAT now verifies the persisted value rather than requiring a redundant write of the same value.

6. **Local release hygiene improved.** `.gitignore` now covers `.pyprojectmgr/*.db`, QC JSON reports, `out/`, `demo.txt`, and `cli_matrix_results.json`. No user artifacts were deleted.

## Verification evidence

- **Build 117 UAT:** `25 passed, 0 failed, 0 errors`. Evidence: `out/build117_user_acceptance_20260826/run_20260827_212922/uat_results.json`.
- **Focused regression set:** `219 passed`.
- **Broad BFT suite, excluding the unresolved governance-ID assertion and external PyThermX subprocess checks:** `1,394 passed, 1 deselected`, coverage `88.86%` on Python 3.13.15.
- **Original three reported failures:** Layer A and CLI output-contract tests now pass. The governance-ID contract remains red by design until the baseline decision is made.
- **Settings coverage:** `test_config_hub_launcher.py` and `test_config_hub_settings_command.py` pass within the broad suite.

The repository's Python 3.11 virtual environment points to a removed interpreter. The complete canonical command therefore has not yet been re-certified in the approved 3.11 environment. A full run under Python 3.13 was attempted, but the cross-project PyThermX subprocess checks did not terminate and were stopped; they are excluded from the `1,394 passed` result above. This is a release-environment action, not evidence of a BFT functional failure.

## Governance state left unchanged

| Governed item | Approved Build 117 identity | Live identity |
|---|---|---|
| `bundle_config.json` | `5cf84eb590925f68…` | `47a37683f0106ecdbba61e5740cd6d1eb0a4ca3f25d87ecb717a7be876166e8e` |
| `.pyprojectmgr/project_manifest.json` | `4e63bb7ea1541432…` | `940435717fe42da7ee6b1f890da9c3efd430e0467b6821f083e1ee2f9e583612` |
| Generated `MANIFEST_HASH` | `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b` | Still approved value; does not match live manifest |

The live config and manifest are internally consistent with one another, but they are outside the approved release record. The live config also contains workstation paths under `global_settings`:

- `input_dir = C:/Users/mpw/Python`
- `output_dir = C:/Users/mpw/Python/bundles`
- `relative_base_path = C:/Users/mpw/Python`

Those paths must not ship. I did not restore, revise, reformat, or re-hash either governed file, and I did not regenerate governance IDs.

## Decisions required from Ringo and George

Choose one governed-baseline path:

1. **Restore the approved Build 117 baseline**, preserving the approved byte/newline convention; or
2. **Authorize a revised ConfigHub baseline**, after removing workstation paths, deciding the governed LF/CRLF convention, and approving an exact diff.

After that decision:

1. Finalize `bundle_config.json` and `.pyprojectmgr/project_manifest.json` as one governed transaction.
2. Regenerate `module_ids.py` and `schema_ids.py` only from the final approved manifest.
3. Obtain explicit ConfigHub Phase 0 authorization/signatures.
4. Repair or recreate the approved Python 3.11 release environment.
5. Run the complete canonical suite, all PyThermX integration checks, Build 117 UAT, and installer/clean-machine gates.
6. Resolve public-release licensing/README disposition.
7. Have the authorized interactive account perform the clean release commit and tag.

## Cross-project ConfigHub pattern

BFT should be the reference implementation for incorporating Settings across the project portfolio:

- Each application registers a stable ConfigHub application key and makes **Settings** invoke `pyprojmgr setup --application <key>` through a small non-blocking adapter.
- Governed configuration contains only portable policy/defaults. Recent folders, window geometry, and other operator preferences live in per-user state.
- ConfigHub writes governed config and manifest as one auditable transaction with deterministic serialization, newline policy, backup/receipt, and before/after digests.
- Generated IDs are refreshed only after the final manifest is approved.
- Every project adopts the same launcher, early-exit, diagnostic, read-only Layer C, transaction-recovery, and no-machine-path regression contracts.
- Rollout begins only after the shared Phase 0 authority explicitly permits live governed writes.

**Paul's recommendation:** keep Build 117 on HOLD, select the governed-baseline branch now, then produce and certify RC2 from that approved state.

