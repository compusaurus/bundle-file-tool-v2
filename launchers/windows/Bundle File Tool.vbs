Option Explicit

Dim runtimeDir, runtimeFile, fso, shell, launcherDir, projectRoot, candidates, pythonw, fallbackPythonw, item, command, probe
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
fallbackPythonw = ""
For Each item In candidates
    If fso.FileExists(item) Then
        If item = runtimeDir & "\Scripts\pythonw.exe" Then
            pythonw = item
            Exit For
        End If
        If fallbackPythonw = "" Then fallbackPythonw = item
        probe = Chr(34) & item & Chr(34) & " -c " & Chr(34) & _
            "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('pysplashx') and importlib.util.find_spec('PySide6') else 1)" & Chr(34)
        If shell.Run(probe, 0, True) = 0 Then
            pythonw = item
            Exit For
        End If
    End If
Next

' Preserve BFT's fail-open contract if no splash-capable environment exists.
If pythonw = "" Then pythonw = fallbackPythonw

If pythonw = "" Then
    MsgBox "No supported BFT Python environment was found." & vbCrLf & vbCrLf & _
        "Create .venv311, .venv312, or .venv313, then try again.", _
        vbCritical, "Bundle File Tool"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectRoot
shell.Environment("PROCESS")("BFT_DIAGNOSTIC") = "0"
command = Chr(34) & pythonw & Chr(34) & " " & _
    Chr(34) & projectRoot & "\src\main.py" & Chr(34)
shell.Run command, 0, False
