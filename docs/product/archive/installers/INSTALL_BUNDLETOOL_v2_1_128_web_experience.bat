@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ============================================================================
REM INSTALL_BUNDLETOOL_v2_1_128_web_experience.bat
REM Bundle File Tool v2.1 Build 128 -- Web experience.
REM
REM   CHECKS  One renderer-independent bft.check-result.v1 contract covers
REM           planned selections, existing bundles and written artifacts.
REM   SAFETY  Shared service gates block unsafe nesting, transport paths,
REM           checksum mismatches and portable path collisions for every adapter.
REM   WORKFLOW Direct Check selection and Check Bundle actions, default checks
REM           on load and before processing, plus post-write verification.
REM   ACTIONS Findings identify severity, path, explanation and remediation;
REM           affected source paths can be selected or excluded for the session.
REM   PREFS   Per-user automation choices never weaken mandatory hard blockers.
REM   PROGRESS Integrity and verification are distinct phases, preventing silent
REM           checksum/path work behind a progress indicator already at 100%%.
REM   UI      Modern responsive cards, full-path presentation and two supported
REM           skins improve readability without changing the core workflow.
REM   IDENTITY BFT-specific mark and favicon ship as local transparent PNGs.
REM   SKINS   Studio and Midnight persist through authenticated per-user state.
REM   CLI     `check` provides text/JSON parity; `bundle --precheck` is available.
REM   WEB     Bundle and Un-bundle browser workspaces render the shared BFT
REM           progress DTO through NodeThermX 0.3.0 Build 3 Schema 1.1.
REM   THERMX  The governed PyThermX 0.5.3 wheel remains exact for CLI/Tk;
REM           NodeThermX JS/CSS and its MIT notice ship locally for the web UI.
REM   LOCAL   IPv4 loopback only, private session route, mutation token, strict
REM           Host/Origin/Fetch-Site checks, CSP and no third-party resources.
REM   JOBS    Bounded cancellable jobs expose truthful shared progress events.
REM   PATHS   Native selectors bridge browser path privacy; source previews,
REM           activity, inspector and table paths remain readable when long.
REM   TRIAD   CLI, Tkinter and web launch from one governed delivery.
REM   ENVS    Clean .venv311, .venv312 and .venv313 matrix; legacy .venv retired.
REM   PROOF   Zero-failure test gates across Python 3.11, 3.12 and 3.13;
REM           coverage remains above the binding 85 percent floor.
REM
REM SUPERSEDES the Build 106 through 127 kits. The payload is a strict superset,
REM so a tree at 2.1.105 through 2.1.128 may install this directly. The stager
REM requires exactly one delivery zip in Downloads.
REM
REM Installs only through PREP_AND_STAGE_BFT.bat. Team Delivery Standard v2.
REM Pure batch, ASCII, CRLF. Helper block reused byte-identical from the
REM ratified family skeleton, SHA256 380037a32db7480db2067efaaaf515b7ffef4167f803ea39b26fe1ff85a4a454.
REM ============================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "INCOMING=%ROOT%\_bundletool_incoming"
set "SUPPORT=%INCOMING%\_delivery"
set "MANIFEST=%SUPPORT%\delivery_manifest.sha256"
set "MARKERS=%SUPPORT%\delivery_markers.txt"
set "INTEGRATION_MANIFEST=%SUPPORT%\integration_manifest.sha256"
set "INTEGRATIONS=%INCOMING%\_integrations"
set "ROLLBACK=%ROOT%\bft_build128_rollback"
set "ORIGLEDGER=%ROLLBACK%\original_files.txt"
set "NEWLEDGER=%ROLLBACK%\new_files.txt"
set "GOVCONFIG=%ROOT%\bundle_config.json"
set "PLACED=0"
set "PY="
set "PXSTATE=absent"
set "PXVER=unknown"
set "PXENVCOUNT=0"
set "PAYLOADCOUNT=0"
set "INTEGRATIONCOUNT=0"
set "MARKERCOUNT=0"
set "LAYERC=not applied"
set "STARTMODE=%BFT_SETUP_STARTUP_MODE%"
set "STARTMODEEXPLICIT=1"
if not defined STARTMODE set "STARTMODE=restore" & set "STARTMODEEXPLICIT=0"
set "INSTALLDIAG=%BFT_INSTALL_DIAGNOSTIC_LAUNCHER%"
if not defined INSTALLDIAG set "INSTALLDIAG=0"

echo.
echo === Bundle File Tool v2.1 Build 128 -- Web experience ===
echo Project root : %ROOT%
echo Staged from  : %INCOMING%
echo Startup mode : %STARTMODE% ^(set BFT_SETUP_STARTUP_MODE to choose^)
echo Diagnostic   : %INSTALLDIAG% ^(set BFT_INSTALL_DIAGNOSTIC_LAUNCHER=1 to install^)
echo.

