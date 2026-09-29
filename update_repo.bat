@echo off
REM ============================================================================
REM  update_repo.bat -- commit and push local work to origin.
REM
REM  Replaces an 8-line version whose `git add .` swept every untracked file
REM  into the repo. Commit ee496aa added 42 bundle_session_*.json runtime logs
REM  and FIX_EVERYTHING.py that way; CP-2026-003 spent four commits undoing it.
REM
REM  This version:
REM    - stages TRACKED changes only by default (git add -u)
REM    - lists untracked files and requires an explicit opt-in before adding
REM    - shows pending DELETIONS before they are committed
REM    - checks every git command and stops on the first failure
REM    - pushes the CURRENT branch; never assumes master
REM    - does not run `git init` or `git remote add` on an existing clone
REM    - re-executes from %TEMP% so a pull cannot rewrite it mid-run
REM
REM  Run from the project root.
REM ============================================================================
setlocal EnableExtensions EnableDelayedExpansion

REM --- R-SELF-01: relaunch from a copy in %TEMP% ------------------------------
REM  cmd.exe does not load a .bat into memory; it reads it incrementally by byte
REM  offset. This script runs `git pull --rebase`, which can rewrite THIS FILE
REM  while it is still executing. Observed 2026-09-28: the previous 238-byte
REM  version was replaced during its own pull, cmd resumed at byte 230 of the
REM  replacement, landed mid-word inside "...swept every untracked file", and
REM  executed the fragment `ed file` as a command.
REM
REM  The guard below is ONE parenthesized command. cmd parses it in full before
REM  executing it, and the `exit /b` inside ends the script without ever reading
REM  another byte of this file. Everything past it runs from the temp copy,
REM  which git never touches. The inner tests are single-statement `if` lines on
REM  purpose: nested parentheses inside a block are where batch fails silently.
set "SELFDIR=%~dp0"
if "%SELFDIR:~-1%"=="\" set "SELFDIR=%SELFDIR:~0,-1%"
if /i not "%~1"=="--relaunched" (
    set "SELFCOPY=%TEMP%\update_repo_%RANDOM%%RANDOM%.bat"
    copy /y "%~f0" "!SELFCOPY!" >nul
    if not exist "!SELFCOPY!" echo [FAIL] could not stage a temp copy in "%TEMP%".
    if not exist "!SELFCOPY!" pause
    if not exist "!SELFCOPY!" exit /b 1
    call "!SELFCOPY!" --relaunched "!SELFDIR!"
    set "RC=!ERRORLEVEL!"
    del /f /q "!SELFCOPY!" >nul 2>&1
    exit /b !RC!
)

REM  From here on we are the temp copy. The project root arrives as %2.
set "ROOT=%~2"
if not defined ROOT set "ROOT=%SELFDIR%"
cd /d "%ROOT%"
if errorlevel 1 echo [FAIL] cannot change to "%ROOT%".
if errorlevel 1 pause
if errorlevel 1 exit /b 1

set "EXPECTED_REMOTE=https://github.com/compusaurus/bundle-file-tool-v2"

echo ================================================
echo  update_repo - commit and push to origin
echo ================================================
echo.

where git >nul 2>&1
if errorlevel 1 ( echo [FAIL] git not found on PATH. & goto :abort )

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [FAIL] not a git working tree: %CD%
    echo        Run this from the project root of an existing clone.
    goto :abort
)

REM --- remote ----------------------------------------------------------------
set "REMOTE="
for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do set "REMOTE=%%R"
if not defined REMOTE (
    echo [FAIL] no 'origin' remote configured.
    echo        Expected: %EXPECTED_REMOTE%
    echo        Add it:   git remote add origin %EXPECTED_REMOTE%
    goto :abort
)
echo Remote : !REMOTE!
if /i "!REMOTE!"=="%EXPECTED_REMOTE%" goto :remoteok
if /i "!REMOTE!"=="%EXPECTED_REMOTE%.git" goto :remoteok
echo [WARN] remote does not match the expected URL.
echo        expected: %EXPECTED_REMOTE%
choice /c YN /n /m "Continue anyway [Y/N]? "
if errorlevel 2 goto :cancelled
:remoteok

REM --- branch ----------------------------------------------------------------
set "BRANCH="
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%B"
if not defined BRANCH ( echo [FAIL] could not determine the current branch. & goto :abort )
if /i "!BRANCH!"=="HEAD" ( echo [FAIL] detached HEAD. Check out a branch first. & goto :abort )
echo Branch : !BRANCH!
echo.

REM --- stage tracked changes only --------------------------------------------
git add -u
if errorlevel 1 ( echo [FAIL] `git add -u` failed. & goto :abort )

REM --- untracked files require an explicit yes -------------------------------
set /a UNTRACKED=0
for /f "delims=" %%F in ('git ls-files --others --exclude-standard') do set /a UNTRACKED+=1
if !UNTRACKED! EQU 0 goto :staged
echo --- !UNTRACKED! untracked file^(s^), NOT staged ---
git ls-files --others --exclude-standard
echo.
echo These are new files git does not track yet. Adding them puts them in the
echo repository permanently. Read the list above before answering.
choice /c YN /n /m "Add these untracked files too [Y/N]? "
if errorlevel 2 goto :skipuntracked
git add .
if errorlevel 1 ( echo [FAIL] `git add .` failed. & goto :abort )
goto :staged
:skipuntracked
echo   left untracked.
:staged
echo.

REM --- review what is staged --------------------------------------------------
git diff --cached --quiet
if errorlevel 1 goto :haschanges
echo Nothing staged to commit.
goto :sync
:haschanges
echo --- staged for commit ---
git --no-pager diff --cached --stat
echo.
set /a DELCOUNT=0
for /f "delims=" %%D in ('git diff --cached --name-only --diff-filter=D') do set /a DELCOUNT+=1
if !DELCOUNT! EQU 0 goto :askmsg
echo [NOTE] !DELCOUNT! tracked file^(s^) will be DELETED from the repository:
git diff --cached --name-only --diff-filter=D
echo.
:askmsg
set "MSG="
set /p "MSG=Commit message: "
if not defined MSG ( echo [FAIL] empty commit message. Nothing was committed. & goto :abort )
git commit -m "!MSG!"
if errorlevel 1 ( echo [FAIL] commit failed. & goto :abort )
echo.

REM --- sync with origin -------------------------------------------------------
:sync
echo --- fetching origin
git fetch origin --prune
if errorlevel 1 ( echo [FAIL] fetch failed. & goto :abort )

git rev-parse --verify "origin/!BRANCH!" >nul 2>&1
if errorlevel 1 goto :push
echo --- rebasing onto origin/!BRANCH!
git pull --rebase origin "!BRANCH!"
if errorlevel 1 (
    echo.
    echo [FAIL] rebase did not complete. NOTHING WAS PUSHED.
    echo        Resolve the conflict, then:  git rebase --continue
    echo        Or back out entirely with:   git rebase --abort
    goto :abort
)

:push
echo --- pushing !BRANCH! to origin
git push -u origin "!BRANCH!"
if errorlevel 1 ( echo [FAIL] push failed. & goto :abort )
echo.
echo ================================================
echo  Done. !BRANCH! is pushed to origin.
echo ================================================
goto :done

:cancelled
echo Cancelled. Nothing was committed or pushed.
goto :done

:abort
echo.
echo *** ABORTED. Nothing was pushed. ***
echo.
pause
endlocal
exit /b 1

:done
echo.
pause
endlocal
exit /b 0
