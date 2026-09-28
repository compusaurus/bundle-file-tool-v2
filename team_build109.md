# BFT v2.1 Build 109 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-23
**Kit:** `INSTALL_BUNDLETOOL_v2_1_109_integrity_and_headers.zip`

## What this build does

Three things, in the order George ratified them.

**Extraction stops corrupting files.** JSON, XML, HTML, CSS, JavaScript and SQL now come back
byte-for-byte identical. Provenance headers go only where a leading `#` is a comment. This
was the critical defect, and at the default setting it had been silently damaging every
structured file we extracted.

**The desktop app and the command line now use the same configuration file.** The GUI had
been resolving its own copy from whatever directory it happened to start in.

**The governed configuration defends itself.** It is write-protected by the installer and
carries a checksum. A stale copy of Bundle File Tool trying to overwrite it now gets refused
by Windows; if one ever gets through anyway, the tool says so and names the process.

Everything George listed is in: all eight scope items, in his dependency order.
**702 tests → 840. Coverage 90.29% → 90.37%.**

## Before you install

Build 109 installs over 105, 106, 107 or 108. The stager wants exactly one delivery zip in
Downloads, so move any older one out first.

**Note the config file becomes read-only after installation.** That is deliberate — it is the
Layer C protection. If you ever need to hand-edit it, clear the flag first:

```
attrib -R bundle_config.json
```

...and be aware the tool will then warn you that it no longer matches its recorded checksum,
which is exactly what it is supposed to do.

## For Ringo

Two things worth knowing.

**The four-way upgrade check you and Paul asked for was run for real**, not asserted. I built
four throwaway copies of the project, rewound each one to look like 105, 106, 107 and 108,
and installed the actual kit into each. All four landed on 2.1.109 with all eight version
surfaces agreeing, the config protected, the old PyThermX wheel retired, and 840 tests
passing inside each installed tree.

**Layer D is still your action and it is still the important one.** Layers C and A make the
governed file hard to damage and loud when it is; only removing the stale runnable copies
removes the cause. `docs/bft_qc_target_base_20260724` is still there at v2.1.102.

## For George

**One deviation from your ruling, flagged rather than folded in.**

Option B+ decides *whether* a `#` header is valid for a format. It does not say where the
header goes, and I prepended it — which is fine for a `.py` file and wrong for a shell script,
because `#!/usr/bin/env bash` has to be on line 1 for the kernel to honour it. My first
implementation moved it to line 13: valid syntax, unexecutable script, which is the same
class of harm F-01 was raised for. I found it while building your round-trip matrix.

The header now goes immediately *after* a shebang. If you would rather scripts carried no
provenance at all than carried it on line 2, say so and I will take them off the allow-list
instead.

Also worth your eye: your ruling lists `.env` as an extension, but it is really a filename —
`Path(".env").suffix` is empty, so a naive implementation would never have matched it. Handled,
and noted in the build record.

Everything else is verbatim: the allow-lists are implemented exactly as ruled and pinned by a
test, so an edit to them fails the suite.

## For Paul

**F-06 is closed the way you asked** — the sink passes through to the writer, and the service
keeps sole ownership of the terminal event, so there are no duplicated or conflicting events.
A test asserts exactly one completion and no repeated write positions.

More usefully, the suite is class-level rather than instance-level. It walks every entry point
that takes a `progress` argument and asserts a real per-unit sequence, and a register test
enumerates those entry points by introspection so a new one cannot be added untested. That
was the second occurrence of the same mistake, so the instance was not the thing to fix.

**Both your cross-project constraints are respected.** BFT's old 14-error QC report was *not*
used as a repair queue — no action taken on it, pending the resolver port. And I checked the
suite for hard-coded sibling paths: every executable path derives from `__file__`. The
absolute paths that do appear are in `# Relative Path:` header comments, which is F-08
documentation debt rather than a functional problem.

## Three defects the process caught, before you had to

Recorded plainly, because all three would have shipped.

**My own shebang bug**, above — caught by writing George's round-trip matrix.

**Two installer defects**, both caught by the multi-predecessor matrix rather than by
reasoning about the batch file. One emitted a doubled backslash so the installer aborted at
its own root guard; the other checked the read-only flag by parsing `attrib` output
positionally and failed against a correctly protected file. The matrix gate paid for itself
on its first run.

And one QA problem worth naming: two Layer A tests rewrite the governed config, and Layer C
makes that file read-only. The suite would have passed in development and failed the first
time anyone re-ran it on an installed tree — which is exactly when they would run it. Fixed,
and the whole suite was then run against a read-only config to prove it: 840 passed.

## Numbers

| | Build 108 | Build 109 |
|---|---|---|
| Tests | 702 passed | **840 passed** |
| Coverage | 90.29% | **90.37%** (85% floor) |
| Upgrade paths proven | 1 | **4** (105/106/107/108) |
| Required dependencies | none | none |

## Still open

F-04 (JSONL) is Build 111 by ruling. F-05 (CLI *and* Tkinter onto the service) is Build 110.
No cancel button yet — also Build 110. F-08 source headers are corrected on the new files;
the historical sweep stays with the Build 111 QA freeze.