if /i "%STARTMODE%"=="restore" goto :startmodeok
if /i "%STARTMODE%"=="normal" goto :startmodeok
if /i "%STARTMODE%"=="maximized" goto :startmodeok
if /i "%STARTMODE%"=="minimized" goto :startmodeok
echo [FAIL] BFT_SETUP_STARTUP_MODE must be restore, normal, maximized, or minimized.
goto :abort
:startmodeok
if not "%INSTALLDIAG%"=="0" if not "%INSTALLDIAG%"=="1" (
    echo [FAIL] BFT_INSTALL_DIAGNOSTIC_LAUNCHER must be 0 or 1.
    goto :abort
)

REM --- root guards ------------------------------------------------------------
for %%Q in ("%ROOT%") do set "ROOTNAME=%%~nxQ"
if /i not "%ROOTNAME%"=="bundle_file_tool_v2" ( echo [FAIL] expected project folder bundle_file_tool_v2; found %ROOTNAME%. & goto :abort )
if not exist "%ROOT%\src\core" ( echo [FAIL] required folder src\core not found. & goto :abort )
if not exist "%ROOT%\src\core\profiles" ( echo [FAIL] required folder src\core\profiles not found. & goto :abort )
if not exist "%ROOT%\src\ui" ( echo [FAIL] required folder src\ui not found. & goto :abort )
if not exist "%ROOT%\src\web" ( echo [FAIL] required folder src\web not found. & goto :abort )
if not exist "%ROOT%\src\web\static" ( echo [FAIL] required folder src\web\static not found. & goto :abort )
if not exist "%ROOT%\tests" ( echo [FAIL] required folder tests not found. & goto :abort )
if not exist "%ROOT%\tests\integration" ( echo [FAIL] required folder tests\integration not found. & goto :abort )
if not exist "%ROOT%\.pyprojectmgr" ( echo [FAIL] required folder .pyprojectmgr not found. & goto :abort )
if not exist "%ROOT%\VERSION.txt" ( echo [FAIL] VERSION.txt not found. & goto :abort )
if not exist "%INCOMING%" ( echo [FAIL] staged payload missing: %INCOMING% & goto :abort )
if not exist "%MANIFEST%" ( echo [FAIL] delivery_manifest.sha256 missing. & goto :abort )
if not exist "%MARKERS%" ( echo [FAIL] delivery_markers.txt missing. & goto :abort )
if not exist "%INTEGRATION_MANIFEST%" ( echo [FAIL] integration_manifest.sha256 missing. & goto :abort )
set "PPMROOT=%PYPROJECTMGR_PROJECT_ROOT%"
if not defined PPMROOT set "PPMROOT=%ROOT%\..\..\pyprojectmgr_project\pyprojectmgrV2"
for %%Q in ("%PPMROOT%") do set "PPMROOT=%%~fQ"
set "CONFIGEDITORROOT=%CONFIGEDITOR_PROJECT_ROOT%"
if not defined CONFIGEDITORROOT set "CONFIGEDITORROOT=%ROOT%\..\..\config_edit_project\config_edit_tool"
for %%Q in ("%CONFIGEDITORROOT%") do set "CONFIGEDITORROOT=%%~fQ"
if not exist "%PPMROOT%\main.py" ( echo [FAIL] PyProjectMgr project root not found: %PPMROOT% & goto :abort )
if not exist "%PPMROOT%\config\config_hub_registry.json" ( echo [FAIL] PyProjectMgr ConfigHub registry not found. & goto :abort )
if not exist "%CONFIGEDITORROOT%\config_edit_hub.py" ( echo [FAIL] ConfigEditor project root not found: %CONFIGEDITORROOT% & goto :abort )
if exist "%ROOT%\.venv" (
    echo [FAIL] legacy .venv is present; Build 128 requires the standardized matrix.
    echo        Close BFT, run this staged migration command, then rerun the installer:
    echo        powershell -ExecutionPolicy Bypass -File "%INCOMING%\scripts\setup_supported_envs.ps1" -TargetProjectRoot "%ROOT%" -PayloadRoot "%INCOMING%" -Recreate
    goto :abort
)
where certutil >nul 2>&1 || ( echo [FAIL] certutil not found. & goto :abort )

REM --- Gate A0: stale-kit guard ----------------------------------------------
echo --- Gate A0: installed-version guard
set "CURVER="
set /p CURVER=<"%ROOT%\VERSION.txt"
if /i "%CURVER%"=="2.1.105" goto :verok
if /i "%CURVER%"=="2.1.106" goto :verok
if /i "%CURVER%"=="2.1.107" goto :verok
if /i "%CURVER%"=="2.1.108" goto :verok
if /i "%CURVER%"=="2.1.109" goto :verok
if /i "%CURVER%"=="2.1.110" goto :verok
if /i "%CURVER%"=="2.1.111" goto :verok
if /i "%CURVER%"=="2.1.112" goto :verok
if /i "%CURVER%"=="2.1.113" goto :verok
if /i "%CURVER%"=="2.1.114" goto :verok
if /i "%CURVER%"=="2.1.115" goto :verok
if /i "%CURVER%"=="2.1.116" goto :verok
if /i "%CURVER%"=="2.1.117" goto :verok
if /i "%CURVER%"=="2.1.118" goto :verok
if /i "%CURVER%"=="2.1.119" goto :verok
if /i "%CURVER%"=="2.1.120" goto :verok
if /i "%CURVER%"=="2.1.121" goto :verok
if /i "%CURVER%"=="2.1.122" goto :verok
if /i "%CURVER%"=="2.1.123" goto :verok
if /i "%CURVER%"=="2.1.124" goto :verok
if /i "%CURVER%"=="2.1.125" goto :verok
if /i "%CURVER%"=="2.1.126" goto :verok
if /i "%CURVER%"=="2.1.128" goto :verok
echo [FAIL] unexpected installed version in VERSION.txt: "%CURVER%"
echo        this kit installs 2.1.128 over 2.1.105 through 2.1.128 only.
goto :abort
:verok
echo   ok: installed version %CURVER%

