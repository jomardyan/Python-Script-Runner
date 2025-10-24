# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Python Script Runner
# Generated for building standalone Windows executable

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect data files and submodules for required packages
datas = []
binaries = []
hiddenimports = [
    'psutil',
    'yaml',
    'requests',
    'urllib3',
    'chardet',
    'idna',
    'certifi',
]

# Collect psutil and requests data files if needed
try:
    datas += collect_data_files('psutil')
except Exception:
    pass

try:
    datas += collect_data_files('requests')
except Exception:
    pass

a = Analysis(
    ['runner.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='python-script-runner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if __name__ == 'BuiltinImporter' else None,
)
