# Memo to George — required architectural rulings

**From:** John, Lead Developer
**To:** George, Lead Architect
**Copy:** Ringo (Owner), Paul (Lead Analyst)
**Date:** 2026-08-18
**Subject:** Config ownership in BFT, plus four open rulings from THERM-SPEC-001 rev B

George,

Ringo has prioritised the BFT configuration defect and approved the therm phase order. Six
things need your ruling before I can execute. The first is the one that blocks real work;
the rest are quick.

---

## 1. Governed-artifact ownership — the priority item

Ringo scoped this to **both apps**. It is one defect pattern with two instances: a
whole-document rewrite that resets ratified fields to hardcoded defaults, with no merge of
the governed values already on disk.

| App | Writer | Governed values clobbered |
|---|---|---|
| BFT | `ConfigManager.save()`, driven by the GUI | `safety.*` (ratified D-005 defaults), `version` |
| pyprojectmgr | `create_baseline_manifest()` on a project that already has a manifest | `project_meta.version`, `meta.version`, `db_uid` |

**Both have fired against BFT since Build 103 shipped.** As of this memo, BFT's
release-contract suite is red again — 3 failed, 3 passed — five days after Build 103
repaired exactly these three tests.

## 1A. BFT — configuration ownership

### The defect

`bundle_config.json` is simultaneously two incompatible things:

- **a delivery payload** — hash-verified by the installer, content-marker checked, and
  asserted by `test_release_contract.py` for the ratified D-005 safety defaults;
- **a runtime scratchpad** — rewritten by the GUI to remember a window geometry and the
  last-used folders.

`ConfigManager.save()` serialises the **entire** document ([config.py:149-158](../bundle_file_tool_v2/src/core/config.py)). So persisting a window position rewrites the `safety` block and the `version` field as a side effect.

Two call sites drive it, both storing pure convenience state:

| Site | Writes |
|---|---|
| `src/ui/bundle_frame.py:311` | `global_settings.last_source_dir`, `last_bundle_save_dir` |
| `src/ui/main_window.py:452` | `session.window_geometry`, `session.first_launch` |

### Evidence it is not theoretical

Build 103 restored the ratified values on 2026-08-13. The file has since reverted **twice**:
`version` back to `2.1.0`, `safety.allow_globs` back to the pre-D-005 extension allow-list,
the five archive/bundle denies gone, and machine-specific absolute paths reinstated. Each
reversion re-breaks `test_release_contract.py`, which is exactly the regression test WP0
added to catch this class of drift.

This will fail the next BFT build's gates unless it is fixed first.

### Three options

| | Approach | Pros | Cons |
|---|---|---|---|
| **A** | **Split the files.** Governed defaults stay in `bundle_config.json`, read-only at runtime. User state moves to a separate store the GUI owns. | Removes the conflict at its root; the delivery payload stops being written at runtime; hash verification becomes meaningful | Largest change; new file path to decide; migration for existing users |
| **B** | **Allowlist on save.** `save()` writes only keys designated user-writable and preserves governed sections from disk. | Smaller; one file | A delivery-payload file is still rewritten at runtime, so formatting and hash drift continue |
| **C** | **Merge on save.** Re-read from disk, apply only changed user-state keys, write back. | Smallest; protects against stale in-memory state | Same as B — the governed file is still a runtime write target |

### My recommendation: A

B and C both reduce the blast radius but leave a hash-verified delivery artifact being
rewritten by an ordinary UI action. Given the installer verifies that file's SHA256 before
and after placement, and the release-contract test asserts its contents, the only stable
answer is that the governed file stops being a runtime write target at all.

**Scope of A, as I read it:**

- `src/core/config.py` — introduce a user-state store, route the four convenience keys to
  it, stop `save()` writing the governed document. `_load_or_create()` still writes
  defaults when the file is absent, which is correct for a fresh install.
- `src/ui/bundle_frame.py`, `src/ui/main_window.py` — call an explicit state API rather
  than the config save.
- Tests — three files exercise `save()` (`test_config.py`, `test_config_migration.py`,
  `test_migration.py`) and 38 assertions across the suite reference `bundle_config.json`.
  Expect real test churn.

**What I need from you:** A, B or C; and if A, where the user-state file should live —
alongside the project, or under `%LOCALAPPDATA%`. The second choice matters for the
delivery standard, because anything inside the project root is a candidate for the
snapshot, the bundle and the installer's file list.

**I have not executed this.** The change alters a ratified artifact's contract, so it needs
your shape before I build it. Say the word and it becomes Build 104.

---

## 1B. pyprojectmgr — governed manifest identity

### The defect

`create_baseline_manifest()` in `src/core/project_init.py` does this when a manifest already
exists (lines 312-325):

1. **renames** the existing manifest to `project_manifest_backup_<ts>.json` — it does not
   read it, merge it, or carry anything forward;
2. **renames** `assets.db` to `assets_backup_<ts>.db`;
3. writes a fresh baseline with `"version": "0.1.0"` hardcoded in **both**
   `project_meta` (line 349) and `meta` (line 449);
4. generates a **fresh `db_uid`** via `uuid.uuid4()`.

So a project that has been governed for months, with a ratified version, silently reverts
to a brand-new identity at version 0.1.0. The backup is a ratchet, not a merge — the
governed values are preserved only in a file nothing reads.

### Evidence

BFT's `.pyprojectmgr` directory carries the fingerprint of this path across the whole
project history — nine `project_manifest_backup_*.json` files. The most recent pair:

