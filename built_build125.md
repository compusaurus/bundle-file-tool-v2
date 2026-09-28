# Bundle File Tool v2.1 Build 125 - Build Record

**Prepared:** 2026-09-01  
**Status:** Installed and verified on Windows  
**Release identity:** `2.1.125`

## Outcome

Build 125 converts bundle checking from a late, generic failure into a shared
workflow state. The service now returns `bft.check-result.v1`, an adapter-neutral
result containing stable finding codes, severity, affected path, explanation,
remediation, blocking state, counts, profile, and plan generation.

The default Selection Workspace can check a plan without publishing an
artifact, marks the result stale when the plan changes, checks before creation,
and verifies a saved bundle afterward. Un-bundle mode checks on open or paste,
shows a direct Check Bundle action, and refuses extraction when the shared hard
gate finds unsafe nesting, paths, checksums, or portable collisions.

The CLI adds `check` text/JSON output and optional `bundle --precheck`. The
legacy `validate` command remains for compatibility. Check progress exposes
integrity and verification as separate phases, so checksum/path work never
runs silently behind a completed integrity indicator.

## Interface roadmap

The web member of the CLI/Tk/web triad moves to Build 126. It must consume the
Build 125 plan, progress, check, creation, and extraction contracts; it may not
reimplement selection precedence or safety policy.

## Identity

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `60d01c14d76acb5dd75b95403b98783d3d3a7a7bcbc69d7b8a648304ff91ab74` |
| `.pyprojectmgr/project_manifest.json` | `6b8aed86aeeffca7d71cd53be4aa72b810cc3b7f3ca3890445b032c28f5c58f4` |

## Verification status

- Qualified Windows Python 3.11/Tk regression: 1,600 passed in 107.05 seconds.
- Branch coverage: 86.10 percent, satisfying the binding 85 percent floor.
- Machine-readable test result: `tmp/build125_py311_results.xml` in the
  development workspace (not shipped in the delivery payload).
- Focused progress and cancellation contract: 47 passed, 7 display-dependent
  skipped in the recovered non-display runtime.
- Two non-failing pytest warnings report Tk variable finalizers after their
  owning roots were destroyed; no test, coverage, or packaging gate failed.
- Official Mac qualification remains an independent release lane.

## Installation acceptance

- Standard staging created and archived `BFTv2_v2.1 Build 125`, then retired
  the older Build 123 snapshot folder as authorized.
- Installed SHA-256 verification passed for 236 BFT files and 7 cross-product
  integration files; all 27 content markers passed.
- Installer acceptance passed 1,600 tests in 113.26 seconds at 86.10 percent
  branch coverage.
- PyProjectMgr/ConfigHub acceptance passed 17 tests; ConfigEditor invocation
  and placement acceptance passed 11 tests.
- PyThermX 0.5.3 was verified in Python 3.11, 3.12, and 3.13 environments;
  governed-config integrity and read-only protection passed.
- The normal no-console desktop launcher was installed successfully.
- Post-install desktop launch exposed that `cmd.exe` stripped the embedded
  quote characters around the VBS path when the shortcut was created. The
  installer now builds those quotes with `[char]34`; the live shortcut was
  recreated, its stored arguments were verified, and launching that exact
  `.lnk` opened `Bundle File Tool v2.1.125 - Selection Workspace`.
- Sixteen focused desktop-launcher and release-contract tests pass, including
  a regression test that requires quote-safe shortcut generation.
- The first marker gate reported a false negative because one `findstr /c:`
  marker contained embedded quotes. All payload hashes had passed. Recovery
  was retained, the non-hashed marker was changed to the quote-free schema
  token, and the complete installer then passed every gate.

Repository commit and tag actions remain reserved for the authorized
interactive release owner.
