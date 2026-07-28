# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\criba\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('src/criba', 'criba')],
    hiddenimports=[
        'criba', 'criba.ui', 'criba.engine', 'criba.lottery',
        'criba.ui.i18n', 'criba.ui.interpreter',
        'criba.ui.blackforge_screen', 'criba.ui.main_window',
        'criba.ui.theme', 'criba.ui.tokens', 'criba.ui.widgets',
        'criba.ui.panels', 'criba.ui.actions', 'criba.ui.dialogs',
        'criba.ui.ranking', 'criba.blackforge_catalog', 'criba.storage',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CRIBA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
