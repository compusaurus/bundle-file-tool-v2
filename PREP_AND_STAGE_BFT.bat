@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ============================================================================
REM  PREP_AND_STAGE_BFT.bat  --  pre-install snapshot + stage for bundle_file_tool v2 deliveries
REM  Adapted from PREP_AND_STAGE_EDSS.bat for the Python bundle_file_tool project.
REM
REM  FLOW (snapshot-before-mutate order is a hard dependency):
REM    1. Preflight  : project root (src\core, src\ui, tests), archives folder, 7z.exe,
REM                    exactly one delivery zip plus its verified SHA256 sidecar in Downloads,
REM                    and no stale _bundletool_incoming.
REM    2. Read vers. : Major.Minor.Build from VERSION.txt (the OUTGOING build). Fail loud if unparseable.
REM    3. Confirm    : show the plan; Y to proceed  (skip with /y).
REM    4. Snapshot   : robocopy live tree to an atomic .partial candidate, then promote it to
REM                    ..\BFTv2_v{ver} Build {build}. Exclude every supported venv, generated
REM                    output/cache tree, Git metadata, and all junctions.
REM    5. Archive    : 7-Zip that snapshot to  archives\{snap}.zip  (-tzip), verify non-zero BEFORE any delete.
REM    6. Retention  : HARD DELETE older "BFTv2_v* Build *" snapshot folders, keeping only the one just made.
REM    7. Stage      : clear stale prior INSTALL_BUNDLETOOL_*.bat, extract the single delivery zip into the
REM                    project root; verify one INSTALL_BUNDLETOOL_*.bat and _bundletool_incoming landed.
REM    8. Move pair  : move the verified delivery zip and checksum sidecar into archives together.
REM    9. Chain      : run the installer (default). Suppress with /norun.
REM   10. Verify     : on a successful install, leave VERSION.txt package-owned and unchanged by this stager.
REM
REM  OPTIONS:  /dryrun  print the resolved plan and exit; change nothing.
REM            /y       skip the confirmation prompt.
REM            /norun   prep + stage only; do not chain to the installer.
REM
REM  PLACEMENT: lives in the project root (bundle_file_tool_v2). archives\ is a sibling of the project root.
REM            Downloads is %USERPROFILE%\Downloads. VERSION.txt lives in the project root (seed: 2.0.100).
REM  Pure batch, ASCII, CRLF. OS built-ins + 7z.exe CLI only. No shell, no PowerShell.
REM ============================================================================

REM --- resolve locations from the script's own folder -------------------------
REM  R-DEL-02: this MUST run before :parseargs. `shift` moves %0, so once any
REM  option has been consumed %~dp0 no longer refers to this script and ROOT
REM  resolves to the current drive, aborting on the root guard.
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "SCRIPTNAME=%~nx0"
for %%P in ("%ROOT%") do set "PARENT=%%~dpP"
if "%PARENT:~-1%"=="\" set "PARENT=%PARENT:~0,-1%"
set "ARCHIVES=%PARENT%\archives"
set "DOWNLOADS=%USERPROFILE%\Downloads"
set "VERSIONFILE=%ROOT%\VERSION.txt"
set "DLPAT=INSTALL_BUNDLETOOL_*.zip"

set "DRYRUN=0"
set "SKIPCONFIRM=0"
set "NORUN=0"
:parseargs
if "%~1"=="" goto :endparse
if /i "%~1"=="/dryrun" ( set "DRYRUN=1" & shift & goto :parseargs )
if /i "%~1"=="/y"      ( set "SKIPCONFIRM=1" & shift & goto :parseargs )
if /i "%~1"=="/norun"  ( set "NORUN=1" & shift & goto :parseargs )
echo [FAIL] Unrecognized option: "%~1"
echo Usage: %SCRIPTNAME% [/dryrun] [/y] [/norun]
endlocal
exit /b 1
:endparse


echo.
echo === BFTv2 prep + stage ===
echo Project root : %ROOT%
echo Parent       : %PARENT%
echo Archives     : %ARCHIVES%
echo Downloads    : %DOWNLOADS%
echo.

REM --- Step 1: preflight ------------------------------------------------------
if not exist "%ROOT%\src\core" ( echo [FAIL] %ROOT%\src\core not found. Run from the project root. & goto :abort )
if not exist "%ROOT%\src\ui"   ( echo [FAIL] %ROOT%\src\ui not found. Run from the project root.   & goto :abort )
if not exist "%ROOT%\tests"     ( echo [FAIL] %ROOT%\tests not found. Run from the project root.    & goto :abort )
if not exist "%VERSIONFILE%"     ( echo [FAIL] VERSION.txt not found: %VERSIONFILE% & goto :abort )
if not exist "%ARCHIVES%"        ( echo [FAIL] archives folder not found: %ARCHIVES% & goto :abort )
if exist "%ROOT%\_bundletool_incoming" ( echo [FAIL] _bundletool_incoming exists ^(stale/aborted run^). Resolve it first. & goto :abort )

