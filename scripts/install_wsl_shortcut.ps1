[CmdletBinding()]
param([string]$Distribution = 'BFT-Ubuntu-24.04')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonw = $null
$runtimePointer = Join-Path $projectRoot '.bft-runtime.txt'
$environments = @('.venv313', '.venv312', '.venv311', '.venv')
if (Test-Path -LiteralPath $runtimePointer) { $environments = @((Get-Content -LiteralPath $runtimePointer -First 1)) + $environments }
foreach ($environment in $environments) {
    $candidate = Join-Path $projectRoot ($environment + '\Scripts\pythonw.exe')
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $pythonw = $candidate; break }
}
if (-not $pythonw) { throw 'Install a Windows BFT Python runtime before registering WSL shortcuts.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
foreach ($entry in @(
    @{Name='Bundle File Tool Linux'; Command='bft-web'; Extra=''; Description='BFT running in Ubuntu - browser workspace'},
    @{Name='Bundle File Tool Linux Native'; Command='bft-gui'; Extra=' --native'; Description='Native Ubuntu BFT - requires working WSLg graphics'}
)) {
    $linuxLauncher = (& wsl.exe -d $Distribution -- sh -lc ('command -v "$HOME/.local/bin/' + $entry.Command + '"')).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxLauncher.StartsWith('/')) { throw 'Install the Linux BFT delivery in this distro first.' }
    $shortcut = $shell.CreateShortcut((Join-Path $desktop ($entry.Name + '.lnk')))
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'launch_wsl_bft.py') + '" --distribution "' + $Distribution + '" --linux-launcher "' + $linuxLauncher + '"' + $entry.Extra
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = $entry.Description
    $shortcut.WindowStyle = 1
    $shortcut.IconLocation = (Join-Path $env:SystemRoot 'System32\wsl.exe') + ',0'
    $shortcut.Save()
    Write-Output (Join-Path $desktop ($entry.Name + '.lnk'))
}