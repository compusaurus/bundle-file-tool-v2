[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$TargetProjectRoot)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $TargetProjectRoot).Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
foreach ($name in @('Bundle File Tool', 'Bundle File Tool Web')) {
    $launcher = Join-Path $root ('launchers\windows\' + $name + '.vbs')
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Missing launcher: $launcher" }
    $shortcut = $shell.CreateShortcut((Join-Path $desktop ($name + '.lnk')))
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\wscript.exe'
    $shortcut.Arguments = '"' + $launcher + '"'
    $shortcut.WorkingDirectory = $root
    $shortcut.WindowStyle = 1
    $shortcut.Description = $name
    $shortcut.Save()
}
