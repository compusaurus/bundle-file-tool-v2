# BFT v2.1 Build 103 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_103_bounded_transport.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-13
**Authority:** George's formal ratification of 2026-08-04 (transport grammar, determinism, failure
policy, integrity policy, test sequencing, extract reconciliation), against Paul's
`Pauls_Analysis_Proposed_Plain_Marker_Self_Hosting_Fix_2026-08-04.md` §8 implementation sequence.
Ringo gave the green light to implement on 2026-08-13.

---

## 1. What this build fixes

An in-band marker cannot be distinguished from identical text inside a file. A test fixture or a
parser that quotes `# FILE:` was byte-identical to a real block boundary, so Build 102 could not
transport its own source safely:

| Same input, two transports | Entries parsed | Body intact |
|---|---|---|
| Build 102 grammar | `tests/conftest.py`, **`src/example.py`** (phantom) | **No** — truncated at the embedded marker |
| Build 103 bounded grammar | `tests/conftest.py` | **Yes** |

Build 103 makes a per-bundle **boundary token** the sole authority. The writer derives it from a
digest of the payload, proves it absent from that payload, and carries it as an ordinary
`boundary=<token>` field on each block's `# META:` line.

## 2. Ratified items and where they landed

| # | Ratified item (George, 2026-08-04) | Implementation |
|---|---|---|
| 1 | Token placement: `boundary=<token>` inside `# META:` | `plain_marker.py` — `BOUNDARY_KEY`, `format_manifest()` |
| 2 | Deterministic digest-derived token with collision counter | `plain_marker.py` — `_boundary_candidate()`, `_derive_boundary_token()` |
| 3 | Fail loudly on malformed structure | `plain_marker.py` — `_detect_boundary_token()`, `_parse_bounded()` |
| 4 | Integrity: keep path rejection, drop marker-count classification | `bundle_integrity.py` — `_opens_as_bundle()` |
| 5 | Sequence the eight integration tests before the unit expansion | `tests/integration/test_selfhosting_integration.py` first, then the s7 unit files |
| 6 | Entry-count reconciliation in the extract path | `writer.py` — `BundleWriter._reconcile_extraction()` |

Two-way legacy compatibility is preserved: the separator line is unchanged, so a Build 102 reader
frames blocks exactly as before and treats `boundary` as one more unknown META field. A bundle with
no boundary token still parses through the unchanged legacy path.

## 3. Element-loss catalog (catalog before code)

Callable surface compared with the governed cataloguer (`scripts/code_catalogger_v3.py` +
`code_catalog_comparison_v3_3.py`) and cross-checked by AST inventory. As Paul recorded on
2026-08-04, the tool's raw stability percentages are distorted when a class body changes as one
region; the callable-level inventory below is the meaningful result.

| File | Old callables | New callables | Removed | Added |
|---|---:|---:|---|---|
| `src/core/profiles/plain_marker.py` | 12 | 20 | **none** | `_is_separator`, `_block_header_at`, `_detect_boundary_token`, `_parse_bounded`, `_emitted_payload`, `_boundary_candidate`, `_derive_boundary_token`, `_parse_legacy` |
| `src/core/writer.py` | 15 | 16 | **none** | `BundleWriter._reconcile_extraction` |
| `src/core/bundle_integrity.py` | 5 | 6 | **none** | `_opens_as_bundle` |

No public method was removed and no public signature changed. `parse_stream()` is retained as the
dispatcher; the Build 102 algorithm is retained verbatim as `_parse_legacy()`.

### Behaviour changes by line of authority

| Old behaviour | New behaviour | Where |
|---|---|---|
| Any entry with ≥2 column-zero `# FILE:` lines was a nested bundle | Only content that OPENS as a complete transport artifact is | `bundle_integrity.py` |
| Every `# FILE:` line opened a block | Only an ACTIVE-token frame opens a block | `plain_marker.py` |
| Separator lines in content were discarded | Preserved byte for byte | `plain_marker.py` |
| A damaged boundary silently dropped a file | Raises `ProfileParseError` | `plain_marker.py` |
| `extract_manifest()` could return short counts as success | Raises `ValidationError` on any unaccounted entry | `writer.py` |

## 4. Governance drift repaired in this build

