# BFT Build 117 Active User-Acceptance Report

**Build tested:** Bundle File Tool `2.1.117` RC1  
**Tested by:** Paul, Lead Developer / Lead Analyst  
**Date:** 2026-08-26  
**Disposition:** **HOLD RC1 — corrective candidate required**  
**Final matrix:** 25 scenarios; **19 passed, 6 failed, 0 harness errors**

## 1. Executive result

Build 117 is materially better in the exact areas Ringo reported:

- a normal single click now deselects a folder without opening it;
- Create Bundle remembers its last output folder and supplies `UAT_Project_Álpha_bundle.txt` as the suggested name;
- remembered source-folder state survives frame recreation;
- Unbundle displays real sizes for all 98 entries, including `0` for an empty file;
- Unbundle file and log scrollbars activate horizontally and vertically under real overflow;
- UTF-8 BOM, explicit UTF-16, malformed transport, plan drift, cancellation, stdout purity, and governed-state preservation behaved correctly.

RC1 nevertheless should not be promoted unchanged. Active round-trip testing found a previously untested **silent CRLF-to-LF conversion**. The same defect reproduced through CLI and GUI extraction. Four additional UX/identity defects were confirmed: nested folders cannot be expanded in the top-left workspace tree, workspace horizontal scrollbars remain inactive, Open Bundle does not remember its folder, and Bundle mode identifies itself as v2.2.

## 2. Method

The pass used a disposable 98-file project containing:

- UTF-8 and Unicode names/content;
- LF and CRLF text;
- an empty file;
- binary data;
- a deeply nested long path;
- 90 top-level component folders to force vertical overflow;
- Python and Node environment structures that must be pruned;
- a recursive bundle-looking artifact that must be blocked.

The installed CLI and service were exercised end to end. Real Tk 8.6.12 widgets were created and driven using Tk button events, scrolling commands, frame recreation, mode changes, bundle creation, bundle opening, and extraction. File chooser and message-box answers were replaced with deterministic responses so the product methods could be exercised without unattended native shell dialogs.

All mutable user state was redirected to the disposable run. The installed governed config and manifest were hashed before and after.

Final evidence:

- Harness: `out/build117_user_acceptance_20260826/uat_build117.py`
- Raw result: `out/build117_user_acceptance_20260826/run_20260826_173635/uat_results.json`
- Disposable artifacts: `out/build117_user_acceptance_20260826/run_20260826_173635/`
- Duration of sealed matrix: 9.37 seconds
- Screen/Tk environment: 1920×1080, Tk 8.6.12, Python 3.11.9

## 3. Confirmed defects

### BFT-117-UAT-001 — P0: CRLF source files silently extract as LF

**Reproduced through:** CLI and Unbundle GUI  
**Affected scenarios:** `UAT-CLI-004`, `UAT-GUI-009`

Minimal observed evidence:

```text
source bytes:    b'one\r\ntwo\r\n'
bundle META:     eol=LF; size=10
extracted bytes: b'one\ntwo\n'
```

The bundle validates successfully and records the original byte size, but the payload extracts two bytes shorter. This is silent data transformation, not the already documented trailing-blank-line normalization.

**Root cause:** `src/core/writer.py` reads text using `Path.read_text()` at line 992. Python universal-newline handling converts CRLF to LF before `_detect_eol(content)` runs at line 994, so the writer records false `eol=LF` metadata. Extraction therefore has no correct EOL fact to restore.

**Required correction:** read/decode without newline translation, detect EOL before any canonical transport normalization, and add end-to-end CRLF/CR/MIXED tests that compare extracted bytes. The displayed original size must reconcile with the bytes actually restored.

**Release effect:** blocker. Do not use RC1 for authoritative round trips of CRLF-bearing source trees without independent byte comparison.

### BFT-117-UAT-002 — P1: top-left nested folders cannot be expanded

**Affected scenario:** `UAT-GUI-003`

The single-click selection fix passes. However, no top-level folder row contains a child Treeview item, so Tk renders no operable native expander for nested folders.

**Root cause:** `WorkspaceModel.tree()` emits children only for paths already present in `_expanded`. `SelectionWorkspaceFrame._on_folder_open()` adds a path to `_expanded` only after Tk raises `<<TreeviewOpen>>`. With no placeholder child, the row cannot open and the event that would populate it cannot occur. Double-click is also intentionally suppressed.

**Required correction:** insert a lazy placeholder child for expandable directories or render the immediate child directory skeleton; on open, update `_expanded`, repopulate the branch, and preserve selection state. Add a real Tk event test using a nested folder, not a mocked `identify_element` call.

### BFT-117-UAT-003 — P1: workspace horizontal scrollbars remain inactive

**Affected scenario:** `UAT-GUI-004`

All three workspace vertical bars activated and moved. Under deliberately long folder names, rule patterns, and decision paths, all three horizontal views remained:

```text
folders:   (0.0, 1.0)
rules:     (0.0, 1.0)
decisions: (0.0, 1.0)
```

The bars exist and are wired, but fixed Treeview column widths never create a horizontal scroll range; long content is clipped. By contrast, Unbundle dynamically sizes its path column and both horizontal bars activated correctly.

**Required correction:** size the relevant workspace columns to measured content, with a safe maximum, and test that `xview()` becomes smaller than `(0.0, 1.0)` and changes after a real horizontal scroll.

### BFT-117-UAT-004 — P1: Open Bundle does not remember its last folder

**Affected scenario:** `UAT-GUI-011`

After successfully opening a bundle from the disposable output folder, the user-state file was byte-identical. A recreated Unbundle frame opened the next chooser at the governed `global_settings.input_dir` value (`""` here), not the prior bundle folder.

