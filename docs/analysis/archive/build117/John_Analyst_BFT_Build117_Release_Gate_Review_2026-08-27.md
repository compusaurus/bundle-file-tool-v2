# BFT — Build 117 Release Gate Review

**Date:** 2026-08-27
**From:** John, Lead Analyst (BFT)
**To:** Paul, Lead Developer
**CC:** Ringo (Owner), George (Lead Architect)
**Subject:** The canonical gate is red as of this morning; two new egress defects; the ratified work still outstanding before public release
**Status:** For disposition
**Tree state at review:** unmodified — no source was changed to produce this document

---

## 0. Summary

Ringo asked for a state-of-the-project read against the roadmap ahead of public release. Three things to report.

1. **The canonical gate is red.** It was green at 1,442 when I last ran it on 2026-08-26. It is now **3 failed, 1,464 passed**. All three failures trace to one event: a ConfigHub governed-config transaction that ran at **11:51 today**.
2. **The ingress family you closed in Build 117 is genuinely closed.** I verified all six items from my 2026-08-26 list. But the same fail-open class is still live on the **egress** side, in the writer's source-read path, and I have a reproduction.
3. **All five Build 117 UAT defects are still open**, including your P0 CRLF finding. I confirmed why 1,464 green tests do not catch it.

My overall read: BFT is close on engineering and not close on governance. The two most serious findings today came from a governed write that ran outside an approved diff, and the open P0 means we cannot yet claim byte fidelity — which is the one promise this tool exists to make.

---

## 1. The gate

```
3 failed, 1464 passed in 86.35s
Required test coverage of 85.0% reached. Total coverage: 89.55%
```

Run from `.venv\Scripts\python.exe -m pytest -q --no-header`, Python 3.11.9. Your handoff requires **1,453 passing** before the release commit.

For the arithmetic: I measured 1,442 on 2026-08-26; the suite is now 1,467 collected, so 25 tests were added since. None of the three failures are flaky and none are environmental — they are all consequences of the 11:51 transaction.

### Evidence that the transaction is the trigger

Both governed files were rewritten at 11:51 today, each leaving a hashed backup:

```
bundle_config.json.923f8a6253c94f359cba89aebd6c0af8.81a4676c.bak
.pyprojectmgr/project_manifest.json.923f8a6253c94f359cba89aebd6c0af8.28a8278f.bak
```

The transaction was internally consistent — the manifest's `governed_config_sha256` matches the config bytes exactly:

```
bundle_config.json           sha256: 47a37683f0106ecdbba61e5740cd6d1eb0a4ca3f25d87ecb717a7be876166e8e
manifest governed_config_sha256    : 47a37683f0106ecdbba61e5740cd6d1eb0a4ca3f25d87ecb717a7be876166e8e   MATCH
```

That is the transaction doing its job. The problem is not integrity within the transaction. The problem is what the transaction wrote, and that it moved the baseline out from under an approval record.

---

## 2. Findings from the governed write

### BFT-A-2026-08-27-01 — Release identity has drifted off the approved record

**Severity: High (release blocker) · Class: governance**

`BUILD117_RELEASE_IDENTITY_EXACT_DIFF_2026-08-26.md` seals the Build 117 proposal at these values. The live tree no longer matches either column.

| File | Approved "Proposed" | Live now |
|---|---|---|
| `bundle_config.json` | `5cf84eb590925f68…` | `47a37683f0106ecd…` |
| `.pyprojectmgr/project_manifest.json` | `4e63bb7ea1541432…` | `940435717fe42da7…` |

Consequences:

- **Handoff precondition 2 is violated** — "the live baseline hashes still match the Live baseline column." They do not.
- The exact diff George is being asked to approve is **stale**. Signing it now would authorize a state that no longer exists.
- `UAT-GOV-001` verified the governed config at `5cf84eb5…` on 2026-08-26. That evidence no longer describes the tree.

