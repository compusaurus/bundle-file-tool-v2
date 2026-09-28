# BFT Folder Row Toggle Fix — 2026-08-26

**Lead Developer:** Paul  
**For:** Ringo, George, and John  
**Status:** Implemented and full-suite verified  
**Release identity:** Current working tree; no version bump, commit, or release tag was made

## 1. Reported behavior

In the Selection Workspace's upper-left **Folders & groups** pane, clicking a folder row only expanded or collapsed it. The visible `[x]`, `[-]`, and `[ ]` state markers therefore looked like checkboxes but did not respond to the normal single-click interaction users expect.

## 2. Root cause

The folder Treeview bound `<<TreeviewSelect>>` directly to expansion-state mutation and refresh. A normal mouse selection therefore changed `_expanded`, while plan toggling was available only through Space or double-click.

The selection model itself was correct: `WorkspaceModel.toggle()` already creates one reversible folder-scoped override such as `exclude: src/**`. The defect was confined to the Tk event adapter.

## 3. Corrected interaction contract

- A single click on a folder row toggles its inclusion state.
- A checked folder becomes excluded and redraws as `[ ]`.
- An unchecked or partial folder becomes included and redraws as `[x]`.
- The native `+ / −` tree indicator only expands or collapses children; it does not modify the plan.
- Merely selecting a row no longer changes expansion state.
- Space continues to toggle the focused folder for keyboard accessibility.
- The selected row is restored after the plan redraws.
- Expansion state remains stable across plan redraws.

## 4. Files changed

- `src/ui/selection_workspace.py`
  - separated row selection, row toggling, and tree expansion handlers;
  - added native open/close state tracking;
  - retained the selected folder after refresh;
  - prevented double-click from becoming two toggles plus expansion.
- `tests/integration/test_selection_workspace_tk.py`
  - verifies single-click folder toggling;
  - verifies glyph redraw;
  - verifies the native expander does not change inclusion;
  - verifies row selection does not expand or collapse;
  - retains the existing Space-key acceptance checks.

## 5. Verification

- Focused mouse/keyboard interaction selection: **5 passed**.
- Workspace UI and model regression selection: **159 passed**.
- Complete repository suite: **1,427 passed** in **96.24 seconds**.
- Total coverage: **90.72%**, above the required **85%**.

## 6. Conclusion

The screenshots identified a real UI regression rather than a selection-model limitation. Folder rows now provide the expected direct deselection interaction while keeping hierarchy expansion as a separate, predictable control.
