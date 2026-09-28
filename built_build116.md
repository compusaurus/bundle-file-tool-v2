# BFT v2.1 Build 116 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_116_workspace_fixes.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-25
**Delivers:** four defects found by Ringo driving the Build 115 workspace on a real project
**Supersedes for installation:** Builds 106 through 115. **Install this instead of the 115 kit.**

---

## 1. Why this build exists

Ringo took the Build 115 Selection Workspace to a 1,115-file project and it
failed on contact in four separate ways. None of them appeared on a test
fixture; all of them appear immediately on real work.

**1,378 → 1,402 tests. Coverage 91.29% → 91.21%.**

## 2. The blocker: a stale header refused as a nested bundle

Bundling pyprojectmgr failed outright:

```
Bundle integrity check FAILED for C:\Users\mpw\Python\bundles\...Build_135x.txt:
  total entries: 1115
  nested-bundle entries: 2
    nested bundle [content]: scripts/seed_entry_points.py (2 embedded '# FILE:' markers)
    nested bundle [content]: scripts/seed_infrastructure_relationships.py (2 ...)
  Refusing to proceed.
```

Those two files open with a transport header an older extraction wrote into
them and nobody stripped:

```
# ===================================================================
# FILE: seed_entry_points.py
# META: encoding=utf-8; eol=LF; mode=text
# ===================================================================
import sys
```

Build 103's content rule is *"the body must itself OPEN as a complete transport
artifact"* — and this does. So the classifier was working exactly as specified
and still gave the wrong answer, because a file wearing a leftover header is
not a bundle.

The diagnostic even printed the evidence against itself: **2 embedded markers**
on an entry that would need one per bundled file — over a thousand — to be
what it was accused of being.

### 2.1 Why block-counting alone was not enough

The obvious fix is to require two or more transport blocks. That works for the
real case and breaks a real test: `test_29_real_historical_bundle_is_still_blocked`
uses a **one-entry** bundle, which is structurally identical to a stale header —
separator, `# FILE:`, `# META:`, separator, body. Counting cannot separate them.

**What separates them is which file the header names.**

| | entry path | header says |
|---|---|---|
| stale header | `scripts/seed_entry_points.py` | `# FILE: seed_entry_points.py` |
| nested bundle | `docs/old_snapshot.txt` | `# FILE: core/thing.py` |

Extraction writes a header describing *the file it is writing*, so a leftover
always names itself. A bundle carries somebody else's files, so it names
something other than its own path. That holds for a bundle of one entry, which
is exactly where block counting runs out.

A single block naming its own file is now reported as a **stale header** —
recorded in the integrity report, never fatal. Everything else is unchanged:
path-based detection is untouched, and multi-block content is still refused.

Verified on the real tree: **1,115 files, 49 MB, exit 0.**

## 3. No scroll bars on any pane

All three panes shipped without them. On a 1,100-file project that is not
cosmetic — rows below the fold are unreachable and long paths run off the right
edge with no way to read the end of them.

Every pane now has both bars, wired and laid out, in a grid-managed holder that
keeps the tree's expansion weight. Six tests, parameterised per pane, check the
bars exist, are connected to the tree, and are actually mapped — a scroll bar
that is present but not connected is worse than none.

## 4. The decision list was 1,100 flat rows

The right pane opened on a thousand near-identical backup files with no way to
see the shape of the selection.

Files now fold under their folders and start **collapsed**, so the pane opens on
a handful of rows, with *Expand all* / *Collapse all* alongside the bulk
actions. A search expands automatically — a match hidden inside a collapsed
folder would make the filter look broken.

## 5. No way to hide blocked files

A **Hide blocked** toggle, off by default. Blocked paths cannot be included and
are not actionable, so on a project with many they are pure noise.

Hiding is a **view filter only**. The counts still report them and the scope
label says so explicitly — *"3 visible files (12 blocked hidden)"* — because
pretending they are absent would be the same dishonesty as inventing a
descendant count for a pruned directory. Asking for the Blocked view explicitly
still shows them.

## 6. Evidence

```
1402 passed in 80.52s
Required test coverage of 85.0% reached. Total coverage: 91.21%
src\core\bundle_integrity.py   91 stmts  4 miss  93%
src\ui\selection_workspace.py 426 stmts 52 miss  84%
src\ui\workspace_model.py     463 stmts 14 miss  95%
```

24 new tests: 9 integrity, 6 scroll bars, 5 folded decisions, 4 hide-blocked.

Governed config digest `7ac770bc…`; manifest `ba59c4b0…`; helper block
`380037a3…` verified before assembly and re-hashed after.

## 7. Supersession

Gate A0 accepts `2.1.105` through `2.1.116`. The 115 kit is superseded — its
payload is a strict subset of this one, and the workspace it installs carries
all four of these defects.
