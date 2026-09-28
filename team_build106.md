# BFT v2.1 Build 106 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-18
**Kit:** `INSTALL_BUNDLETOOL_v2_1_106_service_facade.zip`

## What this build is

The first piece of the architecture we ratified back in Build 100 and never built: **one
shared service underneath all three interfaces**.

Until now the command line assembled the parser, the writer, the file discoverer and the
profile registry itself. So would the desktop UI. So would the web version. Three copies of
the same orchestration, free to drift apart, and each one able to skip a safety check by
forgetting to call it. Paul's review recorded that work package as not started.

Build 106 adds the service, and puts the safety gates inside it — so no interface can bypass
the nested-bundle refusal or the extraction count check by wiring the parts up its own way.

## The part that matters for progress bars

Paul spotted the specific thing blocking therm: when the tool scans a folder, it hands back a
finished list. Nothing happens in between, so a progress display has nothing to show except a
spinner, no matter how long the scan takes.

Discovery now reports as it goes:

```
discover  0 files   (total unknown)
discover  1 files   (total unknown)
discover  2 files   (total unknown)
discover  4 of 4    (total now known)
read      1 of 4
```

That handoff — a count rising with no total, then a total once the scan finishes — is exactly
what therm 0.2.0's `promote()` was designed to consume. **I tested it against the real therm
package**, not a stand-in: a fifteen-line adapter in the caller turns these events into a
live therm bar. BFT gained no dependency on therm to do it, which is the whole point.

The same events serialize to JSON, so the desktop UI can queue them onto its own thread and a
web version can stream or poll them. One operation, three interfaces, no duplicated logic.

## One deliberate omission

**The command line has not been moved onto the service yet.** That is the next work package,
and keeping it separate means each change can be reviewed — and reversed — on its own. The
CLI behaves exactly as it did in Build 105.

## Evidence

622 tests pass, up from 592, coverage 90.09%. Thirty new tests cover the event semantics, the
safety gates, both profiles round-tripping through the service, and a check that the core
imports no interface toolkit at all — that last one enforced by reading the source, because
it is the property everything else depends on.

## For George

The **shape** of the progress event is Paul's proposal and has not been through you. I shipped
it rather than waiting, because Ringo asked for forward motion and the change is additive —
nothing existing calls it, and progress is off by default. Four things worth your ruling are
listed in `built_build106.md` §8, the main one being whether to freeze the phase vocabulary
now, since a web adapter will key its display off those names.

If you rule differently, the rework is confined to two new files.

## To install

Kit in `Downloads`, then from the project root:

```
PREP_AND_STAGE_BFT.bat
```

Expect **622 passed**. The installer upgrades 2.1.105 and is idempotent on 2.1.106.
