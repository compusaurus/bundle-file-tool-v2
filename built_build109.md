# BFT v2.1 Build 109 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_109_integrity_and_headers.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-23
**Authorised by:** Ringo (Product Owner)
**Ratified scope:** `ARCH-RULING-2026-08-23-02` (George), responding to
`BFT-ANALYSIS-2026-08-23-01` (Paul) and `BFT-DEV-RESPONSE-2026-08-23-01` (John)
**Supersedes for installation:** Builds 106, 107 and 108. See §9.

---

## 1. Scope delivered

All eight ratified items, in George's dependency order — F-02 → Layer C → Option B+ →
Layer A → progress and installation tests.

| # | Item | Status |
|---|---|---|
| 1 | Option B+ provenance header allow-list | Delivered, with one refinement (§3) |
| 2 | Multi-format default round-trip suite | Delivered, 57 tests |
| 3 | F-02 GUI governed-config anchoring | Delivered, test-first |
| 4 | Layer C filesystem write-protection | Delivered, full lifecycle proven (§6) |
| 5 | Layer A process telemetry and checksum | Delivered, 12 tests |
| 6 | Class-level monotonic progress suite | Delivered, closes F-06 |
| 7 | Multi-predecessor installation matrix | Delivered, 105/106/107/108 → 109 all pass |
| 8 | Build progression and supersession docs | This document and `team_build109.md` |

**702 → 840 tests. Coverage 90.29% → 90.37%.**

## 2. Test-first, as mandated

George's ruling required a reproduction test before each patch. Each of these failed
against Build 108 and passes now:

| Defect | Reproduction | Failure before the fix |
|---|---|---|
| F-02 | `test_no_ui_module_constructs_configmanager_with_an_explicit_path` | `Offenders: ['main_window.py:65']` |
| F-02 | `test_the_real_app_anchors_when_launched_from_an_unrelated_directory` | `the GUI built a developer-scope ConfigManager` |
| F-01 | `test_json_survives_extraction_under_the_default_setting` | `json.loads()` raised at line 1 column 1 |
| F-06 | `test_service_extract_bundle_reports_every_entry` | `write emitted 2 events for 6 units … [0, 6]` |

The F-06 message is Paul's finding reproduced exactly: a bracket, not a sequence.

## 3. Option B+, and one refinement beyond the ruling

The allow-lists are implemented verbatim from `ARCH-RULING-2026-08-23-02` §2 and bound by a
test, so a silent edit fails the suite. Two implementation details are worth recording
because neither is in the ruling text.

### 3.1 `.env` is a name, not a suffix

The ruling lists `.env` among the extensions, but `Path(".env").suffix` is `""`. Matching on
suffix alone would silently never fire for it. The lookup therefore treats a single
leading-dot filename as its own extension.

### 3.2 A shebang must keep line 1 — found, and fixed

**This is a defect I introduced with Option B+ and caught while building the round-trip
matrix.** Option B+ decides *whether* a `#` header is valid for a format. It says nothing
about *where* the header goes, and I prepended it. A shebang is a comment, so the allow-list
was satisfied — and `#!/usr/bin/env bash` moved to **line 13**, which the kernel does not
honour. Valid syntax, unexecutable file: the same class of harm F-01 was raised for.

`insert_provenance_header()` now places the block immediately after a shebang line.
`test_a_shebang_survives_header_injection` covers `.sh`, `.py`, `.pl` and `.rb`.

I am flagging this rather than folding it in silently because it is a deviation from the
literal ruling. **George**: if you would rather scripts carried no provenance at all than
carried it on line 2, say so and I will move them off the allow-list instead.

### 3.3 What the matrix actually proves

A synthetic repository of 22 text files and 2 binaries is bundled and extracted **through the
real CLI with no flags** — no `--no-headers`, no `--profile` — then each file is checked with
its own native parser: `json`, `tomllib`, `xml.etree`, `configparser`, `csv`, `ast` and
`yaml.safe_load`. Structured formats are asserted byte-identical to source; `#`-comment
formats must carry provenance *and* an unaltered payload; binaries byte-identical.

