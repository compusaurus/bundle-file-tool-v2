# Developer Response — Rulings, Findings, and Build 109 Scope

**Document Ref:** `BFT-DEV-RESPONSE-2026-08-23-01`
**From:** John, Lead Developer
**To:** George (Lead Architect) — *rulings accepted, two corrigenda requested*
**Cc:** Paul (Lead Analyst) — *findings verified, one disputed*
**Cc:** Ringo (Product Owner) — *one item clears a blocker on your kit*
**Date:** 2026-08-23
**Responds to:** `ARCH-RULING-2026-08-23-01` (George) and `BFT-ANALYSIS-2026-08-23-01` (Paul)
**Status:** Verification complete against the live tree. No code changed. Awaiting go-ahead for Build 109.

---

## 1. Disposition

**George's rulings — accepted in full, no amendment requested.** Option B+, the D+C+A tri-layer
defence, GOV-POL-001, the OperationProgress freeze, the Build 105–108 technical ratifications,
and the 109–111 sequencing are all sound and I can execute them as written. Two small
corrigenda are requested in §5, neither of which changes a ruling.

**Paul's findings — I verified all eight against the live tree rather than accepting them on
paper.** Seven are confirmed, including two that land on code I shipped. One does not
reproduce, and I am disputing it with evidence because acting on it would block Ringo
unnecessarily.

I want to be direct about F-06 before anything else: Paul found a defect in the service facade
that is the *same defect class* I found and fixed in the CLI two days ago, and my own facade
test was too weak to catch it. That is covered in §4.

---

## 2. Verification ledger

Every finding checked against the installed 2.1.108 tree, not against a bundle.

| Ref | Finding | Verdict | Evidence |
|---|---|---|---|
| **F-01** | Default header injection corrupts structured text | **Confirmed** | Independently reproduced before Paul's review; `json.load()` fails at line 1 col 1 on a default extract |
| **F-02** | GUI bypasses governed-config anchoring | **Confirmed** | `src/ui/main_window.py:65` — `ConfigManager("bundle_config.json")` |
| **F-03** | PREP increments the outgoing build `+1` | **Not reproducible** | Live stager references `VERSION.txt` three times, all reads. See §3 |
| **F-04** | JSONL validates but is not registered | **Confirmed** | `src/core/config.py:468` — `valid_profiles = ['plain_marker', 'md_fence', 'jsonl']`; registry provides two |
| **F-05** | Tri-UI service boundary not in force | **Confirmed** | `cli.py`, `ui/bundle_frame.py`, `ui/unbundle_frame.py` all construct core classes directly |
| **F-06** | Service extraction progress not granular | **Confirmed** | `src/core/service.py:290` — `extract_manifest(manifest, Path(output_dir))`, no sink passed |
| **F-07** | Frozen ruling and implementation differ | **Confirmed** | Field types verified by introspection; see §5.2 |
| **F-08** | Source header/lifecycle metadata inconsistent | **Confirmed** | Known documentation debt |

---

## 3. F-03 — disputed, and it matters today

**Paul's finding:** the supplied `PREP_AND_STAGE_BFT.bat` writes `outgoing build + 1` after a
successful install, so a 105 → 108 jump would leave `VERSION.txt` reading `2.1.106`. He rates
it High/potentially release-blocking and advises Ringo not to stage Build 108 through the
current PREP path until it is resolved.

**It does not reproduce on the live stager.** Every reference to the version file:

```
42:  set "VERSIONFILE=%ROOT%\VERSION.txt"          -- path assignment
72:  if not exist "%VERSIONFILE%" ( ... abort )    -- existence check
92:  set /p VERSTR=<"%VERSIONFILE%"                -- READ, to name the snapshot
```

There is no write redirect to that file anywhere in the script. It is not a matter of the
increment being conditional — the arithmetic and the write are both absent. The script states
the contract twice in its own output:

> `VERSION.txt is package-owned and is not incremented by this stager.`
> `=== Delivery complete. VERSION.txt remains package-owned; stager did not increment it. ===`

And it is bound by a passing release-contract test, `test_stager_never_increments_package_owned_version`,
which asserts `set /a NEWBUILD` is absent, that the increment write line is absent, and that
the package-owned declaration is present.

