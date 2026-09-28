# BFT Dialog Memory Regression Fix — 2026-08-26

**Lead Developer:** Paul  
**For:** Ringo, George, and John  
**Status:** Implemented and full-suite verified  
**Release identity:** Current working tree; no version bump, commit, or release tag was made

## 1. Reported regression

The active Selection Workspace had lost three established Create Bundle conveniences:

1. Select Source did not reopen in the last source folder.
2. Create Bundle did not reopen in the last bundle-output folder.
3. Create Bundle did not suggest a filename.

## 2. Root cause and alignment review

The external `UserStateStore` and both keys required by the feature were intact:

- `last_source_dir`
- `last_bundle_save_dir`

`MainWindow` also still injected the same user-state store into both bundle modes. The classic `BundleFrame` continued to use the keys and suggest `<source-folder>_bundle.txt`.

The regression was isolated to `SelectionWorkspaceFrame`, which opened both Tk dialogs without `initialdir` and opened the save dialog without `initialfile`. This was an adapter integration omission, not a persistence or configuration failure.

The fix follows the existing architecture: mutable convenience state stays in the OS-level user-state file. The governed `bundle_config.json` remains read-only at runtime and is used only as an initial fallback when a user-state value is absent.

## 3. Implemented behavior

### Select Source

- Opens at the valid `last_source_dir` value.
- Falls back to `global_settings.input_dir` when no source history exists.
- Saves the selected source folder for the next source browse.
- Does not change history when the dialog is cancelled.

### Create Bundle

- Opens at the valid `last_bundle_save_dir` value.
- Falls back to `global_settings.output_dir` when no output history exists.
- Suggests `<source-folder>_bundle.txt` while still allowing the user to replace it.
- Saves the chosen destination folder for the next bundle write.
- Does not change history when the dialog is cancelled.

Source-browse history and bundle-output history remain independent.

## 4. Files changed

- `src/ui/selection_workspace.py`
  - restored remembered dialog initialization;
  - restored external user-state persistence;
  - restored the source-based suggested filename.
- `tests/integration/test_workspace_dialogs_tk.py`
  - records dialog arguments;
  - verifies source-folder restoration and persistence;
  - verifies output-folder restoration and persistence;
  - verifies the suggested filename;
  - verifies cancellation preserves remembered output state.

## 5. Verification

Focused regression tests before the implementation failed on all three missing dialog arguments. After the implementation:

- focused regression selection: **3 passed**;
- workspace-dialog, user-state, and config-anchoring selection: **69 passed**;
- complete repository suite: **1,424 passed** in **94.88 seconds**;
- total coverage: **90.70%**, above the required **85%**.

## 6. Conclusion and recommendation

All three reported features are restored in the active Selection Workspace, and no clarification is required for implementation. The behavior now matches the classic workflow and the ratified external-state design.

Recommendation: retain the new dialog-argument tests as release gates. A later refactor may consolidate the small dialog-state helpers shared by classic and workspace modes, but that is not required to release this correction.