REM --- Gate A: verify every staged byte before target mutation ----------------
echo --- Gate A: staged payload verification
for /f "usebackq tokens=1,*" %%H in ("%MANIFEST%") do (
    call :hashVerify "%INCOMING%\%%I" "%%H"
    if errorlevel 1 goto :abort
    set /a PAYLOADCOUNT+=1
)
echo   ok: !PAYLOADCOUNT! payload files verified
for /f "usebackq tokens=1,2,*" %%H in ("%INTEGRATION_MANIFEST%") do (
    call :resolveIntegration "%%I" "%%J"
    if errorlevel 1 goto :abort
    call :hashVerify "!INTSOURCE!" "%%H"
    if errorlevel 1 goto :abort
    set /a INTEGRATIONCOUNT+=1
)
echo   ok: !INTEGRATIONCOUNT! cross-product files verified

REM --- Gate B: reversible backup ---------------------------------------------
echo --- Gate B: pre-mutation backup
if exist "%ROLLBACK%" ( echo [FAIL] pre-existing rollback folder blocks install: %ROLLBACK% & goto :abort )
mkdir "%ROLLBACK%" >nul 2>&1
if errorlevel 1 ( echo [FAIL] could not create rollback folder: %ROLLBACK% & goto :abort )
> "%ORIGLEDGER%" type nul
> "%NEWLEDGER%" type nul
for /f "usebackq tokens=1,*" %%H in ("%MANIFEST%") do (
    if exist "%ROOT%\%%I" (
        call :backup "%ROOT%\%%I" "%ROLLBACK%\%%I"
        if errorlevel 1 goto :abort
        >> "%ORIGLEDGER%" echo %%I
    ) else (
        >> "%NEWLEDGER%" echo %%I
    )
)
for /f "usebackq tokens=1,2,*" %%H in ("%INTEGRATION_MANIFEST%") do (
    call :resolveIntegration "%%I" "%%J"
    if errorlevel 1 goto :abort
    if exist "!INTTARGET!" (
        call :backup "!INTTARGET!" "%ROLLBACK%\_integrations\%%I\%%J"
        if errorlevel 1 goto :abort
        >> "%ORIGLEDGER%" echo @%%I\%%J
    ) else (
        >> "%NEWLEDGER%" echo @%%I\%%J
    )
)
if exist "%ROLLBACK%\bundle_config.json" attrib -R "%ROLLBACK%\bundle_config.json" >nul 2>&1
echo   ok: backup and recovery ledgers created

REM --- Gate C0: clear write protection before placement -----------------------
echo --- Gate C0: clear config write protection
if exist "%GOVCONFIG%" (
    attrib -R "%GOVCONFIG%" >nul 2>&1
    echo   ok: read-only attribute cleared for placement
) else (
    echo   ok: no existing governed config to unprotect
)

REM --- Gate C: place complete files ------------------------------------------
echo --- Gate C: placement
set "PLACED=1"
for /f "usebackq tokens=1,*" %%H in ("%MANIFEST%") do (
    call :placeResilient "%INCOMING%\%%I" "%ROOT%\%%I"
    if errorlevel 1 goto :abort
)
echo   ok: !PAYLOADCOUNT! files placed
for /f "usebackq tokens=1,2,*" %%H in ("%INTEGRATION_MANIFEST%") do (
    call :resolveIntegration "%%I" "%%J"
    if errorlevel 1 goto :abort
    call :placeResilient "!INTSOURCE!" "!INTTARGET!"
    if errorlevel 1 goto :abort
)
echo   ok: !INTEGRATIONCOUNT! cross-product files placed

REM --- Gate C2: retire superseded wheels --------------------------------------
echo --- Gate C2: retire superseded wheels
set "RETIRED=0"
for %%W in ("%ROOT%\vendor\pythermx-*.whl") do (
    if /i not "%%~nxW"=="pythermx-0.5.3-py3-none-any.whl" (
        del /q "%%~fW"
        if exist "%%~fW" ( echo [FAIL] could not remove superseded wheel: %%~nxW & goto :abort )
        set /a RETIRED+=1
        echo   ok: removed superseded wheel %%~nxW
    )
)
if "!RETIRED!"=="0" echo   ok: no superseded wheel present

