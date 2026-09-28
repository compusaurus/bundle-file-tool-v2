# BFT v2.1 Build 116 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-25
**Kit:** `INSTALL_BUNDLETOOL_v2_1_116_workspace_fixes.zip`
**Delivers:** four defects Ringo found driving the Build 115 workspace on a real project

> **Install this instead of the Build 115 kit.** Its payload is a strict superset
> and the workspace 115 installs carries all four of these defects.

---

## What happened

Ringo took the new Selection Workspace to a 1,115-file project and it failed on
contact four separate ways. None of them showed up on a test fixture. All of
them show up immediately on real work — which is the useful lesson in this
build.

**1,378 → 1,402 tests. Coverage 91.29% → 91.21%.**

## The blocker: bundling was refused outright

```
Bundle integrity check FAILED
  nested-bundle entries: 2
    nested bundle [content]: scripts/seed_entry_points.py (2 embedded '# FILE:' markers)
```

Those files open with a transport header an older extraction wrote into them and
nobody ever stripped. Build 103's rule is *"the body must itself OPEN as a
complete transport artifact"* — and it does. The classifier worked exactly as
specified and still gave the wrong answer.

The diagnostic printed the evidence against itself: **2 embedded markers** on an
entry that would need over a thousand to be what it was accused of being.

### For George and Paul — the interesting part

The obvious fix is "require two or more transport blocks". It works on the real
case and breaks a real test: `test_29_real_historical_bundle_is_still_blocked`
uses a **one-entry** bundle, which is structurally identical to a stale header.
Counting cannot separate them.

What separates them is **which file the header names**:

| | entry path | header says |
|---|---|---|
| stale header | `scripts/seed_entry_points.py` | `# FILE: seed_entry_points.py` |
| nested bundle | `docs/old_snapshot.txt` | `# FILE: core/thing.py` |

Extraction writes a header describing the file it is writing, so a leftover
always names itself; a bundle carries somebody else's files. That holds for a
bundle of one entry, which is exactly where block counting runs out.

A single self-naming block is now reported as a **stale header** — recorded,
never fatal. Path-based detection is untouched and multi-block content is still
refused. Verified on the real tree: **1,115 files, 49 MB, exit 0.**

## Three UI defects, all obvious in use and invisible in tests

- **No scroll bars on any pane.** All three shipped without them. On 1,100 files
  the rows below the fold are simply unreachable and long paths run off the
  right edge. Six tests now check each pane's bars exist, are wired to the tree
  and are actually mapped — a bar that is present but unconnected is worse
  than none.
- **The decision list was 1,100 flat rows.** Files now fold under their folders
  and start collapsed, with Expand all / Collapse all. A search expands
  automatically, because a match hidden in a collapsed folder looks like no
  match.
- **No way to hide blocked files.** A *Hide blocked* toggle, off by default.
  Hiding is a **view filter only** — the counts still report them and the scope
  label says *"3 visible files (12 blocked hidden)"*. Pretending they were
  absent would be the same dishonesty as inventing a descendant count for a
  pruned directory.

## What I take from this

Three builds in a row now, the defects that mattered most were found by Ringo
using the thing rather than by a gate. The gates are not weak — they caught nine
defects in Build 115 alone — but they test what I thought to ask.

Every one of these four needed a **real project**: 1,115 files to make a missing
scroll bar fatal, a decade of accumulated backups to make a flat list unusable,
and a file carrying a header from an extraction years ago to break the integrity
classifier. My fixtures have five files and no history.

I do not have a clean answer yet. The nearest one is that a build touching the
UI should be exercised against a real tree before it ships, and I should say so
in the build record rather than relying on someone else to find it.

## Numbers

| | Build 115 | Build 116 |
|---|---|---|
| Tests | 1,378 | **1,402** |
| Coverage | 91.29% | **91.21%** |
| Real-project bundle | **failed** | **1,115 files, 49 MB, exit 0** |
| Install matrix | 4/4 | **4/4** |

## Next

**WP5**, the incremental preview cache — unchanged from the Build 115 plan. The
seam is ready and there is already a gate asserting re-planning does not get
slower.