```
project_manifest_backup_20260818_022639.json
assets_backup_20260818_022639.db
```

That is **today**, five days after Build 103 set the project version to `2.1.103`. Current
state: `project_meta.version` and `meta.version` are both back to `0.1.0`, and `db_uid` is
`db-6f3763f2`. Because the manifest bytes changed, the `MANIFEST_HASH` constants in
`module_ids.py` and `schema_ids.py` no longer match it either, so a second contract test
fails as a consequence.

This is the same event I predicted in `built_build103.md` §4 — "pyprojectmgr will re-clobber
these on its next export" — and it is the reason that build's governance repairs did not
hold.

### Recommended fix

Preserve governed identity across a re-baseline. When a manifest exists, read it first and
carry forward at minimum:

- `project_meta.version`, `full_name`, `maintainer`, `license`, `team`
- `meta.version`, `description`, `maintainer`
- the existing `db_uid`, unless the operator explicitly asks for a new project identity

and require an explicit flag — `--force-new-identity` or equivalent — before a fresh
`db_uid` and a reset version are written. Backing up is good; discarding is not.

### Relationship to the open defects

This is the same family as PPM-DEFECT-002, where the tool rejects governance state it
produced itself. It is also, in my reading, a material part of why `BFT-WP0-QC-001` has
stayed open since July: each attempt to establish a governed baseline is undone by the next
run of the tool that is supposed to govern it.

---

## 2. therm — promotion contract

`promote(total, *, current=0.0)`, per Paul's revision. Confirm:

- the indeterminate to determinate transition is **one-way** (a second `promote()` raises;
  `set_total()` is the determinate-mode adjustment);
- `current > total` **clamps**, consistent with existing `update()` behaviour;
- `promote(0)` **raises**, consistent with the constructor.

## 3. therm — elapsed time and the clock

Elapsed time is owned by the **core**, not the renderer, because rate is data rather than
presentation. The clock starts at construction, `reset()` restarts it, and it is injected
(`clock: Callable[[], float] = time.monotonic`) so Paul's Gate B can use a fake clock with
no real sleeps. No `start()` is added to the core — that would be a breaking change to a
model that does not need one.

Confirm, or tell me elapsed belongs to the renderer.

## 4. Delivery standard — stager reading a second file

therm needs a SemVer package version *and* a delivery build number, kept separate per
Paul's item 10. The proposal is `VERSION.txt` (generated from `__version__`, never
hand-edited) plus `BUILD.txt` holding a monotonic integer.

The ratified stager reads a single `VERSION.txt`. Reading a second small file is a
parameterisation change rather than a mechanics change, but it touches the ratified
skeleton, so I would rather you confirm than assume.

## 5. pyprojectmgr's vendored therm copy

Ringo has approved retiring it **before** therm 0.2.0. For your awareness of the current
state:

- pyprojectmgr vendors therm at `src/thermometer/` and imports it behind an `ImportError`
  guard; `qc --progress` defaults to `thermometer`, so it is on the critical path of every
  QC run in the family;
- the vendored copy has drifted **19 lines** from ours — pyprojectmgr's own header-policy
  tooling rewrote comment separators inside a vendored library;
- the directory also holds a stray `thermometer.zip` and a duplicate
  `thermometer__init__.py` beside the real `__init__.py`.

Retiring it at therm 0.1.0 is a no-behaviour-change swap, which is the cheapest possible
moment. Your call on whether that lands as its own pyprojectmgr build and where it sits
relative to PPM-DEFECT-001 and -002.

## 6. Two smaller items in your area

**The integrity guard's path rule has a gap.** `_BUNDLE_ARTIFACT_RE` requires `_bundle_`
with a trailing underscore, or `src_bundle`. Tested:
`EDSS_src_bundle_v1_7_0_Build_151.txt` matches; `therm_bundle.txt` and
`bft_self_build103.txt` do **not**. Our actual naming habit is singular, so the primary
control misses it and the Build 103 content rule is carrying the load. It held — a real
nested-bundle specimen was caught by content — but I would widen the pattern.

**`PREP_AND_STAGE_BFT.bat` options are broken.** The argument loop runs `shift` before
`%~dp0` is read, and `shift` moves `%0`, so with any option the stager resolves its root to
`C:` and aborts on the root guard. The no-argument path is unaffected, which is why Build
103 installed cleanly. `/dryrun`, `/y` and `/norun` are all unusable. Fix is a block move
above `:parseargs`; I have a verified corrected copy ready. It touches the ratified stager,
so it is yours to approve.

---

## Summary of what I need

| # | Ruling | Blocks |
|---|---|---|
| 1A | BFT config ownership: A, B or C; and the state file's location | BFT Build 104 — Ringo's priority item |
| 1B | pyprojectmgr: preserve governed identity on re-baseline, behind an explicit flag | pyprojectmgr build; BFT's governance repairs holding |
| 2 | Promotion contract | therm 0.2.0 Phase 3 |
| 3 | Elapsed time ownership and injected clock | therm 0.2.0 Phase 3 |
| 4 | Stager may read `BUILD.txt` | therm Phase 1 |
| 5 | Vendored-copy retirement sequencing | pyprojectmgr build |
| 6 | Path-rule widening; stager option fix | BFT, next build |

Items 2, 3 and 4 unblock therm Phase 1, which is otherwise ready to start.

— John
