# BFT v2.1 Build 111 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_111_open_bundle_progress.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-24
**Authorised by:** Ringo (Product Owner)
**Baseline:** Build 110
**Supersedes for installation:** Build 110. See §7.

---

## 1. Scope delivered

| # | Item | Status |
|---|---|---|
| 1 | Determinate byte progress for the bundle read phase | Delivered |
| 2 | Determinate line progress for the parse phase, both profiles | Delivered |
| 3 | `ThrottledReporter` — shared rate-limited reporting primitive | Delivered |
| 4 | Open Bundle wired to PyThermX with a size-based threshold | Delivered |
| 5 | `ProfileBase.parse_stream` contract extension, backward compatible | Delivered |
| 6 | Acceptance gates for purity, determinacy and throttling | Delivered, 12 tests |

**847 → 859 tests. Coverage 90.25% → 90.41%.**

---

## 2. The gap

Extract Files has reported through PyThermX since Build 107. **Open Bundle never has.**
`unbundle_frame.py` called `parser.parse_file()` directly, and `parser.py`
contained no progress plumbing at all — `parse()` and `parse_file()` took no
sink, so there was nothing to wire. The user got one log line, "Opening bundle
file...", and a blocked Tk main thread.

Measured on a 41.3 MB bundle (1,092 entries, 395,856 lines) built from the
live `pyprojectmgrV2` tree: **0.80s with zero progress events**. The service
facade at `service.py:268` already emitted `PHASE_PARSE`, but the GUI does not
use the facade — the capability existed and the running code went around it.

---

## 3. What was built

**Read phase — determinate from the first event.** `parse_file()` reads in
1 MiB chunks when a sink is supplied, reporting `handle.buffer.tell()` against
`stat().st_size`. Byte position is taken from the file handle rather than the
decoded length, because character and byte counts diverge for multi-byte
encodings and the byte figure is what the disk is actually delivering.

**Parse phase — also determinate.** Both profiles begin from
`text.splitlines(keepends=True)`, so the line total is known before either loop
starts. This did not need the indeterminate mode: it reports a true percentage.
The message carries the recovered file count — `"127 files recovered"` — because
lines are what the bar can honestly measure while files are what the reader
wants to know.

**`ThrottledReporter`** (`core/progress.py`) centralises the emit discipline so
each loop adds two lines rather than eight. It reports on a clock, never on
"interesting" iterations, which is the Build 110 lesson stated as a primitive.

**Contract extension.** `ProfileBase.parse_stream` gains a keyword-only
`progress=None`. A profile written against the earlier contract keeps working:
`BundleParser._accepts_progress()` inspects the signature and calls the
unreported form when the parameter is absent.

**Threshold.** Open Bundle cannot use the existing `min_files` rule — the entry
count is the *result* of the work being measured. `_parse_progress_enabled()`
gates on file size instead, governed by `ui.progress.min_parse_mb` (default 2.0).

---

## 4. Result

| Measure | Build 110 | Build 111 |
|---|---:|---:|
| Progress events opening a 41.3 MB bundle | **0** | 9 |
| Longest gap with no event | full 0.80s | **0.219s** |
| Read phase | opaque | determinate, bytes |
| Parse phase | opaque | determinate, lines |
| Parse overhead with a sink attached | — | within measurement noise |
| Entries and content parsed | — | **byte-identical** |

Equivalence is pinned by two tests, not asserted: `parse_file()` takes a
different read path when a sink is supplied, so "the sink does not change the
result" is a real claim.

---

## 5. Defects found and fixed during implementation

**A `TypeError` fallback that would have swallowed real defects.** The first
version detected legacy profiles by calling `parse_stream(text, progress=...)`
and catching `TypeError`. A genuine `TypeError` raised *inside* parsing would
have been caught by the same handler and silently retried without a sink,
turning a real defect into a missing progress bar. Replaced with signature
inspection. Pinned by `test_type_error_inside_parsing_is_not_swallowed`.

**Two tests that patched an instance the parser never used.**
`ProfileRegistry.get()` constructs a fresh profile on every call, so
`monkeypatch.setattr(profile, ...)` never reached the object under test. One
test failed honestly; **the other passed vacuously** — it asserted legacy-profile
tolerance while exercising the real, progress-aware profile. Both now patch the
class. The passing one is the more instructive: a green test that verifies
nothing is worse than a red one.