REM --- Gate D: installed hashes and content markers --------------------------
echo --- Gate D: post-placement verification
for /f "usebackq tokens=1,*" %%H in ("%MANIFEST%") do (
    call :hashVerify "%ROOT%\%%I" "%%H"
    if errorlevel 1 goto :abort
)
for /f "usebackq tokens=1,2,*" %%H in ("%INTEGRATION_MANIFEST%") do (
    call :resolveIntegration "%%I" "%%J"
    if errorlevel 1 goto :abort
    call :hashVerify "!INTTARGET!" "%%H"
    if errorlevel 1 goto :abort
)
for /f "usebackq tokens=1,* delims=|" %%A in ("%MARKERS%") do (
    call :grepHas "%ROOT%\%%A" "%%B"
    if errorlevel 1 goto :abort
    set /a MARKERCOUNT+=1
)
echo   ok: installed hashes and content markers verified

REM --- Gate D2: the optional progress dependency ------------------------------
echo --- Gate D2: PyThermX (optional)
call :installProgressDep
if errorlevel 1 goto :abort

REM --- Gate D3: the wheel states its own identity -----------------------------
REM 0.5.0 added `python -m pythermx --version` for exactly this: a staged
REM install where Scripts is not on PATH still has an importable package, and
REM the version comes from __version__ rather than install-time metadata.
echo --- Gate D3: PyThermX identity
if /i "!PXSTATE!"=="installed" (
    set "PXVER=0.5.3"
    for %%E in (.venv311 .venv312 .venv313) do if exist "%ROOT%\%%E\Scripts\python.exe" (
        set "ENV_PXVER="
        for /f "delims=" %%V in ('"%ROOT%\%%E\Scripts\python.exe" -m pythermx --version 2^>nul') do set "ENV_PXVER=%%V"
        echo   %%E reported: !ENV_PXVER!
        if /i not "!ENV_PXVER!"=="0.5.3" ( echo [FAIL] expected PyThermX 0.5.3 in %%E, got "!ENV_PXVER!". & goto :abort )
    )
    echo   ok: PyThermX identity confirmed in !PXENVCOUNT! supported environment^(s^)
) else (
    echo   skipped: PyThermX was not installed
)

REM --- Gate C3: apply Layer C write protection --------------------------------
echo --- Gate C3: apply config write protection
if not exist "%GOVCONFIG%" ( echo [FAIL] governed config missing after placement. & goto :abort )
attrib +R "%GOVCONFIG%" >nul 2>&1
call :isReadOnly "%GOVCONFIG%"
if errorlevel 1 ( echo [FAIL] could not apply read-only attribute to the governed config. & goto :abort )
set "LAYERC=applied"
echo   ok: governed configuration is write-protected