The tree had drifted from the ratified WP0 state before this work started; three release-contract
regression tests were already red on entry (**480 collected, 3 failed**). A pyprojectmgr export on
2026-07-30 had reset the project version to `0.1.0` in the generated artifacts, and
`bundle_config.json` had been rewritten with the pre-D-005 allow-list and machine-specific paths.

| Artifact | Found | Restored to |
|---|---|---|
| `bundle_config.json` `version` | `2.1.0` | `2.1.103` |
| `bundle_config.json` `safety.allow_globs` | 14-entry extension allow-list | `["**/*"]` (ratified D-005) |
| `bundle_config.json` `safety.deny_globs` | no archive/bundle denies | five ratified archive/bundle denies added |
| `bundle_config.json` machine paths / geometry | local absolute paths, `1902x980+2+30` | empty, per the WP0 catalog |
| `.pyprojectmgr/project_manifest.json` version (×2) | `0.1.0` | `2.1.103` |
| `src/database/schema_ids.py` `PROJECT_VERSION` | `0.1.0` | `2.1.103` |
| `MANIFEST_HASH` in `module_ids.py` and `schema_ids.py` | `83eceb0d…` | `92476a0b…` (sha256 of the edited manifest) |

**Two judgment calls for Ringo, George and Paul to confirm:**

1. **Version bump to 2.1.103.** D-004 ratified that the payload owns the installed version and
   fixed `2.1.102` for that build. BFT's version is `Major.Minor.Build`, the stager parses the build
   number out of `VERSION.txt`, and delivery standard v2 §4 requires build-stamped documents, so a
   new build payload owning `2.1.103` is D-004 working as ratified. No separate decision record
   exists for the value itself.
2. **Hand-repair of pyprojectmgr-generated artifacts.** `project_manifest.json`, `module_ids.py` and
   `schema_ids.py` are tool-generated and marked "DO NOT EDIT MANUALLY". The generator lives in
   pyprojectmgr, whose strict QC against this project is open blocker `BFT-WP0-QC-001`, so the
   coherent regeneration path is unavailable. The edits are surgical (two version strings and the
   manifest hash they invalidate) and are proved consistent by the release-contract tests.
   **pyprojectmgr will re-clobber these on its next export until BFT-WP0-QC-001 is closed** — the
   durable fix belongs to that blocker, not to this build.

## 5. QA evidence

Environment: `.venv` Python 3.11.9 on Windows 11 (`pyproject.toml` requires >=3.11,<3.13).

| Gate | Result |
|---|---|
| Whole suite (binding) | **538 passed, 0 failed** (entry state: 480 collected, 3 failed) |
| Coverage gate | **89.25%** against the 85% floor; `bundle_integrity.py` 100%, `plain_marker.py` 93% |
| Byte-compile | `compileall -q src tests` — clean |
| CLI `--version` | `bundle-tool 2.1.103` |
| CLI self-hosting bundle | 63 files discovered, integrity gate passed, bundle written |
| CLI validate | `VALID`, 63 files |
| CLI unbundle | processed 63, skipped 0, errors 0 |
| Disk comparison | 63/63 byte-identical, 0 missing, 0 mismatched |
| Code catalog comparison | 0 callables removed across the changed modules |
| `PREP_AND_STAGE_BFT.bat /dryrun` | plan resolved, no changes made |

New tests: **58** (480 → 538).

| File | Tests | Covers |
|---|---:|---|
| `tests/integration/test_selfhosting_integration.py` | 9 | Paul s7 items 23–30 + determinism + the pinned limitation |
| `tests/unit/test_bounded_transport.py` | 30 | Paul s7 items 1–22 |
| `tests/unit/test_selfhosting_roundtrip.py` | 8 | John's original 7, rewritten to the ratified grammar, + old-reader framing |
| `tests/unit/test_extract_reconciliation.py` | 7 | ratified item 6 |
| `tests/unit/test_bundle_integrity.py` | +4 | ratified item 4 (marker mentions, leading blanks, fragments, binary) |

### Two documented divergences from Paul's pre-ratification test list

Both are consequences of the grammar George ratified, not gaps in it. Neither loses bytes.

