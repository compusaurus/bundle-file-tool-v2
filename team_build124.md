# Team Communication - BFT Build 124 Candidate

**Date:** 2026-09-01  
**From:** Paul  
**To:** BFT team  
**Subject:** Self-bundle reliability and first cross-platform release candidate

Team,

The apparent 100-percent hang was not one deadlock. The progress contract
declared reading complete before the final read, and the application then did
several expensive, silent phases while retaining multiple complete artifact
representations. Generated `tmp` and `out` trees made that path dramatically
worse when BFT bundled itself.

Build 124 fixes the system rather than hiding the symptom. BFT source planning
prunes generated work before descent, large plans require informed approval,
each remaining phase is visible and cancellable, and final completion follows
durable atomic publication. Large artifacts are spooled and streamed rather
than duplicated in memory.

The Mac handoff is incorporated. Path assertions now respect canonical macOS
aliases, captured progress is platform-neutral, normal GUI launch is
windowless on Windows and macOS, diagnostic launch remains explicit, and early
failures have per-session logs. Startup window behavior is user-owned state
with Restore Last as the default; closing while minimized does not make the
next launch disappear.

The full non-display suite passes 1,446 tests on each recovered Python 3.11,
3.12, and 3.13 runtime. This is still a release candidate until real-Tk Windows
and official Mac 3.13 acceptance rows are attached; the recovered Windows
runtimes lack `init.tcl`. The web interface remains the first work package of
Build 125 so the Build 124 reliability and cross-platform boundary stays
reviewable.

— Paul