REM --- Gate E: acceptance ----------------------------------------------------
echo --- Gate E: acceptance
if exist "%ROOT%\.venv311\Scripts\python.exe" set "PY=%ROOT%\.venv311\Scripts\python.exe"
if not defined PY if exist "%ROOT%\.venv312\Scripts\python.exe" set "PY=%ROOT%\.venv312\Scripts\python.exe"
if not defined PY if exist "%ROOT%\.venv313\Scripts\python.exe" set "PY=%ROOT%\.venv313\Scripts\python.exe"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where py 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY ( echo [FAIL] no Python interpreter found; create .venv311, .venv312, or .venv313. & goto :abort )
echo   interpreter: !PY!
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHONPATH=%ROOT%\src"
pushd "%ROOT%"
"!PY!" -c "from core.user_state import UserStateStore as U; s=U(); change=(not s.state_file.exists()) or bool(int('%STARTMODEEXPLICIT%')); s.set('startup_mode','%STARTMODE%') if change else None; s.save() if change else None; print('   startup    : '+s.startup_mode())"
if errorlevel 1 ( popd & echo [FAIL] could not seed the per-user startup preference. & goto :abort )
"!PY!" -c "import sys; v=sys.version_info; print('   version    : '+str(v[0])+'.'+str(v[1])); sys.exit(0 if (3,11) <= (v[0],v[1]) < (3,14) else 1)"
if errorlevel 1 ( popd & echo [FAIL] the project requires Python 3.11, 3.12, or 3.13. & goto :abort )
"!PY!" -c "import pytest, coverage; print('   pytest '+pytest.__version__+' coverage '+coverage.__version__)"
if errorlevel 1 ( popd & echo [FAIL] the interpreter cannot import pytest and coverage. & goto :abort )
"!PY!" -m compileall -q src tests
if errorlevel 1 ( popd & echo [FAIL] byte-compile gate failed. & goto :abort )
"!PY!" "%ROOT%\src\cli.py" --version
if errorlevel 1 ( popd & echo [FAIL] bundle-tool --version did not run successfully. & goto :abort )
"!PY!" -c "from core.version import __version__; actual='bundle-tool '+__version__; print('   BFT version : '+actual); raise SystemExit(0 if actual=='bundle-tool 2.1.128' else 1)"
if errorlevel 1 ( popd & echo [FAIL] expected bundle-tool 2.1.128. & goto :abort )
"!PY!" -c "from core.cancellation import OperationCancelled, is_cancelled; print('   cancel     : contract importable')"
if errorlevel 1 ( popd & echo [FAIL] the cancellation contract does not import. & goto :abort )
"!PY!" -c "from core.selection import SelectionEngine, Layer, State; from core.detectors import classify_directory; print('   selection  : WP1 ladder and WP2 detectors importable')"
if errorlevel 1 ( popd & echo [FAIL] the selection core does not import. & goto :abort )
"!PY!" -c "from core.service import BundleToolService as S; from core.metadata_scan import scan_metadata; from core.rule_sources import available_presets; print('   planning   : WP3 facade importable, '+str(len(available_presets()))+' presets')"
if errorlevel 1 ( popd & echo [FAIL] the WP3 planning facade does not import. & goto :abort )
"!PY!" -c "from cli import build_parser; from core.parser import BundleParser as P; a=build_parser().parse_args(['validate','probe.txt','--encoding','cp1252']); assert P.BUNDLE_TEXT_ENCODING=='utf-8-sig' and a.encoding=='cp1252'; print('   ingress    : strict shared decoder and encoding override importable')"
if errorlevel 1 ( popd & echo [FAIL] the governed transport ingress contract does not import. & goto :abort )
"!PY!" -c "from ui.config_hub_launcher import launch_bft_config_hub; from core.config_setup import validate_document; print('   settings   : ConfigHub launcher and setup hook importable')"
if errorlevel 1 ( popd & echo [FAIL] the Build 124 ConfigHub Settings contract does not import. & goto :abort )
"!PY!" -c "from cli_progress import PyThermXReporter, settle_cancellation; from ui.tk_progress import TkProgressReporter; assert hasattr(PyThermXReporter,'failed'); print('   progress   : message, terminal and cancellation adapters importable')"
if errorlevel 1 ( popd & echo [FAIL] the Build 124 PyThermX protocol repair does not import. & goto :abort )
"!PY!" -c "from ui.window_placement import monitor_work_area_for_widget, place_toplevel_on_parent_monitor; print('   display    : invoking-monitor placement contract importable')"
if errorlevel 1 ( popd & echo [FAIL] the Build 124 multi-display placement contract does not import. & goto :abort )
"!PY!" -c "from ui.log_viewer import LogViewer; from ui.text_viewer import TextFileViewer; print('   public UI  : documentation and log viewers importable')"
if errorlevel 1 ( popd & echo [FAIL] the Build 124 public UI contract does not import. & goto :abort )
"!PY!" -c "from ui.workspace_model import WorkspaceModel, TriState; from ui.selection_workspace import SelectionWorkspaceFrame; from ui.rule_editor import RuleEditorPreview; print('   workspace  : WP4 selection workspace importable')"
if errorlevel 1 ( popd & echo [FAIL] the WP4 selection workspace does not import. & goto :abort )
"!PY!" -c "from core.checking import CHECK_RESULT_SCHEMA; from ui.check_results import CheckResultsDialog; from ui.check_preferences import CheckPreferencesDialog; from cli import build_parser; a=build_parser().parse_args(['check','probe.txt','--format','json']); assert CHECK_RESULT_SCHEMA=='bft.check-result.v1' and a.command=='check'; print('   checking   : shared result, Tk surfaces and CLI command importable')"
if errorlevel 1 ( popd & echo [FAIL] the Build 125 integrity-check contract does not import. & goto :abort )
"!PY!" -c "from core.user_state import UserStateStore as U; from web.server import LOOPBACK_HOST, create_server; from web.adapter import WebAdapter; from web.jobs import JobManager; assert LOOPBACK_HOST=='127.0.0.1' and U.DEFAULTS['web_skin']=='studio'; print('   web        : loopback adapter, jobs, skins and security shell importable')"
if errorlevel 1 ( popd & echo [FAIL] the local web contract does not import. & goto :abort )
"!PY!" -c "from pathlib import Path; import hashlib; p=Path('src/web/static'); a={'nodethermx-web.js':'10f654b2dc936a8b99394629b1e1dbb122dbb7ab7038dedd8eab786ba434cb62','nodethermx-web.css':'8d1b844c32c328b4a830fb668d17a515d270febded626e2a3ff237b1dcc933ff'}; assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in a.items()); print('   NodeThermX : 0.3.0 Build 3 browser assets verified')"
if errorlevel 1 ( popd & echo [FAIL] the Build 128 NodeThermX assets do not match the governed release. & goto :abort )
"!PY!" "%ROOT%\src\cli.py" plan --list-presets >nul
if errorlevel 1 ( popd & echo [FAIL] the plan command does not run. & goto :abort )
"!PY!" -c "from core.config import ConfigManager as C; f=C().check_config_integrity(); print('   integrity  : '+('OK' if f is None else 'MISMATCH')); raise SystemExit(0 if f is None else 1)"
if errorlevel 1 ( popd & echo [FAIL] the installed configuration does not match its recorded digest. & goto :abort )
echo   --- running the binding whole-suite gate ...
"!PY!" -m pytest -p no:cacheprovider
if errorlevel 1 ( popd & echo [FAIL] whole-suite acceptance gate failed. & goto :abort )
popd
echo   ok: whole suite and coverage gate passed