REM locate the 7-Zip CLI (never the GUI 7zFM.exe)
set "SZ="
where 7z >nul 2>&1 && set "SZ=7z"
if not defined SZ if exist "%ProgramFiles%\7-Zip\7z.exe" set "SZ=%ProgramFiles%\7-Zip\7z.exe"
if not defined SZ if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SZ=%ProgramFiles(x86)%\7-Zip\7z.exe"
if not defined SZ ( echo [FAIL] 7z.exe not found on PATH or in Program Files\7-Zip. & goto :abort )
where certutil >nul 2>&1 || ( echo [FAIL] certutil not found. & goto :abort )

REM exactly one delivery zip in Downloads matching the locked convention
set "ZIPCOUNT=0"
set "DELZIP="
for /f "delims=" %%Z in ('dir /b /a-d "%DOWNLOADS%\%DLPAT%" 2^>nul') do ( set /a ZIPCOUNT+=1 & set "DELZIP=%DOWNLOADS%\%%Z" )
if %ZIPCOUNT% EQU 0 ( echo [FAIL] no delivery zip matching %DLPAT% in Downloads. & goto :abort )
if %ZIPCOUNT% GTR 1 ( echo [FAIL] %ZIPCOUNT% zips match %DLPAT% in Downloads; leave exactly one. & goto :abort )
set "DELSHA=%DELZIP%.sha256"
if not exist "%DELSHA%" ( echo [FAIL] matching checksum sidecar not found: %DELSHA% & goto :abort )
for %%Z in ("%DELZIP%") do set "DELNAME=%%~nxZ"
for %%S in ("%DELSHA%") do set "SHANAME=%%~nxS"
set "DEL_EXPECTED="
set "DEL_RECORDED_NAME="
for /f "usebackq tokens=1,*" %%H in ("%DELSHA%") do if not defined DEL_EXPECTED ( set "DEL_EXPECTED=%%H" & set "DEL_RECORDED_NAME=%%I" )
if not defined DEL_EXPECTED ( echo [FAIL] checksum sidecar is empty or unreadable: %DELSHA% & goto :abort )
if /i not "!DEL_RECORDED_NAME!"=="!DELNAME!" ( echo [FAIL] checksum sidecar names "!DEL_RECORDED_NAME!" but delivery is "!DELNAME!". & goto :abort )
call :hashVerify "%DELZIP%" "!DEL_EXPECTED!"
if errorlevel 1 ( echo [FAIL] delivery zip does not match its checksum sidecar. & goto :abort )

REM --- Step 2: read the OUTGOING version / build from VERSION.txt (Major.Minor.Build) ---
set "VERSTR="
set /p VERSTR=<"%VERSIONFILE%"
set "MAJOR="
set "MINOR="
set "BUILD="
for /f "tokens=1,2,3 delims=." %%a in ("%VERSTR%") do ( set "MAJOR=%%a" & set "MINOR=%%b" & set "BUILD=%%c" )
if not defined MAJOR ( echo [FAIL] could not parse Major from VERSION.txt ^("%VERSTR%"^). & goto :abort )
if not defined MINOR ( echo [FAIL] could not parse Minor from VERSION.txt ^("%VERSTR%"^). & goto :abort )
if not defined BUILD ( echo [FAIL] could not parse Build from VERSION.txt ^("%VERSTR%"^). & goto :abort )
set "VER=%MAJOR%.%MINOR%"
set "SNAPNAME=BFTv2_v%VER% Build %BUILD%"
set "SNAPDIR=%PARENT%\%SNAPNAME%"
set "SNAPWORK=%SNAPDIR%.partial"
set "ROBOLOG=%TEMP%\BFTv2_prep_robocopy_%BUILD%.log"

echo Outgoing     : v%VER% Build %BUILD%  ^(full: %MAJOR%.%MINOR%.%BUILD%^)
echo Snapshot     : %SNAPNAME%
echo Delivery zip : %DELZIP%
echo Checksum     : %DELSHA%  ^(verified^)
echo.

