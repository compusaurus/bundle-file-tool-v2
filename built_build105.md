# BFT v2.1 Build 105 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_105_registry_and_purity.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-18
**Responds to:** George `ARCH-REVIEW-2026-08-18-02` (registry defect) and Paul
`BFT-ANALYSIS-2026-08-18-03` (**HOLD** on Build 104, three blockers)
**Supersedes for installation:** Build 104. See §9.

---

## 1. Disposition of the two reviews

George found a real defect and recommended a one-line patch to Build 104. Paul held the
release and required a governed successor instead. **Paul's disposition is the one I
followed**, for the reason he gives: `src/core/parser.py` is not in Build 104's 21-file
payload table, so a locally applied patch proves a remedy, not a delivered state. Amending a
hashed, already-installed artifact would break the identity chain the delivery standard
exists to protect.

Build 105 is that governed successor.

| Blocker | Source | Status |
|---|---|---|
| 1. `md_fence` implemented but unregistered | George, confirmed by Paul | **Closed**, with contract tests |
| 2. Governed configuration drift and CWD-relative resolution | Paul | **Closed**, with provenance identified |
| 3. `bundle` contaminates stdout with diagnostics | Paul | **Closed**, with a byte-purity gate |

## 2. Blocker 1 — profile registry

`MarkdownFenceProfile` was fully implemented and never registered. `ProfileRegistry` knew
only `plain_marker`, so anything resolving to `md_fence` — including
`ConfigManager.DEFAULT_CONFIG`'s own default — raised `ProfileNotFoundError`.

The fix is two lines. The reason it survived is the interesting part, and it is what the new
tests target: the Markdown tests instantiate the profile **directly**, and the registry tests
asserted only that `plain_marker` exists. Nothing connected the profile a configuration can
*select* to the profile the registry can *produce*.

`tests/unit/test_profile_registry_contract.py` adds 14 tests covering Paul's list:

- the packaged default profile and the governed config's default are both registered;
- every shipped profile is registered, retrievable and a `ProfileBase`;
- registry order is deterministic and sorted;
- an unknown profile still fails loudly and names the alternatives;
- each registered profile round-trips through the parser and validates through it;
- the governed config resolves identically from the project root, from `src`, and from an
  unrelated working directory;
- a missing governed config yields packaged defaults **without creating a file**, and its
  default profile is still one the registry can produce;
- policy drift is detected, and a clean config reports none.

## 3. Blocker 2 — governed configuration

### Provenance

Paul required the provenance before approval. The live file was byte-identical to the hash
he recorded, written at **2026-08-18 21:29:53**, after Build 104 installed.

Build 104's `ConfigManager.save()` raises, so the new code did not write it. The mechanism:

- `ConfigManager` resolved `bundle_config.json` **relative to the process working
  directory**, so any process started with the live root as its CWD wrote the live governed
  document;
- a fully runnable **pre-104 tree remains on disk** at
  `bundle_file_project/bundle_file_tool_v2  Build 101/`, with `src/main.py`,
  `src/ui/main_window.py` and a `ConfigManager.save()` that writes;
- the drifted file is in pre-104 format, carries a **new** `last_source_dir` pointing at the
  BFT project root, and matches no other copy on disk, so it was freshly written rather than
  restored from a backup.

The drifted copy is preserved as evidence:
`bundle_config.DRIFTED.2026-08-18T21-29-53.json`, SHA256
`063c01638feb0b3106af1f84718e768e1331be7446b02101f260fca199fec215`.

### Fixes

1. **Resolution is anchored to the application root.** `ConfigManager.governed_config_path()`
   derives the path from the package location, not the CWD. Paul's point stands: the
   governed document's location is a property of the installation, not of how the process
   was launched.
2. **A missing governed document is never created.** It yields read-only packaged defaults
   in memory plus a warning on stderr. Writing a governed-looking file into an arbitrary
   directory is how policy drift becomes invisible. An explicit path — developer and test
   scope — retains create-if-absent.
3. **Drift is reported to the operator.** `check_governed_policy()` compares the loaded
   config against the ratified invariants and the CLI prints any findings to stderr before
   doing work. Policy drift has now recurred three times and was found by a test run every
   time, never by the application.

Run against the drifted file, the reporter produced exactly the three findings Paul listed:
narrowed `allow_globs`, missing archive denies, and version `2.1.0`.

**One residual risk, and it is operational rather than code.** Fixing the current code cannot
stop a *stale copy* from writing. The pre-104 tree beside the live one is runnable today. I
have not deleted it — it is your data and deletion is not mine to do — but it should be
archived or retired. Until it is, the drift can recur, and the new reporter is what will
surface it.

## 4. Blocker 3 — stdout artifact purity

`handle_bundle` wrote `Discovering files...`, `Found N files` and `Creating bundle with
profile ...` with ordinary `print()`, then wrote the bundle body to the same stream when
`--output` was omitted. A successful command emitted diagnostics and payload interleaved.

All diagnostics in the bundle path now go to stderr through a `_status()` helper. `unbundle`
and `validate` keep their output on stdout, because there it *is* the product rather than
noise around a payload.

`tests/integration/test_cli_stdout_purity.py` adds 7 tests: stdout is byte-identical to the
formatter's own output for both profiles, it parses back cleanly, progress appears on stderr
and nowhere on stdout, `--output` leaves stdout completely empty, and a marker-bearing
source still round-trips through a pipe.

One pre-existing test asserted progress on **stdout**. It encoded the defect, so it was
corrected to assert the fixed contract rather than deleted.

## 5. George's CLI matrix, re-run with reconciled counts

Paul noted the memo said 16/16 while the table showed 15 rows. Every case below was executed
against Build 105 with captured commands, exit codes and outputs; the machine-readable record
is `cli_matrix_results.json`.

