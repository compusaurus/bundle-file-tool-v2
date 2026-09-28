# Memo — Two decisions for ratification

**From:** John, Lead Developer
**To:** George (Architect) — ruling requested · Paul (Analyst) — sequencing · Ringo (Owner) — awareness
**Date:** 2026-08-23
**Status:** Analysis complete. No code changed. Awaiting ratification before implementation.
**Scope:** Bundle File Tool. Item 2 has family implications for pyprojectmgr and PyThermX.

---

## Why this is a memo and not a build record

Both items outlive Build 108. One is a shipped product defect that predates every build in this
series; the other has now recurred four times across Builds 104, 105, 107 and 108. Parking either
inside `built_build108.md` ties a standing decision to a record that becomes archive the moment
Build 109 ships — which is a fair description of how the second item reached a fourth recurrence.

Two decisions are requested. Neither is urgent enough to interrupt current work, and neither
should be implemented before it is ratified.

| Ref | Item | Ask |
|---|---|---|
| **DEFECT-BFT-001** | Extract-time header injection corrupts structured text | Choose a remedy; confirm whether `add_headers=True` remains the right default |
| **GOV-BFT-001** | Governed artifacts have no defence against a foreign writer | Choose a remedy family; rule on whether this is a code problem or an operational one |

---

# Part 1 — DEFECT-BFT-001

## Extracting a bundle corrupts every structured text file it writes

### What happens

`BundleWriter.write_entry` injects the canonical repository header into **every text entry**, with
no file-type check:

```python
if header_enabled:
    repo_header = self._build_repo_header_block(entry)
    payload = repo_header + text_content
```

The header block is `#`-comment lines. `add_headers` defaults to **`True`**
(`app_defaults.add_headers` in the governed config). So unbundling any bundle containing a file
whose format does not treat `#` as a line comment produces a file that no longer parses.

### Proof

Extracting `bundle_config.json` from `bundles\BFTv2_v2.1 Build 104_bundle.txt` with default
settings produces:

```
# ============================================================================
# SOURCEFILE: bundle_config.json
# RELPATH: bundle_config.json
# PROJECT: Bundle File Tool v2.1
...
{
  "version": "2.1.0",
```

`json.load()` on the result fails at line 1, column 1. With `add_headers=False` the same
extraction produces valid JSON. Reproduction steps are in Appendix A.

### Scope

JSON is proven. The rest follows from the code path having no type check at all: `.json`, `.css`,
`.html`, `.xml`, `.sql`, `.js`, `.c`, `.java` — any format where `#` is not a line comment. Binary
entries are unaffected (they take the other branch). Formats where `#` *is* a comment — `.py`,
`.sh`, `.yaml`, `.toml`, `.ini` — are unharmed.

### Why it survived this long

This is the part worth George's attention, because it is a testing decision rather than a coding
mistake.

**Every round-trip test sets `add_headers=False`.** `tests/unit/test_roundtrip.py` says so in its
own header at line 16 — *"Added `add_headers=False` to writer in tests asserting byte-for-byte"* —
and all ten writer constructions in that file pass it.

That was a reasonable local decision: headers defeat byte-for-byte comparison, so the tests turned
them off to assert the thing they were written to assert. The consequence is that **the shipped
default has no round-trip coverage at all.** We prove fidelity only in a configuration our users
do not run by default.

### Severity

I would rate this above the governance drift. Bundle File Tool's core promise is that a bundle
round-trips. For an entire class of file, at the default setting, it does not — silently, with no
error, and the damage lands in the user's output directory rather than in ours. The original bytes
survive below the header, so it is recoverable, but a user extracting a web project or a config
tree gets files that no longer load.

It is also long-standing: Team Directive v4 era, not introduced by Builds 107 or 108.

### Options

| | Option | Cost | What it does **not** cover |
|---|---|---|---|
| **A** | Comment syntax per file type — map extension to `#`, `//`, `/* */`, `<!-- -->`, and skip types with no comment form | Highest. A syntax table to own and extend | Formats with no comment form at all (JSON) still need a skip rule, so A contains B |
| **B** | Header allow-list: inject only into extensions known to accept `#` | Small and safe. One constant plus a guard | Source files in `//`-comment languages keep getting no header, as today |
| **C** | Flip the default to `add_headers=False` | Smallest change | Does not fix the corruption, only its blast radius; and it silently drops a Team Directive v4 behaviour George ratified |
| **D** | Detect structured content and skip headers for it | Medium, and fragile — content sniffing will be wrong at the margins | Not recommended; a heuristic in the write path is a future defect |

