@echo off
setlocal EnableDelayedExpansion

echo ==============================================================================
echo [BFT DEPLOYMENT BUNDLER] Packaging Outgoing Code Folders to Target Archive
echo ==============================================================================

:: -----------------------------------------------------------------------------
:: 1. Configuration & Path Resolution
:: -----------------------------------------------------------------------------
:: Argument 1 override: Source Project (defaults to bundle_file_tool_v2)
set "SRC_PROJECT=%~1"
if "%SRC_PROJECT%"=="" (
    set "SRC_PROJECT=C:\Users\mpw\Python\bundle_file_project\bundle_file_tool_v2"
)

:: Argument 2 override: Destination Directory (defaults to bundles root)
set "DEST_DIR=%~2"
if "%DEST_DIR%"=="" (
    set "DEST_DIR=C:\Users\mpw\Python\bundles"
)

:: Profile & Output File Naming
set "PROFILE=plain_marker"
for %%I in ("%SRC_PROJECT%") do set "PROJ_NAME=%%~nxI"
set "SAFE_NAME=!PROJ_NAME: =_!"
set "BUNDLE_OUT=%DEST_DIR%\!SAFE_NAME!_src_bundle.txt"
set "MANIFEST_FILE=%DEST_DIR%\!SAFE_NAME!_delivery_manifest.sha256"
set "MARKERS_FILE=%DEST_DIR%\!SAFE_NAME!_delivery_markers.txt"

:: Environment setup
set "PYTHONPATH=%SRC_PROJECT%\src;!PYTHONPATH!"

echo [CONFIG] Source Project: "%SRC_PROJECT%"
echo [CONFIG] Destination   : "%DEST_DIR%"
echo [CONFIG] Bundle Target : "%BUNDLE_OUT%"
echo.

:: -----------------------------------------------------------------------------
:: 2. Preflight Existence Verification
:: -----------------------------------------------------------------------------
if not exist "%SRC_PROJECT%" (
    echo [ERROR] Source project directory not found: "%SRC_PROJECT%"
    exit /b 1
)

if not exist "%SRC_PROJECT%\src" (
    echo [ERROR] Mandatory 'src' folder missing in: "%SRC_PROJECT%"
    exit /b 1
)

if not exist "%DEST_DIR%" (
    echo [SETUP] Creating destination directory: "%DEST_DIR%"
    mkdir "%DEST_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create destination folder: "%DEST_DIR%"
        exit /b 1
    )
)

:: Detect Folders to Bundle
set "FOLDERS_TO_BUNDLE="%SRC_PROJECT%\src""
if exist "%SRC_PROJECT%\tests" (
    set "FOLDERS_TO_BUNDLE=!FOLDERS_TO_BUNDLE! "%SRC_PROJECT%\tests""
)

:: -----------------------------------------------------------------------------
:: 3. Step 1: Execute BFT Bundle Operation
:: -----------------------------------------------------------------------------
echo [STEP 1/4] Generating Source Bundle via BFT CLI...
python "%SRC_PROJECT%\src\cli.py" bundle !FOLDERS_TO_BUNDLE! -o "%BUNDLE_OUT%" --base-path "%SRC_PROJECT%" --profile %PROFILE%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] BFT bundling operation failed.
    exit /b 1
)
echo   -- Successfully created: "%BUNDLE_OUT%"

:: -----------------------------------------------------------------------------
:: 4. Step 2: Validate Generated Bundle
:: -----------------------------------------------------------------------------
echo [STEP 2/4] Validating Bundle Structure and Marker Integrity...
python "%SRC_PROJECT%\src\cli.py" validate "%BUNDLE_OUT%" --profile %PROFILE%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Generated bundle failed validation integrity checks.
    exit /b 1
)
echo   -- Bundle validation passed cleanly.

:: -----------------------------------------------------------------------------
:: 5. Step 3: Generate Structural Delivery Marker
:: -----------------------------------------------------------------------------
echo [STEP 3/4] Stamping Delivery Markers...
echo !SAFE_NAME!_src_bundle.txt^|# BUNDLE MANIFEST> "%MARKERS_FILE%"
if exist "%SRC_PROJECT%\src\core\version.py" (
    echo src\core\version.py^|__version__>> "%MARKERS_FILE%"
)
echo   -- Delivery markers written: "%MARKERS_FILE%"

:: -----------------------------------------------------------------------------
:: 6. Step 4: Compute Authoritative SHA-256 Hash
:: -----------------------------------------------------------------------------
echo [STEP 4/4] Computing Cryptographic SHA-256 Digest...
if exist "%MANIFEST_FILE%" del "%MANIFEST_FILE%"
for /f "tokens=1" %%H in ('certutil -hashfile "%BUNDLE_OUT%" SHA256 ^| findstr /r "^[0-9a-fA-F]*$"') do (
    echo %%H  !SAFE_NAME!_src_bundle.txt> "%MANIFEST_FILE%"
    echo   -- SHA-256: %%H
)
echo   -- Manifest written: "%MANIFEST_FILE%"

echo.
echo ==============================================================================
echo [SUCCESS] Project bundled, validated, and exported cleanly to:
echo           "%DEST_DIR%"
echo ==============================================================================
exit /b 0