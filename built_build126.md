# Bundle File Tool v2.1 Build 126 - Build Record

**Prepared:** 2026-09-01  
**Status:** Installed and verified on Windows; Mac acceptance pending  
**Release identity:** `2.1.126`

## Outcome

Build 126 completes the CLI/Tk/web triad. The browser workspace is a local
application surface over the same `BundleToolService` contracts used by CLI and
Tk; it does not reimplement selection precedence, checking, creation,
validation, or extraction policy.

The dependency-free server binds only to `127.0.0.1`, uses an unguessable
per-run route and mutation token, validates Host/Origin/Fetch-Site, serves no
third-party resources, and applies a restrictive content-security policy.
Plans, jobs, and uploads are bounded process-local state. Uploaded bundles are
streamed into server-owned temporary files and removed when the session ends.

## Interface

- Bundle mode plans metadata without opening source content, shows capacity,
  filters decisions, explains rule chains, applies session overrides, checks a
  selection, creates the exact reviewed plan, and verifies the written output.
- Un-bundle mode accepts a local path or bounded upload, checks and validates,
  reviews entries and findings, and extracts only the exact checked bundle.
- All long operations expose shared progress phases and cooperative cancel.
- A direct native **Choose folder** control is the primary Bundle source action,
  with an explicit secondary single-file picker. Changing the source invalidates
  the prior plan. Other native Browse controls select bundle input/output and
  extraction directories. A short-lived chooser process keeps Tk on its main
  thread on both Windows and macOS.
- Tk, Windows, macOS, and the `bft-web` console entry point launch the private
  browser session.

## Security and parity evidence

- Focused web, launcher, packaging, UI, and governed-release contract: 38
  tests passed before whole-suite qualification.
- Expanded chooser, upload, entry-point, and HTTP fail-closed tests cover raw
  uploads, invalid sessions, origins, hosts, routes, JSON, and job actions.
- Complete Python 3.11 qualification: 1,627 tests passed in 103.63 seconds at
  85.90 percent branch coverage, satisfying the binding 85 percent floor.
- Two non-failing warnings are the previously recorded Tk variable finalizers
  after their owning roots have been destroyed; no test or coverage gate
  failed.
- Installation acceptance counts will be recorded when the release candidate
  is staged and installed.
- Official macOS qualification remains an independent release lane.

## Installation acceptance

- The standard stager verified the delivery pair, created and archived
  `BFTv2_v2.1 Build 126`, and retired the older Build 125 snapshot folder under
  its one-snapshot retention policy. The Build 125 snapshot ZIP and delivery
  pair remain recoverable in `archives`.
- Installed SHA-256 verification passed for 255 BFT files and 7 cross-product
  integration files; all 35 content markers passed.
- Installer acceptance passed 1,627 tests in 105.18 seconds at 85.90 percent
  branch coverage. The single non-failing warning was the known Tk variable
  finalizer after its owning root had been destroyed.
- PyProjectMgr/ConfigHub acceptance passed 17 tests; ConfigEditor invocation
  and placement acceptance passed 11 tests.
- PyThermX 0.5.3 was installed and identity-checked in the Python 3.11, 3.12,
  and 3.13 environments. Governed-config integrity and read-only protection
  passed.
- Native and web no-console desktop shortcuts were installed. The automated
  elevated installer resolved Windows' Desktop special folder outside the
  interactive user's desktop, so both live shortcuts were recreated explicitly
  in `C:\Users\mpw\Desktop`; their `wscript.exe` targets, quoted VBS arguments,
  and working directories were independently verified.
- The staged payload and temporary rollback folder were removed after every
  gate passed. The archived delivery SHA-256 is
  `9ab0a996171129676e398a68c9e43bdc32a664dfdf0bc54e8cc4f9844a5ce5d8`.

## Identity

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `01f3e740df36017c90e77da40d27237d9df12bee09899a752ea48c31d9455030` |
| `.pyprojectmgr/project_manifest.json` | `a9cc7e7f6dd5a776111eaf1bb9fa62f08a9d732eda4d82a02258e495988a4c08` |

Repository commit and tag actions remain reserved for the authorized
interactive release owner.