REM --- dry run: plan only, no changes -----------------------------------------
if not "%DRYRUN%"=="1" goto :notdry
echo [DRY RUN] No changes made. Planned actions:
echo   snapshot candidate to : %SNAPWORK%
echo   promote candidate to  : %SNAPDIR%
echo   exclude               : .venv* .git out tmp caches build artifacts logs sessions outputs and junctions
echo   archive to            : %ARCHIVES%\%SNAPNAME%.zip
echo   HARD DELETE older     : "%PARENT%\BFTv2_v* Build *" except the new snapshot
echo   clear stale installer : %ROOT%\INSTALL_BUNDLETOOL_*.bat  (already in the snapshot)
echo   stage delivery into   : %ROOT%
echo   move delivery pair to : %ARCHIVES%
if "%NORUN%"=="0" echo   then run the extracted INSTALL_BUNDLETOOL_*.bat; the package owns VERSION.txt
goto :done
:notdry

REM --- Step 3: confirm --------------------------------------------------------
if "%SKIPCONFIRM%"=="1" goto :afterconfirm
echo This will build and promote a clean snapshot, replace any same-build snapshot only after the
echo candidate succeeds, archive, HARD DELETE older snapshot folders, stage, (unless /norun) run the
echo installer. VERSION.txt is package-owned and is not incremented by this stager.
choice /c YN /n /m "Proceed [Y/N]? "
if errorlevel 2 goto :cancelled
:afterconfirm
echo.

REM --- Step 4: build a clean candidate without following local environments or junctions.
REM     The current same-build snapshot is preserved until the candidate copy succeeds. -----
echo --- snapshot candidate: %SNAPNAME%.partial
if exist "%SNAPWORK%" (
    echo   removing stale partial snapshot candidate
    attrib -R "%SNAPWORK%\*" /S /D >nul 2>&1
    rd /s /q "%SNAPWORK%"
    if exist "%SNAPWORK%" ( echo [FAIL] could not remove stale candidate: %SNAPWORK% & goto :abort )
)
if exist "%ROBOLOG%" del /f /q "%ROBOLOG%" >nul 2>&1
robocopy "%ROOT%" "%SNAPWORK%" /E /XJ /XD "%ROOT%\.venv" "%ROOT%\.venv311" "%ROOT%\.venv312" "%ROOT%\.venv313" "%ROOT%\.git" "%ROOT%\out" "%ROOT%\tmp" "%ROOT%\.ruff_cache" "%ROOT%\.mypy_cache" "%ROOT%\.tox" "%ROOT%\.nox" "%ROOT%\htmlcov" "%ROOT%\build" "%ROOT%\dist" "%ROOT%\logs" "%ROOT%\sessions" "%ROOT%\outputs" __pycache__ .pytest_cache /XF "%ROOT%\.coverage" /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /LOG:"%ROBOLOG%"
set "RRC=%ERRORLEVEL%"
if %RRC% GEQ 8 (
    echo [FAIL] robocopy snapshot failed ^(code %RRC%^). Diagnostic log follows:
    if exist "%ROBOLOG%" type "%ROBOLOG%"
    goto :abort
)
if not exist "%SNAPWORK%" ( echo [FAIL] snapshot candidate folder was not created. & goto :abort )
if exist "%SNAPDIR%" (
    echo   candidate complete; replacing prior same-build snapshot
    attrib -R "%SNAPDIR%\*" /S /D >nul 2>&1
    rd /s /q "%SNAPDIR%"
    if exist "%SNAPDIR%" ( echo [FAIL] could not replace prior snapshot: %SNAPDIR% & goto :abort )
)
move /y "%SNAPWORK%" "%SNAPDIR%" >nul
if errorlevel 1 ( echo [FAIL] could not promote snapshot candidate to: %SNAPDIR% & goto :abort )
if not exist "%SNAPDIR%" ( echo [FAIL] promoted snapshot folder was not created. & goto :abort )
if exist "%ROBOLOG%" del /f /q "%ROBOLOG%" >nul 2>&1
echo   ok

REM --- Step 5: archive the snapshot, then verify ------------------------------
echo --- archive: %SNAPNAME%.zip
pushd "%PARENT%"
"%SZ%" a -tzip "%ARCHIVES%\%SNAPNAME%.zip" "%SNAPNAME%\*" >nul
set "ZRC=%ERRORLEVEL%"
popd
if %ZRC% GEQ 2 ( echo [FAIL] 7-Zip archive failed ^(code %ZRC%^). & goto :abort )
if not exist "%ARCHIVES%\%SNAPNAME%.zip" ( echo [FAIL] archive not created. & goto :abort )
for %%A in ("%ARCHIVES%\%SNAPNAME%.zip") do set "ASZ=%%~zA"
if "%ASZ%"=="" ( echo [FAIL] archive size unreadable. & goto :abort )
if %ASZ% EQU 0 ( echo [FAIL] archive is empty. & goto :abort )
echo   ok: %ASZ% bytes