REM --- Gate F: cross-product ConfigHub acceptance -----------------------------
echo --- Gate F: cross-product ConfigHub acceptance
set "PPMPY="
if exist "%PPMROOT%\.venv311\Scripts\python.exe" set "PPMPY=%PPMROOT%\.venv311\Scripts\python.exe"
if not defined PPMPY if exist "%PPMROOT%\.venv\Scripts\python.exe" set "PPMPY=%PPMROOT%\.venv\Scripts\python.exe"
if not defined PPMPY if exist "%PPMROOT%\.venv312\Scripts\python.exe" set "PPMPY=%PPMROOT%\.venv312\Scripts\python.exe"
if not defined PPMPY if exist "%PPMROOT%\.venv313\Scripts\python.exe" set "PPMPY=%PPMROOT%\.venv313\Scripts\python.exe"
if not defined PPMPY ( echo [FAIL] no PyProjectMgr Python environment found for ConfigHub acceptance. & goto :abort )
set "PYTHONPATH=%PPMROOT%\src"
pushd "%PPMROOT%"
"!PPMPY!" -m pytest -o addopts="" -q tests\configuration_hub\test_pythermx_vertical_slice.py tests\configuration_hub\test_config_hub_real_tk.py
if errorlevel 1 ( popd & echo [FAIL] PyProjectMgr ConfigHub contract tests failed. & goto :abort )
popd
set "PYTHONPATH=%PPMROOT%\src;%CONFIGEDITORROOT%"
pushd "%CONFIGEDITORROOT%"
"!PPMPY!" -m pytest -o addopts="" -q tests\test_config_edit_hub.py
if errorlevel 1 ( popd & echo [FAIL] ConfigEditor invocation and placement tests failed. & goto :abort )
popd
set "PYTHONPATH=%ROOT%\src"
echo   ok: requester identity and invoking-monitor contracts passed

REM --- Gate G: desktop launch experience ------------------------------------
echo --- Gate G: desktop launchers
call :installLaunchers
if errorlevel 1 goto :abort
echo   ok: native and web no-console launchers installed
if "%INSTALLDIAG%"=="1" echo   ok: diagnostic console launcher installed

REM --- success-only teardown -------------------------------------------------
echo --- teardown
rd /s /q "%ROLLBACK%"
if exist "%ROLLBACK%" ( echo [FAIL] could not remove successful rollback folder. & goto :abort )
rd /s /q "%INCOMING%"
if exist "%INCOMING%" ( echo [FAIL] could not remove successful staged payload. & goto :abort )

echo.
echo ============================================================================
echo  Bundle File Tool v2.1 Build 128 installed and verified.
echo    Gate A  staged SHA256          -- PASS  !PAYLOADCOUNT! files
echo    Gate C0 protection cleared     -- PASS
echo    Gate D  installed SHA256       -- PASS  !PAYLOADCOUNT! files
echo    Gate D  integration SHA256     -- PASS  !INTEGRATIONCOUNT! files
echo    Gate D  content markers        -- PASS  !MARKERCOUNT! markers
echo    Gate D2 PyThermX               -- !PXSTATE! in !PXENVCOUNT! environment^(s^)
echo    Gate D3 PyThermX identity      -- !PXVER!
echo    Gate C3 config write-protect   -- !LAYERC!
echo    Gate E  config integrity       -- PASS
echo    Gate E  WP3 planning facade    -- PASS
echo    Gate E  whole suite            -- PASS  zero failures
echo    Gate E  coverage gate          -- PASS  at or above the 85 percent floor
echo    Gate F  cross-product setup    -- PASS
echo    Gate G  native/web launchers   -- PASS
echo.
echo  You can now see a selection before committing to it:
echo.
echo      bundle-tool plan .
echo      bundle-tool plan . --explain path/to/file.py
echo      bundle-tool plan . --preset python-env --preset vcs --report plan.json
echo      bundle-tool check project_bundle.txt --format json
echo.
echo  Nothing is read during planning, so a plan is cheap to run and safe to
echo  run first. The same flags work on `bundle`, and the two commands share
echo  one selection path so the preview and the artifact cannot disagree.
echo.
echo  NOTE: --exclude now ADDS to the default rules instead of replacing them.
echo        Pass --no-default-rules for the previous behaviour.
echo.
echo  Build record: built_build128.md
echo  Integration: docs\implementation\BFT_BUILD128_WEB_EXPERIENCE_2026-09-04.md
echo ============================================================================
endlocal
exit /b 0

