@echo off
setlocal

:: Set the path to 7z.exe (adjust if installed elsewhere or if it is already in PATH)
set "SEVENZIP=C:\Program Files\7-Zip\7z.exe"

:: Verify 7-Zip exists
if not exist "%SEVENZIP%" (
    where 7z >nul 2>nul
    if %errorlevel% equ 0 (
        set "SEVENZIP=7z"
    ) else (
        echo Error: 7-Zip executable not found. Please verify the path.
        pause
        exit /b 1
    )
)

:: Loop through all directories in the current folder
for /d %%D in (*) do (
    echo Compressing "%%~nxD"...
    "%SEVENZIP%" a -tzip "%%~nxD.zip" "%%~fD"
)

echo Done.
endlocal