**Recommendation:** decide this before anything else moves. Either restore the approved bytes and re-run the gate, or prepare a revised exact diff for George covering both the release identity and the ConfigHub-originated changes. Nothing downstream is meaningful until the governed baseline is a known quantity.

### BFT-A-2026-08-27-02 — Generated governance IDs no longer reference the live manifest

**Severity: High · Class: governance · Test: `test_generated_governance_ids_reference_current_manifest`**

```
assert module_ids.MANIFEST_HASH == manifest_hash
  - 940435717fe42da7ee6b1f890da9c3efd430e0467b6821f083e1ee2f9e583612   (live manifest)
  + 4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b   (baked into module_ids / schema_ids)
```

`src/core/module_ids.py` and `src/database/schema_ids.py` still carry the Build-117-approved manifest hash. The manifest moved; the constants did not. The identity chain that the release contract exists to enforce is currently broken, and this is exactly the check that is supposed to catch it. The test is correct; the tree is wrong.

### BFT-A-2026-08-27-03 — The governed config now carries operator machine paths

**Severity: High for public release · Class: configuration content**

```json
"global_settings": {
  "input_dir": "C:/Users/mpw/Python",
  "output_dir": "C:/Users/mpw/Python/bundles",
  "relative_base_path": "C:/Users/mpw/Python"
}
```

These were `""` before the transaction. This is delivery configuration, not user state — it ships. Three problems: it leaks a developer's directory layout, it is meaningless on any other machine, and it changes CLI behaviour (see 02-04 below).

**Note on what is correct here.** The `safety` block changes in the same write are *good*: `allow_globs: ["**/*"]` plus the five archive/bundle denies is precisely the **D-005 ratified** deny-list default from the WP0 record. That has been ratified since 2026-07-23 and simply never reached a governed build. Keep it. It is the `global_settings` paths that must not ship.

### BFT-A-2026-08-27-04 — `unbundle` without `--output` no longer errors

**Severity: Medium · Class: configuration content, not code · Test: `test_unbundle_requires_output_exits_nonzero`**

```
assert exc.value.code == 1
E   assert 0 == 1

Extracting to: C:/Users/mpw/Python/bundles
Extraction complete:  Processed: 1  Skipped: 0  Errors: 0
```

I want to be precise about this one, because the obvious reading is wrong. `src/cli.py:173` is:

```python
output_dir = args.output or config_manager.get("global_settings.output_dir")
if not output_dir:
    raise BundleFileToolError(...)
```

**The CLI code is behaving exactly as designed.** `--output` *or* config, and the guard fires only when neither is set. The test passed historically because the shipped config had `output_dir: ""`; it fails now because the config has a real path. So this is not a lost safety guard and there is no CLI defect to fix.

What it does mean for a public release is still worth taking seriously: a shipped config with a populated `output_dir` turns a required argument into an optional one, and an end user who omits `--output` silently writes extracted files into a preset directory rather than being told to choose one. Fix it in the config (01-03), not in `cli.py`.

**Secondary observation for the fixture set:** this test silently depends on shipped-config content. It should set `output_dir` explicitly in a fixture rather than inheriting whatever the governed file happens to hold, so it tests the CLI contract rather than the current config.

### BFT-A-2026-08-27-05 — Governed files flipped newline convention

**Severity: Low, but it has a governance edge · Test: `test_a_modified_configuration_is_detected`**

```
bundle_config.json                          CRLF=0    bare-LF=84
bundle_config.json ….81a4676c.bak           CRLF=83   bare-LF=0
.pyprojectmgr/project_manifest.json         CRLF=0    bare-LF=557
```

The pre-transaction backups are CRLF; ConfigHub wrote LF. Since Layer A integrity is a byte digest, newline policy is part of the governed contract, and the approved Build 117 hashes were computed over CRLF files. Worth an explicit decision on which convention the governed writer owns, rather than leaving it to whichever component wrote last.

The test failure itself is a **fragile test**, not a product defect:

```python
original = ConfigManager.governed_config_path().read_text(encoding="utf-8")
governed.write_text(original, encoding="utf-8")
assert manager.check_config_integrity() is None, "clean copy should be quiet"
```

