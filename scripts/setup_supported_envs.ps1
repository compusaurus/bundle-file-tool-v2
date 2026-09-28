[CmdletBinding()]
param(
    [string]$Python311 = $env:BFT_PYTHON311,
    [string]$Python312 = $env:BFT_PYTHON312,
    [string]$Python313 = $env:BFT_PYTHON313,
    [string]$TargetProjectRoot = "",
    [string]$PayloadRoot = "",
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = if ([string]::IsNullOrWhiteSpace($TargetProjectRoot)) {
    (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $TargetProjectRoot).Path
}
$payloadSource = if ([string]::IsNullOrWhiteSpace($PayloadRoot)) {
    $projectRoot
} else {
    (Resolve-Path -LiteralPath $PayloadRoot).Path
}
if ((Split-Path -Leaf $projectRoot) -ne "bundle_file_tool_v2") {
    throw "Target project root must be the bundle_file_tool_v2 directory: $projectRoot"
}
$requirements = Join-Path $payloadSource "requirements-test-matrix.txt"
$progressWheelCandidates = @(Get-ChildItem -LiteralPath (Join-Path $payloadSource "vendor") `
    -Filter "pythermx-*.whl" -File)
$splashWheelCandidates = @(Get-ChildItem -LiteralPath (Join-Path $payloadSource "vendor") `
    -Filter "pysplashx-*.whl" -File)

if ($progressWheelCandidates.Count -ne 1) {
    throw "Expected exactly one governed PyThermX wheel; found $($progressWheelCandidates.Count)."
}
if ($splashWheelCandidates.Count -ne 1) {
    throw "Expected exactly one governed PySplashX wheel; found $($splashWheelCandidates.Count)."
}

function Assert-Interpreter {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Expected
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Python $Expected interpreter not found: $Path"
    }
    & $Path -c (
        "import sys; expected=tuple(map(int, '$Expected'.split('.'))); " +
        "actual=sys.version_info[:2]; print(sys.executable, sys.version); " +
        "raise SystemExit(0 if actual == expected else 2)"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Interpreter $Path is not Python $Expected."
    }
}

function Resolve-Interpreter {
    param(
        [string]$ExplicitPath,
        [Parameter(Mandatory = $true)][string]$Version
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return $ExplicitPath
    }

    $registryPath = "HKCU:\Software\Python\PythonCore\$Version\InstallPath"
    try {
        $registered = Get-ItemPropertyValue -LiteralPath $registryPath `
            -Name "ExecutablePath" -ErrorAction Stop
        if (Test-Path -LiteralPath $registered -PathType Leaf) {
            return $registered
        }
    } catch {
        # Fall through to the conventional per-user location.
    }

    $digits = $Version.Replace(".", "")
    $perUser = Join-Path $env:LOCALAPPDATA `
        "Programs\Python\Python$digits\python.exe"
    if (Test-Path -LiteralPath $perUser -PathType Leaf) {
        return $perUser
    }

    return ""
}

function Remove-KnownEnvironment {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $parent = [IO.Path]::GetDirectoryName($resolved)
    $leaf = [IO.Path]::GetFileName($resolved)
    if ($parent -ne $projectRoot -or $leaf -notin @(".venv", ".venv311", ".venv312", ".venv313")) {
        throw "Refusing to remove unexpected environment path: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

$rows = @(
    [pscustomobject]@{ Version = "3.11"; Interpreter = $Python311; Directory = ".venv311" },
    [pscustomobject]@{ Version = "3.12"; Interpreter = $Python312; Directory = ".venv312" },
    [pscustomobject]@{ Version = "3.13"; Interpreter = $Python313; Directory = ".venv313" }
)

$legacyEnvironment = Join-Path $projectRoot ".venv"
if (Test-Path -LiteralPath $legacyEnvironment) {
    if (-not $Recreate) {
        throw "Legacy .venv exists. Close BFT and rerun with -Recreate to migrate to .venv311."
    }
    Write-Host "Removing legacy .venv before standardized environment creation..."
    Remove-KnownEnvironment -Path $legacyEnvironment
}

foreach ($row in $rows) {
    $row.Interpreter = Resolve-Interpreter `
        -ExplicitPath $row.Interpreter -Version $row.Version
    if ([string]::IsNullOrWhiteSpace($row.Interpreter)) {
        throw "Supply -Python$($row.Version.Replace('.', '')), set BFT_PYTHON$($row.Version.Replace('.', '')), or install the registered per-user CPython runtime."
    }
    Assert-Interpreter -Path $row.Interpreter -Expected $row.Version

    $environment = Join-Path $projectRoot $row.Directory
    if ($Recreate) {
        Remove-KnownEnvironment -Path $environment
    }

    if (-not (Test-Path -LiteralPath $environment)) {
        Write-Host "Creating $($row.Directory) with Python $($row.Version)..."
        & $row.Interpreter -m venv $environment
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create $environment."
        }
    } else {
        Write-Host "Provisioning existing $($row.Directory)..."
    }

    $environmentPython = Join-Path $environment "Scripts\python.exe"
    & $environmentPython -c (
        "import sys; expected=tuple(map(int, '$($row.Version)'.split('.'))); " +
        "raise SystemExit(0 if sys.version_info[:2] == expected else 2)"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "$environment is not a working Python $($row.Version) environment."
    }

    & $environmentPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to bootstrap pip in $environment."
    }

    & $environmentPython -m pip install --disable-pip-version-check `
        --use-feature=truststore `
        --requirement $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the BFT test toolchain into $environment."
    }

    & $environmentPython -m pip install --disable-pip-version-check `
        --use-feature=truststore `
        --no-index --no-deps $progressWheelCandidates[0].FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the governed PyThermX wheel into $environment."
    }

    & $environmentPython -m pip install --disable-pip-version-check `
        --use-feature=truststore `
        --no-index --no-deps $splashWheelCandidates[0].FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the governed PySplashX wheel into $environment."
    }

    & $environmentPython -c (
        "import coverage, pytest, PySide6, pysplashx, pythermx, tkinter, yaml; " +
        "assert pythermx.__version__ == '0.5.3'; " +
        "assert pysplashx.__version__ == '0.1.0'; " +
        "root=tkinter.Tk(); root.withdraw(); " +
        "tk_patch=root.tk.call('info', 'patchlevel'); root.destroy(); " +
        "print('ready:', pytest.__version__, coverage.__version__, " +
        "'PyThermX', pythermx.__version__, 'PySplashX', pysplashx.__version__, " +
        "'PySide6', PySide6.__version__, 'Tk', tk_patch, 'PyYAML', yaml.__version__)"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Post-install import probe failed in $environment."
    }
}

Write-Host "BFT supported environments are ready: .venv311, .venv312, and .venv313."