**A 20% parse overhead from an import statement.** `ThrottledReporter.tick()`
had `import time` in its body — a `sys.modules` lookup on every one of 395,856
lines. Hoisted to module scope; overhead fell to within measurement noise.

**A line-ending regression I introduced.** The version bump wrote the governed
JSON files with `write_bytes`, giving LF, where every prior build used
`write_text` and Windows text mode, giving CRLF. `test_a_modified_configuration_is_detected`
copies the config through `read_text`/`write_text` and compares digests, so an
LF original no longer matched its copy. Caught by that test; convention
restored. Worth recording because the cause was over-applying the Build 110
delivery-manifest lesson: that file needed explicit bytes precisely *because*
text mode doubled its CRLFs, and this file needs text mode for the opposite
reason. The correct write method is a property of the file, not a rule.

---

## 6. Verification evidence

- Full suite: **859 passed, 0 failed**. Coverage **90.41%** against an 85% gate.
- New Build 111 tests: 12, covering purity, determinacy, monotonicity,
  throttling, both profiles, contract tolerance, and error transparency.
- No existing test required modification — the contract extension is
  backward compatible by construction.
- Governance chain re-derived in dependency order: `bundle_config.json` digest →
  `governance.governed_config_sha256` → manifest SHA-256 → `MANIFEST_HASH` in
  `module_ids.py` and `schema_ids.py`.
- Layer C write protection cleared for the config edit and **restored**.
- Release identity agrees across all seven package-owned sources.
- End-to-end: 41.3 MB / 395,856-line bundle parsed with 9 events, 0.219s worst
  gap, output byte-identical to the unreported path.

---

## 7. Supersession and installation

Installs over **2.1.110**, and re-enters idempotently on **2.1.111**. Gate A0
accepts both and fails loud on anything else. Build 110 carried the discovery
performance engine and oversize handling, which this payload does not restate,
so installing onto 2.1.109 or earlier would leave those absent.

Installation is through `PREP_AND_STAGE_BFT.bat` in the project root, which
expects exactly one delivery zip in `%USERPROFILE%\Downloads`. The stager is
host-owned and is not replaced by this kit. Team Delivery Standard v2.

Rollback material is written to `bft_build111_rollback\` before any target byte
is mutated.

---

## 8. Files changed

| Path | Change |
|---|---|
| `src/core/progress.py` | `ThrottledReporter`, `EMIT_INTERVAL_S`, module-scope `monotonic` |
| `src/core/parser.py` | `progress` on `parse`/`parse_file`, chunked reporting read, `_accepts_progress` |
| `src/core/profiles/base.py` | `parse_stream` contract extension |
| `src/core/profiles/plain_marker.py` | Reporting in both bounded and legacy paths |
| `src/core/profiles/markdown_fence.py` | Reporting in `parse_stream` |
| `src/ui/unbundle_frame.py` | Open Bundle via `run_with_progress`; size threshold |
| `src/core/config.py` | `ui.progress.min_parse_mb` default |
| `src/core/version.py`, `src/core/module_ids.py`, `src/database/schema_ids.py` | Version, manifest hash |
| `bundle_config.json`, `VERSION.txt`, `pyproject.toml` | Release identity |
| `.pyprojectmgr/project_manifest.json`, `.pyprojectmgr/project_spec.json` | Version, config digest |
| `tests/unit/test_open_bundle_progress_b111.py` | New — 12 acceptance gates |
| `tests/unit/test_release_contract.py` | Expected version |

---

## 9. Open items not in this build

- **Memory.** `read_text()` plus `splitlines(keepends=True)` holds a large
  bundle roughly twice. Progress makes the cost visible; it does not reduce it.
  A streaming parse would be a materially larger change.
- **Extract Files emits per entry, unthrottled.** Not a defect today — extraction
  does real I/O per entry, so events are naturally paced — but it is the same
  shape of assumption that failed in discovery, and `ThrottledReporter` now
  exists to fix it cheaply if a very large bundle ever proves it a problem.
- **`service.py`'s `PHASE_PARSE` path remains unused by the GUI.** The facade and
  the UI still reach parsing by different routes. Consolidating them is a design
  question, not a defect.
