# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Python Script Runner
# Builds a standalone Windows EXE named python-script-runner.exe

block_cipher = None

a = Analysis(
    ['runner.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'psutil',
        'yaml',
        'requests',
        'sqlite3',
        'smtplib',
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        'gzip',
        'uuid',
        'queue',
        'runners',
        'runners.workflows.workflow_engine',
        'runners.workflows.workflow_parser',
        'runners.tracers.otel_manager',
        'runners.scanners.code_analyzer',
        'runners.scanners.dependency_scanner',
        'runners.security.secret_scanner',
        'runners.integrations.cloud_cost_tracker',
        'runners.profilers.performance_profiler',
        'runners.templates.template_manager',
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
