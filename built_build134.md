# Bundle File Tool Build 134

Release identity: `2.1.134`.

The native workspace can display selected views as Tabs, Side by side, Stacked,
or an equal Grid. Show all displays all four views. New window detaches a live
view; closing it or selecting Return to workspace docks the same view again.

RailGun detects distinct Windows displays and provides Other display controls
for individual views and the main workspace. Disconnected displays trigger
recovery of separate windows. Layout and visibility are saved in per-user state.

For Selections and Result set on one display with guidance on another, select
those three views, choose Side by side, then use Operational Guidance's Other
display button. The two remaining views divide the main window evenly.

Use `INSTALL_BFT.cmd` or `INSTALL_BFT.command` to select a fresh folder or upgrade.
The stable-WSL browser launcher remains available. Linux native layout and
detach/return behavior are tested under Xvfb. Automatic physical monitor
detection uses the existing Windows RailGun driver; other native platforms
offer New window and manual OS placement. These controls are native-Tk features.

This remains an internal release candidate pending native Mac qualification and
neutral folder defaults for public distribution. See the
[implementation record](docs/implementation/BFT_BUILD134_COMPARISON_VIEWS_2026-09-22.md).