**17 of 17 passed.** The four cases that failed in Build 104 — md_fence directory bundling,
the config-default profile, include/exclude filtering, and the R-BFT-02 integrity refusal —
all pass. Two cases are new: stdout purity for a piped bundle, and a piped bundle parsing
back as valid.

## 6. QA evidence

| Gate | Result |
|---|---|
| Whole suite | **592 passed, 0 failed** (Build 104 shipped 571) |
| Coverage | **89.75%** against the 85% floor, on the declared scope |
| Byte-compile | `compileall -q src tests` clean |
| CLI matrix | **17/17**, reconciled and captured |
| CLI `--version` | `bundle-tool 2.1.105` |
| Drift reporter | reproduces all three findings against the preserved drifted file |

New tests: **21** (571 → 592).

## 7. Payload SHA256 table (15 files)

| SHA256 | Bytes | Path |
|---|---:|---|
| `be7b9b29882090b208ec62ba39622f009a606012f18d060c45a9ffb8b0283e9b` | 10422 | `src/core/parser.py` |
| `044630b8ca75962cbfd50d21250883183c8f2904a5aebeb4c113537b4088c245` | 19228 | `src/core/config.py` |
| `e1db9df6e58b9ad50e97216bc3716666b7d5a8a9ffe9334f13427f240f4b8e81` | 11568 | `src/cli.py` |
| `437314c88b7c82bbc59d748395357afb6a98275c48614d0c04ca0dca2fcc07e5` | 628 | `src/core/version.py` |
| `0d46b8c1d87043ccafe54112c3d0b8a7f8f3e80289421788503bcfb00b633314` | 2050 | `src/core/module_ids.py` |
| `030c33e599c3ee33caa92a3561e7b0f4ce1e412350a5f40434406ccf7170fb7a` | 37217 | `src/database/schema_ids.py` |
| `3841f6c3dba5aad38edfdb175a7fc8a6c3d863528cfb746adb1414a5d1a084c6` | 8 | `VERSION.txt` |
| `308a28adc6313bca768743dad1aac8decb00bd888ba19487d8f8ad87d933459f` | 2132 | `pyproject.toml` |
| `4bba0059607a40063389c7b7b4baa46a241b5ebe1fb0e0a7caecdb10eb805b7f` | 1473 | `bundle_config.json` |
| `0a174802b9e2757c77dd2aa454bdad2d5ed09fd5cf2dc022f03716a5b70a33a2` | 2617 | `.pyprojectmgr/project_spec.json` |
| `fc6868a6bcb8a0abf19da65b12c5fa34d59a8325201d74d5b6a17cf111684897` | 15837 | `.pyprojectmgr/project_manifest.json` |
| `0c42e8f800d72d348a9a2ee1fcbf2931b39109926c2c6f9c8ad3e04862727ee3` | 7578 | `tests/unit/test_profile_registry_contract.py` |
| `5a27a91f55a4ab8336c088b1f7e449bf3dc3edfd5f565a3d9a8cb784997bb981` | 5451 | `tests/integration/test_cli_stdout_purity.py` |
| `574c954ea0255b359d07ee6a8fc9396a2985b265708b5a083f570f47b5994223` | 3967 | `tests/coverage_extra/test_cli_commands_cextra.py` |
| `d55902fbc7aa7fbe2ac6b551370851cdbb042fc5546b8df439e5c1978cc9d1f3` | 3923 | `tests/unit/test_release_contract.py` |

## 8. Skeleton-diff proof, and the canonical copy restored

```
helper block SHA256 : 53948714915169d1309e5157030ee437231ac408e576483dbc427f164dfa677e
installer SHA256    : e26799ef9165c83d8c9e77e0bd07e2b98f503528a9cf8c99887442d5cba6290f
```

George's Gap 3 and Paul's requirement are both closed: the verified block is restored to a
governed, source-controlled location at
`pyprojectmgrV2/delivery_templates/FAMILY_DELIVERY_HELPERS_v2_0.bat`, and
`tests/build126/test_delivery_template_integrity.py` asserts its presence, its hash, the four
required routines, and that it is pure ASCII with CRLF endings.

## 9. Relationship to Build 104

Per Paul's document action 1, **`built_build104.md` is preserved unchanged** as the original
build record. This section is the successor cross-reference.

Build 104's R-BFT-01, R-BFT-02 and R-DEL-02 work is retained in full and was ratified by
both reviewers. Build 104's *installation* is superseded by Build 105, which contains
everything Build 104 delivered plus the three blocker closures. The Build 104 kit remains in
`archives/` as history.

## 10. Directive compliance

- **No guessing:** the drift provenance was traced to a mechanism and a specific stale tree,
  not asserted.
- **Catalog before code:** §7.
- **No shims:** the config resolution change is a proper anchor, not a patch over `save()`.
- **Complete files:** every payload file ships whole.
- **Delivery standard v2:** one kit on the locked pattern, one in-kit installer, build-stamped
  documents, SHA pre/post gates, backups, content markers, success-only teardown.

## 11. Open items

1. **The pre-104 tree at `bundle_file_tool_v2  Build 101/` should be archived or retired.**
   It is runnable and can still write the governed config. Yours to action.
2. **UI coverage debt** — `src/ui/*` has no automated tests; George proposes a headless Tk
   harness in Phase 6. Recorded, not closed.
3. **`BFT-WP0-QC-001`** stays open while `PPM-DEFECT-002` blocks a disposable-mirror run.
4. **Paul's Build 100 status addendum** and the readiness-plan work-package update are
   document actions I have not performed; they are his records to amend.
5. **3.12 test environment** remains unavailable on this machine.