**Recommendation: B now, A later if the team wants headers in `//` languages.** B is a handful of
lines, it cannot make anything worse than today, and it is easy to review.

**And, independent of which option is chosen: a round-trip test at the default setting, across
file types.** That is the control that was missing. Whichever remedy is ratified, the test is what
keeps it ratified — without it, the same gap reopens the first time someone touches the writer.

I would rather George rule on C explicitly than have me quietly change a default he approved.

### Ask

1. Choose A, B, C or D.
2. Confirm whether `add_headers=True` remains the correct shipped default.
3. Confirm the round-trip-at-default test is in scope for the same build.

---

# Part 2 — GOV-BFT-001

## Governed artifacts have no defence against a foreign writer

### What happened

On 2026-08-23 at 11:54:52 the live `bundle_config.json` was replaced: `version` reverted to
`2.1.0`, and `safety.allow_globs` reverted from the ratified `["**/*"]` deny-list posture to a
14-entry allow-list. This is the **fourth** such event.

### Provenance — confirmed, not inferred

The file that landed is the Build-104-era configuration archived inside
`C:\Users\mpw\Python\bundles\BFTv2_v2.1 Build 104_bundle.txt`. Parsed out of that bundle and
compared field by field, it matches in **every value** — `version`, the allow-list,
`window_geometry` `1902x980+-3+24`, `first_launch`, `last_bundle_save_dir` — except one:
`last_source_dir`, which on disk reads `…/bundle_file_tool_v2/scripts`.

That geometry string exists in exactly two places on the machine: inside that bundle, and in the
saved copy from the 2026-08-18 incident. No current default produces it.

### What was ruled out, and how

**pyprojectmgr.** Ringo's first hypothesis, and a fair one — a scan did run that morning. Ruled
out three ways: BFT's own `.pyprojectmgr/logs/pyprojmgr.log` and `assets.db` were last written
2026-08-20; no pyprojectmgr log mentions `bundle_file_tool`, and its only run in that window
(11:59:49) scanned its own directory *after* the overwrite; and its source contains no reference
to `bundle_config.json`.

**The installed Build 107.** Verified rather than assumed, because if the current build could do
this it would be a defect in my own work. `ConfigManager.save()` raises `ReadOnlyConfigError`
unconditionally, `_create_default_file()` is creation-only and never overwrites, and nothing under
`src/` calls `.save()`.

**Our own extract path.** This was the interesting candidate — the bundle *contains*
`bundle_config.json`, so extracting it over the live tree would write exactly that file. Ruled out
by experiment (Appendix A):

- At the **default** setting, extraction produces **invalid JSON**. The file on disk is valid
  JSON, so a default extraction did not produce it.
- Extraction writes `src/core/config_ids.py` at **939 bytes**; the live file is **940** and
  matches the 2026-08-20 snapshot. Same for `static_ids.py`, 1098 against 1099. The writer does
  not normalise the trailing newline under either header setting, so those two files were not
  written by extracting that bundle.

There is an irony worth recording: the drifted file is valid JSON *because* it did not come
through our extract path.

**What remains** is an older Bundle File Tool — the pre-Build-104 whole-document save that wrote
UI state back over the governed config — running against this project root. That matches Ringo's
recollection of having used the tool that day.

### Why Build 105 did not close it

Build 105 anchored config resolution to the installed application's own root. That stops *this*
copy writing someone else's file. It cannot stop a *different, older* copy writing *ours*, because
that copy resolves the path itself and never runs our code.

The enabler is structural: several runnable copies of Bundle File Tool exist on one disk, and
`bundle_config.json` sits in the project root where any of them can resolve it. **No change
confined to the current copy can fully close this.** That is the honest constraint, and it is why
I am asking for a ruling rather than proposing a patch.

Known stale trees at time of writing include `docs\bft_qc_target_base_20260724` (VERSION 2.1.102,
no `ReadOnlyConfigError` guard).

### Options

