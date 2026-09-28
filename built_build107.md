# BFT v2.1 Build 107 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_107_pythermx_progress.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-20
**Responds to:** Ringo's request to integrate PyThermX 0.2.0 into Bundle File Tool, and
Paul's ratified sequencing step 5, "BFT CLI integration with therm as its own governed build"
**Supersedes for installation:** Build 106. See §9.

---

## 1. What this build does

Build 106 made every operation emit `OperationProgress` events. Nothing drew them. Build 107
draws them, closing the original complaint Ringo raised: no feedback on large folder
operations.

The integration is deliberately thin, because Paul's Build 104 review set the shape and it
is the right one:

> CLI maps those events to therm; Tkinter queues them onto the UI thread; Web streams or
> polls the same events. Do not make the shared service return CLI renderer objects.

So the renderer is an adapter in the CLI layer, `src/cli_progress.py`. Core still imports no
renderer, and a test now enforces that rather than trusting it.

## 2. The discovery handoff

This is the part worth the attention, and it is the reason PyThermX 0.2.0 was a prerequisite
rather than a nice-to-have.

Discovery cannot know its total until it has finished walking. It therefore reports a rising
count with `total=None`. Every other phase knows its size up front. A naive adapter shows a
spinner, throws it away, and starts a bar — two widgets for one operation, and a visible
discontinuity at exactly the moment the user starts to care.

`ThermometerCore.promote()` (R-THM-01) exists to avoid that. The adapter keeps one handle per
phase and promotes it in place:

```
\ | discover | 0 files | 0.0s
[########################################] | 100.0% | 8 files found - 8/8 | discover | 0.0s | 500 files/s | OK
[#####-----------------------------------] |  12.5% | 1/8 | read | 0.0s
[########################################] | 100.0% | 8/8 | read | 0.0s | OK
```

`8 files found - 8/8` is the promotion: the indeterminate count is preserved as history
beside the determinate total, on the same bar.

One implementation note. The adapter decides to promote by testing `self._model.total is
None`, **not** by comparing mode strings. Both packages happen to spell it `"indeterminate"`
today, but PyThermX's vocabulary is its own and nobody has promised to keep the two in step.
Comparing across that seam would have been a silent coupling.

## 3. stdout stays pure

Build 105 established that `bundle` writes the artifact to stdout and diagnostics to stderr.
A progress bar is a diagnostic, and a bar on stdout would corrupt every piped bundle with
carriage returns.

PyThermX 0.2.0 defaults to stderr (R-THM-02), which agrees with that rule; the adapter also
passes the stream explicitly rather than relying on the default. `test_forced_bar_writes_
nothing_to_stdout` runs the CLI as a **subprocess** with the bar forced on and asserts no
`\r` reaches stdout. In-process capture would not have proved it, because a captured stream
is not a real redirect.

## 4. Defaults, and why `auto` is the right one

| `--progress` | Behaviour |
|---|---|
| `auto` (default) | Bar only when stderr is a terminal **and** PyThermX is importable |
| `bar` | Force the bar on, tty or not |
| `none` | No bar; the plain Build 105 status lines stand alone |

`auto` has a property that matters beyond convenience: a captured or redirected stream is not
a tty, so under the test suite and under any shell redirect the resolved behaviour is
byte-identical to Build 106. That is why 622 pre-existing tests required no amendment.

When the bar is active the three duplicated status lines (`Discovering files...`, `Found N
files`, `Creating bundle with profile:`) are suppressed — the bar already says all three, and
their newlines would tear the in-place redraw. The completion summary still prints.

## 5. PyThermX is optional, and the wheel ships in the kit

`dependencies = []` is unchanged. PyThermX sits in an extra:

```toml
progress = ["pythermx>=0.2.0,<0.3"]
```

The floor is a hard requirement, not a preference: 0.2.0 is the release that added
`promote()` (R-THM-01) and moved the default stream to stderr (R-THM-02). On 0.1.x this
integration would both lose the handoff and corrupt piped bundles.

`build_reporter()` returns `None` when PyThermX is absent, and every call site already treats
a missing sink as "no progress" — the same path `--progress none` takes. Constructing
`PyThermXReporter` directly without PyThermX raises instead, because there the caller has
explicitly asked for a renderer and silently handing back a broken one would be worse.

Per Ringo's approved wheel-in-kit approach, `vendor/pythermx-0.2.0-py3-none-any.whl`
(sha256 `df6a46db8bdd9fcaf8df3bfdacfb196e05bce2124da09319f36179d6bc062023`) ships inside the
kit and is verified by Gates A and D like any other payload file. Gate D2 installs it into
`.venv` offline (`--no-index --no-deps`). **Gate D2 is non-fatal by design**: failing a build
over an optional renderer would be the wrong trade.

## 6. Extraction reports progress too

`BundleWriter.extract_manifest()` gained a `progress` parameter. Extraction knows its size up
front, so every event is determinate, and it closes with a `PHASE_COMPLETE` event.

## 7. One policy addition, flagged rather than slipped in

