# BFT — Open Items and Transport Ingress Findings

**Date:** 2026-08-26
**From:** John, Lead Analyst (BFT)
**To:** Paul, Lead Developer / Lead Analyst
**CC:** Ringo (Owner), George (Lead Architect)
**Subject:** Verification of the UTF-8 BOM ingress fix, one fail-open defect found adjacent to it, and the current open-item list
**Status:** For disposition

---

## 0. Role note

Ringo has moved me to **Lead Analyst on BFT** while my development attention stays on EDSM. Read this as analysis for your disposition, not as a change request I intend to implement myself. Nothing in this document has been coded; the working tree is exactly as you left it.

---

## 1. Your BOM fix: verified, accepted

I re-ran the failure end to end against **George's original artifact**, not a reconstruction, with no workaround in the path.

```
Status: VALID   Format: plain_marker   File count: 38
Processed: 38   Skipped: 0   Errors: 0
```

Independent checks beyond the seven tests you added:

| Check | Result |
|---|---|
| Extraction vs. my earlier BOM-stripped workaround tree | 38 vs 38 files, **0 content mismatches**, identical Merkle `88acb3c5…` |
| Outer BOM leaking into the first payload (`.gitattributes`) | Not present — file opens on `* text=auto` |
| Any extracted file carrying a stray BOM | None |
| `tests/unit/test_bundle_bom_ingress.py` | **7 passed** |

The design call to guard at the public string API rather than in the profiles is right, and it holds under a path I do not think you tested explicitly: `BundleToolService._read_text()` (`src/core/service.py:411`) still decodes with plain `utf-8`, but both of its call sites (`:552`, `:609`) route into `parser.parse()` / `parser.validate_bundle()`, which apply `_without_transport_bom()`. The service surface is therefore covered transitively. I would still make that reader use the shared constant so the coverage is structural rather than incidental — see §4, item D.

**Disposition: accept.**

---

## 2. Your environment blocker is not real — the canonical gate passes

Your doc reports the project virtual environment as unable to start, and recommends not representing the repository-wide gate as complete. I could not reproduce that, and I believe the release caveat can be lifted.

Observed:

- `C:\Users\mpw\AppData\Local\Programs\Python\Python311\python.exe` **exists** and runs. It reports **3.11.9**.
- `.venv/Scripts/python.exe` starts normally, reports 3.11.9, and carries pytest 9.0.2.
- `.venv/pyvenv.cfg` records `version = 3.11.8`.

The base interpreter was patch-updated in place, 3.11.8 → 3.11.9, and the version recorded at creation time went stale. That mismatch is the most likely trip for whatever launcher reported the interpreter as missing — the interpreter is there; only the bookkeeping is wrong.

Running the canonical gate directly in that venv:

```
1442 passed in 106.51s
Required test coverage of 85.0% reached. Total coverage: 90.69%
```

**Zero failures.** All seven failures in your fallback run were artifacts of the 3.12 bundled interpreter, exactly as you suspected — the PyThermX rendering assertions, the strict performance gates, and the coverage C extension all behave normally here, and the Tk tests execute rather than skip. The arithmetic is consistent: 1,435 at the unbundle-size fix plus your 7 BOM tests equals 1,442. Coverage moved 90.67% → 90.69%.

**Recommended action:** correct `pyvenv.cfg` to `3.11.9` (or recreate the venv) so this does not cost someone else an afternoon, then treat the repository-wide gate as **complete** for this change.

---

## 3. New finding — ingress decoding fails *open* and silently loses data

**ID:** BFT-A-2026-08-26-01
**Severity:** High — silent corruption reported as success
**Class:** Same as the BOM defect (transport ingress decoding). Worse consequence: the BOM bug failed closed and loudly; this one fails open and silently.

### 3.1 What I found

All three bundle read paths decode with `errors="ignore"`:

- `src/core/parser.py:143` — `read_text(encoding=..., errors='ignore')`
- `src/core/parser.py:167` — the chunked progress-reporting reader
- `src/core/service.py:414` — `BundleToolService._read_text()`

Any byte that is not valid UTF-8 is therefore **deleted without a word**, and parsing continues over the damaged text.

### 3.2 Demonstration

