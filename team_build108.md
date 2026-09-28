# BFT v2.1 Build 108 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-23
**Kit:** `INSTALL_BUNDLETOOL_v2_1_108_pythermx_tk.zip`

## Ringo asked whether PyThermX was fully integrated. It was not.

Two gaps:

**We were a version behind.** Build 107 vendored PyThermX 0.2.0. The current release is
**0.3.1**, and 0.2.0 is no longer even in the therm project's `dist/`.

**The GUI had no progress bar at all.** Build 107 did the CLI only. Since the original
complaint — no feedback on large folder operations — was about the GUI, the half that shipped
was not the half that was asked for.

Build 108 closes both.

## Before you install

Move the Build 106 and Build 107 zips out of Downloads. The stager requires exactly one
delivery zip, and this kit contains everything both of them contained. It installs over
2.1.105, 2.1.106 or 2.1.107.

## The GUI was not missing a widget — it was frozen

This is the part worth understanding, because it changes what the fix had to be.

The window called the folder scan directly from the button handler. Tkinter cannot repaint
while that is running, so the whole window sat dead until the scan finished. Dropping a
progress bar into that code would have drawn one frame and then frozen along with everything
else — a hang with a bar on it, which is worse than a hang.

So the work now runs on a **background thread** and the window stays alive and repainting.
PyThermX 0.3.0 added the machinery for exactly this, with a firm rule about which side
touches what, and we follow it: the background thread only ever posts values into a queue,
and the display is built and updated purely on the UI thread.

You will see this in Select Source, in the preview build, and in Extract.

## What you will see

Same behaviour as the CLI, because it is the same event stream. The scan starts as a moving
marquee — until the walk finishes, nobody can know how many files there are — and then turns
into a real percentage on the same bar rather than being replaced by a different one.

## Controls

Two new settings in `bundle_config.json`:

```json
"ui": { "progress": { "enabled": true, "min_files": 200 } }
```

`enabled` turns the dialog off completely. `min_files` is the size below which work just runs
inline with no dialog — a modal popup for eleven files is worse than no popup. Folder
scanning ignores the threshold, because it cannot know its size in advance.

## For George — two things, one of them recurring

**The governed config drifted again, today at 11:54** — `version` reset to `2.1.0` and the
safety rules replaced with the old allow-list.

**We know exactly what it was.** Ringo used Bundle File Tool today, and the file that landed is
the configuration archived inside `bundles\BFTv2_v2.1 Build 104_bundle.txt` — identical in every
single value except `last_source_dir`. So this was not a mystery process; it was our own tool,
in an older build, doing the pre-Build-104 thing of writing UI state back over the whole
governed document.

Two suspects were ruled out properly rather than by assumption:

- **pyprojectmgr** (Ringo's first thought, and a fair one — a scan had run that morning). BFT's
  own pyprojectmgr log and database were last written on the 20th, no pyprojectmgr log mentions
  `bundle_file_tool`, its only run that hour scanned itself *after* the overwrite, and its
  source has no reference to `bundle_config.json` at all.
- **The installed 2.1.107.** `save()` raises unconditionally, the only remaining write path
  creates a missing file and never overwrites one, and nothing in the source calls `save()`.
  I checked this rather than trusting it, because if the installed build could do this it would
  be a defect in my own work.

I restored the file from the Build 107 payload and checked it byte-for-byte against that kit's
manifest, and kept the drifted copy as evidence.

**One correction.** I told you earlier that only `bundle_config.json` changed today. That was
wrong — I read it off a listing I had truncated. Two generated files, `src/core/config_ids.py`
and `src/core/static_ids.py`, also have today's timestamp. Their contents are byte-identical to
the 20th, so nothing was damaged, but I should not have said "only".

This is the fourth recurrence, and the shape of it is now clear: Build 105 stopped *this* copy
from doing it, but it cannot stop an **older copy of Bundle File Tool** elsewhere on the disk
from writing our file. That is the thing to close, and it is George's call. The cheap version is
to have the config record who wrote it, so a fifth occurrence identifies itself instead of
costing an afternoon.

## For Paul

Your Build 104 ruling now has both adapters it called for. Same `OperationProgress` stream;
`cli_progress.py` draws it with the CLI thermometer, `ui/tk_progress.py` draws it with the Tk
one. The two make identical decisions about phases and promotion, and they share the phase
labels rather than each spelling them out.

The layering test grew accordingly: no file under `src/core/` may import `tkinter`,
`pythermx`, either adapter, or `pythermx.tk`. It parses every core file to check.

The Web adapter, your third consumer, is still unwritten.

## A test of mine that could not fail

Build 107 shipped the pin `pythermx>=0.2.0,<0.3` and a test that checked the **floor**. When
0.3.1 got installed, the environment broke the shipped pin and the suite stayed green,
because a floor check cannot catch an upper-bound breach. The test now evaluates the actual
specifier against the actually-installed version, which catches the class rather than the
instance.

## A defect this caught, in Build 107

While checking the demo commands actually worked, I found that
`unbundle --progress bar` drew nothing at all. The flag was there, the events
were there, but the command never handed the progress sink to the extractor -
an edit of mine in Build 107 that silently did not apply.

Nothing failed, and that is the instructive part: progress reporting is
deliberately built so a broken reporter can never break the operation it is
reporting on. The cost of that choice is that a *missing* reporter looks exactly
like a working one. Only looking at real output tells them apart.

There is now a test that runs the real command and checks a bar appears. Bundling
was never affected, and no bundle or extraction ever produced wrong files - only
the display was missing.

## Numbers

| | Build 107 | Build 108 |
|---|---|---|
| Tests | 661 passed | **702 passed** |
| Coverage | 90.23% | **90.29%** (85% floor) |
| PyThermX | 0.2.0 | **0.3.1** |
| Required dependencies | none | none |

All 661 Build 107 tests pass unchanged on 0.3.1 — expected, since PyThermX's core file is
byte-identical to the 0.2.0 release and their own release test enforces that.

Coverage note: `src/ui/*` had been excluded wholesale since Build 104. The new adapter is
genuinely tested, so it is now measured (91%) and only the four untested frames stay
excluded. Hiding it would have flattered the number and exempted the new code from the gate.

## Still open

No **cancel** button. The dialog's close button is deliberately disabled rather than offering
a control that would do nothing — cancelling needs cooperative checks inside the scan itself,
which is a core change and its own build. Say the word and I will schedule it.
