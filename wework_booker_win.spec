# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Windows .exe."""

from pathlib import Path

block_cipher = None

# Get Playwright driver path
import playwright
playwright_path = Path(playwright.__file__).parent

a = Analysis(
    ['gui_entry.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include Playwright driver (required for browser automation)
        (str(playwright_path / 'driver'), 'playwright/driver'),
        # Include .env.example for reference
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'playwright',
        'playwright.sync_api',
        'playwright._impl',
        'click',
        'dotenv',
        'schedule',
        'wework_booker',
        'wework_booker.gui',
        'wework_booker.gui.app',
        'wework_booker.gui.booking_thread',
        'wework_booker.browser',
        'wework_booker.booker',
        'wework_booker.config',
        'wework_booker.scheduler',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WeWork Booker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WeWork Booker',
)