**Why Paul saw otherwise.** His evidence set was Build 102/103/104 records plus the Build 108
source, tests, and scripts bundles. The `+1` behaviour was real, and it was closed by
ratification **D-004 — the delivery payload owns the version, the stager never increments it**
— in Build 103. An older stager in the review material is the most likely source. This is a
genuine hazard of reviewing from bundles rather than the installed tree, and it is worth
noting for future reviews rather than being anyone's fault.

**Consequence for Ringo:** the blocker Paul raises does not apply. The Build 108 kit in your
Downloads is clear to stage. I additionally rehearsed the 107 → 108 upgrade end to end against
a throwaway clone before delivery: all gates green, `VERSION.txt` reads `2.1.108` afterwards.

**One thing Paul is right about regardless:** the *contract* should be stated, not merely
observed. I will add the installation matrix he asks for — 105/106/107/108 → 109 all leaving
`VERSION.txt`, `core.version`, CLI `--version`, package metadata, config version, and manifest
metadata at one identical value — to the Build 109 gates. The behaviour is correct today; it
is not yet proven correct across every permitted predecessor.

---

## 4. F-06 — my defect, and my test was the reason it survived

`BundleToolService.extract_bundle()` emits a write event at 0 and another at completion, and
never passes its sink into `BundleWriter.extract_manifest()`. Paul measured write currents of
`[0, 2]` on a two-file extraction rather than a rising per-file sequence. Confirmed at
`service.py:290`.

This is the **same defect class** as the Build 107 CLI omission I found last week: a progress
sink that is accepted, threaded partway, and then dropped at the final call. Two instances of
one mistake means it is not a slip, it is a pattern I need to design against.

The reason it survived is the part worth recording. `emit()` deliberately swallows sink
failures so a broken reporter can never break the operation it observes — correct, and I would
not change it. The cost is that **a missing sink is indistinguishable from a working one from
the inside**: nothing raises, nothing logs, the extraction succeeds. Only rendered output or an
asserted event sequence tells them apart, and my facade test asserted only that a completion
phase exists.

**Build 109 remedy, broader than the instance:** a single parametrised test that walks every
public entry point accepting a `progress` argument — service, CLI, and both Tk frames — and
asserts a monotonic per-unit event sequence, not merely the presence of a terminal phase. That
closes the class rather than the two occurrences.

---

## 5. Two corrigenda requested

Neither changes a ruling. Both keep the permanent record accurate.

### 5.1 Build progression matrix — PyThermX column

`ARCH-RULING-2026-08-23-01` §4 records Build 106 as using **PyThermX 0.1.0 (Stub)**. Build 106
shipped no PyThermX at all — its payload was the service facade and the `OperationProgress`
event model, with no renderer and no dependency. **Build 107 introduced 0.2.0** as the first
vendored wheel. The distinction matters because Build 106's whole point was that the event
model carries no renderer dependency; recording a PyThermX version against it inverts that.

Suggested correction: `Build 106 | 622 | 90.09% | none (event model only) | Service Facade, Progress Event`.

### 5.2 OperationProgress corrigendum — freeze the implemented shape

Paul's F-07 is correct. The ruling text and the code describe different schemas. The
implemented form, verified by introspection:

| Aspect | Ruling text | Implemented |
|---|---|---|
| `mode` | dataclass field | derived `@property`, included in `to_dict()` |
| `current` | `int` | `float`, default `0.0` |
| `total` | `Optional[int]` | `Optional[float]`, default `None` |
| `message` | `str` | `Optional[str]`, default `None` |
| Operation vocabulary | `bundle`, `unbundle`, `validate` | `bundle`, **`extract`**, `validate` |

**I recommend freezing the implemented form**, for the reason Paul gives: a derived `mode`
cannot contradict `total`, whereas a stored field can. `float` counts allow byte-denominated
progress without a second type. `Optional[str]` message avoids forcing empty strings through
the wire.

The one item I would flag for a deliberate decision rather than a rubber stamp is the
operation constant. The code says `extract`; the ruling says `unbundle`. The CLI subcommand
users type is `unbundle`. If the Web adapter is going to serialise this vocabulary, the
mismatch between the wire value and the command name should be settled now, while there is
exactly one consumer pair, rather than after Build 111. My preference is to keep `extract` in
the contract — it names the operation, not the command — and document the mapping.

Phase vocabulary, `Optional[float]` percent semantics, the never-raise sink, and the AST
layering rule are ratified exactly as implemented. No change needed there.

---

## 6. Layer C — notes before I build it

