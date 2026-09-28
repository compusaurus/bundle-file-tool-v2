Option Explicit

Dim runtimeDir, runtimeFile, fso, shell, launcherDir, projectRoot, candidates, pythonw, item, command
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

launcherDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectRoot = fso.GetParentFolderName(fso.GetParentFolderName(launcherDir))
runtimeDir = projectRoot & "\.bft-uninstalled"
If fso.FileExists(projectRoot & "\.bft-runtime.txt") Then
    Set runtimeFile = fso.OpenTextFile(projectRoot & "\.bft-runtime.txt", 1)
    runtimeDir = projectRoot & "\" & Replace(Trim(runtimeFile.ReadLine), "/", "\")
    runtimeFile.Close
End If
candidates = Array( _
    runtimeDir & "\Scripts\pythonw.exe", _
    projectRoot & "\.venv311\Scripts\pythonw.exe", _
    projectRoot & "\.venv312\Scripts\pythonw.exe", _
    projectRoot & "\.venv313\Scripts\pythonw.exe")

pythonw = ""
For Each item In candidates
    If fso.FileExists(item) Then
        pythonw = item
        Exit For
    End If
Next

If pythonw = "" Then
    MsgBox "No supported BFT Python environment was found." & vbCrLf & vbCrLf & _
        "Create .venv311, .venv312, or .venv313, then try again.", _
        vbCritical, "Bundle File Tool Web"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectRoot
command = Chr(34) & pythonw & Chr(34) & " " & _
    Chr(34) & projectRoot & "\src\web_main.py" & Chr(34)
shell.Run command, 0, False
