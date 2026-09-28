# BFT v2.1 Build 112 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-25
**Kit:** `INSTALL_BUNDLETOOL_v2_1_112_pythermx_050_cancel.zip`

## What you asked for, and what you get

PyThermX is now on **0.5.0** (Build 12), and **long operations can be stopped**.

The Tkinter progress dialog has a **Cancel** button. On the command line, **Ctrl+C** does the
same thing. Both route into one cooperative request that the scan, the file reading and the
extraction all check between units of work.

## No design round was needed, and here is why

I checked before starting rather than assuming. PyThermX 0.4.0 had already defined the entire
cancellation protocol upstream — two parties with one direction each, four states, a third
terminal outcome on both renderers, Ctrl+C capture, and the Cancel button itself as a widget
option. George had already ratified the direction, and Paul had already set the acceptance
bar ("cancellation reconciles partial work safely").

So the protocol was not mine to invent. One judgement was genuinely open — what happens to
files already written — and that is in §"For George" below rather than decided quietly.

## Nothing is ever killed mid-file

This is the part worth understanding, because it shapes what Cancel feels like.

Cancel does not abort anything. It raises a flag that the work checks **between** units — after
this directory, before that file, between extracted entries. So a cancel can take a moment to
land on a big file, and in exchange **every file already written is complete**. There are no
half-files to find later.

That is tested rather than asserted: a test cancels an extraction partway, then reads back
every file that landed and checks its full contents.

## What happens to work already done

Files already extracted **stay on disk**, and the tool tells you how many:

```
Cancelled: extract cancelled by request during write after 4 of 10 units
  4 file(s) were already written and have been left in place.
```

A cancelled run is treated as its own outcome — not a success, not a failure. The progress bar
closes as CANCELLED rather than OK, and the CLI exits with status 130 and **never** prints
`ERROR`. Cancelling is your decision; reporting it as a fault would blame the tool for it.

## Before you install

Build 112 installs over anything from 2.1.105 to 2.1.111. One delivery zip in Downloads, as
always. The governed config stays read-only after install (Layer C, unchanged from Build 109).

## For George

**One judgement to confirm.** On cancel I keep partially-extracted files and report them,
rather than rolling them back. My reasoning: deleting someone's files because they pressed
Cancel is a bigger surprise than leaving them. But it is a judgement, not a deduction — the
paths are already carried on the exception, so switching to rollback-on-cancel is a small
change if you would rather have that.

**One interaction I want on the record.** `_reconcile_extraction` halts when an extraction is
short, because a silently incomplete extract is corruption. A *cancelled* extraction is also
short, deliberately. Cancellation raises before reconciliation is reached, so you get the real
reason rather than a bogus integrity failure — and there is a second test that drives a
genuine silent loss through the normal path and requires reconciliation to **still** halt.
That one matters more: it stops "cancellation returns early" from drifting into "short
extractions are fine now".

**Still outstanding: WP5.** Builds 110 and 111 were performance and open-bundle work, so the
CLI/Tkinter facade migration has now slipped three builds. Cancellation is wired into the
current call sites and will need re-wiring when WP5 lands. Small, but real, and I would rather
flag it than let it accumulate quietly.

## For Paul

**Your exit gate is met**: cancellation reconciles partial work safely, and the reconciliation
guard is proven still live rather than assumed.

**A defect in my own test suite, found and fixed.** Adding a second Tk-using module gave the
session two Tk roots. Tcl does not survive that, and my fixture turned the resulting fault into
a *skip* labelled "no usable display". Under coverage this silently skipped six Tk tests —
including the Cancel-button ones — while the suite still reported green:

```
891 passed, 6 skipped     (with coverage)
897 passed                (without)
```

One session-scoped fixture in `conftest.py` fixes it; 897 pass either way now. The lesson is
the one worth keeping: a skip is not a pass, and a fixture that converts infrastructure faults
into skips will hide exactly the coverage you most wanted.

**The upgrade was verified before anything was built on it.** I installed 0.5.0 and ran the
existing suite first. Exactly one test failed — the pin test from Build 108, correctly
reporting that 0.5.0 violated the shipped `<0.4`. The other 858 passing unchanged is the
evidence that two minor versions of PyThermX changed nothing BFT relies on.

## Numbers

| | Build 111 | Build 112 |
|---|---|---|
| Tests | 859 passed | **897 passed** |
| Coverage | 90.41% | **90.17%** (85% floor) |
| PyThermX | 0.3.1 | **0.5.0** (Build 12) |
| Upgrade paths proven | — | **7** (105 → 111) |
| Required dependencies | none | none |

Coverage dips slightly because the new cancellation branches in the UI adapters are not all
reachable from a headless test; `core/cancellation.py` itself is at **100%**.

## Still open

Cancellation is not offered on `validate` — it is fast enough that nobody has wanted to stop
it, and the seam is there if that changes. JSONL (F-04) and the facade migration (F-05/WP5)
remain where the roadmap put them.
