# Bundle File Tool v2.1 Build 121 - Build Record

**Prepared:** 2026-08-30  
**Status:** Governed corrective delivery; technical gates passed  
**Release identity:** `2.1.121`

## Outcome

Build 121 is the repaired baseline candidate for BFT. It incorporates the
Build 120 PyThermX protocol corrections and closes the two remaining native UI
defects reported during baseline review: preset changes blocked Tk for roughly
30 seconds, and child windows could open on a different display from the BFT
window that invoked them.

The candidate is technically qualified but is not a Git release commit or tag.
Repository policy reserves index, ref, commit, and tag writes for an authorized
interactive account.

## Responsiveness repair

Preset selection no longer performs the full filesystem/rule replan on Tk's
event thread. Large preset replans use the same background progress boundary as
other long operations, retain the prior plan if cancelled, and expose planning
phases through the shared progress contract. Core replanning also reuses the
already-resolved safety evidence instead of resolving every path again.

Selection processing remains deterministic and fail-closed. Performance gates
cover a 4,000-path plan, a real project tree, checkbox toggles, repeated replans,
and the preset-change path that previously froze the interface.

## PyThermX and display behavior

The governed `pythermx-0.5.2` wheel remains unchanged. BFT now preserves event
messages, terminal success/failure/cancel states, cooperative cancellation, and
the Tk command-queue drain established in Build 120.

A shared native placement service determines the monitor work area containing
the invoking BFT window, including displays with negative coordinates, then
centers and clamps the child window within that work area. It is applied to:

- Review Selection;
- Rule Editor;
- Review Report;
- the PyThermX progress dialog; and
- ConfigHub Settings, through an explicit launch placement context.

The service has platform-neutral geometry tests and a real hidden-Tk integration
test. When native monitor APIs are unavailable, it safely falls back to the
invoking window's Tk screen bounds.

## Supported environment matrix

| Environment | Python | Tk | PyThermX | Full suite |
|---|---:|---:|---:|---:|
| `.venv` | 3.11.9 | 8.6.12 | 0.5.2 | 1,520 passed; 87.74% branch coverage |
| `.venv312` | 3.12.10 | 8.6.15 | 0.5.2 | 1,520 passed |
| `.venv313` | 3.13.15 | 8.6.15 | 0.5.2 | 1,520 passed |

All three environments contain their standard `Scripts\activate.bat` and
`Scripts\deactivate.bat` entry points. The project bootstrap continues to define
and verify all three supported rows.

## Governed identities

| Artifact | SHA-256 |
|---|---|
| `bundle_config.json` | `69cdbff09366646110cec9491aff6374a15828007c7c14cb3cb1ee3b0fc2dac2` |
| `.pyprojectmgr/project_manifest.json` | `8d3c523a1e48f76b6a228e5ae9750969e6eefc07727d9cac474eff450b44e1ac` |
| `vendor/pythermx-0.5.2-py3-none-any.whl` | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |

## Delivery controls

The Build 121 archive contains exactly one installer, this build record, the
team communication, and one explicit incoming payload. The installer verifies
every staged byte before mutation, creates a reversible backup, uses resilient
hash-checked placement, verifies PyThermX in every supported environment
present, restores Layer C write protection, and runs the binding whole-suite
coverage gate before success-only teardown.

The stager now requires and verifies the adjacent ZIP `.sha256` sidecar before
making a snapshot. After staging, it archives the checksum and ZIP as one pair;
if the ZIP move fails, it attempts to restore the sidecar to Downloads. This
prevents the loose-checksum condition observed after Builds 119 and 120.

The authorized release owner must still review the candidate and perform any
Git commit or tag action required by repository governance.
