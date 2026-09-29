[CmdletBinding()]
param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildName = "INSTALL_BUNDLETOOL_v2_1_136_macos_confighub_launch"
$deliveryRoot = Join-Path $projectRoot "tmp\build136_delivery"
$incomingRoot = Join-Path $deliveryRoot "_bundletool_incoming"
$supportRoot = Join-Path $incomingRoot "_delivery"
$integrationRoot = Join-Path $incomingRoot "_integrations"
$installer = Join-Path $projectRoot "$buildName.bat"
$buildRecord = Join-Path $projectRoot "built_build136.md"

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $projectRoot "tmp"
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)

function Remove-ExactBuildDirectory([string]$Path) {
    $resolvedParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $Path))
    $expectedParent = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "tmp"))
    if ($resolvedParent -ne $expectedParent -or (Split-Path -Leaf $Path) -ne "build136_delivery") {
        throw "Refusing to remove an unexpected delivery directory: $Path"
    }
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

function Get-ProjectRelativePath([string]$BasePath, [string]$FullPath) {
    $base = [System.IO.Path]::GetFullPath($BasePath).TrimEnd("\") + "\"
    $full = [System.IO.Path]::GetFullPath($FullPath)
    if (-not $full.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside the expected project root: $full"
    }
    return $full.Substring($base.Length)
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
        $relative = Get-ProjectRelativePath $projectRoot $_.FullName
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
    "docs\MACOS_SETUP.md",
    "docs\LINUX_SETUP.md",
    "LICENSE.txt",
    "VERSION.txt"
    "INSTALL_BFT.cmd"
    "INSTALL_BFT.command"
    "docs\INSTALLATION.md"
    ".pyprojectmgr\project_manifest.json"
    ".pyprojectmgr\project_spec.json"
    ".pyprojectmgr\setup_contribution.json"
    "built_build136.md"
    "$buildName.bat"
)
foreach ($relative in $rootFiles) {
    Copy-RelativeFile $projectRoot $relative $incomingRoot
}
foreach ($relativeTree in @("config", "docs\implementation", "launchers", "scripts", "src", "tests", "vendor")) {
    Copy-RelativeTree $relativeTree
}

$pythonWorkspace = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "..\.."))
$ppmRoot = Join-Path $pythonWorkspace "pyprojectmgr_project\pyprojectmgrV2"
$configEditorRoot = Join-Path $pythonWorkspace "config_edit_project\config_edit_tool"
$integrations = @(
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "src\configuration_hub\launcher.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "src\configuration_hub\providers.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "src\cli\cli_interface.py" },
    @{ Key = "ppm"; SourceRoot = $ppmRoot; Relative = "config\config_hub_registry.json" },
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
    $relative = Get-ProjectRelativePath $incomingRoot $_.FullName
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
    "CHANGELOG.md|2.1.136",
    "LICENSE.txt|All rights reserved.",
    "VERSION.txt|2.1.136",
    "scripts\setup_supported_envs.ps1|.venv311",
    "src\core\module_ids.py|$manifestHash",
    "src\core\service.py|class PlanEstimate",
    "src\core\startup.py|def begin_gui_startup",
    "src\ui\config_hub_launcher.py|--target-work-area=",
    "src\ui\config_hub_launcher.py|_fallback_executable_dirs",
    "launchers\macos\Bundle File Tool.app\Contents\MacOS\bft-gui|export PATH",
    "launchers\macos\Bundle File Tool Web.app\Contents\MacOS\bft-web|export PATH",
    ".gitattributes|project_manifest.json -text",
    "src\ui\log_viewer.py|class LogViewer",
    "src\ui\log_viewer.py|path.stat().st_size > 0",
    "src\ui\main_window.py|def menu_validate_bundle",
    "src\ui\main_window.py|def menu_unbundle_clipboard",
    "src\ui\main_window.py|apply_window_icon",
    "src\ui\window_icon.py|def apply_window_icon",
    "src\ui\assets\pysplashx_profile.json|Bundle File Tool Crex Startup",
    "src\core\splash.py|def run_startup_splash",
    "src\core\splash.py|place_process_tree_windows",
    "src\railgun_display\resolver.py|def resolve_application_launch",
    "src\railgun_display\windows.py|def place_process_tree_windows",
    "src\main.py|launch_work_area",
    "src\cli.py|--skip-splash",
    "src\ui\config_hub_launcher.py|pysplashx",
    "src\ui\main_window.py|def show_startup_preferences",
    "src\core\checking.py|bft.check-result.v1",
    "src\ui\selection_workspace.py|def check_selection",
    "src\ui\workspace_layout.py|class WorkspaceLayout",
    "src\railgun_display\resolver.py|def other_display",
    "src\ui\unbundle_frame.py|def check_current_bundle",
    "src\ui\check_results.py|class CheckResultsDialog",
    "src\ui\check_preferences.py|class CheckPreferencesDialog",
    "src\cli.py|def handle_check",
    "src\web\server.py|LOOPBACK_HOST",
    "src\web\adapter.py|class WebAdapter",
    "src\web\jobs.py|class JobManager",
    "src\web\static\index.html|browse-source",
    "src\web\static\index.html|bft-web-mark.png",
    "src\web\static\index.html|pysplashx-splash",
    "src\web\static\index.html|replay-splash",
    "src\web\static\app.js|api/dialogs",
    "src\web\static\app.js|ensurePlanTargetsOutput",
    "src\web\static\app.js|api/preferences/skin",
    "src\web\static\app.js|NodeThermXWeb.WebThermometer",
    "src\web\static\app.css|.skin-picker button.active",
    "src\core\user_state.py|web_skin",
    "src\web\static\nodethermx-web.js|global.NodeThermXWeb = api",
    "src\web\static\nodethermx-web.css|thermx-indeterminate",
    "src\web\static\pysplashx-splash.mjs|class PySplashXSplash",
    "src\web\static\pysplashx-splash.css|position: fixed",
    "src\web\server.py|def _send_media_bytes",
    "vendor\NODETHERMX_LICENSE.txt|NodeThermX 0.3.0 Build 3",
    "src\web_main.py|create_server",
    "launchers\windows\Bundle File Tool.vbs|pythonw.exe",
    "launchers\windows\Bundle File Tool Web.vbs|web_main.py",
    "launchers\macos\Bundle File Tool.app\Contents\Info.plist|CFBundleExecutable",
    "launchers\macos\Bundle File Tool Web.app\Contents\Info.plist|bft-web",
    "src\ui\text_viewer.py|class TextFileViewer",
    "tests\unit\test_logging.py|test_log_file_created_on_first_event",
    "tests\unit\test_pythermx_tk_integration.py|test_no_cancel_dialog_maps_a_full_progress_canvas",
    "tests\unit\test_ui_public_surface.py|test_native_ui_contains_no_public_placeholder_messages"
)
foreach ($marker in $markers) {
    $markerText = ($marker -split "\|", 2)[1]
    if ($markerText.Contains('"') -or $markerText.Contains('%')) {
        throw "Batch-unsafe delivery marker: $marker"
    }
}
[System.IO.File]::WriteAllLines(
    (Join-Path $supportRoot "delivery_markers.txt"),
    $markers,
    [System.Text.UTF8Encoding]::new($false)
)

foreach ($topLevel in @($installer, $buildRecord, (Join-Path $projectRoot "INSTALL_BFT.cmd"), (Join-Path $projectRoot "INSTALL_BFT.command"))) {
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

Write-Host "Build 136 delivery: $zipPath"
Write-Host "SHA256 sidecar  : $sidecarPath"
Write-Host "BFT files      : $($manifestLines.Count)"
Write-Host "Integration    : $($integrationLines.Count)"