It also asserts that `**/*.whl` is still excluded by governed safety policy, so a round-trip
suite that quietly started carrying wheels would fail rather than pass.

PyYAML is now a declared dev dependency for the one YAML assertion; it guards with
`importorskip`, so its absence degrades the matrix rather than breaking it.

## 4. F-02, and why it had to be first

`main_window.py:65` passed an explicit relative path, which `ConfigManager` treats as
developer scope: resolved against the working directory, and creatable. The GUI could
therefore address — and bring into existence — a different document from the one the CLI
reads and the installer governs.

The static test is an AST check across **all** UI modules rather than a check of that one
line, so a future UI surface cannot reintroduce it. The explicit-path form is deliberately
retained for tests and tooling; what changed is that no shipped UI may use it.

George ratified this as a hard prerequisite to Layer C, and the reason is concrete: a
read-only flag on the installed file protects nothing while the application is using another
one. It would have produced a build that looked hardened and was not.

## 5. Layer A — integrity and telemetry

`bundle_config.json` now carries a SHA-256 baseline in
`.pyprojectmgr/project_manifest.json` under `governance.governed_config_sha256`. On load, a
governed `ConfigManager` compares the file against it and reports a mismatch with everything
Paul specified: both digests, application version, executable path and UTC timestamp, and no
other user data.

Three properties are load-bearing and tested:

- **It never raises.** Same guarantee as the progress sink, for the same reason.
- **A missing baseline is silent.** An installation predating Layer A must not report itself
  as compromised — false alarms are how a warning becomes background noise, and this one has
  to still mean something the fifth time.
- **The alert goes to stderr.** Build 105's purity rule holds; a tampered config still
  produces a byte-clean piped bundle.

Reported on both surfaces per the ruling: stderr, plus the GUI status bar and a dialog.

**Bump ordering is now load-bearing.** The digest must be taken *after* the config's version
is written and *before* the manifest is hashed. Get it wrong and the build ships an
installation that reports itself as tampered with. The order is documented in the bump
script.

## 6. Layer C — the full lifecycle, proven

The installer clears the read-only attribute at **Gate C0** before placement, and applies it
at **Gate C3** before acceptance — deliberately before, so the whole suite runs against the
protected state a user will actually have.

| Path | Result |
|---|---|
| Success (×4 predecessors) | config protected, 840 tests pass |
| Idempotent re-run onto a protected tree | exit 0, still protected |
| Abort after C0 had cleared protection | non-zero exit, **re-protected**, recovery retained |

The abort case is the one that matters: the window between C0 and C3 must never leave the
governed document writable, because the next run assumes it is protected.

Two further details, both from my §6 notes and both now real:

- **Backup copies are unprotected on creation.** A read-only source copies with its attribute
  intact, so rollback material would be unrestorable. Gate B clears it on the backup only.
- **The suite must survive a protected config.** Two Layer A tests rewrite the governed file.
  They now clear and restore the attribute around the write, and the full suite was run
  end-to-end against a read-only config: **840 passed**. Without this the suite would pass in
  development and fail the first time anyone re-ran it on an installed tree — precisely when
  they would run it.

## 7. F-06 — closing the class, not the instance

`BundleToolService.extract_bundle()` never handed its sink to the writer. Fixed by passing it
through with `emit_complete=False`, so the writer produces the per-file sequence and the
service — which also ran the parse phase the writer knows nothing about — owns the single
terminal event. That satisfies Paul's constraint of no duplicated or conflicting events, and
a test asserts exactly one completion and no repeated write positions.

The suite is deliberately class-level. It walks every entry point taking a `progress`
argument — creator, writer, service, CLI and Tk — and asserts a per-unit non-decreasing
sequence reaching its total. A final register test enumerates sink-accepting methods by
introspection and fails if one is not covered, so a new one cannot be added untested.

That matters because this was the *second* instance of one mistake. The structural cause is
that `emit()` swallows sink failures by design, which is correct and which also makes a
missing sink indistinguishable from a working one from the inside.

## 8. Two installer defects the matrix caught

Recorded because they are exactly what the matrix gate exists for, and both would have
shipped:

