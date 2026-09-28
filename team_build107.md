# BFT v2.1 Build 107 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-20
**Kit:** `INSTALL_BUNDLETOOL_v2_1_107_pythermx_progress.zip`

## The short version

Bundle File Tool now shows you what it is doing during long operations. That was Ringo's
original complaint — no feedback on large folder operations — and this is the build that
answers it.

## Read this before you install

**The Build 106 kit is still in Downloads, uninstalled.** Move it out before staging this
one. Two reasons:

1. The stager requires exactly one delivery zip in Downloads and will abort with two.
2. Build 107 contains everything Build 106 contained, so you do not need it. Installing 106
   *after* 107 would take the tree backwards.

Build 107 installs over 2.1.105 or 2.1.106.

## What you will see

Discovery starts as a moving counter, because until the walk finishes nobody can know how
many files there are:

```
\ | discover | 0 files | 0.0s
```

The moment the count is known, the same bar becomes a real percentage — it does not vanish
and get replaced by a different widget:

```
[########################################] | 100.0% | 8 files found - 8/8 | discover | 500 files/s | OK
[#####-----------------------------------] |  12.5% | 1/8 | read
```

`8 files found - 8/8` is the join: the counter's final value is kept as history next to the
total. That is exactly what `promote()` was added to PyThermX 0.2.0 for, and it is why this
integration waited for that release.

Unbundling reports progress too.

## Controls

```
bundle-tool bundle SRC                    bar on if you are at a terminal
bundle-tool bundle SRC --progress bar     force it on
bundle-tool bundle SRC --progress none    turn it off
```

The default is `auto`, and it has a property worth stating: when you redirect output to a
file or a pipe, there is no terminal, so there is no bar. Your redirected output is
unchanged from Build 106, byte for byte.

## Piping a bundle is still safe

Build 105 made `bundle` write the artifact to standard output and everything else to standard
error. A progress bar is full of carriage returns, so on the wrong stream it would quietly
corrupt every piped bundle.

The bar draws on standard error. There is a test that runs the real CLI as a separate process
with the bar forced on and checks that not one carriage return reaches standard output.

## PyThermX is optional

Bundle File Tool does not require it. Without it, the tool behaves exactly as Build 106 did,
minus the bar — no error, no warning, nothing to configure.

The wheel ships **inside the kit** and installs offline, so there is no network step. If that
install fails for any reason the build still succeeds, on purpose: refusing to install Bundle
File Tool because an optional progress bar could not be set up would be the wrong trade.

## For George

Two things need your eye:

**A safety-policy addition.** Vendoring the wheel into the tree meant `.whl` files would have
been swept into every self-bundle as base64. `**/*.whl` is now on the deny list, alongside
`**/*.zip` and `**/*.tar` which were already there. I consider it completing an existing rule
rather than a new one, and the ratified governed-policy list is untouched — but it is safety
policy, so you should see it rather than find it.

**A correction.** I had been carrying the wrong SHA-256 for the family delivery helper block
in my notes. The contract defines it as the bytes from `BEGIN` through `END` inclusive, which
is `380037a3…`. Build 106's installer already matched that value, so no shipped kit was
affected — my note was wrong, not the kits. This installer copies the block from the
canonical include and re-hashes it after assembly.

Still waiting on your ruling on the `OperationProgress` contract shape (built_build106.md
§8). Build 107 renders the contract as it stands. If you change it, the adapter is the only
thing that reads it and it is a single file.

## For Paul

This is your sequencing step 5, and it holds the line you drew in the Build 104 review: the
service emits events, the adapter draws them. Core imports no renderer, and that is now a
test rather than an intention — it AST-parses every file under `src/core/` and fails if any
of them imports `pythermx` or the adapter.

WP5, migrating the CLI onto `BundleToolService`, is deliberately **not** in this build. I
wired progress into the existing CLI call sites instead. WP5 changes control flow for every
command; combining it with a new renderer would mean a failure could be either, and I would
rather ship one thing that can be judged cleanly.

## Numbers

| | Build 106 | Build 107 |
|---|---|---|
| Tests | 622 passed | **661 passed** |
| Coverage | 88.04% | **90.23%** (85% floor) |
| Required dependencies | none | none |

39 new tests. No existing test was amended to accommodate this change — a point worth making,
because a renderer that forced edits to 622 tests would be a renderer in the wrong place.