`read_text` normalises to `\n`, `write_text` re-expands to `\r\n` on Windows. That round trip used to be byte-neutral because the source was CRLF; with an LF source the "clean copy" is no longer clean. **Fix the test to use `read_bytes`/`write_bytes`** regardless of how the newline decision goes — the current form asserts something about Windows text mode, not about integrity.

---

## 3. New code defects — the egress side of the ingress family

Your Build 117 ingress work holds up. I re-verified `parser._decode_bundle_bytes`: strict decoding, byte-offset diagnostics, UTF-16/32 signature sniffing ahead of profile detection, and `service._read_text` now routed through the shared reader. All six items from my 2026-08-26 list are landed. That family is closed.

But the same fail-open posture is still live in `BundleCreator._read_file_to_entry` (`src/core/writer.py:943`) — the path that reads **source files on the way into a bundle**. Binary detection samples only the first 1024 bytes, then text is read at `src/core/writer.py:992` with `errors='replace'`.

### BFT-A-2026-08-27-06 — Source files corrupt silently past the 1 KB sniff window

**Severity: High — silent corruption reported as success**

A non-UTF-8 byte beyond byte 1024 is never seen by the sniffer, so the file is classified text and the offending byte is replaced with U+FFFD:

```
A late-cp1252  : binary= False  enc= utf-8
   disk tail   : b'Acost \x97 five'
   entry tail  : 'Acost \ufffd five'
   round-trips?: False
```

Reproduction (2,000 filler bytes, then a cp1252 em dash):

```python
a.write_bytes(b'A'*2000 + b'cost \x97 five')
BundleCreator()._read_file_to_entry(a, 'late_ansi.txt')
```

This is the same class we closed on ingress, on the opposite boundary, with the same consequence: the operator is told `Errors: 0` while a shipped file is quietly altered. It also carries the same reasoning as my §3 from 2026-08-26 — BFT fails closed everywhere else it is uncertain, and guesses here in the direction of data loss.

### BFT-A-2026-08-27-07 — Valid UTF-8 misclassified as binary at the sniff boundary

**Severity: Low**

A multi-byte character straddling byte 1024 raises `UnicodeDecodeError` on the truncated chunk, so a perfectly valid UTF-8 text file is classified binary and base64-encoded:

```
B straddle-utf8: binary= True  enc= base64   <- file IS valid UTF-8 text
```

Lossless, so no data is harmed, but the file becomes opaque in the bundle and roughly 33% larger.

**Both are one fix.** Either sniff over the whole file, or decode strict and let the exception drive classification — which also removes the `errors='replace'` fallback and brings egress into line with the posture ingress now has.

---

## 4. Build 117 UAT defects — all five still open

I checked each against current source. None have been touched since your report.

| ID | Defect | Verified state |
|---|---|---|
| BFT-117-UAT-001 | **P0** CRLF source extracts as LF | **Open** — reproduced |
| BFT-117-UAT-002 | P1 nested folders cannot expand | Open — `selection_workspace.py:419` still emits children only for already-expanded paths; no placeholder |
| BFT-117-UAT-003 | P1 workspace horizontal scrollbars inactive | Open |
| BFT-117-UAT-004 | P1 Open Bundle forgets its folder | Open — `last_bundle_open_dir` does not appear anywhere in `src/`; `unbundle_frame.py:281` still reads only `global_settings.input_dir` |
| BFT-117-UAT-005 | P2 title reports v2.2 | Open — `src/ui/main_window.py:464` |

The P0, reproduced through `_read_file_to_entry` directly:

```
-- crlf.txt
  disk bytes : b'one\r\ntwo\r\n'
  eol_style  : LF | binary: False | enc: utf-8
  content    : 'one\ntwo\n'
```

Your root-cause analysis was right: universal-newline translation happens in `read_text` before `_detect_eol` runs, so the recorded `eol=LF` is false and extraction has no correct fact to restore.

### Why the suite misses it — and why it missed 06 and 07 too

