# Bundle File Tool Build 127 — ThermX Integration

**Prepared:** 2026-09-03  
**Status:** Source-qualified; delivery prepared  
**Predecessor:** Build 126 installed and Windows-verified

## Decision

Build 127 standardizes BFT's three progress surfaces on the ThermX family
without coupling the renderer-independent service to a user interface. CLI and
Tk continue to consume `OperationProgress` through the governed PyThermX 0.5.3
Build 16 wheel. Web consumes the same DTO through the standalone NodeThermX
0.3.0 Build 3 DOM adapter.

No replacement PyThermX artifact was required: the latest governed 0.5.3 wheel
was already integrated, vendored, constrained by the `progress` extra, and
verified by the installer in Python 3.11–3.13. Its byte identity remains
`fdf58d38c61a91f539aed37f846eb25b94f8aaa7d3cba401308c312e517f2690`.

## Browser boundary

The BFT service continues to emit `bft.web-job.v1` job snapshots containing
BFT-owned progress events. Browser application code maps the current event and
job lifecycle to strict ThermX Schema 1.1 at the rendering boundary. That map
supplies determinate/indeterminate mode, coherent current/total/percent,
per-phase elapsed time, cancellation state, and terminal outcome. Selection,
integrity, extraction, job, and cancellation policy remain owned by BFT.

The NodeThermX adapter emits cancellation intent through its own control; BFT
performs the authenticated cancellation request and later renders the server's
authoritative requested or cancelled state. Terminal rendering retains the
last actual progress value rather than inventing 100 percent.

The first live integration run exposed one producer defect that the prior web
bar had hidden by forcing success to 100 percent: plan completion used the
included-path count as work completed and the all-decision count as its total.
Build 127 now closes plan and replan at all decisions processed, while keeping
the included-path result in the message. The DTO and renderer therefore agree
without a display-only correction.

## Distribution

The exact standalone NodeThermX browser assets are packaged under
`src/web/static/`, served only by BFT's allowlisted loopback route, and loaded
under the existing self-only content-security policy. They add no browser
framework, Node.js runtime, CDN, or network dependency. The upstream MIT notice
is retained in `vendor/NODETHERMX_LICENSE.txt` and in the asset banners.

| Asset | SHA-256 |
|---|---|
| `nodethermx-web.js` | `10f654b2dc936a8b99394629b1e1dbb122dbb7ab7038dedd8eab786ba434cb62` |
| `nodethermx-web.css` | `8d1b844c32c328b4a830fb668d17a515d270febded626e2a3ff237b1dcc933ff` |

## Ratified-work audit

The approved Build 125 checking/actionable-UI scope and Build 126 web-triad
scope are complete. No additional ratified product behavior remains suitable
for silent inclusion in this build. Build 127 therefore includes only the
ThermX integration and correction of stale implementation-index/baseline text;
draft VCS work and other proposed features remain out of scope.

Positive user-reported Safari testing applies to the NodeThermX adapter. It is
not treated as a complete BFT/macOS release qualification without the BFT
launcher, workflow, runtime, and version evidence required by that separate
lane.

## Qualification

- JavaScript syntax checks passed for both shipped browser scripts.
- Focused progress, web, release, and vendor regression passed 44 tests.
- The complete suite passed 1,628 tests on Python 3.13.15 at 85.91 percent
  branch coverage; the two warnings are known non-failing Tk finalizers.
- A live local-browser source plan rendered the canonical NodeThermX control and
  reached a truthful `3222/3222`, 100.0 percent, `completed` terminal state.
- Delivery preparation verified 260 BFT manifest entries, 7 cross-product
  integration entries, and 39 content markers without a mismatch.
