# BFT v2.1 Build 114 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_114_selection_service.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-25
**Delivers:** v2.2 Selection Workspace **WP3 — Service Facade and CLI Adapter**
**Authority:** `ARCH-RULING-2026-08-25-01`, `ARCH-RULING-ADDENDUM-2026-08-25-01`,
`BFT-ANALYSIS-2026-08-25-02`, and Ringo's rulings of 2026-08-25
**Supersedes for installation:** Builds 106 through 113. See §9.

---

## 1. Version identity, settled

Ringo answered the question I left open in Build 113 §7:

> "My original direction was to target a Build 2.2 and we are in incremental steps
> moving toward that goal. The workspace should ship at the current Build, always."

So: **v2.2 is the destination, reached incrementally, and no work package is held
back waiting for a version event.** Build numbers stay monotonic and this ships as
`2.1.114`. There is no minor-version turnover in this build and none is scheduled;
whoever declares 2.2 does so when the programme is complete, not as a gate on WP3.

**983 → 1,169 tests. Coverage 90.73% → 91.42%.**

## 2. What WP3 delivers

Build 113 built the ladder. It had no way in. WP3 is the way in.

```
bundle-tool plan .
bundle-tool plan . --explain src/app.py
bundle-tool plan . --preset python-env --preset vcs --report plan.json
bundle-tool plan . --list | xargs wc -l
```

Four service methods, per spec §11 and Paul's §13.1:

| Method | Reads files | Purpose |
|---|---|---|
| `plan_bundle(...)` | **no** | scan metadata, assemble six ladder layers, decide every path |
| `explain_selection(plan, path, fmt)` | no | the rule chain for one path or all |
| `preview_bundle(plan, limit)` | no | counts, estimate, order, confirmations |
| `create_bundle(..., plan=)` | yes | write exactly what the plan chose |

The plan opens nothing. That is asserted, not assumed: two tests patch
`builtins.open` and fail if any file under the source tree is opened during
planning. It is the premise the whole workspace rests on — if planning ever
starts reading, a 4,000-file tree stops being re-plannable on a checkbox click.

### 2.1 New modules

- **`src/core/metadata_scan.py`** — the walk. Stats, never opens; prunes a
  classified directory **before descent**, so a 400-file vendored tree is never
  touched. Unreadable files become `Unknown` entries with a reason rather than
  vanishing. WP5's cache will sit on this seam.
- **`src/core/rule_sources.py`** — where rules come from. Ten shipped presets,
  the `--rules` file loader, CLI and session overrides. Each source lands on its
  own ladder layer, and **a source cannot choose its layer**: a test asserts every
  shipped preset produces Layer 4 rules and only Layer 4 rules.
- **`src/cli_plan.py`** — the `plan` command. Renders; decides nothing.

## 3. Three defects this build found in itself

All three would have shipped. All three are the same shape: each layer correct,
the composition wrong.

### 3.1 `--include` did not narrow anything

Build 113 established that an allow-list is a base-action switch, and tested it.
The service then resolved the base action from the **union** of every layer's
allow-list — and the governed default is `**/*`, which is always present. So
`--include src/**` added a rule that changed nothing, and `docs/`, `notes.log`
and everything else stayed in the bundle. Silently.

The unit test passed the whole time, because the unit was right.

`resolve_base_action()` now takes the allow-list from the **highest-priority
layer that supplies one** and ignores the rest. Six tests cover the ladder
positions, and an end-to-end test asserts `--include src/**` yields exactly two
files on a five-file tree.

### 3.2 `plan` and `bundle` anchored differently

`bundle` defaulted `base_path` to `Path.cwd()` before planning. The plan then
computed every relative path against the current directory instead of the source
root, and the writer rejected the result: *"File ... is outside the specified base
path."*

Caught by the parameterised gate that drives every selection flag through both
commands and compares the file sets. That gate exists because Build 107 shipped
`unbundle --progress` doing nothing — a flag threaded into one path and dropped
from another — and it earned its place on the first run.

### 3.3 Routing `--include` through the ladder would have silently narrowed every existing command

The engine uses strict glob semantics, where `*` does not cross a separator. The
Build 113 discovery filter did not: `--include '*.py'` matched `src/app.py`, as
it does in git, rsync and every tool an operator has muscle memory for.

Measured, not assumed:

| pattern | path | legacy | strict ladder |
|---|---|---|---|
| `*.py` | `app.py` | ✓ | ✓ |
| `*.py` | `src/app.py` | ✓ | **✗** |

Routing the flag through unchanged would have stopped `--include '*.py'` from
matching nested files, with no error and no message, in the build whose entire
subject is that selections stop changing behind your back.

`expand_bare_pattern()` anchors a pattern that names no directory at any depth.
The **engine stays strict**; the CLI adapter translates what a human typed. A
pattern containing `/` is already explicit about position and is left alone.

## 4. The one behaviour change, and why it is announced

**`--exclude` now adds to the default rules instead of replacing them**, per
Paul's ruling. Under the old behaviour `--exclude '*.log'` replaced the entire
governed deny list, silently re-admitting `.git`, `node_modules`, `__pycache__`
and everything else. That is how an environment ends up in a bundle.

A flag whose meaning changed must say so, so every run that uses it prints to
stderr:

```
note: --exclude now adds to the default rules instead of replacing them.
      Pass --no-default-rules for the previous behaviour.
```

`--no-default-rules` is the escape hatch, and it does **not** disable Priority 0:
a test force-includes `**/*` with defaults off and asserts a nested bundle is
still `Blocked`.

## 5. Stdout purity — the WP3 exit gate

