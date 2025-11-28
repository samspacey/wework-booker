#!/bin/bash
# Build script for macOS .app bundle
set -e

echo "=== Building WeWork Booker for macOS ==="

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"

# Create/activate virtual environment for building
if [ ! -d "build_venv" ]; then
    echo "Creating build virtual environment..."
    python3 -m venv build_venv
fi

echo "Activating build environment..."
source build_venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller>=6.0.0 -q

# Install Playwright browsers
echo "Installing Playwright Chromium..."
playwright install chromium

# Find Chromium path (macOS stores in Library/Caches, Linux in .cache)
CHROMIUM_PATH=$(python3 -c "
import glob
from pathlib import Path
import sys

# macOS location
mac_paths = sorted(glob.glob(str(Path.home() / 'Library/Caches/ms-playwright/chromium-*')), reverse=True)
# Linux location
linux_paths = sorted(glob.glob(str(Path.home() / '.cache/ms-playwright/chromium-*')), reverse=True)

paths = mac_paths + linux_paths
# Filter to only include full chromium (not headless_shell)
paths = [p for p in paths if 'headless_shell' not in p]
if paths:
    print(paths[0])
")

echo "Chromium path: $CHROMIUM_PATH"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "Building with PyInstaller..."
pyinstaller wework_booker_mac.spec --clean --noconfirm

# Copy Chromium to app bundle
if [ -d "$CHROMIUM_PATH" ]; then
    echo "Copying Chromium browser to app bundle..."
    CHROMIUM_DEST="dist/WeWork Booker.app/Contents/Resources/chromium"
    mkdir -p "$CHROMIUM_DEST"

    # Find and copy the Chromium.app
    if [ -d "$CHROMIUM_PATH/chrome-mac/Chromium.app" ]; then
        cp -R "$CHROMIUM_PATH/chrome-mac/Chromium.app" "$CHROMIUM_DEST/"
        echo "Chromium copied successfully"
    elif [ -d "$CHROMIUM_PATH/chrome-mac-arm64/Chromium.app" ]; then
        cp -R "$CHROMIUM_PATH/chrome-mac-arm64/Chromium.app" "$CHROMIUM_DEST/"
        echo "Chromium (ARM64) copied successfully"
    else
        echo "WARNING: Could not find Chromium.app in expected locations"
        ls -la "$CHROMIUM_PATH/"
    fi
else
    echo "WARNING: Chromium path not found: $CHROMIUM_PATH"
fi

# Ad-hoc code sign the app (allows right-click → Open without "move to bin" error)
echo "Ad-hoc signing the app bundle..."
codesign --force --deep --sign - "dist/WeWork Booker.app"
echo "App signed successfully"

# Remove quarantine attribute for local testing
xattr -cr "dist/WeWork Booker.app" 2>/dev/null || true

echo ""
echo "=== Build complete ==="
echo "App bundle: dist/WeWork Booker.app"
echo ""
echo "To test the app:"
echo "  open 'dist/WeWork Booker.app'"
echo ""
echo "To create a DMG:"
echo "  ./scripts/create_dmg.sh"
echo ""
echo "Note: Users downloading the DMG should right-click → Open the first time"

# Deactivate venv
deactivate