I can implement the filesystem write-protection as ruled. Four things I want on the record
first, because they change the implementation rather than the decision.

**Why `+R` genuinely works against this threat.** The observed writer was old Python code doing
an ordinary open-for-write on the governed file. On a read-only file that raises
`PermissionError` immediately, before any content is written. It does not stop a determined
process that clears the attribute first — but nothing short of ACLs would, and the stale-copy
scenario we actually observed is fully covered.

**F-02 is a hard prerequisite, not a parallel task.** Paul is right, and the consequence is
concrete: if the GUI keeps resolving `bundle_config.json` from the working directory, Layer C
protects the installed file while the application reads and writes a different, unprotected
one. Shipping C before F-02 would produce a build that *looks* hardened and is not. **F-02
lands first in Build 109, in the same kit.**

**Every installer exit path must restore protection.** The strip/apply pair has to survive
success, abort, rollback, and idempotent re-run. A failed install that leaves the config
writable is worse than no protection, because the next run assumes it is protected. I will
gate this explicitly and test the abort path, not just the happy path.

**The backup path needs attention.** Gate B copies the existing config into the rollback
folder. A read-only source copies fine, but the copy inherits the attribute, and rollback then
needs to strip it before restoring. That is a small detail that will silently break recovery
if it is missed, so it gets its own test.

---

## 7. Build 109 as I would execute it

Accepting George's scope with Paul's expansions folded in.

| Item | Source | Note |
|---|---|---|
| Option B+ header allow-list | George | Extension and exact-filename sets, case-normalised; everything else byte-pure |
| Multi-format round-trip at **default** settings | George / Paul | The control that was missing; includes extensionless files and binaries |
| F-02 GUI config anchoring | Paul | **Prerequisite for Layer C** |
| Layer C filesystem protection | George | With abort/rollback/idempotent coverage |
| Layer A hash + process telemetry | George | Reports expected/actual hash, app version, executable path, timestamp |
| Version-surface installation matrix | Paul | 105/106/107/108 → 109 all resolve to one value |
| Progress sink pass-through test (class-level) | John, from F-06 | Every entry point accepting `progress` |
| Supersession cross-references in build records | George | Documentation |

**Acceptance gates.** Structured formats parse with their native engines after a default
extract; `#`-comment formats carry the provenance block; no config is created in the working
directory from any launch location; OS protection survives success, failure and rollback;
every permitted predecessor installs to one consistent `2.1.109`; per-unit progress is
monotonic at every entry point; full kit rehearsal passes from a throwaway clone.

Per Paul's instruction, **each defect gets a test that reproduces it before the fix lands.** I
have used that pattern on the last two builds — restoring the defect must make the new test
fail — and it is what turned the CLI progress omission from an anecdote into a guarded
contract.

**Not in Build 109:** WP5, Tkinter facade migration, cancellation, JSONL, Web. All correctly
placed in 110/111.

---

## 8. What I need to proceed

1. **George** — the two corrigenda in §5, in particular the `extract` vs `unbundle` operation
   constant, since freezing the wrong one costs more after the Web adapter exists.
2. **George** — confirmation that F-02 leading Layer C within Build 109 is acceptable
   sequencing.
3. **Ringo** — go-ahead to start Build 109.

I support Paul's F-05 recommendation that **Tkinter facade migration join CLI migration in
Build 110**. Putting one interface on the service while the other stays on direct construction
would leave two orchestration paths and make the Web adapter a third. If George agrees, that
belongs in the 110 scope explicitly rather than by implication.

---

## 9. For Ringo — immediate

**You are clear to stage Build 108.** The version-ownership blocker Paul raises does not apply
to the live stager (§3). The kit in Downloads is `INSTALL_BUNDLETOOL_v2_1_108_pythermx_tk.zip`,
sha256 `d99c0ee1…`, and it is the only delivery zip present, so the stager will not complain.

**Layer D quarantine — your action, and it is the layer that actually stops the recurrence.**
Confirmed stale runnable trees:

- `bundle_file_project/docs/bft_qc_target_base_20260724` — VERSION 2.1.102, no `ReadOnlyConfigError` guard
- any historical bundle previously extracted as a runnable tree

Per GOV-POL-001 these become inert `.zip` archives under `archives/`. Worth saying plainly:
Layers C and A are detection and hardening, but **D is the one that removes the cause we
actually observed.**

---

**John**
Lead Developer
