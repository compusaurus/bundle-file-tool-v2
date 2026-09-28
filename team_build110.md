# Team Communication — BFT v2.1 Build 110

**From:** John, Lead Developer
**To:** Ringo, George, Paul
**Date:** 2026-08-24
**Kit:** `INSTALL_BUNDLETOOL_v2_1_110_discovery_performance.zip`

---

Ringo, the hang in your recording is fixed, and it was not PyThermX.

Discovery against `pyprojectmgrV2` took 16.04 seconds, and **13.15 of those
were a single unbroken window with no progress events at all**. BFT emitted
progress only when a file *matched*, and it spent that window walking `.venv` —
16,685 files that your deny list already excluded. PyThermX was rendering
faithfully; it had simply not been told anything since the last match. The
throughput figure made it worse: 117 files/s described matched files, not work
done, so a healthy disk looked saturated.

Three changes, all ratified in `ARCH-RULING-2026-08-24-01`:

- Discovery now prunes denied directories before descending into them, instead
  of walking them and discarding the contents.
- `resolve()` is deferred to files that survive filtering — it was 44% of the
  runtime, spent on paths about to be thrown away.
- Progress reports files *scanned*, not files *matched*, throttled to 100ms and
  showing `included / scanned` so an empty subtree still moves the bar.

**16.04s → 1.71s, and the longest silence is now 4 milliseconds.** The
discovered file set is bit-identical: the prune list is derived from the deny
patterns already in force, so nothing is excluded that was not already filtered
out. That equivalence is a test, not an assurance.

The second problem in your recording was separate and arguably worse. One
20.58 MB video — `assets/splash/pyprojectmgr_splash.mp4` — raised an exception
that blanked the preview and disabled Create Bundle across 1,335 healthy files,
with no indication of what to do about it. Oversize files are now recorded and
skipped: the size limit still holds, the file stays out of the payload, the
preview leads with a notice naming the file and the remedy, and everything else
bundles normally. Verified against that exact file.

Default deny patterns gained the Tier 1 set George ratified — `venv`, the tool
caches, `node_modules`, backup trees. Your own configuration already covered
most of them, which is why the deny list was never the cause; the four missing
entries were appended without removing anything you had.

847 tests pass, coverage 90.25%. Two Build 109 tests were updated rather than
deleted, because they encoded contracts the rulings deliberately replaced —
per-file progress emission, and a fatal oversize error. Both still assert the
part that remains true.

One defect worth flagging, found during implementation and fixed before it
shipped: the throttle was primed by subtracting an interval from
`time.monotonic()`, which fails on float precision — `t - (t - 0.10)` evaluates
to `0.09999999998`, so the first scan event never fired. On small trees no
progress event was emitted at all. A test caught it. It is the kind of thing
that reviews do not.

**Installation.** This kit installs over 2.1.109 only — Build 109 carried the
tri-layer defence and header allow-list that this build does not restate, so
installing onto anything earlier would leave those absent. Gate A0 enforces
that. Drop the single zip in Downloads and run `PREP_AND_STAGE_BFT.bat` from
the project root. Rollback material is written before any file is touched.

George — one deviation from your ruling. It directs this into "the Build 109
delivery candidate", but 109 shipped yesterday and is installed on Ringo's
machine; folding new payload into a delivered build number would break its
supersession claim over 106–108. This ships as Build 110. Items 5, 6 and 7 in
your §4 matrix were already delivered in 109 and are untouched.

Paul — the benchmark harness is in
`docs/discover_files_performance_patch_proposed.py` and runs standalone against
any tree. It proves both the speedup and the output equivalence, so it should
drop into the QA staging suite without modification.

— John
