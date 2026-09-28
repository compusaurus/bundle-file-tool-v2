# Bundle File Tool Build 125 — Integrity Checking and Actionable UI

**Prepared:** 2026-09-01  
**Status:** Implemented, installed, and Windows-verified  
**Current release identity:** 2.1.125

## Roadmap decision

Build 125 owns the integrity-checking and application-behavior improvements
identified after the Build 124 self-bundle run. The web member of the
CLI/Tk/web triad moves to Build 126.

This order is intentional. A web adapter must consume the same checked,
blocked, and ready states as the CLI and Tk surfaces. Building the web surface
before that contract exists would either duplicate safety logic or require the
web workflow to be redesigned immediately afterward.

## Evidence

The Build 124 selection workspace correctly refused a bundle containing two
nested bundle artifacts, but it discovered them only after Create Bundle began
reading content and presented the expected policy decision as a generic
failure with no remediation actions.

The current selection plan is metadata-only, so it cannot classify a generic
file such as `demo.txt` as a complete embedded bundle. Existing-bundle
validation is available through Tools, but Open Bundle and extraction do not
share a persistent validation state. This leaves validation discoverable but
optional in the normal unbundle workflow.

## Build 125 scope

1. Introduce one renderer-independent check result with structured findings,
   severity, path, reason, remediation, subject kind, and serializable output.
2. Check a planned source selection without producing an artifact.
3. Check an existing bundle after one parse, including nested artifacts,
   checksums, stale headers, empty bundles, and path safety.
4. Make mandatory integrity gates live in the shared service so no adapter can
   bypass them.
5. Add direct **Check selection** and **Check bundle** actions.
6. Support per-user automatic-check preferences without mutating governed
   configuration.
7. Check bundles on load by default; an unchecked bundle is checked at the
   extraction boundary and a blocked manifest can never be extracted.
8. Automatically check a selection before creation by default, and invalidate
   the visible state whenever the plan changes.
9. Verify a written bundle on request/default and report “created and verified”
   only when that verification succeeds.
10. Replace generic modal-only failure handling with actionable findings that
    can select or session-exclude affected source paths.
11. Improve filter counts, empty states, search labeling, disabled zero-scope
    actions, inspector guidance, and status presentation.
12. Expose the shared result through a CLI `check` command for parity and for
    the future web adapter.

Confirmed hard blockers remain mandatory even if convenience automation is
disabled. Preferences control when checks start automatically; they do not
authorize unsafe extraction or publication.

## Build 126 scope

Build 126 adds the web interface over the established service contracts. It
must consume the Build 125 plan, progress, check result, creation, validation,
and extraction DTOs rather than reimplementing any selection or safety rule.

## Acceptance boundary

Build 125 is complete when CLI and Tk surfaces agree on check results, creation
cannot publish a blocked selection, loading reports a checked state, extraction
cannot bypass hard blockers, check preferences persist per user, and the
existing 85 percent coverage floor remains binding.

The Build 125 boundary is clean on the qualified Windows Python 3.11/Tk lane:
1,600 tests passed with 86.10 percent branch coverage, installation acceptance
passed, and 28 cross-product ConfigHub tests passed. Official Mac qualification
remains an independent release lane. The shared Build 125 contracts are now the
fixed integration boundary for the Build 126 web adapter.
