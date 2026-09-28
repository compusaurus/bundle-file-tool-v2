# Bundle File Tool v2.1 Build 124 — PC Development Handoff

**Prepared:** 2026-09-01  
**Prepared by:** Paul, Lead Analyst and Collaborative Developer  
**Owner:** Ringo  
**Project:** Bundle File Tool v2  
**Current production baseline:** v2.1 Build 123  
**Proposed development target:** v2.1 Build 124  
**Purpose:** Transfer the Mac feasibility work, test evidence, architectural conclusions, and launch-experience decisions to the authoritative PC development environment.

---

## 1. Executive handoff

Build 123 was transferred to a Mac as `bundle_file_tool_v2.zip`. The archive contained the important development directories but did not contain the complete governed project root. The application was successfully configured and launched on an Intel Mac using Python 3.13.15, Tk 9.0, and PyThermX 0.5.3. Ringo confirmed that the live Tkinter GUI works very well on the Mac.

The Mac qualification establishes that BFT is technically viable as a cross-platform application. It also identified a small, bounded set of test-portability, delivery-completeness, and launch-experience work suitable for a formal Build 124.

**Recommendation:** Perform Build 124 development and official delivery on the PC from the complete governed Build 123 project. Retain the Mac as the independent compatibility and acceptance-test lane. Do not convert the locally reconstructed Mac tree into the authoritative release baseline.

---

## 2. Decisions reached during the Mac session

### D1 — Build ownership

The PC remains the authoritative environment for:

- version advancement;
- governed source and manifest changes;
- complete Windows regression testing;
- installer and staging execution;
- official Build 124 packaging;
- checksum and delivery evidence.

The Mac is the independent environment for:

- macOS installation testing;
- Python/Tk compatibility testing;
- automated non-GUI regression testing;
- live Tkinter GUI acceptance;
- launcher and window-state validation.

### D2 — Formal build required

The macOS work should be delivered as **Bundle File Tool v2.1 Build 124**, not as silent edits to Build 123.

Build 123 remains the Windows-qualified baseline. Build 124 is proposed as the first formally supported cross-platform release.

### D3 — Normal launches should not display a command window

The large Terminal window observed on the Mac is caused by the temporary `.command` launcher, not by BFT itself.

The preferred Build 124 behavior is:

- normal GUI launch: no command or Terminal window;
- diagnostic launch: separate, clearly named launcher with visible console output;
- startup failures: written to a session log and surfaced with a useful error;
- the temporary `.command` mechanism remains developer/diagnostic scope only.

### D4 — BFT opening-state options

Build 124 should consider these user-selectable startup states:

1. **Restore Last** — recommended default; falls back to Normal on first launch.
2. **Normal** — remembered standard geometry.
3. **Maximized** — fills the monitor work area without entering macOS fullscreen.
4. **Minimized** — starts in the Dock/taskbar; supported but not recommended as the default.

The application should remember the last non-minimized state. Closing BFT while minimized should not silently force future minimized launches unless the user explicitly selected Start Minimized.

### D5 — Configuration ownership

Launcher/console behavior belongs to setup and shortcut creation because it occurs before BFT starts.

Window geometry, monitor, and startup state are per-user convenience state. They belong in `UserStateStore`, not in the governed read-only `bundle_config.json`.

---

## 3. Mac setup performed

The following environment was established successfully:

| Component | Mac qualification value |
| --- | --- |
| Hardware/runtime architecture | Intel macOS (`x86_64`) |
| BFT source identity | v2.1.123 |
| Python | CPython 3.13.15 |
| Tcl/Tk | 9.0 |
| PyThermX | 0.5.3 from the governed vendored wheel |
| Test runner | pytest 9.1.1 |

Python and Tk were installed through the existing Homebrew installation using:

```text
python@3.13
python-tk@3.13
```

An isolated `.venv313` was created inside the extracted Mac test tree. PyThermX was installed from:

```text
vendor/pythermx-0.5.3-py3-none-any.whl
```

The temporary Mac launcher sets `BFT_PORTABLE=1` so test user state stays inside the test tree instead of modifying the governed application root or relying on an unqualified home-directory setup.

---

## 4. Important archive limitation

The transferred ZIP contained these top-level directories:

```text
docs/
htmlcov/
scripts/
sessions/
src/
tests/
vendor/
```

It did **not** contain the complete governed project root. Important absent items included at least:

- `pyproject.toml`;
- the authoritative root `VERSION.txt`;
- the governed root `bundle_config.json`;
- `.pyprojectmgr/project_manifest.json` and related governance files;
- root `README.md` and `USER_GUIDE.md`;
- Windows installer and staging files;
- the complete test-matrix requirements files.

The Mac test tree locally reconstructed `VERSION.txt` and `bundle_config.json` only so the application could identify itself as Build 123 and run without a misleading missing-config warning. No production logic was modified.

Because the project root was incomplete, the PC’s complete Build 123 tree must be the source for Build 124.

---

## 5. Test evidence

### 5.1 Live GUI result

Ringo launched the Tkinter application on the Mac and reported:

> Bundle file tool works very well on the Mac.

