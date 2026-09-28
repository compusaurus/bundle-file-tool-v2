@echo off
setlocal EnableExtensions
set "ROOT=%~dp0..\.."
for %%R in ("%ROOT%") do set "ROOT=%%~fR"
set "PY="
if exist "%ROOT%\.bft-runtime.txt" for /f "usebackq delims=" %%E in ("%ROOT%\.bft-runtime.txt") do if exist "%ROOT%\%%E\Scripts\python.exe" set "PY=%ROOT%\%%E\Scripts\python.exe"
for %%E in (.venv311 .venv312 .venv313) do if not defined PY if exist "%ROOT%\%%E\Scripts\python.exe" set "PY=%ROOT%\%%E\Scripts\python.exe"
if not defined PY (
  echo [FAIL] No supported BFT Python environment was found.
  echo        Create .venv311, .venv312, or .venv313, then try again.
  pause
  exit /b 1
)
set "BFT_DIAGNOSTIC=1"
set "PYTHONPATH=%ROOT%\src"
pushd "%ROOT%"
"%PY%" "%ROOT%\src\main.py"
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" pause
exit /b %RC%
