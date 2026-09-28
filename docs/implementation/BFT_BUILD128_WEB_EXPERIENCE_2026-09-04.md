# Bundle File Tool Build 128 — Web Experience

**Prepared:** 2026-09-04  
**Status:** Source-qualified; delivery prepared  
**Predecessor:** Build 127 installed and user-accepted on PC

## Decision

Build 128 is a focused presentation and usability release for the local web
member of the BFT triad. It does not change selection, checking, bundle format,
extraction, or progress semantics. The existing renderer-independent service
and NodeThermX boundary remain intact.

## Long-path behavior

The source selector now dedicates the control width to the path and places the
folder/file actions on their own row. A wrapping, monospaced preview beneath it
shows the complete selection. Programmatically selected inputs scroll to the
leaf end while retaining the full path as native hover text.

Activity messages and the selected-path inspector wrap arbitrary path segments.
Path columns in both data tables can use multiple lines instead of permanently
ellipsizing long names; every dynamically rendered cell also carries its full
value as hover text. These behaviors cover long folders, long filenames, and
deep paths without requiring a wider monitor.

## Appearance and identity

The browser workspace now ships two supported skins:

- **Studio** is the default warm, high-contrast light workspace.
- **Midnight** is a dark teal workspace using the same semantic status colors.

The choice is authenticated through the existing private session API and stored
under `web_skin` in `UserStateStore`. Browser storage was deliberately avoided:
BFT chooses a new loopback port for each launch, so browser origin storage would
not reliably carry a preference into the next session.

The former letter tile is replaced by a BFT-specific documents-to-sealed-bundle
mark, with a square bundle icon for the favicon. Both PNGs are transparent,
served through the static allowlist, included in package data, and verified by
the delivery manifest. No external font, image, script, CDN, or network service
was added.

## Accessibility and responsive behavior

The skin selector is a labeled two-button group with authoritative
`aria-pressed` state. Focus indicators, explicit textual state, reduced-motion
handling, and NodeThermX accessibility remain active in both skins. The desktop
grid gives the source and activity panels more useful minimum widths, collapses
to a two-column layout at 1120 pixels, and becomes a single column on narrow
screens.

## Qualification

- JavaScript syntax validation passed.
- Focused static, adapter, user-state, packaging, HTTP, and security regression
  passed 37 tests.
- Complete Python 3.13.15 qualification passed 1,632 tests at 85.92 percent
  branch coverage; two notices were the previously recorded non-failing Tk
  variable finalizers.
- Live Chromium acceptance covered a 1440-by-900 desktop layout and the default
  narrow in-app viewport, a real large-project source plan, multi-line table and
  inspector paths, both skins, preference survival across reload, packaged
  image dimensions, and an empty browser warning/error log.

Repository commit and tag actions remain reserved for the authorized
interactive release owner.