- **Item 10** ("one block uses a different active boundary token: fail loudly"): under the ratified
  META-boundary design a frame bearing a *different* token is, by construction, ordinary content —
  which is precisely what lets this project's own fixtures survive. Flagging foreign frames would
  re-break self-hosting. Pinned by `test_item10_foreign_token_block_is_content_not_a_boundary`.
- **Item 13** ("truncated final block: fail loudly"): truncation that removes the `# META:` line
  removes the only evidence a block existed, so the remaining header text is indistinguishable from
  a fixture and is preserved as content. Truncation that leaves the META line intact **is** caught.
  Closing the residual gap needs a bundle-level entry count, which is outside this ratification.
  Pinned by `test_item13_truncated_tail_below_the_meta_line_is_content`.

Also unchanged and pinned: trailing blank lines collapse to a single final newline, and a file with
no final newline gains one. Pre-existing Build 102 behaviour, recorded rather than hidden
(`test_known_limitation_trailing_blank_lines_are_normalised`).

## 6. Payload SHA256 table (17 files)

| SHA256 | Bytes | Path | Disposition |
|---|---:|---|---|
| `5f1ee17d567738cdc2c5b32bfd39cc764af2a80bd4f3b79491c63cb24f6e1deb` | 30644 | `src/core/profiles/plain_marker.py` | MODIFIED |
| `b60e334cf311a8cca1f9fde4a08a42b11d69121624e5a710deb6e8c83495cde3` | 6247 | `src/core/bundle_integrity.py` | MODIFIED |
| `d7e7408efa997a37ff526386cd7639f0c3f35cea58c22ef82d3e71300f5b4b9c` | 35226 | `src/core/writer.py` | MODIFIED |
| `ca54ac30c00e148416a328f7a5473ef4a5a17c9cf416f3a2a46aff84678422d0` | 628 | `src/core/version.py` | MODIFIED |
| `66a3f85f19b91da8dd8edc5a695620e77696aec6ced80ee6ed1c232cc822b667` | 2063 | `src/core/module_ids.py` | MODIFIED (generated) |
| `dd8895a071185b3b79dcae605f0a5b932cf368a422144c62b2f10c6972b09da1` | 37243 | `src/database/schema_ids.py` | MODIFIED (generated) |
| `aa46957083e4790f1ee18a2cd9b3c9eb02555069c8a7100f159c3e148b889d8b` | 8 | `VERSION.txt` | MODIFIED |
| `30c2b1e7a832413ac02825f9e08fd59061132b3abf99594ff157bfdcbf9313aa` | 1239 | `pyproject.toml` | MODIFIED |
| `f333d28824cb1d149ae5a621059185056e0009172191bfe5d857a8dbf2510ca3` | 1542 | `bundle_config.json` | MODIFIED |
| `e6d769340d07bedb5ba513cf9fbfc3d6530f06b6e6768bb38e45407e80d2523b` | 2724 | `.pyprojectmgr/project_spec.json` | MODIFIED |
| `92476a0ba77e9ccd19c20c24d420f4e0b567329292a684a95f87e1a9c0459ca7` | 16457 | `.pyprojectmgr/project_manifest.json` | MODIFIED (generated) |
| `a3b9e25ae8c87800ff87c89c48842174a46feab77cf7754819ccd29da9137b7c` | 6346 | `tests/unit/test_bundle_integrity.py` | MODIFIED |
| `3b84b82554fd19dcdadf7c811a6b380af4a11e4afa4322173550cb267a85a267` | 3923 | `tests/unit/test_release_contract.py` | MODIFIED |
| `f5914b395040803ff9319959ca220dc6ca107bf8954b872ad1b14ee525602b15` | 5522 | `tests/unit/test_selfhosting_roundtrip.py` | ADDED |
| `d8b97a2f5130b46492d3abf91dfeb800b3cf73ac1ca02336214a32bcac05d3f9` | 14254 | `tests/unit/test_bounded_transport.py` | ADDED |
| `b9b4ff08d016b86a8e20d9d104f9ae9c3db637c96c8c8a9c7ed0a1e1a9e7e52a` | 5228 | `tests/unit/test_extract_reconciliation.py` | ADDED |
| `7885a46da32204b04a15221502787852e6422cb0fe84241f306c6d30fb3bf11b` | 7940 | `tests/integration/test_selfhosting_integration.py` | ADDED |

