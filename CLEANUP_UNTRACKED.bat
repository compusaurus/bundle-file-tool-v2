@echo off
REM ---------------------------------------------------------------
REM CLEANUP_UNTRACKED.bat
REM Archives the runtime artifacts left untracked by CP-2026-003:
REM   - root bundle_session_*.json  (runtime session logs)
REM   - FIX_EVERYTHING.py           (superseded)
REM
REM Files are MOVED into .bft-backups\untracked_cleanup_<timestamp>\
REM Nothing is deleted, so this is reversible. Any file git still
REM tracks is skipped, never moved.
REM Run from the project root.
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [ABORT] Not a git working tree. Run this from the project root.
    goto :end
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "ARCHIVE=.bft-backups\untracked_cleanup_%TS%"

echo ================================================
echo  Cleanup of untracked runtime artifacts
echo ================================================
echo.
echo These files will be MOVED to:
echo   %ARCHIVE%
echo.

set /a FOUND=0
for %%F in (bundle_session_*.json) do call :tally "%%F"
call :tally "FIX_EVERYTHING.py"

if %FOUND%==0 (
    echo Nothing to clean up - already done.
    goto :end
)

echo.
echo   %FOUND% file^(s^) to archive.
echo.
set /p "OK=Proceed? [y/N] "
if /i not "%OK%"=="y" (
    echo Cancelled. Nothing was moved.
    goto :end
)

mkdir "%ARCHIVE%" 2>nul
set /a MOVED=0
set /a SKIPPED=0
echo.
for %%F in (bundle_session_*.json) do call :archive "%%F"
call :archive "FIX_EVERYTHING.py"

echo.
echo ================================================
echo  archived: %MOVED%    skipped ^(tracked^): %SKIPPED%
echo  location: %ARCHIVE%
echo ================================================
echo.
echo Verify with:  git status -sb
echo Once happy, delete the archive with:
echo   rmdir /s /q "%ARCHIVE%"
goto :end

:tally
if not exist "%~1" goto :eof
echo   %~1
set /a FOUND+=1
goto :eof

:archive
if not exist "%~1" goto :eof
git ls-files --error-unmatch "%~1" >nul 2>&1
if %errorlevel%==0 (
    echo   [SKIP - still tracked] %~1
    set /a SKIPPED+=1
    goto :eof
)
move /y "%~1" "%ARCHIVE%" >nul
if %errorlevel%==0 (
    set /a MOVED+=1
) else (
    echo   [FAILED] %~1
)
goto :eof

:end
echo.
pause
endlocal
