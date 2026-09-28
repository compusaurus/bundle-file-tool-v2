# BFT UTF-8 BOM Ingress Fix

**Date:** 2026-08-26  
**Status:** Implemented; canonical verification passed  
**Owner:** Paul, Lead Developer / Lead Analyst  
**Diagnosis source:** John's NodeThermX bundle verification notes

## Outcome

BFT now accepts a valid UTF-8 bundle whose byte stream begins with the UTF-8 BOM `EF BB BF`. The correction is made at the shared parser ingress boundary. Plain-marker and Markdown-fence profile grammars are unchanged, including the strict rule that rejects genuinely damaged bounded bundles.

## Root cause confirmed

The normal and progress-reporting file readers decoded with plain `utf-8`. That preserved the signature as `U+FEFF` at the beginning of the decoded text. Python's `\s` does not treat `U+FEFF` as whitespace, so the bounded plain-marker opening separator did not match. The boundary-token detector then correctly classified the token-bearing but apparently malformed opening block as damaged.

The failure was therefore decoding/ingress behavior, not a defect in the boundary classifier or separator grammar.

## Implementation

Changed `src/core/parser.py`:

1. Added one shared file-decoding constant: `BUNDLE_TEXT_ENCODING = "utf-8-sig"`.
2. Centralized ordinary and progress-reporting reads in one strict byte-decoding boundary.
3. Added `_without_transport_bom()` for public APIs receiving text already decoded by a caller with plain UTF-8.
4. Applied that guard to `parse()`, `detect_profile_name()`, and `validate_bundle()`.
5. Removed exactly one BOM only when it is the first code point of the external bundle text.
6. Preserved the former universal-newline behavior after strict decoding.

No profile regular expression or boundary-token rule was loosened.

## Preservation guarantees

- BOM-free UTF-8 uses the same behavior because `utf-8-sig` is equivalent to `utf-8` when no signature exists.
- A BOM within a bundled file's payload is preserved.
- A valid outer BOM is removed for both ordinary and progress-reporting file reads.
- Already-decoded string callers receive the same behavior as path-based callers.
- Both shipped profiles inherit the fix.
- CLI and service path inputs use the same shared decoder structurally.
- Genuinely malformed bounded headers still fail closed.

## Regression coverage

Added `tests/unit/test_bundle_bom_ingress.py` with seven cases:

1. bounded plain-marker file with an outer BOM, ordinary and progress reads;
2. Markdown-fence file with an outer BOM;
3. public string parse, detection, and validation with leading `U+FEFF`;
4. CLI validation surface with a BOM-bearing file;
5. shared service validation surface with a BOM-bearing file;
6. preservation of a BOM inside the first bundled payload while an outer BOM is removed;
7. unchanged BOM-free behavior.

## Verification

### Focused ingress and compatibility gate

```text
47 passed in 2.28s
```

Covered:

- new BOM ingress tests;
- strict transport-encoding tests;
- all bounded-transport tests;
- open-bundle progress/read-path tests;
- service-facade integration tests.

### Canonical repository gate

```text
1453 passed, 1 warning in 105.95s
Total coverage: 90.82% (required: 85.0%)
```

The gate ran in `.venv` with Python 3.11.9 and pytest 9.0.2. The sole warning is an existing Tkinter `Variable.__del__` warning after a workspace-dialog test; it is non-failing and unrelated to ingress.

The stale `.venv/pyvenv.cfg` version entry was reconciled from 3.11.8 to the running base interpreter's 3.11.9. George's original BOM-bearing NodeThermX artifact also validates directly as `plain_marker`, 38 files.

## Files changed

- `src/core/parser.py`
- `src/core/service.py`
- `src/cli.py`
- `tests/unit/test_bundle_bom_ingress.py`
- `tests/unit/test_bundle_transport_encoding.py`
- `docs/implementation/BFT_UTF8_BOM_INGRESS_FIX_2026-08-26.md`

## Release recommendation

Accept the correction and the adjacent fail-closed transport hardening. The canonical gate is complete. Build 117 is recommended as the next governed release, but versioning, installer/export work, commit, and tagging remain an owner/architect approval action rather than an implicit consequence of this implementation pass.
