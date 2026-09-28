# Bundle File Tool v2.1 Build 122 - Build Record

**Prepared:** 2026-08-30  
**Status:** Ratified scope implemented; governed delivery candidate qualified  
**Release identity:** `2.1.122`

## Outcome

Build 122 closes the public-release and cross-product defects found after Build
121. BFT now sends a versioned invocation context through PyProjectMgr to
ConfigEditor. That context carries the governed requester identity and the work
area of the display containing the BFT window. ConfigEditor validates the
contract, positions itself before it is shown, and reports:

`Requested by Bundle File Tool • governed by PyProjectMgr`

The delivery contains the coordinated PyProjectMgr and ConfigEditor source and
test changes as a separately hashed integration payload. The installer resolves
both project roots before mutation, backs up every integration target, places
the files resiliently, verifies their installed hashes, and runs the focused
cross-product tests before success.

## Native UI release repairs

- **Help > Documentation** opens the installed `USER_GUIDE.md` in an owned,
  read-only viewer.
- **Tools > Validate Bundle** performs real parser, structure, checksum, and
  nested-bundle validation through the shared service and PyThermX boundary.
- **Tools > View Logs** opens an owned, monitor-aware read-only log browser.
- **File > Un-bundle from Clipboard** loads clipboard bundle text through the
  normal un-bundle parsing path.
- `Ctrl+O` is bound to the advertised Open Bundle action.
- Native dialogs have explicit owners, saved window geometry is reconciled with
  the current display topology, and child windows remain with their caller.
- Public UI notices and metadata no longer expose internal phase promises,
  architecture-document dependencies, or individual development roles.
- Extracted-file headers no longer invent BFT project, team, or lifecycle
  metadata when a bundle does not provide it.

## Environment repair

The damaged legacy `.venv` was removed. The supported matrix was recreated from
clean bases under the explicit names `.venv311`, `.venv312`, and `.venv313`.
Each contains working `activate.bat` and `deactivate.bat` entry points, passes
`pip check` and byte-compilation, creates a real Tk root, reports BFT 2.1.122,
and imports governed PyThermX 0.5.2.

| Environment | Runtime / Tk | Strict full suite |
|---|---|---:|
| `.venv311` | CPython 3.11.9 / Tk 8.6.12 | 1,537 passed; 87.37% branch coverage |
| `.venv312` | CPython 3.12.10 / Tk 8.6.15 | 1,537 passed |
| `.venv313` | CPython 3.13.15 / Tk 8.6.15 | 1,537 passed |

All final runs promoted warnings to errors. The late Tk variable-finalization
warning observed during the first binding run was corrected by binding Tk
variables explicitly to their owning widgets; the strict reruns are clean.

## Cross-product and display evidence

PyProjectMgr's focused ConfigHub suite and ConfigEditor's focused client suite
pass. A real-Tk integration opens the governed BFT session on each physical
display reported by Windows and verifies both the resulting window center and
the visible requester/governor text. The test passed on `DISPLAY1`
(`0,0–1920,1080`) and `DISPLAY2` (`1920,0–3840,1080`).

## Packaging evidence

The corrected `pyproject.toml` builds a valid `bundle_file_tool-2.1.122`
universal wheel containing the CLI, native GUI, core, database, and UI packages.
Its console entry points are `bft`, `bundle-file-tool`, and `bft-gui`.

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `3a32fde8d2b55149691e265fa0b5ba0dd8b6d8e3ef919b5d9b1be61f55f3efd4` |
| `.pyprojectmgr/project_manifest.json` | `be4d3ff32b662be33e57acfcd81fc4924955767ea0e4642b0a89292b3833b56c` |
| `vendor/pythermx-0.5.2-py3-none-any.whl` | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |
| verified BFT 2.1.122 wheel | `1694864e5304fe4219c918a7916aa1bfe4946af922c97916ebdb57c913c1d8f6` |

The governed delivery ZIP is accompanied by a filename-bound SHA-256 sidecar.
`PREP_AND_STAGE_BFT` verifies that pair before taking a snapshot or staging the
installer.

## Release control

The implementation owner has prepared and qualified the candidate within the
ratified Build 122 scope. Repository commit, tag, and other Git metadata writes
remain reserved for the authorized interactive release owner.