:abort
echo.
echo *** BUILD 128 INSTALLATION ABORTED ***
if exist "%GOVCONFIG%" (
    attrib +R "%GOVCONFIG%" >nul 2>&1
    echo Governed configuration left write-protected.
)
if "%PLACED%"=="1" (
    echo Files may have been placed. Recovery material is retained:
    echo   %ROLLBACK%
    echo   originals replaced: %ORIGLEDGER%
    echo   files newly created: %NEWLEDGER%
    echo   PyProjectMgr root: %PPMROOT%
    echo   ConfigEditor root: %CONFIGEDITORROOT%
    echo   NOTE: clear the read-only attribute on a restored config with
    echo         attrib -R "%ROOT%\bundle_config.json"
) else (
    echo No payload file was placed.
)
if exist "%INCOMING%" echo Staged payload retained: %INCOMING%
endlocal
exit /b 1

REM --- Build 128 delivery logic (not part of the frozen helper family) --------
:installLaunchers
if not exist "%ROOT%\launchers\windows\Bundle File Tool.vbs" ( echo [FAIL] normal launcher missing. & exit /b 1 )
if not exist "%ROOT%\launchers\windows\Bundle File Tool Web.vbs" ( echo [FAIL] web launcher missing. & exit /b 1 )
if not exist "%ROOT%\launchers\windows\Bundle File Tool Diagnostic.cmd" ( echo [FAIL] diagnostic launcher missing. & exit /b 1 )
set "BFT_SHORTCUT_ROOT=%ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=$env:BFT_SHORTCUT_ROOT; $d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([IO.Path]::Combine($d,'Bundle File Tool.lnk')); $s.TargetPath=[IO.Path]::Combine($env:SystemRoot,'System32','wscript.exe'); $s.Arguments=[char]34+[IO.Path]::Combine($r,'launchers','windows','Bundle File Tool.vbs')+[char]34; $s.WorkingDirectory=$r; $s.Description='Bundle File Tool - normal no-console launch'; $s.Save()"
if errorlevel 1 ( echo [FAIL] could not create the normal desktop shortcut. & exit /b 1 )
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=$env:BFT_SHORTCUT_ROOT; $d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([IO.Path]::Combine($d,'Bundle File Tool Web.lnk')); $s.TargetPath=[IO.Path]::Combine($env:SystemRoot,'System32','wscript.exe'); $s.Arguments=[char]34+[IO.Path]::Combine($r,'launchers','windows','Bundle File Tool Web.vbs')+[char]34; $s.WorkingDirectory=$r; $s.Description='Bundle File Tool - local web workspace'; $s.Save()"
if errorlevel 1 ( echo [FAIL] could not create the web desktop shortcut. & exit /b 1 )
if "%INSTALLDIAG%"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=$env:BFT_SHORTCUT_ROOT; $d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut([IO.Path]::Combine($d,'Bundle File Tool Diagnostic.lnk')); $s.TargetPath=[IO.Path]::Combine($r,'launchers','windows','Bundle File Tool Diagnostic.cmd'); $s.WorkingDirectory=$r; $s.Description='Bundle File Tool - diagnostic console launch'; $s.Save()"
    if errorlevel 1 ( echo [FAIL] could not create the diagnostic desktop shortcut. & exit /b 1 )
)
exit /b 0

:resolveIntegration
set "INTSOURCE="
set "INTTARGET="
if /i "%~1"=="ppm" (
    set "INTSOURCE=%INTEGRATIONS%\pyprojectmgr\%~2"
    set "INTTARGET=%PPMROOT%\%~2"
)
if /i "%~1"=="configeditor" (
    set "INTSOURCE=%INTEGRATIONS%\configeditor\%~2"
    set "INTTARGET=%CONFIGEDITORROOT%\%~2"
)
if not defined INTSOURCE ( echo [FAIL] unknown integration target key: %~1 & exit /b 1 )
if not exist "!INTSOURCE!" ( echo [FAIL] integration source missing: !INTSOURCE! & exit /b 1 )
exit /b 0

:placeResilient
REM Windows can return ERROR_USER_MAPPED_FILE after the destination already
REM contains the requested bytes (for example, a scanner briefly maps a .py
REM file). Retry three times. A nonzero copy result is accepted only when the
REM destination SHA256 equals the staged source; every other case fails closed.
if not exist "%~1" ( echo [FAIL] staged source missing: %~1 & exit /b 1 )
for %%D in ("%~2") do if not exist "%%~dpD" mkdir "%%~dpD" >nul 2>&1
for %%D in ("%~2") do if not exist "%%~dpD" ( echo [FAIL] could not create target parent: %%~dpD & exit /b 1 )
set "PLACE_EXPECTED="
for /f "tokens=*" %%X in ('certutil -hashfile "%~1" SHA256 ^| findstr /r /i /c:"^[0-9a-f][0-9a-f]*$"') do if not defined PLACE_EXPECTED set "PLACE_EXPECTED=%%X"
set "PLACE_EXPECTED=!PLACE_EXPECTED: =!"
if not defined PLACE_EXPECTED ( echo [FAIL] could not calculate staged SHA256: %~1 & exit /b 1 )
for /l %%R in (1,1,3) do (
    copy /y "%~1" "%~2" >nul
    if not errorlevel 1 exit /b 0
    call :hashVerify "%~2" "!PLACE_EXPECTED!" >nul 2>&1
    if not errorlevel 1 (
        echo   [WARN] copy returned nonzero after destination bytes matched; continuing: %~2
        exit /b 0
    )
    if not %%R==3 ping 127.0.0.1 -n 2 >nul
)
echo [FAIL] copy failed after 3 attempts: %~1 -^> %~2
exit /b 1

