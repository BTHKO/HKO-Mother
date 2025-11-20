@echo off
title HKO Grunt v12 - Optimized Builder

echo ========================================
echo   HKO GRUNT v12 - Build System
echo   Optimized & Fully Functionalized
echo ========================================
echo.

echo [1/4] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec
echo     Done.
echo.

echo [2/4] Checking Python environment...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo     Done.
echo.

echo [3/4] Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)
echo     Done.
echo.

echo [4/4] Building HKO Grunt v12 EXE...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "HKO_Grunt_v12" ^
    --icon=NONE ^
    --add-data "README.md;." ^
    HKO_Grunt_v12_optimized.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Executable location: dist\HKO_Grunt_v12.exe
echo.
echo You can now run the application!
echo.
pause
