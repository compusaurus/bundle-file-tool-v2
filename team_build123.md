# Team Communication - BFT Build 123 Qualified

**Date:** 2026-08-31  
**From:** Paul  
**To:** BFT and PyThermX team  
**Subject:** No-cancel progress geometry and empty-session-log repairs

Team,

The progress-window defect reported in Open Bundle and Validate Bundle was a
shared PyThermX 0.5.2 layout error. With Cancel hidden, `None` meant both
“unresolved” and “no button,” so the first layout pass was skipped and the
canvas never entered the Tk grid. PyThermX 0.5.3 separates those states. Both
operations now receive the complete 520 by 56 progress canvas, and the same
regression is present in the upstream renderer and at BFT's integration seam.

The log report was also correct. Of 400 supported files in BFT's governed log
directory, 399 were zero-byte session placeholders. Those were removed; the
populated diagnostic log was preserved. Future sessions do not create a file
until they write an event, and the viewer filters any legacy empty files.

The repaired wheel is installed in `.venv311`, `.venv312`, and `.venv313`.
Focused BFT progress/validation/logging tests pass 151 of 151 on every runtime,
and the strict full suite passes 1,538 of 1,538 on each supported Python. The
binding branch-coverage result is 87.41 percent. The isolated final rows are
warning-free after binding the remaining classic-frame Tk variables to their
owning frames.

Build 123 supersedes Build 122 for delivery and baseline review.

— Paul
