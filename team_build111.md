# Team Communication — BFT v2.1 Build 111

**From:** John, Lead Developer
**To:** Ringo, George, Paul
**Date:** 2026-08-24
**Kit:** `INSTALL_BUNDLETOOL_v2_1_111_open_bundle_progress.zip`

---

Ringo — Open Bundle now reports through PyThermX, and it turned out not to need
the indeterminate mode at all.

Both bundle profiles start from `splitlines(keepends=True)`, so the line count
is known before parsing begins. That makes the parse phase **determinate** — a
real percentage, not a spinner. The read phase is determinate too: `stat()`
gives the file size up front, and the file is now read in 1 MiB chunks reporting
actual byte position rather than one blocking call. Indeterminate remains
available as the fallback for any future profile whose parse isn't
line-oriented, but neither shipped profile needs it.

Opening a 41.3 MB bundle from the live pyprojectmgr tree — 1,092 files,
395,856 lines — previously produced **zero** progress events across 0.80
seconds of blocked UI. It now produces nine, with a worst gap of 0.219s, and
the parsed result is byte-identical. That last part is a test, not a claim:
`parse_file()` takes a different read path when a sink is attached, so
equivalence had to be proven rather than assumed.

The progress message carries both numbers — *"127 files recovered"* against a
line-based bar. Lines are what the bar can honestly measure; files are what you
actually want to know. Same reasoning as the discovery fix in Build 110.

Two things worth knowing about the design. The profile contract gained a
keyword-only `progress` parameter, and a profile written against the old
contract still works — acceptance is decided by inspecting the signature.
And Open Bundle can't use the existing 200-file threshold, because the entry
count is the *result* of the work being measured; it gates on file size instead,
governed by `ui.progress.min_parse_mb`, default 2 MB.

859 tests pass, coverage 90.41%. No existing test needed changing — the contract
extension is backward compatible by construction.

**Four defects were caught during the build**, all before shipping, and three
share a root cause worth naming.

The first version detected legacy profiles by catching `TypeError` from the
call. A genuine `TypeError` inside parsing would have hit the same handler and
been silently retried without a sink — a real defect converted into a missing
progress bar. Replaced with signature inspection, and there is now a test that
fails if a real error is ever swallowed there.

Two of my new tests patched a profile instance, but `ProfileRegistry.get()`
builds a fresh object every call, so the patch never reached the code under
test. One failed honestly. **The other passed** — it claimed to verify
legacy-profile tolerance while actually exercising the modern profile. A green
test that verifies nothing is worse than a red one, and it would have shipped as
coverage.

And I introduced a line-ending regression: the version bump wrote the governed
JSON with `write_bytes` (LF) where every prior build used `write_text` (CRLF).
The Layer A integrity test caught it. The cause was over-applying the Build 110
lesson — the delivery manifest needed explicit bytes *because* text mode doubled
its CRLFs; this file needs text mode for exactly the opposite reason. The right
write method is a property of the file, not a rule.

All four are the same hazard we named `H-01`: a check whose result had more than
one explanation. It has now paid for itself across two consecutive builds.

**Installation.** Installs over 2.1.110 and re-enters idempotently on 2.1.111 —
Gate A0 accepts both, which is the correction from last build. Drop the single
zip in Downloads and run `PREP_AND_STAGE_BFT.bat`. The installer runs the full
859-test suite as its acceptance gate, so give it a minute.

George — the profile contract change is the one architectural item here.
`ProfileBase.parse_stream` now takes an optional keyword-only sink. It is
backward compatible by inspection rather than by exception handling, which I
think is the right call for a contract that third parties could implement, but
it is your call whether the tolerance should exist at all or whether profiles
should simply be required to accept it.

Paul — `ThrottledReporter` in `core/progress.py` is the shared primitive for
this. Discovery still has its own inline copy of the same logic from Build 110;
folding it onto the shared class would be a small, safe cleanup whenever that
file is next open.

— John
