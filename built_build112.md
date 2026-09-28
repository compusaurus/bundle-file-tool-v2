# BFT v2.1 Build 112 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_112_pythermx_050_cancel.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-25
**Authorised by:** Ringo (Product Owner) — "integrate the latest PyThermX (Build 12) including
Cancel button; proceed if a design round is not required"
**Supersedes for installation:** Builds 106 through 111. See §8.

---

## 1. Why no design round was needed

I checked before proceeding rather than after. PyThermX Build 12 is **0.5.0**, and 0.4.0 had
already defined the whole cancellation protocol upstream:

- `CancellationSource` may `request()`; `CancellationToken` may `acknowledge()` and
  `complete()`. Neither party can forge the other's half.
- Four states, because `requested` is not `cancelled` — the gap between them is unbounded.
- `finish_cancelled()` on both renderers, as a third terminal outcome beside OK and FAIL.
- `capture_sigint()` for the CLI, escalating on a second Ctrl+C.
- `TkThermometer(show_cancel=True, cancellation_source=...)` — **the Cancel button itself**.

So the protocol was not mine to invent. George had already ratified the direction in
`ARCH-RULING-2026-08-23-02` ("CancellationToken protocol in discover/write/read", "wire Cancel
button in the Tkinter progress modal"), and Paul had set the exit gate ("cancellation
reconciles partial work safely").

One judgement remained — what happens to files already written — which §5 records and flags
rather than deciding silently.

## 2. The upgrade, verified before anything was built on it

0.3.1 → 0.5.0 is two minor versions. I installed it and ran the existing suite **before**
writing a line of cancellation code. Exactly one test failed:

```
FAILED test_installed_pythermx_satisfies_the_declared_pin
```

That is the Build 108 test doing its job: the installed 0.5.0 violated the shipped
`>=0.3.1,<0.4`. The other 858 passed unchanged, which is the evidence that 0.5.0 is compatible
with everything BFT already does. The pin is now `>=0.5.0,<0.6` and the floor test names each
0.4.0 cancellation symbol individually, so a partial upgrade fails there rather than at the
first cancel a user attempts.

## 3. Core owns the seam; PyThermX stays on the far side of it

`src/core/` must not import PyThermX, and an AST test enforces it. That rule is why one event
stream can feed CLI, Tkinter and a future Web adapter, and it applies to cancellation exactly
as it does to progress.

So `src/core/cancellation.py` owns a minimal contract — **one callable returning a bool** —
and the adapters bridge. `ui/tk_progress.py` and `cli_progress.py` supply
`lambda: token.is_requested` over a real PyThermX source. Core never sees the library.

| Layer | Responsibility |
|---|---|
| `core/cancellation.py` | `OperationCancelled`, `is_cancelled()`, `raise_if_cancelled()` |
| `core/writer.py` | polls between units in discover, read and write |
| `core/service.py` | passes the predicate through, unchanged |
| `cli_progress.py` | `cancellation_scope()` — Ctrl+C via `capture_sigint` |
| `ui/tk_progress.py` | `show_cancel=True` plus a `CancellationSource` |

## 4. Cancellation is cooperative, and that is a design property

Nothing is ever forcibly aborted. Each long operation polls **between units of work, never
inside one**:

- **discover** — per directory, because `os.walk` yields a directory at a time
- **read** — before opening each file, so no partially-read file reaches the manifest
- **write** — between entries, so every file already written is complete

A test asserts the last one by reading back every file that landed and checking its contents
in full, because "no half-written files" is a claim that deserves evidence rather than an
argument.

## 5. Partial output is reported, not deleted — flagged for George

When an extraction is cancelled, files already written **stay on disk** and the operator is
told how many there are. `OperationCancelled` carries `partial_paths` for exactly this.

The alternative — rolling back what was written — was rejected on the grounds that deleting a
user's files because they pressed Cancel is a bigger surprise than leaving them. But it is a
judgement, not a deduction. **George**: if the ratified behaviour should be rollback-on-cancel,
say so; the paths are already carried on the exception, so the change is small.

## 6. The interaction that would have been easy to get wrong

`_reconcile_extraction` halts when an extraction is short, because a silently incomplete
extract is corruption (Build 103, ratified). A **cancelled** extraction is also short —
deliberately.

Cancellation raises before reconciliation is reached, so the operator gets the real reason
instead of a bogus integrity failure. Two tests hold that line: one proves a cancelled extract
raises `OperationCancelled` and not `ValidationError`, and the other drives a genuine silent
loss through the normal path and requires that reconciliation **still** halts. The second
matters more than the first — it is what stops "cancellation returns early" from quietly
becoming "short extractions are fine now".

## 7. A cancelled run is a third outcome

Not a success, not a failure.

| Surface | Behaviour |
|---|---|
| CLI | exits **130**, prints `Cancelled: …`, and **never** prints `ERROR:` |
| CLI | reports how many files were already written |
| CLI bar | closes as CANCELLED via `finish_cancelled()`, not OK |
| Tkinter | bar closes as CANCELLED before the dialog is destroyed |
| Core | `OperationCancelled` subclasses `BundleFileToolError` so existing handlers still catch it, but the CLI reports it **first** so it is never printed as an error |

That ordering is pinned by a test, because the inheritance is what makes it fragile.

## 8. A silent-skip defect found in my own test suite

Worth recording, because the suite reported green while it happened.

Adding a second Tk-using test module gave the session two module-scoped `tk_root` fixtures.
Tcl does not survive a second `Tk()` in one process after the first is destroyed — it raises
`invalid command name "tcl_findLibrary"`, which my fixture reported as *"no usable display"*
and **skipped**.

Under coverage that silently skipped **six Tk tests, including the Cancel-button ones**, while
the run still showed as passing:

```
891 passed, 6 skipped     (with coverage)
897 passed                (without)
```

A session-scoped `tk_root` in `conftest.py` removes the second construction entirely. Now 897
pass either way, and the difference between the two invocations is gone.

The lesson is the one this project keeps relearning: a skip is not a pass, and a fixture that
converts an infrastructure fault into a skip will hide real coverage.

## 9. Supersession and the installation matrix

Gate A0 accepts `2.1.105` through `2.1.112`. The payload is a strict superset of the 106–111
kits, including the Build 110 discovery-performance and Build 111 open-bundle files.

New in this installer:

- **Gate C2** now retires *any* superseded `pythermx-*.whl`, not one hard-coded name — trees
  arriving from 105–107 carry 0.2.0 and trees from 108–111 carry 0.3.1.
- **Gate D3** runs `python -m pythermx --version` and requires `0.5.0`. That entry point is new
  in 0.5.0 and exists for this: the version comes from `__version__`, not from install-time
  metadata that goes stale.

Layer C's full lifecycle from Build 109 is unchanged: protection cleared at C0, applied at C3
before acceptance, and restored on every abort path.

## 10. Payload — 42 files

New: `src/core/cancellation.py`, `tests/unit/test_cancellation_contract.py`,
`tests/integration/test_cancellation_end_to_end.py`, and `tests/conftest.py` enters the
payload for the session Tk fixture.

Changed: `src/core/writer.py` (three poll points), `src/core/service.py`, `src/cli.py`,
`src/cli_progress.py`, `src/ui/tk_progress.py`, `src/ui/bundle_frame.py`,
`src/ui/unbundle_frame.py`, `pyproject.toml`, the vendored wheel, and every version surface.
Carried forward: the Build 109/110/111 files so the superset holds.

## 11. Evidence

```
897 passed in 20.02s
Required test coverage of 85.0% reached. Total coverage: 90.17%
src\core\cancellation.py    31 stmts   0 miss   100%
```

- 34 new tests: 21 on the core contract, 13 end-to-end (service, CLI, Cancel button).
- **The Cancel control was pressed for real.** A test builds a `TkThermometer` with
  `show_cancel=True`, walks the widget tree to find the control, calls `invoke()` — which is
  precisely what a mouse click does — and asserts `source.is_requested` flips to True.
  Threadless and synchronous, so there is no timing in it to be flaky about.
- Real-app smoke: `BundleFileToolApp` constructs, the dialog renders a control labelled
  `Cancel`, the worker runs on thread `bft-progress` with a live predicate, no dialog leaks.
- PyThermX 0.5.0, wheel `b8bba738…`; governed config digest `3d5e0d96…`; manifest
  `a2594bf7…`; helper block `380037a3…` verified before assembly and re-hashed after.

## 12. Open items

- **George**: §5, partial output retained rather than rolled back — confirm or redirect.
- **F-05 / WP5** (CLI *and* Tkinter onto `BundleToolService`) is still outstanding. Builds 110
  and 111 were performance and open-bundle work, so the facade migration has now been deferred
  three times. Cancellation is wired into the current call sites and will need re-wiring when
  WP5 lands — small, but real rework worth naming.
- **F-04 JSONL** still validates-but-unregistered, deferred to Build 111 by ruling and not yet
  done.
- Cancellation is not yet offered on `validate`, which is fast enough that no one has wanted
  to stop it. The seam is there if that changes.
