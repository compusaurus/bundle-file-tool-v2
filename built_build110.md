# BFT v2.1 Build 110 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_110_discovery_performance.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-24
**Authorised by:** Ringo (Product Owner)
**Ratified scope:** `ARCH-RULING-2026-08-24-01` (George), responding to
`bft_discovery_performance_analysis_john.md` (John)
**Baseline:** Build 109
**Supersedes for installation:** Build 109. See §8.

---

## 1. Scope delivered

| # | Ruling | Item | Status |
|---|---|---|---|
| 1 | PERF-BFT-001 | In-flight `os.walk` directory pruning | Delivered |
| 2 | PERF-BFT-002 | Throttled dual-counter discovery telemetry | Delivered |
| 3 | UX-BFT-001 | Non-blocking oversize file skipping | Delivered |
| 4 | GOV-BFT-002 | Expanded Tier 1 default deny patterns | Delivered |
| 5 | TEST-SUITE | Equivalence and telemetry-gap acceptance gates | Delivered, 7 tests |

**840 → 847 tests. Coverage 90.37% → 90.25%.**

### Scope deviation from the ruling — build number

The ruling directs the work into "the Build 109 delivery candidate". Build 109
was already delivered on 2026-08-23, is installed on Ringo's workstation
(`v2.1.109` in the recording), and its record states that it supersedes 106–108.
Merging new payload into a delivered build number would break supersession and
installer identity, so this ships as **Build 110**. Ringo's authorisation —
"the next governed build" — is consistent with that reading. Ruling items 5, 6
and 7 in George's §4 matrix (Option B+ headers, tri-layer defence, F-02 config
anchoring) were already delivered in Build 109 and are unchanged here.

---

## 2. The defect

Ringo's screen recording of 2026-08-24 10:02:13 showed discovery apparently
hanging for ~10 seconds against `pyprojectmgr_project/pyprojectmgrV2`.

Measured against that same tree with his live configuration:

| Measure | Build 109 |
|---|---:|
| Filesystem nodes visited | 19,164 |
| Files included | 1,190 |
| Wasted node visits | 17,974 (93.8%) |
| Discovery elapsed | 16.04s |
| **Longest unbroken progress silence** | **13.15s** |

Three compounding causes:

**D1** `Path.rglob("*")` offers no pruning hook, so every node under a denied
directory was visited and then discarded. 16,685 of the 19,164 nodes were
inside `.venv` — which the deny list already excluded. The deny list was
correct; it was consulted after the walk instead of during it.

**D2** `path.resolve()` ran on every file before filtering — 4.08s of the
runtime, spent normalising paths that were immediately thrown away.

**D3** `emit()` sat inside the `should_include()` branch, so progress advanced
only on *matched* files. Walking a dense excluded subtree produced no events at
all. PyThermX rendered faithfully; it simply received nothing for 13.15
seconds. The reported throughput described matched files, not work done, which
made a healthy disk look saturated.

---

## 3. Result

Same tree, same configuration, after the change:

| Measure | Build 109 | Build 110 |
|---|---:|---:|
| Nodes visited | 19,164 | **1,280** |
| Discovery elapsed | 16.04s | **1.71s** |
| Longest telemetry gap | 13.15s | **0.004s** |
| Files included | 1,190 | **1,190** |

**9.4× faster, and the discovered file set is bit-identical.** The prune set is
derived from the deny patterns already in force — only `**/NAME/**` forms
qualify — so nothing is excluded that was not already being filtered out. That
equivalence is pinned by
`test_discover_files_output_identical_to_unpruned_baseline`.

End-to-end on the live tree: 1,666 files discovered in 1.68s, manifest built in
2.37s, bundle formatted in 0.76s. Total 4.81s.

---

## 4. Oversize assets (UX-BFT-001)

`create_manifest()` raised `FileSizeError` on the first oversize file, which
`bundle_frame.py` turned into a blanked preview and a disabled Create Bundle
button. In the recording, one 20.58 MB asset made 1,335 healthy files
unbundlable.

Exceeding `max_file_mb` is now a recorded exclusion:

- the file is kept out of the payload, so the limit is still enforced;
- it is recorded in `BundleManifest.skipped_entries` as
  `{path, reason, size_mb, limit_mb}`, with a `skipped_count` in metadata;
- the preview leads with a notice naming the files and the remedy;
- bundle creation stays enabled for everything that fits.

Verified against the recording's own file: `assets/splash/pyprojectmgr_splash.mp4`
(20.58 MB) is now skipped, and the other 1,664 files bundle normally.

`skipped_entries` defaults to an empty list, so every bundle that skips nothing
produces byte-identical output to Build 109.

---

## 5. Deny-list expansion (GOV-BFT-002)

