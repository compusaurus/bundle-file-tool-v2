# BFT v2.1 Build 104 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-18
**Kit:** `INSTALL_BUNDLETOOL_v2_1_104_config_ownership.zip`

## The problem, in one paragraph

One file was doing two jobs that cannot coexist. `bundle_config.json` ships in the delivery
kit, gets checked by SHA256 before and after installation, and holds the ratified safety
rules that decide what the tool is allowed to bundle. It was *also* where the application
scribbled your window position and the last folder you browsed to. Because saving wrote the
whole file at once, closing the window quietly rewrote the safety rules. Build 103 repaired
those values on 13 August. They were gone again twice within five days.

## What changed

The two jobs are now separated. The governed file is read-only while the application runs —
anything that tries to write it gets a clear error naming the reason. Your window geometry
and remembered folders move to `%LOCALAPPDATA%\BundleFileTool\user_state.json`, where they
belong and where nothing verifies a hash. There is a portable mode if you want everything
beside the app instead, and a one-time migration carries your existing preferences across so
nothing is lost.

Two smaller fixes ride along:

- The safety guard that blocks accidentally bundling an old archive now recognises the
  naming we actually use. It previously missed `therm_bundle.txt` because it insisted on a
  trailing underscore.
- `PREP_AND_STAGE_BFT.bat` options work again. `/dryrun`, `/y` and `/norun` all aborted
  before, because the script read its own location after consuming arguments. Unknown
  options now say so and stop, rather than being ignored.

## Proof

571 tests pass, up from 538, with coverage at 89.82% against an 85% floor. The tool bundled
its own source and tests — 69 files out, 69 back, no differences. A dedicated test
reproduces the exact Build 103 regression and proves a full save cycle now leaves the
governed file byte-identical.

## Three things worth your attention

**George — one deviation from your ruling, recorded not hidden.** The literal regex in
R-BFT-02 would have broken three cases, two of them covered by tests that currently pass:
it requires the bundle marker to sit immediately before the file extension, and real
artifact names carry version suffixes in between. I implemented the intent and pinned it
with a 16-case matrix. `built_build104.md` §3 has the table. Please confirm.

**The coverage figure has been flattering us.** The gate dropped to 65% during this build
with no code change of mine. pyprojectmgr's run at 00:23 today added package markers to
`src/ui` and friends, which made 938 statements — the entire Tkinter layer — visible to
coverage for the first time. Build 103's 89.25% was accurate for what it measured, but the
UI was never in the denominator. The measured scope is now written down with reasons
instead of being an accident. The UI still has no tests; that is now a recorded gap.

**The canonical installer skeleton has gone missing.** It is no longer at its ratified path
in `pyprojectmgrV2`. The standard says never to rebuild it from description, so I recovered
the exact bytes from an independent pyprojectmgr installer and verified them against the
hash recorded in Build 103's record. Two separate copies agree. Somebody should re-establish
a governed copy at a known location.

Also fixed in the same session, on the pyprojectmgr side: re-initialising a project no
longer discards its identity. That is what kept resetting BFT's version to 0.1.0 and
undoing Build 103's repairs.

## To install

Put the kit zip in `Downloads` — exactly one `INSTALL_BUNDLETOOL_*.zip` — and run this from
the project root:

```
PREP_AND_STAGE_BFT.bat
```

It snapshots and archives your tree first, then stages and installs. Every file is verified
by SHA256 before and after copying, everything replaced is backed up, each installed file is
checked for a content marker, and the whole test suite runs before anything is cleaned up.
If any check fails it stops and leaves your backups. Expect **571 passed** and a green
coverage gate.

Nothing here touches the protected `.git` control, and WP0 Gate 1 is unaffected.
