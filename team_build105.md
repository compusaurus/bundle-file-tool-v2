# BFT v2.1 Build 105 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-18
**Kit:** `INSTALL_BUNDLETOOL_v2_1_105_registry_and_purity.zip`

## Why there is a Build 105

George found a real defect in Build 104 and offered a one-line patch. Paul held the release
and asked for a governed successor instead. **Paul is right**, and here is why in plain
terms: `src/core/parser.py` was never part of Build 104's payload. Patching an
already-installed, hash-verified build in place would mean the thing on your disk no longer
matches the thing we recorded and signed. That is precisely the identity chain the delivery
standard exists to protect, so the correction ships as its own build.

Build 105 contains everything Build 104 delivered, plus all three of Paul's blockers closed.

## The three fixes

**Markdown Fence was never switched on.** The profile was fully written but never registered,
so any command that fell back to it failed outright. Two lines fix that. More useful is *why*
it survived: the Markdown tests created the profile directly, and the registry tests only
checked that the other profile existed. Nothing joined "what the config can ask for" to "what
the registry can hand back". Fourteen new tests now join them.

**The governed config could be written by the wrong process.** It resolved its own filename
relative to whatever directory the program happened to be started in. So any process launched
with the project root as its working directory wrote the live governed file — including a
**pre-104 copy of BFT that is still sitting on disk** at `bundle_file_tool_v2  Build 101`,
which still has the old save-everything behaviour. That is what overwrote your safety rules
again at 21:29 last night. The config now resolves from the installed application's own
location, is never created behind your back, and the CLI warns you on stderr the moment it
notices drift.

**A piped bundle was not a clean bundle.** `bundle` printed "Discovering files…" and friends
to standard output, then wrote the bundle to the same place. Anyone redirecting the output to
a file got progress text mixed into their artifact. Diagnostics now go to stderr; standard
output carries the bundle and nothing else, verified byte for byte against the formatter.

## Evidence

592 tests pass, up from 571, coverage 89.75% against the 85% floor. George's CLI matrix was
re-run in full with captured commands and outputs: **17 of 17 pass**, and the count is
reconciled — Paul was right that the earlier memo said 16/16 over a 15-row table. The four
cases that failed in Build 104 all pass, and two new cases cover the stdout purity gate.

## One thing only you can do

**There is a runnable, out-of-date copy of BFT beside the live one**, at
`bundle_file_project/bundle_file_tool_v2  Build 101/`. It has a working GUI and the old
write-the-whole-config behaviour. Build 105 stops the *current* code from misbehaving, but it
cannot stop that old copy from being launched. It should be archived or deleted. I have left
it alone — it is your data, and removing it is not my call.

## Also closed

The canonical installer template that had gone missing is restored to a governed location in
pyprojectmgr, with a test that asserts its presence, its hash, its four required routines,
and its line endings. Two independent copies agreed on the hash before I put it back.

## To install

Put the kit zip in `Downloads` — exactly one `INSTALL_BUNDLETOOL_*.zip` — and run from the
project root:

```
PREP_AND_STAGE_BFT.bat
```

Expect **592 passed** and a green coverage gate. The installer upgrades 2.1.104 and is
idempotent on 2.1.105.

## Still open

The UI layer has no automated tests, which George proposes to address with a headless Tk
harness. `BFT-WP0-QC-001` stays open behind the pyprojectmgr preflight defect. Paul's Build
100 status addendum and readiness-plan update are his records to amend — I have not touched
them.
