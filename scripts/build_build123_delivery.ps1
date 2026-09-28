[CmdletBinding()]
param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildName = "INSTALL_BUNDLETOOL_v2_1_123_pythermx_layout_and_log_hygiene"
$deliveryRoot = Join-Path $projectRoot "tmp\build123_delivery"
$incomingRoot = Join-Path $deliveryRoot "_bundletool_incoming"
$supportRoot = Join-Path $incomingRoot "_delivery"
$integrationRoot = Join-Path $incomingRoot "_integrations"
$installer = Join-Path $projectRoot "$buildName.bat"
$buildRecord = Join-Path $projectRoot "built_build123.md"
$teamRecord = Join-Path $projectRoot "team_build123.md"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $projectRoot "tmp"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)

function Remove-ExactBuildDirectory([string]$Path) {
    $resolvedParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $Path))
    $expectedParent = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "tmp"))
    if ($resolvedParent -ne $expectedParent -or (Split-Path -Leaf $Path) -ne "build123_delivery") {
        throw "Refusing to remove an unexpected delivery directory: $Path"
    }
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Copy-RelativeFile([string]$SourceRoot, [string]$RelativePath, [string]$DestinationRoot) {
    $source = Join-Path $SourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required delivery source is missing: $source"
    }
    $destination = Join-Path $DestinationRoot $RelativePath
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-RelativeTree([string]$RelativeRoot) {
    $sourceRoot = Join-Path $projectRoot $RelativeRoot
    Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | Where-Object {
        $_.FullName -notmatch "[\\/](__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|[^\\/]+\.egg-info)[\\/]" -and
        $_.Extension -notin @(".pyc", ".pyo")
    } | ForEach-Object {
        $relative = [System.IO.Path]::GetRelativePath($projectRoot, $_.FullName)
        Copy-RelativeFile $projectRoot $relative $incomingRoot
    }
}

Remove-ExactBuildDirectory $deliveryRoot
New-Item -ItemType Directory -Force -Path $supportRoot, $integrationRoot, $OutputDirectory | Out-Null

$rootFiles = @(
    ".gitignore",
    "bundle_config.json",
    "PREP_AND_STAGE_BFT.bat",
    "pyproject.toml",
    "pytest.ini",
    "requirements-test-matrix.txt",
    "requirements.txt",
    "README.md",
    "USER_GUIDE.md",
    "CHANGELOG.md",
    "LICENSE.txt",
    "VERSION.txt"
)
foreach ($relative in $rootFiles) {
    Copy-RelativeFile $projectRoot $relative $incomingRoot
}
foreach ($relativeTree in @(".pyprojectmgr", "config", "docs\implementation", "scripts", "src", "tests", "vendor")) {
    Copy-RelativeTree $relativeTree
}

$pythonWorkspace = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "..\.."))
$ppmRoot = Join-Path $pythonWorkspace "pyprojectmgr_project\pyprojectmgrV2"
$configEditorRoot = Join-Path $pythonWorkspace "config_edit_project\config_edit_tool"
$integrations = @(
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "src\configuration_hub\launcher.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "src\cli\cli_interface.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "tests\configuration_hub\test_pythermx_vertical_slice.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "tests\configuration_hub\test_config_hub_real_tk.py" },
    @{ Key = "configeditor"; SourceRoot = $configEditorRoot; Relative = "config_edit_hub.py" },
    @{ Key = "configeditor"; SourceRoot = $configEditorRoot; Relative = "config_edit_hub_tkinter.py" },
    @{ Key = "configeditor"; SourceRoot = $configEditorRoot; Relative = "tests\test_config_edit_hub.py" }
)

$integrationLines = foreach ($item in $integrations) {
    $integrationFolder = "configeditor"
    if ($item.Key -eq "ppm") {
        $integrationFolder = "pyprojectmgr"
    }
    $destinationRoot = Join-Path $integrationRoot $integrationFolder
    Copy-RelativeFile $item.SourceRoot $item.Relative $destinationRoot
    $copied = Join-Path $destinationRoot $item.Relative
    $hash = (Get-FileHash -LiteralPath $copied -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash $($item.Key) $($item.Relative)"
}
[System.IO.File]::WriteAllLines(
    (Join-Path $supportRoot "integration_manifest.sha256"),
    $integrationLines,
    [System.Text.UTF8Encoding]::new($false)
)

$manifestLines = Get-ChildItem -LiteralPath $incomingRoot -Recurse -File | Where-Object {
    $_.FullName -notlike "$supportRoot\*" -and
    $_.FullName -notlike "$integrationRoot\*"
} | Sort-Object FullName | ForEach-Object {
    $relative = [System.IO.Path]::GetRelativePath($incomingRoot, $_.FullName)
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash $relative"
}
[System.IO.File]::WriteAllLines(
    (Join-Path $supportRoot "delivery_manifest.sha256"),
    $manifestLines,
    [System.Text.UTF8Encoding]::new($false)
)

$manifestHash = (Get-FileHash -LiteralPath (Join-Path $projectRoot ".pyprojectmgr\project_manifest.json") -Algorithm SHA256).Hash.ToLowerInvariant()
$markers = @(
    "README.md|Bundle File Tool (BFT) creates, reviews, validates, and extracts",
    "USER_GUIDE.md|identifies BFT as the requester",
    "CHANGELOG.md|2.1.123",
    "LICENSE.txt|All rights reserved.",
    "VERSION.txt|2.1.123",
    "scripts\setup_supported_envs.ps1|.venv311",
    "src\core\module_ids.py|$manifestHash",
    "src\ui\config_hub_launcher.py|--target-work-area=",
    "src\ui\log_viewer.py|class LogViewer",
    "src\ui\log_viewer.py|path.stat().st_size > 0",
    "src\ui\main_window.py|def menu_validate_bundle",
    "src\ui\main_window.py|def menu_unbundle_clipboard",
    "src\ui\text_viewer.py|class TextFileViewer",
    "tests\unit\test_logging.py|test_log_file_created_on_first_event",
    "tests\unit\test_pythermx_tk_integration.py|test_no_cancel_dialog_maps_a_full_progress_canvas",
    "tests\unit\test_ui_public_surface.py|test_native_ui_contains_no_public_placeholder_messages"
)
[System.IO.File]::WriteAllLines(
    (Join-Path $supportRoot "delivery_markers.txt"),
    $markers,
    [System.Text.UTF8Encoding]::new($false)
)

foreach ($topLevel in @($installer, $buildRecord, $teamRecord)) {
    if (-not (Test-Path -LiteralPath $topLevel -PathType Leaf)) {
        throw "Required top-level delivery file is missing: $topLevel"
    }
    Copy-Item -LiteralPath $topLevel -Destination $deliveryRoot -Force
}

$zipPath = Join-Path $OutputDirectory "$buildName.zip"
$sidecarPath = "$zipPath.sha256"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path -LiteralPath $sidecarPath) {
    Remove-Item -LiteralPath $sidecarPath -Force
}
Compress-Archive -Path (Join-Path $deliveryRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText(
    $sidecarPath,
    "$zipHash  $(Split-Path -Leaf $zipPath)`r`n",
    [System.Text.ASCIIEncoding]::new()
)

Write-Host "Build 123 delivery: $zipPath"
Write-Host "SHA256 sidecar  : $sidecarPath"
Write-Host "BFT files      : $($manifestLines.Count)"
Write-Host "Integration    : $($integrationLines.Count)"
