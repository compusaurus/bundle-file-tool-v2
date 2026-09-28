# BFT Unbundle Size and Scrollbar Fix — 2026-08-26

**Lead Developer:** Paul  
**For:** Ringo, George, and John  
**Status:** Implemented and full-suite verified  
**Release identity:** Current working tree; no version bump, commit, installer, or release tag was made

## 1. Reported defects

Two Unbundle-mode defects were reported:

1. every Bundle Contents row displayed `?` in the Size column;
2. scrollbars were visible but did not provide access to overflowing content.

Both reports were confirmed as functional defects.

## 2. Size root cause

`BundleCreator` recorded each source file's exact `file_size_bytes` in its `BundleEntry`. Both shipped transport profiles then omitted that field while formatting and did not restore it while parsing. Consequently, every reopened bundle entry normally had `file_size_bytes=None`.

The UI introduced a second defect by testing the value for truthiness. A legitimate zero-byte file was therefore also rendered as unknown.

## 3. Size correction

- Plain Marker and Markdown Fence bundles now emit optional `size=<bytes>` metadata when an exact source size is available.
- Both parsers restore non-negative size metadata into `BundleEntry.file_size_bytes`.
- The added field is backward-compatible: older parsers already ignore unknown metadata fields.
- Older bundles without size metadata still parse normally.
- For those legacy bundles, Unbundle mode infers the extractable payload size:
  - text is measured using its declared encoding;
  - binary base64 is decoded and measured as bytes.
- A recorded zero-byte file now displays `0`, not `?`.
- Invalid or undecodable legacy payloads remain `?` rather than displaying an invented value.

## 4. Scrollbar root cause

The file table had scrollbar commands, but its path column was fixed at 300 pixels. Tk Treeview computes its horizontal scroll range from column widths, not from clipped text. Long paths could therefore be invisible while the scrollbar correctly—but unhelpfully—reported that the fixed columns fit.

The Operation Log used `wrap="word"` and had no horizontal scrollbar. Long diagnostics wrapped rather than producing a horizontal range.

## 5. Scrollbar correction

- Bundle Contents retains dedicated vertical and horizontal scrollbar objects.
- The path column is measured from the loaded manifest and assigned a non-stretching content width, producing a real horizontal range for long paths.
- Bundle Contents vertical scrolling activates when file rows exceed the viewport.
- Operation Log now uses unwrapped text with dedicated vertical and horizontal scrollbars.
- Every scrollbar is laid out, has a live widget command, and activates under real overflow.

Scrollbars remain naturally inactive when all content genuinely fits in the viewport; that state no longer occurs while content is clipped or wrapped out of reach.

## 6. Files changed

- `src/core/profiles/plain_marker.py`
- `src/core/profiles/markdown_fence.py`
- `src/ui/unbundle_frame.py`
- `tests/unit/test_bundle_size_metadata.py`
- `tests/integration/test_unbundle_frame_tk.py`
- `tests/integration/test_cli_stdout_purity.py`

## 7. Verification

- Focused size/overflow acceptance: **8 passed**.
- Profile, round-trip, writer, Open Bundle, and Tk compatibility selection: **200 passed**.
- CLI stdout purity plus focused regressions: **15 passed**.
- Complete repository suite: **1,435 passed** in **92.51 seconds**.
- Total coverage: **90.67%**, above the required **85%**.

The Tk acceptance test uses a real 1000×600 window with 180 long file paths and 100 long log records. It verifies that the visible fraction on all four axes is below 1.0 and that every scrollbar is both laid out and connected.

## 8. Conclusion

Unbundle mode now reports useful byte sizes and makes overflowing Bundle Contents and Operation Log data reachable in both directions. No product clarification is required for these corrections.
