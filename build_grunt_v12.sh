#!/bin/bash

echo "========================================"
echo "  HKO GRUNT v12 - Build System"
echo "  Optimized & Fully Functionalized"
echo "========================================"
echo ""

echo "[1/4] Cleaning previous build artifacts..."
rm -rf build dist *.spec
echo "    Done."
echo ""

echo "[2/4] Checking Python environment..."
python3 --version
if [ $? -ne 0 ]; then
    echo "ERROR: Python not found!"
    exit 1
fi
echo "    Done."
echo ""

echo "[3/4] Checking PyInstaller..."
python3 -m PyInstaller --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi
echo "    Done."
echo ""

echo "[4/4] Building HKO Grunt v12..."
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --name "HKO_Grunt_v12" \
    --add-data "README.md:." \
    HKO_Grunt_v12_optimized.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    exit 1
fi

echo ""
echo "========================================"
echo "  BUILD COMPLETE!"
echo "========================================"
echo ""
echo "Executable location: dist/HKO_Grunt_v12"
echo ""
echo "You can now run the application!"
echo ""
