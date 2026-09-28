Option Explicit
Dim shell, fso, root, desktop, name, launcher, shortcut
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
If WScript.Arguments.Count <> 1 Then WScript.Quit 2
root = fso.GetAbsolutePathName(WScript.Arguments(0))
desktop = shell.SpecialFolders("Desktop")
For Each name In Array("Bundle File Tool", "Bundle File Tool Web")
    launcher = root & "\launchers\windows\" & name & ".vbs"
    If Not fso.FileExists(launcher) Then WScript.Quit 3
    Set shortcut = shell.CreateShortcut(desktop & "\" & name & ".lnk")
    shortcut.TargetPath = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
    shortcut.Arguments = Chr(34) & launcher & Chr(34)
    shortcut.WorkingDirectory = root
    shortcut.WindowStyle = 1
    shortcut.Description = name
    shortcut.Save
Next