1. **Backslash emission.** My kit builder's escape helper produced `\\` where batch needed
   `\`, so the trailing-separator strip never fired and the root guard reported
   `expected project folder bundle_file_tool_v2; found .` — the installer aborted before
   touching anything.
2. **Read-only detection.** `:isReadOnly` parsed `attrib` output positionally; the `R` flag is
   not in a fixed token, so Gate C3 failed against a *correctly* protected file. It now reads
   the file attribute string directly.

A third, milder one: a `%~a` sequence inside a `REM` comment was expanded by the batch parser
and broke the script. Comments in generated batch must avoid `%~`.

## 9. Supersession and the version matrix

Gate A0 accepts `2.1.105` through `2.1.109`. The payload is a strict superset of the 106, 107
and 108 kits.

Paul's requested gate, executed for real — four throwaway clones, each rewound to look like
its predecessor, each installed with the actual kit:

| From | Install | Tests | Version surfaces | Config protected | Stale wheel |
|---|---|---|---|---|---|
| 2.1.105 | PASS | 840 | all 8 unified at 2.1.109 | yes | retired |
| 2.1.106 | PASS | 840 | all 8 unified at 2.1.109 | yes | retired |
| 2.1.107 | PASS | 840 | all 8 unified at 2.1.109 | yes | retired |
| 2.1.108 | PASS | 840 | all 8 unified at 2.1.109 | yes | retired |

Surfaces checked: `VERSION.txt`, CLI `--version`, `core.version`, `pyproject.toml`,
`bundle_config.json`, `project_manifest.project_meta`, `project_manifest.meta`, and
`project_spec.json`.

`PREP_AND_STAGE_BFT.bat` requires exactly one delivery zip in Downloads.

## 10. Payload — 30 files

New: `tests/unit/test_gui_config_anchoring.py`, `test_header_allowlist.py`,
`test_layer_a_integrity.py`, `test_layer_c_readonly_config.py`,
`tests/integration/test_multiformat_roundtrip_default.py`,
`test_progress_monotonic_contract.py`, and `src/ui/main_window.py` enters the payload.

Changed: `src/core/writer.py` (Option B+, shebang, `emit_complete`), `src/core/config.py`
(Layer A), `src/cli.py` (Layer A reporting), `src/core/service.py` (F-06),
`src/ui/main_window.py` (F-02, Layer A UI), `pyproject.toml` (PyYAML), plus every version
surface and the Build 106–108 superset.

## 11. Cross-project items from Paul's Build 131 communication

Two land on BFT and both are respected here:

- **BFT's old 14-error QC report is not a valid repair queue.** Paul is explicit that the
  lexical/import-aware resolver must be ported before that report means anything. **No action
  was taken on it in this build**, deliberately.
- **No absolute sibling paths in the test suite.** Verified: every executable path in
  `tests/` is derived from `__file__`. Absolute paths appear only in `# Relative Path:`
  header comments, which is F-08 documentation debt rather than a functional violation.

The resolver port itself is not Build 109 scope and is not started.

## 12. Evidence

```
840 passed in 13.91s
Required test coverage of 85.0% reached. Total coverage: 90.37%
```

- Full suite also run with the governed config **read-only**: 840 passed.
- Multi-predecessor matrix: 4/4 PASS, all surfaces unified.
- Layer C lifecycle: idempotent PASS, abort PASS.
- Helper block `380037a3…`, verified against the canonical include and re-hashed inside the
  finished installer.
- Governed config digest `973fb70c…`; manifest digest `c313d3ba…`.

## 13. Open items

- **George**: §3.2, the shebang placement refinement — confirm or redirect.
- **F-04 JSONL** deferred to Build 111 by ruling; still validates-but-unregistered until then.
- **F-05 tri-UI migration** (CLI *and* Tkinter together) is Build 110.
- **F-08 source headers** partially addressed; new Build 109 files carry correct metadata,
  the historical inconsistency remains for the Build 111 QA freeze.
- No cancel path yet; Build 110 per the roadmap.
- MAX_PATH: `certutil` cannot hash payload paths beyond the Windows limit. Not reachable from
  the governed install root, but a very deeply nested installation would abort at Gate A.
