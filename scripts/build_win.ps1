# Build script for Windows .exe
# Run this script from PowerShell on Windows
$ErrorActionPreference = "Stop"

Write-Host "=== Building WeWork Booker for Windows ===" -ForegroundColor Green

# Navigate to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$ScriptDir\.."
$ProjectRoot = Get-Location

Write-Host "Project root: $ProjectRoot"

# Create virtual environment if it doesn't exist
if (-not (Test-Path "build_venv")) {
    Write-Host "Creating build virtual environment..."
    python -m venv build_venv
}

# Activate virtual environment
Write-Host "Activating build environment..."
& ".\build_venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller>=6.0.0 -q

# Install Playwright browsers
Write-Host "Installing Playwright Chromium..."
playwright install chromium

# Find Chromium path (Windows location)
$ChromiumPath = python -c @"
import glob
import os
from pathlib import Path

localappdata = os.environ.get('LOCALAPPDATA', '')
paths = sorted(glob.glob(localappdata + r'\ms-playwright\chromium-*'), reverse=True)
# Filter out headless_shell
paths = [p for p in paths if 'headless_shell' not in p]
if paths:
    print(paths[0])
"@

Write-Host "Chromium path: $ChromiumPath"

# Clean previous builds
Write-Host "Cleaning previous builds..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Build with PyInstaller
Write-Host "Building with PyInstaller..."
pyinstaller wework_booker_win.spec --clean --noconfirm

# Copy Chromium to dist folder
if ($ChromiumPath -and (Test-Path $ChromiumPath)) {
    Write-Host "Copying Chromium browser to dist folder..."
    $ChromeDest = "dist\WeWork Booker\chromium"
    New-Item -ItemType Directory -Force -Path $ChromeDest | Out-Null

    # Find chrome-win folder
    $ChromeWin = Get-ChildItem -Path $ChromiumPath -Directory -Filter "chrome-win*" | Select-Object -First 1
    if ($ChromeWin) {
        Copy-Item -Recurse "$($ChromeWin.FullName)\*" $ChromeDest
        Write-Host "Chromium copied successfully"
    } else {
        Write-Host "WARNING: Could not find chrome-win folder in $ChromiumPath" -ForegroundColor Yellow
        Get-ChildItem $ChromiumPath
    }
} else {
    Write-Host "WARNING: Chromium path not found: $ChromiumPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Output: dist\WeWork Booker\"
Write-Host ""
Write-Host "To create an installer, run Inno Setup with installer\setup.iss"

# Deactivate virtual environment
deactivate
