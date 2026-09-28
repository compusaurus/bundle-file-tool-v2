# Build 134: Mac Create Bundle investigation

Update: the supplied Mac traceback identified framework file-alias collisions.
The exact exception was reproduced and repaired in Build 135; see
[the repair record](BFT_BUILD135_MAC_FRAMEWORKS_2026-09-22.md). Native Mac retest
is pending. The notes below preserve the investigation before the log arrived.

Ringo's 37.4-second recording shows Bundle File Tool 2.1.134 on macOS,
with SNW_Intake selected, 466 included files and an estimated 89.9 MB.
After Create bundle is clicked, no save chooser appears and the integrity
label remains "not checked". The recording does not expose an exception,
so it does not establish which pre-save operation failed or whether a
review window was hidden. The recording is retained in the parent project's
docs folder as `Screen Recording 2026-09-22 at 5.57.56 PM.mov` (its actual
filename contains a narrow no-break space before PM).

## Linux qualification

Ubuntu 24.04 under the existing stable WSL installation was tested using
Xvfb and Python 3.12.3. This tests Linux Tk and its real file chooser;
it does not qualify the previously reported WSLg display-client problem.

The complete application successfully opened its real Save As chooser,
created a bundle, and verified the output for:

- One included file, below the progress-dialog threshold.
- 466 included files, exercising progress during checking and creation.
- Three included files plus a blocked nested bundle, exercising the review
  window before checking and saving.

Four permanent real-chooser regression cases were added in
`tests/integration/test_native_save_dialog_tk.py`. They cover those branches
and cancellation, which must leave the destination empty. The tests drive
the chooser's actual Tk entry and buttons; they do not replace the file
dialog or fabricate its return value. OS-owned Windows and macOS panels
remain outside this X11-specific automation.

Combined review, integrity, progress and native-chooser regression results:

- Ubuntu: 107 passed in 8.34 seconds.
- Windows: 103 passed, with the four X11-only cases skipped, in 17.55 seconds.

The tested selection workspace, rule editor and progress adapter hashes
match the Build 134 staged delivery. No product code, installed runtime,
configuration or release archive was changed during this investigation.

## Evidence needed from the Mac

After reproducing the failure, use Tools > View Startup Logs and inspect
the newest log for the final callback traceback. GUI stdout and stderr are
already retained there by `core.startup.StartupSession`, including errors
from Tk callbacks. Ringo has been asked for that error text.

Use the traceback to select and reproduce the repair before publishing a
new build. If it contains no error, investigate review-window visibility
and focus on the Mac. A successful native Mac retest is still required.
