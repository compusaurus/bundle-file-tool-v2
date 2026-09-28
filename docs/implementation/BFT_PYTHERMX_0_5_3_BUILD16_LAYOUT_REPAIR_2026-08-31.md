# BFT / PyThermX 0.5.3 Build 16 Layout Repair

**Date:** 2026-08-31  
**Disposition:** Integrated for BFT Build 123

## Cause and correction

PyThermX 0.5.2 initialized its cached Cancel-control placement to `None`.
`None` is also the correct resolved placement when Cancel is hidden. The first
layout therefore appeared unchanged, the Tk canvas was never gridded, and its
owning dialog collapsed to a narrow window shell. BFT exposed the defect in
Open Bundle and Validate Bundle because both intentionally use
`allow_cancel=False`.

PyThermX 0.5.3 uses a one-shot unresolved sentinel so the first layout always
maps the canvas. A real-Tk upstream regression verifies the hidden-Cancel form,
and a BFT boundary regression verifies a mapped canvas with at least the
configured 520 by 56 requested geometry.

The 0.5.3 integration wheel was built from the sealed 0.5.2 Build 15 source
snapshot plus this isolated correction and version/release metadata. It does
not absorb unrelated work from the live PyThermX checkout. The same source and
regression correction was also applied to the live checkout so later PyThermX
work retains the fix.

## Identity

| Field | Value |
|---|---|
| Package | `pythermx` |
| Version | `0.5.3` |
| Integration build | `16` |
| Wheel | `pythermx-0.5.3-py3-none-any.whl` |
| Size | 54,044 bytes |
| SHA-256 | `fdf58d38c61a91f539aed37f846eb25b94f8aaa7d3cba401308c312e517f2690` |

## Qualification

- Direct real-Tk wheel probe: canvas manager `grid`, requested geometry
  `520x56`.
- PyThermX source candidate: Python 3.11 `608 passed, 23 skipped`; Python 3.12
  and 3.13 `607 passed, 24 skipped`. Skips are release-kit checks requiring a
  governed Git checkout and final distributions, not functional renderer
  checks.
- BFT focused progress, validation, dependency, and logging boundary:
  `151 passed` on each of Python 3.11, 3.12, and 3.13.
- BFT full supported-environment matrix: `1,538 passed` on every row; binding
  Python 3.11 branch coverage remains above the 85 percent release floor.

## Log hygiene included in Build 123

The governed BFT log directory contained 400 supported log files: 399
zero-byte session files and one populated diagnostic log. The 399 empty files
were removed and the populated log was retained. `StructuredLogger` now creates
its persistent session file on the first event rather than on construction,
and the log viewer ignores any legacy zero-byte files.

