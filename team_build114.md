# BFT v2.1 Build 114 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-25
**Kit:** `INSTALL_BUNDLETOOL_v2_1_114_selection_service.zip`
**Delivers:** v2.2 Selection Workspace **WP3** — the plan API and the `plan` command

---

## The version question is closed

Ringo settled it: **v2.2 is the destination, reached incrementally, and the
workspace ships at whatever the current build is.** No work package waits for a
version event. This is `2.1.114`, build numbers stay monotonic, and there is no
minor turnover scheduled — whoever declares 2.2 does so when the programme is
done, not as a gate on any work package.

**983 → 1,169 tests. Coverage 90.73% → 91.42%.**

## Build 113 built the ladder. This one gives you a way in

```
bundle-tool plan .
bundle-tool plan . --explain src/app.py
bundle-tool plan . --preset python-env --preset vcs --report plan.json
```

You can now see a selection before committing to it, and nothing is read to show
it to you — planning stats files and never opens one. Two tests patch
`builtins.open` and fail if that ever changes, because it is the premise the
whole workspace rests on.

The same flags work on `bundle`, and both commands share one selection path. A
parameterised gate drives five flag combinations through **both** and compares
the file sets, so a preview that disagrees with the artifact cannot ship.

## The defect I want on the record

**`--include` did not narrow anything, and the unit test passed the whole time.**

Build 113 established that an allow-list is a base-action switch. That was
correct and tested. The service then resolved the base action from the *union* of
every layer's allow-list — and the governed default is `**/*`, which is always
in that union. So `--include src/**` added a rule that changed nothing. Every
other file stayed in the bundle. Silently.

Each layer was right. The composition was wrong, and no unit test can see that.

The base action now comes from the **highest-priority layer that supplies an
allow-list**, and there is an end-to-end assertion on a real tree rather than
only a unit one.

Two more of the same shape, both caught by gates rather than by luck:

- **`plan` and `bundle` anchored differently.** `bundle` defaulted its base path
  to the current directory before planning, so relative paths were computed
  against the wrong root and the writer rejected them. The plan/bundle agreement
  gate caught it on its first run.
- **`plan_bundle` was missing from the progress register.** George's Build 109
  guard failed by name. Its docstring says add a test rather than extend the
  list, so planning now proves a determinate discovery sequence.

## For Paul — one thing I changed on my own judgement

Routing `--include` through the ladder would have **silently narrowed every
existing command**, and I do not think the specification anticipated it.

The engine uses strict glob semantics, where `*` does not cross a separator. The
Build 113 discovery filter did not. Measured:

| pattern | path | old behaviour | strict ladder |
|---|---|---|---|
| `*.py` | `src/app.py` | included | **dropped** |

`--include '*.py'` would have stopped matching nested files, with no error and no
message, in the build whose subject is that selections stop changing behind your
back.

So the CLI adapter anchors a pattern that names no directory at any depth —
gitignore behaviour, and what the tool already did. **The engine stays strict**;
only the surface where a human types translates. A pattern containing `/` is
already explicit about position and is left exactly as written.

Flag it if you disagree — it is one function, `expand_bare_pattern()`, and it is
tested in both directions.

Your `--exclude` ruling is implemented as additive, and because it changes the
meaning of a flag people already use, every run that uses it says so on stderr
and names `--no-default-rules` as the way back. Disabling defaults does not
disable Priority 0; there is a test that force-includes `**/*` with defaults off
and asserts a nested bundle is still blocked.

Your §13.1 method signatures are what I built to. `--rules` accepts the shape the
specification describes and reports precisely which element it rejected, so
Revision 1.1's schema can be bolted on without changing the loader.

## For George

The precedence contract holds where it matters most — **a rule source cannot
choose its own layer**. A test asserts every shipped preset produces Layer 4
rules and only Layer 4 rules, and a rules file that tries to mint a Priority 0
`block` is refused with an error that points at `exclude` instead. Priority 0
belongs to the tool; a project file that could create non-overridable rules would
bind the operator running it.

2a before 2b is tested as a genuine **conflict** on the same path, not as a union
of disjoint patterns. I got that wrong first — disjoint patterns satisfy both
orderings, so the test would have passed while proving nothing. Same mistake as
the Build 113 group-order test, made a second time; the lesson is now in the
docstring.

## Scope I deliberately did not take

`bundle` is **not** migrated onto the facade. Only commands using a WP3 selection
flag route through it; a plain `bundle` still uses the Build 113 path untouched.

That migration is WP5/F-05. Folding an untested rewrite of the most-used command
into the build that introduces the plan API would have made both unreviewable.
The routing predicate is one tuple, so WP5's migration is a deletion.

## Numbers

| | Build 113 | Build 114 |
|---|---|---|
| Tests | 983 | **1,169** |
| Coverage | 90.73% | **91.42%** |
| `plan_bundle`, 1,200 files (p50) | — | **295 ms** vs 2,000 ms budget |
| Required dependencies | none | none |

`service.py` 99%, `rule_sources.py` 98%, `metadata_scan.py` 98%, `cli_plan.py` 95%.

## Next

WP4 (desktop workspace) is the natural next step and now has a contract object to
bind a tree to — `PlanResult` carries no renderer and no open handle, so it
crosses a thread boundary unchanged. WP5's cache sits on the `metadata_scan`
seam, and I have a gate asserting planning is stateless today so that cache has
something to prove itself against.