:installProgressDep
set "PXSTATE=absent"
set "PXENVCOUNT=0"
for %%E in (.venv311 .venv312 .venv313) do if exist "%ROOT%\%%E\Scripts\python.exe" (
    echo   installing PyThermX 0.5.3 into %%E
    "%ROOT%\%%E\Scripts\python.exe" -m pip install --no-index --no-deps --quiet --force-reinstall "%ROOT%\vendor\pythermx-0.5.3-py3-none-any.whl"
    if errorlevel 1 ( echo [FAIL] PyThermX install failed in %%E. & exit /b 1 )
    set /a PXENVCOUNT+=1
)
if "!PXENVCOUNT!"=="0" (
    echo   [WARN] no supported virtual environment found; skipping the optional PyThermX install.
    echo          the CLI will run without a progress bar, and without cancel.
    exit /b 0
)
set "PXSTATE=installed"
echo   ok: PyThermX 0.5.3 installed from the in-kit wheel into !PXENVCOUNT! environment^(s^)
exit /b 0

:isReadOnly
REM Reads the file attribute string directly rather than parsing attrib output:
REM the R flag is not in a fixed token there, which is how the first draft of
REM this gate failed against a correctly protected file.
set "FATTR="
for %%F in ("%~1") do set "FATTR=%%~aF"
if not defined FATTR exit /b 1
if /i "!FATTR:~1,1!"=="r" exit /b 0
exit /b 1

REM === BEGIN FAMILY DELIVERY HELPERS v2.0 - HASHED INCLUSIVE ===
:hashVerify
if not exist "%~1" ( echo [FAIL] missing file for hash: %~1 & exit /b 1 )
set "ACTUAL="
for /f "tokens=*" %%X in ('certutil -hashfile "%~1" SHA256 ^| findstr /r /i /c:"^[0-9a-f][0-9a-f]*$"') do if not defined ACTUAL set "ACTUAL=%%X"
set "ACTUAL=%ACTUAL: =%"
if not defined ACTUAL ( echo [FAIL] could not calculate SHA256: %~1 & exit /b 1 )
if /i not "%ACTUAL%"=="%~2" ( echo [FAIL] SHA256 mismatch: %~1 & echo expected %~2 & echo actual   %ACTUAL% & exit /b 1 )
exit /b 0

:backup
if not exist "%~1" ( echo [FAIL] backup source missing: %~1 & exit /b 1 )
if exist "%~2" ( echo [FAIL] backup destination already exists: %~2 & exit /b 1 )
set "BACKUP_ACTUAL="
for /f "tokens=*" %%X in ('certutil -hashfile "%~1" SHA256 ^| findstr /r /i /c:"^[0-9a-f][0-9a-f]*$"') do if not defined BACKUP_ACTUAL set "BACKUP_ACTUAL=%%X"
set "BACKUP_ACTUAL=%BACKUP_ACTUAL: =%"
if not defined BACKUP_ACTUAL ( echo [FAIL] could not calculate backup-source SHA256: %~1 & exit /b 1 )
for %%D in ("%~2") do if not exist "%%~dpD" mkdir "%%~dpD" >nul 2>&1
for %%D in ("%~2") do if not exist "%%~dpD" ( echo [FAIL] could not create backup parent: %%~dpD & exit /b 1 )
copy /y "%~1" "%~2" >nul
if errorlevel 1 ( echo [FAIL] backup copy failed: %~1 -^> %~2 & exit /b 1 )
call :hashVerify "%~2" "%BACKUP_ACTUAL%"
if errorlevel 1 ( echo [FAIL] backup byte verification failed: %~2 & exit /b 1 )
exit /b 0

:place
if not exist "%~1" ( echo [FAIL] staged source missing: %~1 & exit /b 1 )
for %%D in ("%~2") do if not exist "%%~dpD" mkdir "%%~dpD" >nul 2>&1
for %%D in ("%~2") do if not exist "%%~dpD" ( echo [FAIL] could not create target parent: %%~dpD & exit /b 1 )
copy /y "%~1" "%~2" >nul
if errorlevel 1 ( echo [FAIL] copy failed: %~1 -^> %~2 & exit /b 1 )
if not exist "%~2" ( echo [FAIL] target missing after copy: %~2 & exit /b 1 )
exit /b 0

:grepHas
if not exist "%~1" ( echo [FAIL] marker target missing: %~1 & exit /b 1 )
findstr /l /c:"%~2" "%~1" >nul
if errorlevel 1 ( echo [FAIL] content marker missing in %~1 & exit /b 1 )
exit /b 0
REM === END FAMILY DELIVERY HELPERS v2.0 - HASHED INCLUSIVE ===