I took George's bundle and re-encoded it as **cp1252** — precisely what a Windows editor does when someone saves a bundle as "ANSI", and an entirely plausible way for an artifact to reach us. The only non-ASCII character in the file is the em dash U+2014, which cp1252 writes as the single byte `0x97`.

Validation:

```
Status: VALID   Format: plain_marker   File count: 38
```

Extraction:

```
Processed: 38   Skipped: 0   Errors: 0
```

Diffed against the known-good extraction, **9 of the 38 files came out silently altered**:

```
built_build1.md, package.json, README.md, team_build1.md, TESTING.md,
bin/nodethermx.js, demos/showcase.js, demos/web/demo.js, src/index.js
```

```
GOOD: '  "description": "NodeThermX — structured progress and cooperative cancellation contract f'
BAD : '  "description": "NodeThermX  structured progress and cooperative cancellation contract fo'
```

`package.json` and `src/index.js` are shipped product files. The tool reported complete success while corrupting them.

### 3.3 Why this matters more than the byte count suggests

The damage is small and legible here because the payload was English source with one em dash. Substitute a bundle carrying UTF-8 identifiers, non-English content, or any file whose bytes matter, and the same code path produces a plausible-looking artifact that is quietly wrong — with `Errors: 0` on the console and `VALID` on the report.

This directly contradicts the posture the rest of BFT has earned. Build 116's integrity check refuses to proceed on a suspicion it cannot resolve. Build 103's grammar refuses ambiguity. The extraction reconciler raises on a short write rather than reporting success. Ingress is the one place where BFT currently guesses, and it guesses in the direction of data loss.

### 3.4 Recommendation

1. Decode with `errors="strict"` on all three read paths.
2. On `UnicodeDecodeError`, raise `BundleReadError` naming the **byte offset** and the offending byte, so the diagnostic points at the encoding rather than at some downstream symptom.
3. Add an explicit `--encoding` override on `validate`, `unbundle`, and the service surface, so an operator who *knows* the artifact is cp1252 or latin-1 can say so and get a correct extraction rather than a silent one.
4. Consider a `--lenient` escape hatch that restores today's behaviour but prints a per-occurrence warning and marks the report degraded. Not required for the fix; useful for salvage work.

Fail closed by default, with a documented way to say "I know what this is."

---

## 4. Secondary findings

### A. UTF-16 bundles are misdiagnosed

**ID:** BFT-A-2026-08-26-02 · Severity: Low (fails closed) · Cost: support time

A UTF-16LE bundle — what Windows PowerShell 5.1 produces from `>` and `Out-File` by default — is rejected with:

```
Profile detection failed: Could not auto-detect bundle format.
Attempted: plain_marker, md_fence
```

The file is a perfectly well-formed plain-marker bundle. It is not a profile problem, it is an encoding problem, and the message sends the reader to the wrong layer. This is the same *misdiagnosis* pattern as the BOM defect: the error named the boundary classifier when the fault was in the decoder.

**Recommendation:** sniff for UTF-16/UTF-32 signatures at ingress and fail with a message naming the detected encoding. Cheap to add alongside §3, and it closes the family rather than one member of it.

### B. Where George's BOM actually came from

Worth recording, because it shapes the fixture set. **BFT did not produce it.** The bundle writer publishes through `service.py:391` as plain `utf-8` with no signature, and George's generator (`scripts/build_source_bundle.js`) writes UTF-8 without a BOM — I regenerated his bundle from the extracted tree and it came out byte-identical to the original apart from the BOM and one missing trailing CRLF.

So the BOM was introduced **in transport**, between George's machine and our archive. Given the toolchain, PowerShell redirection is the most likely vector, and it is the same mechanism that would produce the UTF-16 case in item A. That means these are not exotic inputs. They are what our own shell does to a file in passing.

### C. Governance — Build 117 is owed

`VERSION.txt` and `pyproject.toml` both still read **2.1.116**, but two substantive corrections have landed since that build:

1. the unbundle size/scrollbar fix (2026-08-26), explicitly recorded as "no version bump, commit, installer, or release tag";
2. the BOM ingress fix (2026-08-26), same.

`git status` shows **182 modified or untracked paths**. Build 116's own record states that Gate A0 accepts `2.1.105`–`2.1.116`; there is now real, verified work sitting outside any governed build, and the installed-kit story for a fresh machine is stale by two fixes. With the canonical gate now passing at 1,442 (§2), the evidence for cutting **Build 117** exists — it only needs assembling.