| | Option | Cost | What it does **not** cover |
|---|---|---|---|
| **A** | **Detect.** Record the config's SHA256 and the writing process identity at load; report loudly on mismatch, extending the Build 105 drift reporter | Small | Prevents nothing. Converts an afternoon of forensics into a startup warning |
| **B** | **Refuse.** Verify the config against a governed digest at load and decline to run on a tampered file until reconciled | Medium | Still does not prevent the write; and a hard refusal on a config edit will annoy whoever legitimately edits one |
| **C** | **Deny at the filesystem.** Installer marks `bundle_config.json` read-only or ACL-denies writes; the installer clears the flag for its own gated placement | Small, and it is the only option that actually prevents the write | Sidesteps the code entirely; an operator with rights can still override, and it must not fight the installer |
| **D** | **Retire the stale trees.** Operational: delete or neuter pre-104 copies | Smallest | Fixes the observed cause and nothing structural. A new stale copy reintroduces it |
| **E** | **Relocate.** Move the governed config out of the project root to a path older copies do not resolve | Largest; touches the installed layout and the delivery standard | Real fix, but disproportionate unless the family adopts it together |

**Recommendation: D plus A now, and C if George wants prevention rather than detection.**

D is what actually stops the cause we observed. A is cheap and means a fifth occurrence names
itself. C is the only genuine prevention and is nearly free, but it changes how the installer
handles that file, so it needs George's ruling rather than my judgement. I would not do B or E on
current evidence — B trades a rare silent problem for a frequent loud one, and E is a family-wide
change that should be decided on its own merits, not as a reaction to this.

### Ask

1. Choose a remedy family: detect (A), prevent (C), operational (D), or a combination.
2. Rule on whether stale runnable trees are permitted to remain on the working machine. That is
   the real control, and it is a policy question rather than an engineering one.
3. If the answer touches the governed-artifact pattern generally, say so — pyprojectmgr and
   PyThermX carry the same shape and would inherit the rule.

---

## Non-goals

To keep the asks clean, these are explicitly **not** proposed here:

- No change to the ratified deny-list posture (D-005) or to `GOVERNED_POLICY`.
- No change to the delivery standard, the family helper block, or the stager.
- No extract-side governed-artifact gate. It was the natural remedy for the hypothesis the
  experiment killed, and I am not carrying it forward on sentiment.
- No cancel path for the Tkinter progress dialog. Tracked separately in `built_build108.md` §11.

## Effect on the Build 108 documents

`built_build108.md` §7 and the *For George* section of `team_build108.md` raise GOV-BFT-001 as an
open item. This memo supersedes them as the place where it is decided. Their factual content
stands; DEFECT-BFT-001 is new and appears in neither.

---

## Appendix A — Reproduction

**DEFECT-BFT-001**, from the project root:

```
python src\cli.py unbundle "C:\Users\mpw\Python\bundles\BFTv2_v2.1 Build 104_bundle.txt" -o probe --overwrite overwrite
python -c "import json; json.load(open('probe/bundle_config.json', encoding='utf-8'))"
```

The second command raises `JSONDecodeError: Expecting value: line 1 column 1`. Adding
`--no-headers` to the first makes it succeed.

**The extract-path experiment** for GOV-BFT-001 is
`scratchpad\extract_probe.py`: it extracts that bundle into a scratch tree under both header
settings and compares the three affected files against the drifted copy and against the live tree.
The live tree is only ever read.

## Appendix B — Evidence index

| Artifact | Location |
|---|---|
| Drifted config, as found 11:54:52 | `scratchpad\bundle_config.DRIFTED_20260823_1154.json`, sha256 `699ab8d6…` |
| Restored config, verified against the Build 107 delivery manifest | live tree, sha256 `c2d6365a…` |
| Source of the drifted content | `bundles\BFTv2_v2.1 Build 104_bundle.txt`, entry `bundle_config.json` |
| Prior incident copy | `bundle_config.DRIFTED.2026-08-18T21-29-53.json` |
| Clean pre-108 reference tree | `bundle_file_project\BFTv2_v2.1 Build 107` |

**A correction on the record.** In my first report of this incident I said only
`bundle_config.json` had changed that day. That was wrong — I read it from a directory listing I
had truncated. `src/core/config_ids.py` and `src/core/static_ids.py` also carry that day's mtime
(11:53:32). Their content is byte-identical to the 2026-08-20 snapshot, so nothing was lost, and
what touched them remains unidentified and benign. It does not affect either conclusion above,
but the earlier statement was too strong and should not stand uncorrected.