Vendoring a wheel into the tree created an exposure: `.whl` was not on the deny list, so
every self-bundle would have silently absorbed an 11 KB base64 archive. `**/*.whl` is now
denied in both `bundle_config.json` and `ConfigManager.DEFAULT_CONFIG`.

This completes an existing rule rather than inventing one — `**/*.zip`, `**/*.tar` and
`**/*.tar.*` were already denied, and a wheel is the same class of artifact. It is an
**addition** to the shipped deny list; the ratified `GOVERNED_POLICY` contains-list is
untouched, so no drift is reported. **George**: flagging it explicitly because it touches
safety policy, small and consistent as it is.

## 8. Correction to the record

I have been carrying `53948714915169d1309e5157030ee437231ac408e576483dbc427f164dfa677e` as
the ratified family helper hash. That is wrong. The contract defines the hash as SHA-256 over
the bytes from the `BEGIN` marker through the `END` marker inclusive, which is the canonical
`FAMILY_DELIVERY_HELPERS_v2_0.bat.inc`:

```
380037a32db7480db2067efaaaf515b7ffef4167f803ea39b26fe1ff85a4a454
```

The Build 106 installer's block matches this exactly, so no shipped kit was affected — only
my note was. This kit's block is copied from the canonical include and re-hashed after
assembly to prove it survived unchanged.

## 9. Supersession — action required before installing

The Build 106 kit is **still sitting uninstalled in Downloads**. Build 107's payload is a
strict superset of Build 106's fourteen files, so installing 107 over a 2.1.105 tree delivers
everything both builds contain. Gate A0 accepts `2.1.105`, `2.1.106` and `2.1.107`.

`PREP_AND_STAGE_BFT.bat` requires **exactly one** `INSTALL_BUNDLETOOL_*.zip` in Downloads and
aborts otherwise. So the Build 106 zip must be moved out of Downloads before staging this
one. Installing 106 *after* 107 would regress the tree.

## 10. Payload — 19 files

| # | File | Change |
|---|---|---|
| 1 | `src/cli_progress.py` | **New.** PyThermX adapter |
| 2 | `src/cli.py` | `--progress` flag; sinks wired; duplicate status lines suppressed |
| 3 | `src/core/writer.py` | `extract_manifest(progress=...)` |
| 4 | `src/core/config.py` | `**/*.whl` denied |
| 5 | `bundle_config.json` | `**/*.whl` denied; version |
| 6 | `pyproject.toml` | `progress` extra; version |
| 7 | `tests/unit/test_pythermx_integration.py` | **New.** 39 tests |
| 8 | `vendor/pythermx-0.2.0-py3-none-any.whl` | **New.** In-kit wheel |
| 9–19 | `VERSION.txt`, `src/core/version.py`, `src/core/progress.py`, `src/core/service.py`, `src/core/module_ids.py`, `src/database/schema_ids.py`, `.pyprojectmgr/project_spec.json`, `.pyprojectmgr/project_manifest.json`, `tests/unit/test_progress_contract.py`, `tests/unit/test_release_contract.py`, `tests/integration/test_service_facade.py` | Version surfaces and the Build 106 superset |

## 11. Evidence

```
661 passed in 8.79s
Required test coverage of 85.0% reached. Total coverage: 90.23%
src\cli_progress.py    67 stmts   1 miss   97%
```

- Build 106 baseline: 622 passed, 88.04% (measured on this tree before the change).
- Build 107: 661 passed, 90.23%. 39 new tests, no test amended to accommodate the change.
- Helper block: `380037a3…`, verified against the canonical include before assembly and
  re-hashed inside the finished installer.
- Wheel: `df6a46db…`, identical to the file in `therm_project/therm/dist/`.

### What the new tests bind

| Area | Guarantees |
|---|---|
| Discovery handoff | Promotion reuses the handle; `promoted_from` preserved; unknown total reads as `None`, never `0%` |
| Reporter resolution | `none`→None, `auto`+non-tty→None, `auto`+tty→reporter, `bar`→always; default stream is stderr |
| Optional dependency | Absent PyThermX yields None, not an error; direct construction raises; version pin enforced |
| Layering | No module under `src/core/` imports `pythermx` or `cli_progress` (AST-parsed, every file) |
| Extract progress | Determinate throughout; monotonic; closes with `PHASE_COMPLETE`; a hostile sink cannot break extraction |
| stdout purity | Subprocess run with `--progress bar`: no `\r` on stdout, bundle intact, bar present on stderr |

## 12. Open items

- **George**: the `OperationProgress` contract shape is still awaiting your ruling
  (built_build106.md §8). Build 107 renders the contract as it stands; if the shape changes,
  the adapter is the only consumer and is one file.
- **WP5**, migrating the CLI onto `BundleToolService`, remains separate and unstarted. Build
  107 wires progress into the existing CLI call sites, which is why it does not depend on
  WP5. I did not fold them together: WP5 changes control flow for every command, and pairing
  that with a new renderer would make a failure ambiguous.
- The Tkinter adapter consuming the same event stream is not in this build.