**Root cause:** `UnbundleFrame.open_bundle()` lines 281–284 reads only `global_settings.input_dir`. It never reads or writes `user_state`. `UserStateStore` owns `last_source_dir` and `last_bundle_save_dir`, but has no `last_bundle_open_dir` key.

**Required correction:** add a dedicated `last_bundle_open_dir` per-user key and make Open Bundle use it with the governed input directory as fallback. Persist the selected file's parent without writing `bundle_config.json`. Test persistence across a recreated frame/process.

### BFT-117-UAT-005 — P2: Bundle workspace title reports v2.2

**Affected scenario:** `UAT-GUI-013`

Switching the installed `2.1.117` application to Bundle/Selection Workspace changes the title to:

```text
Bundle File Tool v2.2 - Selection Workspace
```

The status-bar package version remains correctly `v2.1.117`.

**Root cause:** `src/ui/main_window.py` line 460 hard-codes `v2.2`.

**Required correction:** derive every title/version label from `core.version.__version__` or a single deliberate display-version formatter.

## 4. Scenario matrix

| ID | User scenario | Result |
|---|---|---|
| `UAT-ID-001` | Installed identity and governed integrity | **PASS** |
| `UAT-CLI-001` | CLI reports the installed Build 117 identity | **PASS** |
| `UAT-CLI-002` | Plan a realistic project with pruned environments | **PASS** |
| `UAT-CLI-003` | Create the canonical bundle artifact | **PASS** |
| `UAT-CLI-004` | Validate and byte-compare a complete extraction | **FAIL — P0** |
| `UAT-CLI-005` | Piped stdout contains only a parseable bundle | **PASS** |
| `UAT-ING-001` | Open and validate a UTF-8 BOM bundle | **PASS** |
| `UAT-ING-002` | Fail closed on UTF-16 unless explicitly selected | **PASS** |
| `UAT-ING-003` | Reject malformed, NUL-bearing, and unknown transports | **PASS** |
| `UAT-SAFE-001` | Refuse source drift after review and publish nothing | **PASS** |
| `UAT-SAFE-002` | Cancellation is a controlled third outcome | **PASS** |
| `UAT-GUI-001` | Workspace source dialog remembers its last folder | **PASS** |
| `UAT-GUI-002` | Single-click a folder row to deselect without opening it | **PASS** |
| `UAT-GUI-003` | Native expander opens nested folders without changing selection | **FAIL — P1** |
| `UAT-GUI-004` | Workspace scrollbars activate and move under real overflow | **FAIL — P1** |
| `UAT-GUI-005` | Create Bundle remembers output folder and suggests a name | **PASS** |
| `UAT-GUI-006` | Remembered source folder survives frame recreation | **PASS** |
| `UAT-GUI-007` | Open Bundle displays real sizes including zero | **PASS** |
| `UAT-GUI-008` | Unbundle file/log scrollbars activate under real overflow | **PASS** |
| `UAT-GUI-009` | Extract through Unbundle and compare every file | **FAIL — same P0** |
| `UAT-GUI-010` | Malformed GUI open is explained and retains prior work | **PASS** |
| `UAT-GUI-011` | Open Bundle remembers its last file folder across sessions | **FAIL — P1** |
| `UAT-GUI-012` | Classic bundle surface remains behaviorally aligned | **PASS** |
| `UAT-GUI-013` | Main-window titles agree with installed identity | **FAIL — P2** |
| `UAT-GOV-001` | User workflows preserve governed application state | **PASS** |

## 5. Important passes

- CLI created a 98-entry artifact and the canonical plan excluded `.venv`, `node_modules`, and the recursive bundle-looking file.
- Stdout-only bundle output parsed back as 98 entries with no diagnostic contamination.
- UTF-8 BOM validated and parsed as 98 entries.
- Default UTF-16 ingress failed with an encoding-specific diagnostic; `--encoding utf-16` succeeded.
- Invalid UTF-8, NUL-bearing transport, and an unknown explicit encoding all failed with diagnostics.
- A file changed after planning raised `PlanDriftError` and no artifact was published.
- Cancellation left no bundle artifact; extraction reported four partial paths as designed.
- Single-click folder deselection produced `("exclude", "src/**")` without changing expansion state.
- Create Bundle opened at the remembered write folder, proposed `UAT_Project_Álpha_bundle.txt`, created the file, and persisted the chosen parent.
- All 98 Unbundle sizes were known; the empty file displayed `0`.
- Unbundle file/log horizontal and vertical ranges activated and moved under overflow.
- A malformed GUI open showed a Parse Error and retained the previously valid bundle.
- Classic mode created the same 98-file default selection as the canonical CLI surface.
- Governed config SHA-256 remained `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a` and manifest SHA-256 remained `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b`.

## 6. Acceptance recommendation

Do not promote or tag RC1 as the final Build 117 delivery while `BFT-117-UAT-001` is open. The ordinary test suite is green, but it does not currently exercise real CRLF discovery through the product's file-reading path.

Recommended sequence:

1. Correct the P0 EOL-fidelity path and add binding CLI/service/GUI round-trip tests.
2. Correct the three P1 workflow defects in the same candidate because each maps directly to Ringo's observed usability requirements.
3. Remove the hard-coded v2.2 title.
4. Rerun the 25-scenario matrix plus the complete regression and installer gates.
5. If Build 117 has not been committed/tagged, issue a Build 117 RC2. If its identity has already been formally released elsewhere, advance to Build 118 rather than replacing an immutable release.

Until corrected, the installed RC1 is suitable for continued exploratory testing, but authoritative CRLF-bearing source trees should be independently byte-compared after extraction.
