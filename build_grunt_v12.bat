@echo off
title HKO Grunt v12 - Ultimate Edition Builder

echo ============================================================
echo   HKO GRUNT v12 - ULTIMATE EDITION BUILD PROCESS
echo ============================================================
echo.

echo [1/4] Cleaning previous build artifacts...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del *.spec 2>nul
echo     Done.
echo.

echo [2/4] Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo     Python OK.
echo.

echo [3/4] Building executable with PyInstaller...
echo     Target: HKO_Grunt_v12.py
echo     Mode: Single file, No console
python -m PyInstaller --onefile --noconsole --name "HKO_Grunt_v12" HKO_Grunt_v12.py
if %errorlevel% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo     Build successful!
echo.

echo [4/4] Build complete!
echo.
echo ============================================================
echo   EXECUTABLE LOCATION:
echo   %CD%\dist\HKO_Grunt_v12.exe
echo ============================================================
echo.
echo Ready to deploy!
echo.
pause