This confirms the essential real-display runtime check that could not be automated from the restricted background test shell.

### 5.2 End-to-end CLI smoke test

A two-file source tree was exercised through:

1. bundle creation;
2. bundle validation;
3. extraction;
4. byte-for-byte comparison.

Result:

```text
Bundle creation: PASS
Validation: PASS
Extraction: PASS
Byte-for-byte comparison: PASS
```

The comparison used `--no-headers` during extraction so the round-trip test measured original payload fidelity rather than optional header injection.

### 5.3 Focused core qualification

Focused parser, profile, writer, round-trip, and service tests produced:

```text
156 passed
2 deselected Mac path-alias assertions
```

### 5.4 Broad non-GUI Mac qualification

The broader Mac pass covered core profiles, CLI behavior, service integration, validation and safety, discovery, selection, configuration, encoding/BOM handling, self-hosting, progress contracts, PyThermX integration, and public UI seams that do not create a real Tk root.

Result:

```text
1,331 passed
17 failed
Runtime: 21.41 seconds
```

The 17 failures were classified as follows:

| Count | Classification | Meaning |
| ---: | --- | --- |
| 10 | Incomplete transferred project root | Tests require absent `pyproject.toml`, governance manifest/digest, README, User Guide, or equivalent release files. Not a Mac product defect. |
| 6 | macOS temporary-path alias | Tests compare unresolved `/var/...` paths with resolved `/private/var/...` paths. The safety and bundle operations themselves succeeded. |
| 1 | Captured progress-rendering assumption | A test expects carriage-return redraw behavior that is not emitted in the captured macOS subprocess stream. This is a platform-neutrality issue in the assertion/rendering contract, not a bundle failure. |

No functional bundle creation, validation, parsing, extraction, encoding, or safety failure was found.

### 5.5 Tk automation boundary

The restricted task shell aborts when it attempts to create a macOS Tk root, even though the same Python/Tk environment launches correctly for the logged-in user. Therefore, real-Tk automated files were excluded from the background run. Build 124 acceptance on the Mac should run those tests from the user’s normal Terminal or qualified local test runner, followed by manual GUI smoke testing.

---

## 6. Proposed Build 124 scope

### WP1 — Portable path assertions and contracts

- Normalize both expected and actual paths before containment/equality assertions.
- Account explicitly for the macOS `/var` to `/private/var` alias.
- Preserve the existing security property: validation must compare canonical paths when enforcing output-root containment.
- Do not weaken traversal or symlink protections merely to satisfy a test.

Candidate affected areas observed on Mac:

- writer default base-path assertions;
- single-file discovery assertions;
- safe relative-path validator assertions;
- multiple-path validation assertions;
- combined filter/validation security assertions.

### WP2 — Platform-neutral progress tests

- Keep stdout artifact purity mandatory.
- Keep progress output on stderr.
- Verify meaningful progress, percentage, phase, and completion signals.
- Require carriage-return redraw only when the selected renderer and stream capability promise it.
- Permit line-oriented captured output on platforms or subprocess streams where in-place redraw is not appropriate.

### WP3 — Complete cross-platform delivery payload

- Ensure Build 124 packages every governed root file.
- Update `pyproject.toml` operating-system classifiers and supported-environment documentation.
- Retain the governed PyThermX wheel.
- Add reproducible Mac environment/setup instructions.
- Define Mac install, uninstall, upgrade, log, and user-state locations.
- Preserve Windows installer and staging governance.

### WP4 — No-console GUI launch

Mac recommendation:

- deliver a proper `Bundle File Tool.app` wrapper or packaged application;
- start the qualified Python/Tk runtime without opening Terminal;
- redirect early stdout/stderr to a per-session log;
- surface startup failure without requiring a console;
- retain a separate diagnostic launcher.

Windows recommendation:

- normal GUI shortcut should use `pythonw.exe`, `.pyw`, or the equivalent packaged windowed executable;
- provide a separate diagnostic-console shortcut using `python.exe`;
- keep CLI entry points unchanged.

Avoid using AppleScript to minimize whichever Terminal window happens to be frontmost. That approach can target the wrong window and may require Automation permission. Eliminating the console is safer than hiding it after it flashes.

### WP5 — Configurable BFT startup state

Recommended per-user keys or equivalent typed state:

```text
startup_window_state = restore | normal | maximized | minimized
remember_window_geometry = true | false
window_geometry = <platform geometry>
window_monitor = <stable monitor identity or best available hint>
last_non_minimized_state = normal | maximized
```

Recommended behavior:

- first launch: Normal, centered/reconciled on the active or primary monitor;
- Restore Last: restore geometry and last non-minimized state;
- Maximized on macOS: use the monitor work area, not fullscreen;
- Minimized: apply after the window is mapped so Tk behaves consistently;
- missing/disconnected monitor: reconcile to an available work area;
- malformed geometry: fall back safely to the standard default.

The existing `ui/window_placement.py` and `UserStateStore` should be extended rather than creating a second window-state subsystem.

### WP6 — Setup choices

Recommended setup-facing choices:

```text
Launch experience:
  [x] Standard application launch with no console (recommended)
  [ ] Install diagnostic console launcher

Initial BFT window state:
  [x] Restore Last / Normal on first launch (recommended)
  [ ] Normal
  [ ] Maximized
  [ ] Minimized
```

Setup should seed per-user preferences without rewriting the governed configuration.

---

## 7. Recommended PC development sequence

1. Start from the complete, governed Build 123 PC project root.
2. Create the formal Build 124 branch/work area using the team’s existing procedure.
3. Record the unchanged Build 123 Windows baseline and full test result.
4. Add the Mac findings as traceable Build 124 requirements and tests.
5. Implement WP1 and WP2 without weakening path safety or stdout-purity contracts.
6. Implement the no-console and diagnostic launch paths.
7. Extend `UserStateStore` and the existing window-placement layer for startup states.
8. Update setup, documentation, environment matrix, classifiers, and governed records.
9. Run the complete Windows Python 3.11–3.13 matrix and real-Tk tests.
10. Produce the official Build 124 delivery package on the PC.
11. Transfer that exact package and checksum to the Mac.
12. Recreate the Mac environment from documented instructions.
13. Run the complete eligible Mac suite from the user’s normal Terminal.
14. Perform live GUI acceptance for launch visibility, startup states, monitor reconciliation, bundling, validation, and extraction.
15. Archive Windows and Mac evidence before Build 124 approval.

---

## 8. Build 124 acceptance criteria

Build 124 should not be called cross-platform complete until all of the following are true:

- the full governed delivery payload is present and internally version-consistent;
- Windows Python 3.11, 3.12, and 3.13 regression rows pass;
- Mac Python 3.13 qualification passes, with any additional supported Mac rows explicitly declared;
- both Plain Marker and Markdown Fence round trips pass on Windows and Mac;
- binary, BOM, CRLF/LF, and Windows-1252 fixtures remain faithful;
- traversal, symlink, overwrite, and nested-bundle protections remain fail-closed;
- GUI normal launch shows no command window;
- the diagnostic launcher shows useful console output;
- Normal, Maximized, Minimized, and Restore Last behave as specified;
- disconnected-monitor and invalid-geometry recovery work;
- startup failures produce a discoverable log;
- the official PC-produced package installs and runs unchanged on the Mac;
- the Mac qualification does not modify the governed application configuration.

---

## 9. Risks and cautions

1. **Do not promote the reconstructed Mac tree.** It lacks authoritative root and governance files.
2. **Do not “fix” path tests by removing canonicalization.** Canonical paths are part of safe containment enforcement.
3. **Do not make Minimized the default.** A successful but invisible launch looks like a failure.
4. **Do not treat maximized and fullscreen as synonyms on macOS.** Fullscreen creates a separate Space and materially changes behavior.
5. **Do not hide all startup diagnostics.** No-console launch requires reliable session logging and an explicit diagnostic path.
6. **Do not overwrite governed config to remember window state.** Use per-user state.
7. **Do not claim complete Mac support from the current partial ZIP.** Re-test the official Build 124 package.

---

## 10. Ready-to-paste PC continuation prompt

Copy the following into the PC development conversation and attach or add this handoff file to the Bundle File Tool project:

```text
Paul, continue as lead analyst and collaborative developer for Bundle File Tool v2.1. We are back on the authoritative PC environment with the complete governed Build 123 project. Read BFT_BUILD124_PC_DEVELOPMENT_HANDOFF_2026-09-01.md completely and use it as the context from our Mac feasibility and brainstorming session.

The current baseline must remain Build 123 until the formal version/build procedure opens Build 124. The proposed objective is to prepare Build 124 as the first formally supported cross-platform release, including macOS path-test portability, platform-neutral progress tests, a complete governed delivery payload, no-console normal GUI launch, a separate diagnostic launcher, and configurable BFT startup window states using per-user state.

First inspect the complete PC project and verify its Build 123 status, git/worktree state, governed root files, environment matrix, current launchers, setup scripts, window-placement implementation, UserStateStore, and full baseline test result. Then compare the actual project against the handoff, identify any conflicts or missing evidence, and propose a bounded Build 124 implementation and validation plan before changing production files. Preserve Windows behavior and all safety guarantees.
```

---

## 11. Transfer recommendation

Preferred transfer method:

1. Keep this Markdown file in the Bundle File Tool project’s files/reference area.
2. Open the same project from the PC.
3. Reference or attach this file to the PC development conversation.
4. Paste the continuation prompt from Section 10.

Google Drive is reasonable as a redundant backup or cross-device transport location, but it should not become the authoritative development record. The versioned project copy should remain primary so the handoff evolves with Build 124 and can be included in release evidence if appropriate.

---

## 12. Final disposition

The Mac session achieved its purpose:

- BFT Build 123 runs successfully on macOS;
- live GUI viability is confirmed;
- core and broad automated qualification are strongly positive;
- remaining compatibility work is understood and bounded;
- release ownership and cross-platform validation roles are clear;
- launch-window and BFT-window-state requirements are ready for formal Build 124 planning.

Proceed on the PC from the complete Build 123 baseline. Return the official PC-produced Build 124 candidate to the Mac for independent qualification before release approval.
