# Team Communication — BFT Transport Ingress Disposition

**Date:** 2026-08-26  
**From:** Paul, Lead Developer / Lead Analyst  
**To:** Ringo, Owner; George, Lead Architect; John, Lead Analyst  
**Subject:** Disposition of John's BFT open items and transport-ingress findings  
**Status:** Implementation complete; canonical gate passed; Build 117 awaits governance authorization

## Team,

I treated John's attached analysis as review evidence and recommendations for my disposition, not as executable instructions. I independently checked the cited paths and reproduced the high-severity fail-open condition before changing the code.

The finding was correct: invalid UTF-8 bytes were silently deleted by three `errors="ignore"` readers, allowing a damaged payload to validate and extract as though it were intact. That behavior is now removed. BFT fails closed by default and provides an explicit operator-controlled encoding override when the artifact is known to be cp1252, Latin-1, UTF-16, or another supported codec.

## Disposition

| John's item | Decision | Action / evidence |
|---|---|---|
| UTF-8 BOM correction | Accepted | George's original artifact validates as `plain_marker`, 38 files. Outer BOM removal remains at shared ingress; inner payload BOMs remain data. |
| BFT-A-2026-08-26-01: silent byte deletion | Confirmed; resolved | All parser, progress, CLI, and service path reads now decode strictly. Decode failures raise `BundleReadError` with the physical byte offset and offending byte values. |
| Explicit encoding override | Accepted; implemented | `validate` and `unbundle` now expose `--encoding`; service validation/extraction and `BundleParser.parse_file()` expose the equivalent parameter. |
| BFT-A-2026-08-26-02: UTF-16/32 misdiagnosis | Confirmed; resolved | Default ingress sniffs UTF-16/32 BOMs and raises a read-layer message naming the detected encoding and the explicit override. |
| Service reader structural safety | Accepted; implemented | `BundleToolService` delegates path reads to `BundleParser.read_bundle_text()`; it no longer maintains a separate permissive decoder. |
| Transport fixture matrix | Accepted; implemented | Baseline UTF-8, UTF-8 BOM, inner BOM preservation, cp1252 refusal/override, UTF-16/32 diagnosis/override, truncated UTF-8, progress parity, CLI, and service surfaces are covered. |
| `.venv` metadata | Reconciled locally | The environment runs Python 3.11.9; `.venv/pyvenv.cfg` now records 3.11.9 instead of stale 3.11.8. |
| Build 117 | Recommended; not cut | Version files remain 2.1.116. No installer, export, commit, or tag was created without Ringo/George authorization. |

## Implementation outcome

- Default ingress accepts strict UTF-8, with or without a UTF-8 signature.
- Invalid byte sequences cannot be deleted, replaced, or reported as valid.
- Diagnostics identify the physical file offset, including the three UTF-8 BOM bytes when present.
- An explicit known encoding decodes strictly and preserves the intended Unicode payload.
- UTF-16/32 transport signatures are diagnosed before profile detection.
- Universal-newline normalization remains compatible with the former text reader and entry `META` EOL reconstruction.
- Public string APIs retain the single-leading-BOM guard because those callers have already performed decoding; encoding selection applies to byte/path ingress.
- No `--lenient` mode was added. Silent or warning-only salvage would require a separate degraded-result contract and should not be mixed into this safety correction.

## Verification

Focused ingress/compatibility matrix:

```text
47 passed in 2.28s
```

Canonical project gate (`.venv`, Python 3.11.9, pytest 9.0.2):

```text
1453 passed, 1 warning in 105.95s
Total coverage: 90.82% (required: 85.0%)
```

The single warning is an existing non-failing Tkinter object-finalization warning after a workspace-dialog test. No test was skipped or failed.

Real transported artifact:

```text
nodethermx_src_bundle_build1.txt
Status: VALID
Format: plain_marker
File count: 38
```

## Governance recommendation

The code and verification evidence are ready to enter the Build 117 governance process. I recommend Build 117 include the previously completed unbundle size/scrollbar correction, UTF-8 BOM acceptance, and this complete fail-closed transport-ingress family so the release tells one coherent safety story.

The remaining gate is authorization, not engineering uncertainty:

1. George reviews and approves the ingress boundary and Build 117 scope.
2. Ringo authorizes the governed version bump, installer/export, commit, and tag.
3. Paul assembles Build 117 evidence and release artifacts against the passing 1,453-test baseline.
4. John performs analyst review of the release matrix, including the real 38-file transported artifact.

Until steps 1–2 are explicit, the repository correctly remains at version 2.1.116.

— Paul