REM --- Step 6: retention -- keep only the new snapshot; hard-delete older ------
echo --- retention: keep "%SNAPNAME%", remove older snapshot folders
for /d %%D in ("%PARENT%\BFTv2_v* Build *") do (
    if /i not "%%~nxD"=="%SNAPNAME%" (
        echo   removing older: %%~nxD
        rd /s /q "%%~fD"
        if exist "%%~fD" ( echo   [FAIL] could not delete %%~fD & goto :abort )
    )
)

REM --- Step 7: stage the delivery into the project root -----------------------
REM clear any stale installer .bat from a PRIOR delivery first. These are already preserved in the
REM snapshot + verified archive created above, so removing them here is zero-loss.
for /f "delims=" %%B in ('dir /b /a-d "%ROOT%\INSTALL_BUNDLETOOL_*.bat" 2^>nul') do (
    echo   removing stale installer: %%B
    del /f /q "%ROOT%\%%B"
    if exist "%ROOT%\%%B" ( echo [FAIL] could not remove stale installer %%B & goto :abort )
)
echo --- stage: extracting delivery into project root
"%SZ%" x -y -o"%ROOT%" "%DELZIP%" >nul
if errorlevel 2 ( echo [FAIL] extract failed. & goto :abort )
set "ICOUNT=0"
set "INSTALLER="
for /f "delims=" %%B in ('dir /b /a-d "%ROOT%\INSTALL_BUNDLETOOL_*.bat" 2^>nul') do ( set /a ICOUNT+=1 & set "INSTALLER=%ROOT%\%%B" )
if %ICOUNT% EQU 0 ( echo [FAIL] no INSTALL_BUNDLETOOL_*.bat at project root after extract. & goto :abort )
if %ICOUNT% GTR 1 ( echo [FAIL] %ICOUNT% installer .bat files at project root; expected one. & goto :abort )
if not exist "%ROOT%\_bundletool_incoming" ( echo [FAIL] _bundletool_incoming missing after extract. & goto :abort )
echo   ok: %INSTALLER%

REM --- Step 8: move the verified delivery pair into archives ------------------
REM Move the sidecar first. If the ZIP move fails, restore the sidecar so the
REM usable pair remains together in Downloads rather than creating another orphan.
echo --- moving delivery zip and checksum to archives
move /y "%DELSHA%" "%ARCHIVES%\" >nul
if errorlevel 1 ( echo [FAIL] could not move delivery checksum to archives. & goto :abort )
move /y "%DELZIP%" "%ARCHIVES%\" >nul
if errorlevel 1 (
    move /y "%ARCHIVES%\%SHANAME%" "%DOWNLOADS%\" >nul 2>&1
    echo [FAIL] could not move delivery zip to archives; checksum restore attempted.
    goto :abort
)
echo   ok

REM --- Step 9: chain to the installer (default) -------------------------------
echo.
if "%NORUN%"=="1" (
    echo Prep complete. Installer NOT run ^(/norun^).
    echo To install: "%INSTALLER%"
    goto :done
)
echo === Prep complete. Chaining to installer ===
echo %INSTALLER%
echo.
call "%INSTALLER%"
set "IRC=%ERRORLEVEL%"
echo.
if not "%IRC%"=="0" (
    echo === Installer returned %IRC% ^(non-zero^). Investigate the installer output above. ===
    goto :done
)

REM --- Step 10: package-owned version contract ---------------------------------
echo === Delivery complete. VERSION.txt remains package-owned; stager did not increment it. ===
goto :done

:cancelled
echo Cancelled by user. No changes made.
goto :done

:abort
echo.
echo *** ABORTED. Snapshot/archive (if created^) are retained. Delivery pair left together when possible. ***
echo *** No older snapshot was deleted unless a delete was explicitly reported above. ***
endlocal
exit /b 1

:done
endlocal
exit /b 0

:hashVerify
if not exist "%~1" ( echo [FAIL] missing file for hash: %~1 & exit /b 1 )
set "ACTUAL="
for /f "tokens=*" %%X in ('certutil -hashfile "%~1" SHA256 ^| findstr /r /i /c:"^[0-9a-f][0-9a-f]*$"') do if not defined ACTUAL set "ACTUAL=%%X"
set "ACTUAL=!ACTUAL: =!"
if not defined ACTUAL ( echo [FAIL] could not calculate SHA256: %~1 & exit /b 1 )
if /i not "!ACTUAL!"=="%~2" ( echo [FAIL] SHA256 mismatch: %~1 & echo expected %~2 & echo actual   !ACTUAL! & exit /b 1 )
exit /b 0