Tier 1 additions to the shipped defaults, per ruling §3.3: `**/venv/**`,
`**/.pytest_cache/**`, `**/.mypy_cache/**`, `**/.ruff_cache/**`,
`**/node_modules/**`, `**/*_bak*/**`, `**/_legacy_backup/**`,
`**/_governance_backups/**`.

Tier 2 (`deliverables/`, `reports/`, `htmlcov/`) is deliberately **not** in the
defaults — those are project output directories and remain user-governed.

Each Tier 1 entry is written as `**/NAME/**` so discovery can prune it rather
than walk and discard it. `**/*_bak*/**` is a deliberate exception: it contains
a wildcard in the directory segment, so it filters correctly but cannot be
pruned. That is by design — `prunable_dir_names()` accepts only unambiguous
whole-subtree patterns, and being conservative there is what guarantees output
equivalence.

The existing governed `bundle_config.json` was updated additively — four
patterns appended, none removed, so no user customisation was lost.

---

## 6. Defect found and fixed during implementation

The first implementation primed the emit throttle by subtracting one interval
from `time.monotonic()`. That silently failed: `monotonic()` returns a large
float, so `t - (t - 0.10)` evaluates to `0.09999999998`, just below the
threshold, and the first scan event never fired. On a tree small enough to
finish inside one interval, *no* dual-counter event was emitted at all.

Caught by `test_discover_files_reports_scanned_and_included_counts`. Replaced
with an explicit `None` sentinel. Recorded because the failure mode is invisible
in review and would have shipped as "the bar is dead for the first 100ms".

---

## 7. Verification evidence

- Full suite: **847 passed, 0 failed**. Coverage **90.25%** against an 85% gate.
- New Build 110 tests: 7, all passing.
- Two Build 109 tests updated to the ratified contract rather than deleted:
  - `test_discover_files_reports_every_file` → `..._reports_monotonically_and_closes_determinate`.
    Per-file emission is no longer the contract; monotonicity and a determinate
    close still are.
  - `test_create_manifest_enforces_file_size_limit` →
    `..._skips_oversize_file_without_raising`. The limit is still asserted — the
    file does not enter the bundle — but as an exclusion, not a crash.
- Governance chains re-derived in order: `bundle_config.json` digest →
  `governance.governed_config_sha256` in the manifest → manifest SHA-256 →
  `MANIFEST_HASH` in `module_ids.py` and `schema_ids.py`.
  Verified by `test_generated_governance_ids_reference_current_manifest`.
- Layer C write protection cleared for the config edit and **restored**; the
  attribute is `A R` as shipped.
- Release identity agrees across all seven package-owned sources.
- End-to-end bundle of the live tree completes in 4.81s with 2 oversize skips.

---

## 8. Supersession and installation

This kit installs over **2.1.109 only**. Build 109's payload included the
tri-layer defence and header allow-list, which this build does not restate;
installing 110 onto 2.1.108 or earlier would leave those items absent. Gate A0
enforces the single-predecessor rule and fails loud on anything else.

Installation is through `PREP_AND_STAGE_BFT.bat` in the project root, which
expects exactly one delivery zip in `%USERPROFILE%\Downloads`. The stager is
host-owned and is not replaced by this kit. Team Delivery Standard v2.

Rollback material is written to `bft_build110_rollback\` with original and new
file ledgers, before any target byte is mutated.

---

## 9. Files changed

| Path | Change |
|---|---|
| `src/core/writer.py` | `prunable_dir_names()`, pruned walk, lazy resolve, throttled dual-counter emit, oversize soft-skip |
| `src/core/models.py` | `BundleManifest.skipped_entries` |
| `src/core/config.py` | Tier 1 deny defaults |
| `src/ui/bundle_frame.py` | Skipped-file banner; preview no longer blanked |
| `src/core/version.py`, `src/core/module_ids.py`, `src/database/schema_ids.py` | Version and manifest hash |
| `bundle_config.json`, `VERSION.txt`, `pyproject.toml` | Release identity; additive deny entries |
| `.pyprojectmgr/project_manifest.json`, `.pyprojectmgr/project_spec.json` | Version; governed config digest |
| `tests/unit/test_discovery_performance_b110.py` | New — 7 acceptance gates |
| `tests/unit/test_writer.py`, `tests/unit/test_release_contract.py`, `tests/integration/test_progress_monotonic_contract.py` | Updated to ratified contracts |

---

## 10. Open items not in this build

- **Tier 2 deny governance** (`deliverables/`, `reports/`, `htmlcov/`) remains a
  per-project decision, per ruling §3.3.
- **Paul's benchmark-harness integration** into the QA staging suite
  (ruling §4, Paul) is not included here; the reproducible harness ships in
  `docs/discover_files_performance_patch_proposed.py`.
- **`*_bak*` pruning.** The pattern filters but cannot prune. If backup trees
  prove to be a measurable cost in practice, the prune derivation would need to
  handle wildcard segments — deliberately out of scope for a build whose safety
  argument rests on output equivalence.
