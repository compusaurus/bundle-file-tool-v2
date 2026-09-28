# Build 134: comparison views and displays

The native Selection Workspace now preserves its live widgets and one selection
model while arranging views as tabs, equal horizontal panes, equal vertical
panes, or a grid. Show all selects every view and the grid layout. Detached views
continue to show model changes; hiding a view does not alter the plan.

New window uses Tk's window-manager support for existing Frame widgets. Return
to workspace, the separate window's close button, and Return all to workspace
restore those same widgets. Switching to Un-bundle hides the separate Bundle
views and switching back restores the visible ones. Rules and Result set dialogs
follow their owning view.

RailGun's existing Win32 topology provider supplies taskbar-safe work areas.
Other display chooses relative to the window's current display, retaining signed
coordinates and cycling distinct work areas in spatial order for three or more
monitors. Mirrored work areas do not count twice. A two-second topology refresh
updates controls and rescues off-screen detached views after a display change.
An enumeration failure leaves windows in place; a failed recovery docks the view.

Result controls wrap at narrow widths. Show explanation starts collapsed in
short panes so rows remain readable in a four-view layout, and the user can
expand it. Short panes use an Actions menu for the five result actions and
place filter/explanation checkboxes beside it. The full application was checked
at 1000 by 700 on Windows and Linux. Layout and view visibility persist outside
governed settings. Ctrl+Tab and Ctrl+Shift+Tab continue to work from page contents.

Windows and Linux Tk regression checks cover equal resizing, view identity,
live results, docking, visibility, disconnected-monitor recovery, invalid saved
preferences, and window-manager failures. Physical display detection is currently
Windows-only; Linux/macOS still provide layouts, separate windows and manual
placement. Native macOS qualification remains outstanding. WSL retains the
user-selected stable browser launcher. Browser workspace controls are unchanged.

Final build qualification and checksums are recorded beside the archives in
`dist/BUILD_134_VERIFICATION.md`. The existing fresh-folder/upgrade installer is
included, and the prior Build 133 delivery remains available.