ADDED files are placed and hash-verified but not backed up — `:backup` requires an existing target.
They are listed in `new_files.txt` in the rollback folder so a manual rollback knows to delete them.

## 7. Skeleton-diff proof

The installer's helper block was copied byte-for-byte out of the ratified family skeleton
(`INSTALL_PYPROJECTMGR_v2_1_build100_relationship_idempotence_r5.bat`), never reconstructed from
description. Verified by extracting the region from `BEGIN FAMILY DELIVERY HELPERS v2.0 - HASHED
INCLUSIVE` through the matching `END` marker in both files:

```
helper block SHA256 : 53948714915169d1309e5157030ee437231ac408e576483dbc427f164dfa677e
installer SHA256    : <recorded in the kit listing>
```

Only the header comment, the guards, the manifest/marker-driven steps, the acceptance commands and
the success banner are build-specific. `:hashVerify`, `:backup`, `:place` and `:grepHas` are
identical. The installer is pure ASCII with CRLF endings; no marker string contains
`( ) & | < > ^`.

## 8. Install and gates

The operator runs exactly one command, from the project root, with the kit zip in `Downloads`:

```
PREP_AND_STAGE_BFT.bat
```

It snapshots and archives the live tree, applies retention, stages the kit, moves the zip to
`archives\`, and chains to the installer. The installer then runs:

| Gate | Check |
|---|---|
| Root guards | folder name, `src\core`, `src\core\profiles`, `src\ui`, `tests`, `tests\integration`, `.pyprojectmgr`, `VERSION.txt`, staged payload, manifest, markers, `certutil` |
| A0 | installed version is `2.1.102` (upgrade) or `2.1.103` (idempotent re-run); anything else aborts |
| A | SHA256 of all 17 staged files before any mutation |
| B | `.bak`-equivalent backup of every existing target into `bft_build103_rollback\`, with original/new ledgers |
| C | placement of complete files |
| D | SHA256 of all 17 installed files, then 17 literal content markers |
| E | Python 3.11/3.12 preflight, `pytest`+`coverage` import, `compileall`, CLI `--version`, then the binding whole suite with the coverage gate |
| Teardown | rollback folder and `_bundletool_incoming\` removed only after every gate passes |

Any failure calls `:abort`, which leaves the rollback folder, both ledgers and the staged payload on
disk and returns exit code 1.

**Expected observation:** `538 passed`, coverage `89.25%`, exit code 0.

## 9. Directive compliance

- **No guessing:** the canonical installer skeleton was located and reused; nothing was rebuilt from
  description. Where a decision was not covered by the ratification (§4), it is flagged rather than
  assumed.
- **Catalog before code:** §3, produced with the governed catalog tools.
- **No shims, workarounds, one-off scripts or fallbacks:** the legacy parse path is retained
  behaviour, not a shim; there is exactly one boundary primitive and both the writer and the parser
  use it.
- **Complete files:** every payload file ships whole.
- **JSON handling:** `bundle_config.json`, `project_spec.json` and `project_manifest.json` were
  edited surgically (named keys only, formatting and key order preserved), not wholesale-replaced.
  The approved EDSM JSON tools are project-specific and not present here — see §4 note 2.
- **Delivery standard v2:** one kit zip on the locked `INSTALL_BUNDLETOOL_*` pattern, one in-kit
  installer, build-stamped `built_build103.md` / `team_build103.md`, payload under
  `_bundletool_incoming\`, SHA pre/post gates, backups, content markers, success-only teardown.

## 10. Open items this build does not close

1. `BFT-WP0-QC-001` — canonical pyprojectmgr strict QC remains TOOL-BLOCKED. Reproduction artifacts
   dated 2026-07-24 exist in the project docs folder and have never been dispositioned into a
   governed record; that routing is Paul's.
2. WP0 Gate 1 remains conditional, and the protected baseline branch/commit still requires an
   authorized interactive account. Nothing in this build weakens the intentional `.git` ACL.
3. A bundle-level entry count would close the residual truncation gap in §5. Recommend George rule
   on it as a separate, additive grammar item.
4. `bundle_config.json` is both the shipped default configuration and the file the running
   application rewrites, which is how the D-005 defaults were lost. Recommend Paul and George decide
   whether shipped defaults and user state should be separated; this build restores the values but
   does not change that design.
