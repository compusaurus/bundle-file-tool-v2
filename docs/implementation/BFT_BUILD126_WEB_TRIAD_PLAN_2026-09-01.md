# Bundle File Tool Build 126 — Local Web Triad

**Prepared:** 2026-09-01  
**Status:** Implemented and Windows-verified; Mac acceptance pending  
**Predecessor:** Build 125 installed and Windows-verified

## Decision

Build 126 completes the CLI/Tk/web triad with a local browser workspace over
the Build 125 service contracts. It is not a remotely hosted file service.
BFT's purpose requires access to operator-selected local source, bundle, and
output paths; moving that authority to a public host would both break the
workflow and create a materially different security boundary.

The server binds only to `127.0.0.1`, chooses an available port by default, and
uses an unguessable per-run session token in both the route and every mutating
API request. It rejects unexpected Host, Origin, and Fetch-Site values, serves
no third-party resources, and adds a restrictive content-security policy.

## Fixed service boundary

The web adapter consumes these existing Build 125 contracts directly:

- `PlanResult.to_dict()` and `PlanEstimate.to_dict()` for selection planning;
- `OperationProgress.to_dict()` for polled job progress;
- `CheckResult.to_dict()` for checked, warning, and blocked states;
- `BundleResult.to_dict()` for artifact creation;
- `ValidationResult.to_dict()` for compatibility validation; and
- `ExtractResult.to_dict()` for extraction outcomes.

Selection precedence, nested-bundle detection, checksum verification, path
safety, portable collision handling, plan reconciliation, and extraction
authorization remain in `BundleToolService`. The web layer may validate its
request shape and require an explicit large-plan confirmation, but it may not
reimplement or weaken those rules.

## Primary workflow

The first viewport is an operational workspace with Bundle and Un-bundle modes.

Bundle mode provides:

1. local source path and selection-preset controls; a primary native folder
   picker and an explicit secondary single-file picker, with prior plans
   invalidated whenever the source changes;
2. metadata-only plan creation with counts, capacity, decisions, search, and
   included/excluded/blocked filters;
3. per-file or per-folder session overrides through `service.replan()`;
4. a direct selection integrity check with actionable findings; and
5. confirmed bundle creation followed by verification of the written output.

Un-bundle mode provides:

1. a local server-side path or browser file upload; local input, save, and
   extraction paths use native selectors because browser security deliberately
   withholds absolute filesystem paths;
2. direct check and validation actions;
3. entry metadata and actionable findings; and
4. extraction to an operator-specified local directory through the shared hard
   gate, with explicit overwrite behavior and dry-run support.

## HTTP and job model

Long operations run as cancellable jobs. The browser submits an operation,
polls a bounded event stream, renders the shared progress DTOs, and may request
cooperative cancellation. A job has one of `queued`, `running`, `succeeded`,
`failed`, or `cancelled`; adapter exceptions are returned as structured error
data without a traceback or private process details.

Planned selections and uploaded bundles are referenced by opaque identifiers.
They remain process-local, are size/count bounded, and are removed when the web
server stops. Upload bodies are streamed to server-owned temporary files rather
than duplicated in memory.

## Visual direction

The web workspace uses a compact document-tool aesthetic: warm paper surfaces,
ink text, a teal action color, amber warnings, red blockers, tabular path data,
and restrained motion. The desktop Selection Workspace remains the behavioral
reference, while the browser layout becomes responsive rather than copying Tk
geometry literally. All dynamic path and finding text is inserted as text, not
HTML.

## Acceptance boundary

Build 126 is complete when:

- the server is unreachable through non-loopback binding or an invalid session;
- plan/check/create/validate/extract results agree with direct service calls;
- no creation or extraction request bypasses a Build 125 hard gate;
- progress and cooperative cancellation are observable over the job API;
- uploads are streamed, bounded, isolated, and cleaned up;
- the working surface covers loading, empty, warning, blocked, failure,
  cancellation, and success states on desktop and narrow layouts;
- Windows and macOS launch paths open the per-run session URL;
- the full Python 3.11–3.13 and coverage gates remain clean; and
- official Mac launch and browser acceptance are recorded in the Mac lane.