**Recommendation:** cut 117 covering both fixes, ideally after §3 lands so the ingress family ships as one coherent story rather than three.

### D. Make the service reader structurally safe

`BundleToolService._read_text()` (`service.py:411`) is correct today only because its callers happen to pass through the guarded parser APIs. Point it at `BUNDLE_TEXT_ENCODING` so a future caller cannot reintroduce the defect by adding a read path that skips `parse()`.

---

## 5. Your open ask — the release verification matrix

Your release recommendation asked for George's bundle, or a distributable byte-equivalent, in the verification matrix. **Endorsed, and I would widen it.** Every defect in this document was invisible to synthetic fixtures and appeared the moment a real transported artifact arrived. The fixture set should encode the transport hazards, not just the grammar:

| Fixture | Guards against | Expected |
|---|---|---|
| BOM-free UTF-8 (baseline) | regression in the common path | VALID, exact round-trip |
| UTF-8 **with** BOM | the Build-116-era defect | VALID, exact round-trip, no BOM leak into payload 1 |
| BOM **inside** payload 1, outer BOM present | over-stripping | outer removed, inner preserved |
| **UTF-16LE with BOM** | §4.A | fails, message names the *encoding* |
| **cp1252 / ANSI** | §3 | fails closed — must **not** report VALID |
| Single trailing byte truncation | fail-open generally | fails closed |

The cp1252 row is the one that matters most: it is the only row in the table that BFT currently answers wrongly, and it answers wrongly in the direction that loses work.

On distributability — George's bundle is our own product under MIT, so I see no obstacle to committing it whole. If size is the concern, a 3-file minimal bundle carrying one em dash reproduces §3 exactly and costs a few hundred bytes. I am happy to build that fixture set as analyst work if you would rather keep your hands on the ingress code; say the word and it is yours either way.

---

## 6. Priority

| # | Item | Severity | Owner | Note |
|---|---|---|---|---|
| 1 | §3 — ingress fails open, silent data loss | **High** | Paul | Blocks Build 117 in my view |
| 2 | §4.C — cut Build 117 | Medium | Paul / Ringo | Two verified fixes outside governance |
| 3 | §5 — transport fixture matrix | Medium | John (offered) | Would have caught 1, 2, and the BOM defect |
| 4 | §4.A — UTF-16 misdiagnosis | Low | Paul | Bundle with item 1 |
| 5 | §2 — `pyvenv.cfg` 3.11.8 → 3.11.9 | Low | Anyone | One line; lifts your release caveat |
| 6 | §4.D — service reader uses shared constant | Low | Paul | Hardening, not a defect today |

---

## 7. Reproduction commands

All run from `C:\Users\mpw\Python\bundle_file_project\bundle_file_tool_v2`.

Confirm your fix on the real artifact:

```
.venv\Scripts\python.exe src\cli.py validate "C:\Users\mpw\Python\NodeThermX_project\archives\nodethermx_src_bundle_build1.txt"
```

Run the canonical gate that your fallback run could not complete:

```
.venv\Scripts\python.exe -m pytest -q --no-header
```

Reproduce the §3 fail-open defect — writes a cp1252 copy, then validates it:

```
.venv\Scripts\python.exe -c "import pathlib; p=pathlib.Path(r'C:/Users/mpw/Python/NodeThermX_project/archives/nodethermx_src_bundle_build1.txt'); pathlib.Path('tmp/bundle_cp1252.txt').write_bytes(p.read_text(encoding='utf-8-sig').encode('cp1252'))"
```

```
.venv\Scripts\python.exe src\cli.py validate tmp\bundle_cp1252.txt
```

The second command reports `VALID`, 38 files. Extracting it produces nine silently altered files.

---

## 8. Summary

Your fix is correct, verified against the real artifact, and complete for the case it targets. The repository-wide gate you could not finish does in fact pass — 1,442 tests, 90.69% coverage — so that caveat can come off the record.

What I would not close yet is the *family*. The BOM was one member of it. Immediately next door, the same ingress layer will accept a mis-encoded bundle, delete the bytes it cannot read, corrupt nine product files, and report `Errors: 0`. I would rather we fixed the decoder's posture once than met this again under a different encoding.

— John, Lead Analyst (BFT)
