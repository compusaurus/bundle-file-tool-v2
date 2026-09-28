# BFT v2.1 Build 103 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-13
**Kit:** `INSTALL_BUNDLETOOL_v2_1_103_bounded_transport.zip`

## The problem, in one paragraph

The Bundle File Tool marks where each file starts with a comment line — `# FILE: ...`. That works
until you bundle a file that *contains* that same line, which is exactly what our own parsers, test
fixtures and documentation do. The tool could not tell a real boundary from an example of one, so
bundling our own project either invented files that do not exist, cut real files short at the
embedded marker, or was refused outright by the safety guard. A product whose job is faithful source
transport could not transport its own source.

## What changed

Every bundle now carries a **boundary token** — a short fingerprint calculated from the contents
themselves, and checked to be absent from every file in the bundle before anything is written. Only
a block stamped with that token counts as a boundary. Everything else, including text that looks
exactly like a boundary, is treated as ordinary file content and is preserved character for
character.

Four consequences worth knowing:

- **Old bundles still open, and old readers still open new bundles.** The visible format is
  unchanged. The token rides along as one extra field on the existing `# META:` line, which an older
  reader simply ignores.
- **Same input, same output, byte for byte.** The token is calculated, not random, so rebuilding an
  unchanged project produces an identical file. Our delivery process hashes payload files, so this
  had to hold.
- **Damage is reported, not absorbed.** If a bundle's structure is broken, the tool now stops and
  says so instead of quietly returning fewer files than it was given.
- **Extraction is counted.** Every file in a bundle must come out as written, skipped or errored. If
  the numbers do not add up, extraction halts rather than reporting success.

The safety guard that blocks accidentally bundling an old archive was also corrected. It used to
flag any file containing two or more marker lines, which caught our own test suite. It now only
flags content that genuinely begins as a complete bundle. Archive and bundle filenames are still
blocked exactly as before.

## Proof it works

The tool bundled its own `src` and `tests` trees end to end through the real command line: 63 files
discovered, bundled, validated, extracted back to disk, and compared. All 63 came back identical.
Nothing invented, nothing truncated.

The test suite went from 480 tests to 538, all passing, with coverage at 89.25% against an 85%
floor.

## Two things we need you to confirm

1. **Ringo:** this kit sets the installed version to **2.1.103**. The build number is part of our
   version string and the delivery standard requires build-stamped deliveries, so a new build has to
   own a new number — but the value itself was never separately ratified. Say the word if you want it
   held at 2.1.102.
2. **Paul and George:** three governance files were already out of step with the ratified state
   before this work began, and three release-contract tests were failing on arrival. A pyprojectmgr
   run on 30 July reset the project version to `0.1.0` in generated files, and the shipped
   configuration had reverted to the old allow-list with local machine paths in it. This build
   restores the ratified values, but **pyprojectmgr will overwrite them again on its next export**
   until blocker `BFT-WP0-QC-001` is resolved. That one belongs to the blocker, not to this build.

Two points from Paul's original test list now behave differently than that list assumed — both are
direct consequences of the grammar George ratified rather than gaps in it, both are tested, and both
are explained in `built_build103.md` §5. Neither loses a single byte.

## To install

Put the kit zip in your `Downloads` folder — exactly one `INSTALL_BUNDLETOOL_*.zip` there — then run
this from the project root:

```
PREP_AND_STAGE_BFT.bat
```

It snapshots and archives your current tree first, then stages and installs. The installer verifies
every file by SHA256 before and after copying, backs up everything it replaces, checks a content
marker in each installed file, and finally runs the whole test suite. If any check fails it stops and
leaves your backups in place. Expect it to finish with **538 passed** and a green coverage gate.

Nothing in this build touches the protected `.git` control, and WP0 Gate 1 is unaffected.
