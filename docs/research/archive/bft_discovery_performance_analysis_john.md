# Bundle File Tool — Discovery Hang: Root Cause and Mitigations

**From:** John, Lead Developer (BFT) — acting as analyst
**To:** Ringo, George
**Date:** 2026-08-24
**Re:** Screen recording 2026-08-24 10:02:13, and George's architectural analysis
**Evidence:** video frame analysis, `src/core/writer.py`, `src/core/validators.py`, `src/core/config.py`, and direct measurement against the recorded source tree

---

## Bottom line

**The hang is not PyThermX, and it is not really "slow I/O" either.** George is right that PyThermX renders faithfully. What he could not see from the recording is *why* it looks frozen:

> **BFT stops sending progress events for 7.82 seconds of a 9.23-second operation** — because it only emits progress when a file is *matched*, and it spends that entire window walking subtrees where nothing matches.

The indicator isn't malfunctioning. It's starved. PyThermX is displaying, accurately, the last thing it was told.

Underneath that sits a genuine performance defect: **87% of the traversal is inside `.venv`, which the deny list already excludes.** BFT walks 16,685 files it has been explicitly told to ignore, because the deny patterns are applied *after* the walk instead of during it.

I have a verified fix. **16× faster, silence down from 7.82s to 0.004s, and the output is bit-identical** — no change to what gets bundled. It is written and benchmarked but **not applied**; BFT is governed and I want your authorization before touching source.

There is also a second problem visible in every frame of your video that I don't think is part of the same issue — see *Secondary finding*.

---

## What the video shows

| Timestamp | Reading |
|---|---|
| t ≈ 0.2s | `195 files · discover · 0.2s · 1,250 files/s` |
| t ≈ 8.5s | `997 files · discover · 8.5s · 117 files/s` |
| Final | `Source: 1296 files` |

Throughput collapses by 10× and the counter crawls. George read this as I/O saturation. It is partly that — but the dominant effect is that the counter only advances on matched files.

---

## Measured root cause

Reproduced against the exact source from your recording (`pyprojectmgr_project/pyprojectmgrV2`):

| Measure | Value |
|---|---:|
| Filesystem nodes visited | **19,157** |
| Files included in the bundle | **1,336** |
| Wasted node visits | **17,821 (93.0%)** |
| Total discovery time | **9.23s** |
| **Longest unbroken progress silence** | **7.82s** |

Where the nodes live:

| Subtree | Nodes | Already in `deny_globs`? |
|---|---:|---|
| `.venv` | **16,685** | **Yes — `**/.venv/**`** |
| `deliverables` | 838 | No |
| `src` | 398 | — |
| `tests` | 319 | — |
| `scripts` | 187 | — |
| `htmlcov` | 130 | No |

### Three compounding defects

**D1 — `rglob("*")` cannot prune directories.** `writer.py:694` walks every node on disk, then filters. The deny list is *correct*; it is consulted at the wrong moment. `.venv` is denied and traversed anyway — 16,685 nodes of pure waste.

**D2 — `path.resolve()` runs on every file before filtering.** `writer.py:697`. Measured at **4.08s of the 9.23s (44%)**, spent normalising paths that are then discarded. `resolve()` costs roughly 5× `is_file()` per node on Windows NTFS.

**D3 — progress is emitted only on matched files.** `writer.py:710-713` — the `emit()` call sits *inside* the `should_include()` branch. Walking 16,685 excluded files produces **zero events**. This is the hang.

`emit()` in `core/progress.py:122` calls the sink synchronously with no throttling, which is why the naive version of this fix would flood the UI thread. The fix needs a rate limit; mine uses 100ms.

---

## The fix

Delivered alongside this memo: `docs/discover_files_performance_patch_proposed.py` — a drop-in replacement for `discover_files()` plus a benchmark harness that proves equivalence.

| | Before | After |
|---|---:|---:|
| Nodes visited | 19,157 | **1,433** |
| Elapsed | 9.23s | **0.57s** |
| Longest silence | 7.82s | **0.003s** |
| Files included | 1,336 | **1,336** |
| | | **Output bit-identical ✅ — 16.1× faster** |

Three changes matching the three defects: prune denied directories before descending; defer `resolve()` to files that survive filtering; emit on files *scanned* rather than *matched*, throttled, reporting `matched / scanned` so the message stays truthful during an empty subtree.