Every CRLF fixture in the suite is a hand-constructed `BundleEntry` with `eol_style` **passed in** (`tests/conftest.py:78`, `:93`). Nothing exercises `_read_file_to_entry` against a real CRLF file on disk. The suite verifies that a manifest carrying `eol_style="CRLF"` round-trips; it never verifies that a CRLF *file* produces `eol_style="CRLF"`.

That single gap explains all three writer defects in this document. The transport fixture matrix I proposed on 2026-08-26 should extend to the source-read boundary:

| Fixture | Guards against | Expected |
|---|---|---|
| Real CRLF file on disk | UAT-001 | `eol_style=CRLF`, byte-exact extraction |
| Real CR and mixed-EOL files | UAT-001 family | correct metadata, byte-exact extraction |
| Non-UTF-8 byte past offset 1024 | 06 | fails closed — must **not** report success |
| Multi-byte char straddling offset 1024 | 07 | classified text, not binary |
| Empty file, single-byte file | boundary | round-trips |

Every one of these compares **bytes**, not manifest fields. I am happy to build this set as analyst work if you would rather keep your hands on the writer — say the word either way.

---

## 5. Ratified work outstanding

### Governance gates

| Gate | Owner | State |
|---|---|---|
| WP0 Gate 1 — accept normalized baseline | George + John | **Conditional.** Blocker `BFT-WP0-QC-001` is OPEN. Canonical strict QC has never completed cleanly on the exact candidate, and no waiver was granted. |
| Phase 0 architecture (ADR-SETUP-001…005) | George | **Unsigned draft.** Every checkbox empty; all three signature blocks blank. |
| Build 117 exact-diff approval | George | Pending — and now stale per finding 01. |
| Build 117 UAT re-run | Paul | Blocked on the five open defects. |

**One question I cannot answer from the record.** The Phase 0 memorandum §8 states that approval does *not* authorize "live modification of BFT governed metadata", "changing `bundle_config.json` values", or "any direct ConfigEditor write to BFT configuration". The memo is unsigned, and a ConfigHub write to both governed files executed today. `BFT_CONFIG_HUB_INTEGRATION_2026-08-27.md` documents the integration but records no approval for it.

I am not asserting a violation — it is entirely possible Ringo authorized this separately and the record has not caught up. But the authorization is not in the documents, and Phase 0 completion gate item 6 ("the config digest is unchanged and verified") is now demonstrably not satisfied. This needs an explicit disposition from George and Ringo before the release commit, not after.

### The repository itself

This is the largest single gap between where we are and a public release.

```
last commit : b88d67c   2025-10-28   "Update project with current local code"
tags        : (none)
untracked, not ignored : 3,189 files
```

Builds 103 through 117 — every fix discussed in this document — exist **only as working-tree state**. There is no release commit, no tag, and no protected baseline. The WP0 exit rule requires a baseline branch to exist; it does not.

This is the intentional `.git` separation-of-duties ACL working as designed (`automated_agents: deny`), so it needs an authorized interactive account. It is not something an agent can or should resolve. But it does mean the entire release history is currently one power failure away from gone, and I would treat that as urgent independently of the release schedule.

Your handoff is right that `git add -A` must not be used here. For scale: `out/` alone holds five UAT run trees plus the RC1 zip, and some paths exceed the Windows path limit (`git status` emits "Filename too long" warnings on the `very_long_directory_segment_*` fixtures).

### Public-release gaps

Distinct from everything above — these only matter because the target is *public*:

