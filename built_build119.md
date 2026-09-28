# Bundle File Tool v2.1 Build 119 — Build Record

**Prepared:** 2026-08-29  
**Status:** Governed repair delivery; technical gates passed  
**Release identity:** `2.1.119`

## Outcome

Build 119 repairs the Build 118 native Selection Workspace responsiveness
regression. It retains the standardized Settings / ConfigHub integration,
PyThermX `0.5.2`, and Python 3.11/3.12/3.13 environment matrix delivered in
Build 118.

The candidate is technically qualified but is not a Git release commit or tag.
Repository policy reserves index, ref, commit, and tag writes for an authorized
interactive account.

## Root cause and repair

Build 118 made every Treeview horizontal scrollbar truthful by measuring every
cell after every refresh. It also materialized every file below collapsed
decision folders. On BFT's remembered self-source, accumulated generated output
raised the plan to 79,538 decisions, causing hundreds of thousands of
synchronous Python/Tcl calls after each interface action.

Build 119:

- bounds Treeview font measurement to 256 sampled rows and accepts longest-value
  hints so off-screen long values still activate horizontal scrolling;
- preserves the complete folded tree for ordinary plans of at most 1,000 files;
- virtualizes larger plans, loading one folder branch at a time and limiting any
  synchronous branch to 1,000 rows;
- keeps broad plans fully searchable and states when folders load on demand;
- bounds Expand all on large plans instead of recreating the original freeze;
- reuses the immutable scan topology across I/O-free replans instead of indexing
  the same 79,538 paths separately for both workspace panes; and
- treats literal single-file overrides as hash lookups and the UI's canonical
  `folder/**` scopes as prefix checks, while retaining the glob engine and
  exact selection semantics for genuinely wildcarded patterns.

No selection, precedence, safety, plan, or bundle-emission rule was changed.

## Measured result

Hidden-Tk measurement against the exact remembered BFT source:

| Phase | Build 118 behavior | Build 119 |
|---|---:|---:|
| Initial metadata scan | ~47–64 s with progress/cancel | 63.746 s with progress/cancel |
| Single-file checkbox replan | 0.697 s | 0.386 s |
| Post-toggle redraw | 1.717 s | 0.104 s |
| Combined post-scan interaction | ~2.414 s plus unbounded Tcl work | ~0.490 s, bounded |

An 80,000-row synthetic native-Tk plan refresh completed in 0.430 s and created
two initial Treeview items. The initial scan remains proportional to the real
source tree: BFT's local `out` directory contains tens of thousands of generated
QA files, but ordinary controls no longer re-materialize that output.

## Governed identities

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `54501d8215f45d82519e3223b5e68aa8ac6dadeca83517ec6335add60f1d1919` |
| `.pyprojectmgr/project_manifest.json` | `168f5278c5bd1d83c44eb4b56dc278e8d95e684ca512f1db924f6480832d540e` |
| `vendor/pythermx-0.5.2-py3-none-any.whl` | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |

## Qualification evidence

| Runtime | Tk | PyThermX | Full suite | Coverage | Dependency check |
|---|---:|---:|---:|---:|---:|
| CPython 3.11.9 | 8.6.12 | 0.5.2 | 1,497 passed | 88.66% | clean |
| CPython 3.12.10 | 8.6.15 | 0.5.2 | 1,497 passed | 88.66% | clean |
| CPython 3.13.15 | 8.6.15 | 0.5.2 | 1,497 passed | 88.66% | clean |

The 3.11 and 3.12 runs emitted one non-failing Tk variable-finalizer warning;
3.13 emitted none. The warnings are teardown-only after passing live-Tk tests
and do not represent product failures.

## R2 installer correction — 2026-08-30

The first live staging run exposed a transient Windows
`ERROR_USER_MAPPED_FILE` while Gate C copied
`tests/unit/test_config_migration.py`. The destination already had the exact
staged SHA-256, Gate C stopped at manifest entry 99 of 145, and the complete
pre-mutation rollback was retained as designed.

R2 retries placement three times. A nonzero Windows copy result is accepted
only when the destination SHA-256 equals the staged source; a missing or
different target still fails closed and retains recovery material. A release
contract pins the retry, equality check, and terminal failure path. The
interrupted rollback was preserved in the external project archives before the
installer was resumed.

That resumed run cleared placement but its binding full-suite gate then caught
a 901 ms checkbox sample against the Windows-adjusted 750 ms ceiling. Five
accumulated `folder/**` overrides were still applying a cached regex to every
decision under coverage. The final R2 payload recognizes that canonical UI
scope with exact string-prefix tests; true wildcard patterns still use the glob
engine. Selection-parity tests and the performance gate passed in all three
supported Python environments. The final live installer run completed every
gate and removed its staging and rollback directories during normal teardown.

## Delivery controls

The Build 119 archive contains one installer, this build record, the team
communication, and one explicit incoming payload. The installer verifies every
staged file before mutation, makes a reversible backup, places the payload,
installs and verifies PyThermX in every supported environment present, restores
Layer C read-only protection, and executes the full suite and coverage gate.

The archive SHA-256 is published in the adjacent `.sha256` sidecar. The
authorized release owner must still review the candidate and perform any Git
commit/tag action required by repository governance.