**The prune set is derived strictly from the existing deny list** — only patterns of the form `**/NAME/**` qualify, which today yields `.venv`, `__pycache__`, `archives`. Nothing is excluded that wasn't already excluded, which is why the file set cannot change. Run the harness yourself:

```bash
python docs/discover_files_performance_patch_proposed.py C:\Users\mpw\Python\pyprojectmgr_project\pyprojectmgrV2
```

### Separately: the deny list itself is thin — but that's your call

George is right that patterns are missing: `venv` (un-dotted), `node_modules`, `deliverables`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, backup and rollback directories. Adding them would cut the remaining 1,433 nodes to about 550.

**I have deliberately kept that out of the fix.** Expanding `deny_globs` changes *what ships in bundles* — it is a policy decision for you and George, and `config.py:120` shows deny entries are governed by a ratified policy list. The performance fix stands on its own and needs no such decision.

---

## Secondary finding — one oversized file kills the whole preview

Visible in every frame of your recording, and I don't think it belongs to the hang:

> `Error generating preview:`
> `File 'assets/splash/pyprojectmgr_splash.mp4' size (20.58 MB) exceeds limit (10.00 MB)`

`create_manifest()` raises `FileSizeError` on the first oversize file. `bundle_frame.py:594-599` catches it, wipes the preview, sets `current_manifest = None`, and disables bundle creation.

**One 20 MB video makes 1,335 perfectly good files unbundlable.** There is no way past it from the UI short of manually deselecting the file — and the error names the file but doesn't tell you that's the remedy.

**Recommendation:** treat `max_file_mb` as a discovery-time exclusion rather than a manifest-time exception — skip the file, list it in a "skipped: too large" summary, and let the bundle proceed. That is a behaviour change, so I'd want your agreement before implementing it. If you'd rather keep the hard failure, the error message should at least say what to do about it.

---

## Corrections to George's analysis

His direction is right and his recommended action item #1 — directory-level pruning — is exactly the fix. Three details are off:

**1. The un-dotted `venv` premise doesn't apply here.** George attributes the cost to the target using `venv` without a dot, falling outside `**/.venv/**`. The recorded source has **`.venv`, dotted** — it *is* denied. It was walked anyway. That distinction matters: fixing the pattern name would not have helped, because deny patterns don't prune traversal at all. The defect is architectural, not a typo in the pattern list.

**2. The oversize asset is `pyprojectmgr_splash.mp4` at 20.58 MB**, not `pyintrosp_splash.mp4` at 10.98 MB.

**3. "Only path names and basic `stat().st_size` checks" understates the win.** We can do less than that: `os.walk` hands us filenames for free, so discovery needs no `stat()` at all. Dropping `resolve()` alone recovers 44% of the runtime.

His point about Windows Defender intercepting recursive directory queries is plausible and I haven't isolated it — but it is now moot at 1,433 nodes.

**On his item for Paul** (benchmark the discovery path): built, and included here. Paul is on pyprojectmgr, so I've picked it up.

---

## What I have and haven't done

**Done:** diagnosed and measured the root cause; written and benchmarked the patch; verified output equivalence.

**Not done — deliberately:** I have not modified any BFT source. BFT is governed — manifest, authority chain, Team Delivery Standard v2 build kits. Editing `src/core/writer.py` outside a build would create exactly the governed drift we spent Builds 128–133 cleaning up in pyprojectmgr. The patch sits in `docs/`, which is outside the scanned tree.

**What I need from you:**

1. **Authorization to ship this as a governed BFT build** — the change is small, measured, and output-identical. I'd add a regression test asserting both the file-set equivalence and a maximum inter-event gap, so a future change can't silently reintroduce the silence.
2. **A decision on the oversize-file behaviour** (skip-and-warn vs. hard fail).
3. **George's call on expanding `deny_globs`**, since `config.py` treats it as ratified policy.

---

## One thing worth saying about the indicator

Your framing was that a progress indicator which doesn't work is barely better than none. I'd go further after looking at this: **it was actively misleading.** It showed 117 files/s while the process was reading 2,000 files/s — the throughput figure described matched files, not work done. Someone reading that number would conclude the disk was struggling. It was not; the reporting was.

The fix reports `matched / scanned` for exactly that reason. When BFT spends eight seconds inside a virtualenv it should say so, not go quiet and let the user guess.

— John