- **No `README.md`, `LICENSE`, `CHANGELOG`, or `CONTRIBUTING`.** `pyproject.toml` declares `readme = "README.md"` for a file that does not exist. The sdist still builds, so this is not a hard failure, but the published metadata has no description.
- **Licensing is contradictory.** `pyproject.toml` classifies the package `License :: Other/Proprietary License`, while my 2026-08-26 memo describes the product as MIT when discussing distributing George's bundle as a fixture. One of those is wrong. Ringo's call.
- **`description` still reads `"(internal)"`.**
- **`.gitignore` gaps** that would put local runtime data in the release commit: `qc_report_*.html` is ignored but `qc_report_*.json` is not; `.pyprojectmgr/*.db` (four SQLite files, ~1 MB), `out/`, `demo.txt` (422 KB), and `cli_matrix_results.json` are all untracked and unignored. WP0's exit rule explicitly requires the staged diff to contain no local runtime data, backups, logs, sessions, or generated reports.
- **Stale root documents.** `BUILT.md` and `TEAM.md` both describe "build 198", contradicting `VERSION.txt` 2.1.117. D-008 retains them as legacy history, which is fine internally, but they would confuse a public reader.

---

## 6. Recommended sequence

1. **Settle the governed baseline first.** Restore the approved config bytes, or prepare a revised exact diff for George covering both the release identity and the ConfigHub changes. Strip the `global_settings` machine paths either way; keep the D-005 safety block. Re-run the gate and expect green before anything else proceeds.
2. **Get an explicit disposition on the ConfigHub authorization** from George and Ringo, and get Phase 0 signed or returned.
3. **Cut one corrective candidate — Build 117 RC2** covering: UAT-001, findings 06 and 07 (same code path, one fix), UAT-002/003/004, and the v2.2 title. Refresh `module_ids` / `schema_ids` against the final manifest in the same candidate.
4. **Land the source-read fixture matrix** from §4 before RC2 seals, so the class is closed rather than the three instances.
5. **Create the git baseline** from your interactive account, with the public-release files added and the `.gitignore` gaps closed.
6. **Close or waive `BFT-WP0-QC-001`**, then re-run the 25-scenario UAT matrix plus the installer gates.

Items 1 and 5 are the two I would not defer. Everything else is ordinary engineering; those two are the ones where the current state is actively costing us — one has invalidated an approval record in flight, and the other means ten months of ratified work exists in exactly one place.

---

## 7. Reproduction

All from `C:\Users\mpw\Python\bundle_file_project\bundle_file_tool_v2`.

Canonical gate:

```
.venv\Scripts\python.exe -m pytest -q --no-header
```

The three failures in isolation:

```
.venv\Scripts\python.exe -m pytest tests/unit/test_layer_a_integrity.py::test_a_modified_configuration_is_detected tests/unit/test_release_contract.py::test_generated_governance_ids_reference_current_manifest tests/coverage_extra/test_cli_error_paths_cextra.py::test_unbundle_requires_output_exits_nonzero -q --no-cov
```

Findings 06 and 07 (writes two probe files to a temp dir, reads them back through the writer):

```
.venv\Scripts\python.exe -X utf8 -c "import sys,pathlib,tempfile; sys.path.insert(0,'src'); from core.writer import BundleCreator; d=pathlib.Path(tempfile.mkdtemp()); c=BundleCreator(); a=d/'late.txt'; a.write_bytes(b'A'*2000+b'cost \x97 five'); e=c._read_file_to_entry(a,'late.txt'); print('binary=',e.is_binary,'round-trips=',e.content.encode('utf-8')==a.read_bytes())"
```

UAT-001:

```
.venv\Scripts\python.exe -c "import sys,pathlib,tempfile; sys.path.insert(0,'src'); from core.writer import BundleCreator; d=pathlib.Path(tempfile.mkdtemp()); f=d/'crlf.txt'; f.write_bytes(b'one\r\ntwo\r\n'); e=BundleCreator()._read_file_to_entry(f,'crlf.txt'); print(e.eol_style, repr(e.content))"
```

Governed digests:

```
.venv\Scripts\python.exe -c "import hashlib,json,pathlib; b=pathlib.Path('bundle_config.json').read_bytes(); m=json.loads(pathlib.Path('.pyprojectmgr/project_manifest.json').read_text(encoding='utf-8')); print(hashlib.sha256(b).hexdigest()); print(m['governance']['governed_config_sha256'])"
```

— John, Lead Analyst (BFT)
