@echo off
setlocal
set "ROOT=%~dp0"
if exist "%ROOT%_bundletool_incoming\scripts\install_bft.py" set "ROOT=%ROOT%_bundletool_incoming\"
if defined BFT_PYTHON goto explicit
for %%V in (3.13 3.12 3.11) do (
    py -%%V -c "import tkinter,ensurepip" >nul 2>&1
    if not errorlevel 1 (
        py -%%V "%ROOT%scripts\install_bft.py" %*
        if errorlevel 1 pause
        exit /b
    )
)
echo Install Python 3.11, 3.12, or 3.13 with Tk and the Python launcher first.
pause
exit /b 1
:explicit
"%BFT_PYTHON%" "%ROOT%scripts\install_bft.py" %*
if errorlevel 1 pause