Paul's three-way rule (S-10), each clause a subprocess test:

| | stdout |
|---|---|
| `plan` | may write — the plan *is* the artifact |
| `bundle` without `--output` | bundle text, nothing else |
| `bundle` with `--output` | **empty** |

Subprocesses on purpose. Stdout purity is a property of the process, and an
in-process test capturing `sys.stdout` cannot see a stray print from a library or
a progress bar on the wrong stream. One test counts **bare** CR bytes rather than
decoding first — Build 108's lesson, where `text=True` normalised newlines and
made the assertion vacuous.

`plan --list` prints paths and nothing else, and the test asserts every line
resolves to a real file, so a stray banner cannot pass as a path.

## 6. Scope held: `bundle` is not migrated

Only commands using a WP3 selection flag route through the facade. A plain
`bundle` still uses the Build 113 discovery path, unchanged.

Migrating `bundle` wholesale onto the facade is **WP5/F-05**, and folding an
untested rewrite of the most-used command into the build that introduces the plan
API would have made both unreviewable. The routing predicate is one tuple in
`src/cli.py`, so the migration is a deletion when WP5 arrives.

## 7. Performance — SEL-PERF-004

Build 113 gated the engine. WP3 put a filesystem walk in front of it, and a
budget covering only the half that does no I/O is not a budget for what the
operator waits on.

| | measured | budget |
|---|---:|---:|
| `plan_bundle`, 1,200 files incl. walk (p50) | **295 ms** | 2,000 ms |
| p95 | **299 ms** | 2,000 ms |

85% headroom. Wider than the in-memory gates because the walk is bounded by the
filesystem, and a budget tight enough to fail on a busy disk teaches people to
ignore gates.

Two companion gates: re-planning must not get slower (guards the WP5 cache
seam by proving planning is stateless today), and the 400-file vendored subtree
must never be statted — stated as a **cost**, because if pruning regressed to
filtering after the walk the file list would be identical and only the scan
count would show it.

## 8. Four more defects the process caught

Recorded because each was caught by a mechanism rather than by luck:

1. **`plan_bundle` was missing from the progress register.** The Build 109
   class-level guard failed: *"untested progress entry points:
   BundleToolService.plan_bundle"*. Its docstring says to add a test rather than
   extend the list, so I did — planning now proves a determinate discovery
   sequence and a completion event.
2. **The helper functions landed after the `__main__` guard**, so `python -m cli`
   ran `main()` before they existed. Fourteen tests failed with a `NameError`.
3. **The manifest digest was computed and never written** into `module_ids` and
   `schema_ids` during the version bump. The release contract test caught it —
   step 3 of a three-step ordered bump is exactly where attention lapses.
4. **My pruning assertion was too strict.** I asserted nothing under `.venv312`
   was ever statted, but the detector *must* probe marker files to classify the
   directory at all — that is what makes recognition signature-based rather than
   name-based. The corrected assertion is the real property: classification is
   where the cost stops, so the 25 files inside are never touched and the probe
   count is bounded per directory. Same shape as Build 113's `statted == 21`.

Two of my own test defects, for the record: I wrote size expectations against
source literals when Windows text mode had translated `\n` to `\r\n`, and I wrote
a precedence test with **disjoint** patterns — which both orderings satisfy, so
it would have passed while proving nothing. That is the Build 113 group-order
mistake made a second time; it is now a conflict test, and the lesson is written
into the docstring where the next person will read it.

## 9. Supersession and the matrix

Gate A0 accepts `2.1.105` through `2.1.114`. Payload is a strict superset of the
106–113 kits. Gate E gains a WP3 import smoke check and a `plan --list-presets`
run before the suite gate.

## 10. Payload — 55 files, 54 markers

New: `src/core/metadata_scan.py`, `src/core/rule_sources.py`, `src/cli_plan.py`,
`tests/unit/test_metadata_scan.py`, `tests/unit/test_rule_sources.py`,
`tests/unit/test_service_planning.py`, `tests/unit/test_cli_plan_rendering.py`,
`tests/integration/test_cli_plan.py`. Plus every version surface and the Build
106–113 superset.

## 11. Evidence

```
1169 passed
Required test coverage of 85.0% reached. Total coverage: 91.42%
src\core\service.py       231 stmts   4 miss  99%
src\core\rule_sources.py  162 stmts   3 miss  98%
src\core\metadata_scan.py  88 stmts   2 miss  98%
src\cli_plan.py           140 stmts   4 miss  95%
```

- 186 new tests: 47 rule sources, 20 metadata scan, 42 service planning,
  28 renderer, 36 CLI integration, 3 performance gates, 2 progress contract,
  8 carried adjustments.
- WP3 exit gate — *`plan` displays identical decisions to the service output;
  stdout purity 100% preserved; JSON reports validate* — met. The plan/bundle
  agreement gate is parameterised across five flag combinations.
- Governed config digest `7775997a…`; manifest `d8d281ba…`; helper block
  `380037a3…` verified before assembly and re-hashed after.
- Layer A verified positively on the live tree: recorded digest equals actual,
  and the manifest hash matches both id modules.

## 12. Not in this build

WP4 (desktop workspace), WP5 (incremental cache and the `bundle` migration),
WP6 (presets and groups persistence). Still open from earlier builds: F-04
(JSONL validates-but-unregistered), F-08 (source-header normalisation).

Awaited from Paul: Specification Revision 1.1, the formal JSON Schema, and the
two persona fixtures. The `--rules` loader accepts the shape the specification
describes and reports precisely which element it rejected, so a schema can be
bolted on without changing it.
