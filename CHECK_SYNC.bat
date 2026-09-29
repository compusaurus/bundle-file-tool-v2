@echo off
REM ---------------------------------------------------------------
REM CHECK_SYNC.bat - report drift between this working folder and
REM the GitHub repo (compusaurus/bundle-file-tool-v2).
REM Read-only: this script never modifies, stages, or deletes.
REM Run from the project root.
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo ================================================
echo  Bundle File Tool v2 - sync check
echo ================================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [FAIL] This folder is not a git working tree.
    echo        Nothing here is tracked against the repo.
    goto :end
)

echo --- Current branch ---
git rev-parse --abbrev-ref HEAD
echo.

echo --- Fetching remote refs ---
git fetch origin --prune
echo.

echo --- Commits: local vs origin ---
for /f "tokens=1,2" %%A in ('git rev-list --left-right --count "@{u}...HEAD" 2^>nul') do (
    echo   behind origin: %%A
    echo   ahead  origin: %%B
)
echo.

echo --- Uncommitted changes to TRACKED files ---
git --no-pager diff --stat HEAD
echo.

echo --- Full porcelain status ^(M=modified D=deleted ??=untracked^) ---
git status --porcelain
echo.

echo --- Version marker ---
type VERSION.txt
echo.

echo ================================================
echo  Clean + "behind 0 / ahead 0" = in sync.
echo  Anything listed above is drift.
echo ================================================

:end
echo.
pause
endlocal
