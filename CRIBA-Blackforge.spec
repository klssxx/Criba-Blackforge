# -*- mode: python ; coding: utf-8 -*-
# CRIBA + BLACKFORGE portable build: GUI (windowed) + CLI (console), shared runtime.
# Data bundled at _MEIPASS root so constants.PACKAGE_ROOT (sys._MEIPASS) resolves
# data/ and imports/blackforge_v2/ (723-record catalog) correctly.

ROOT = 'E:/PROYECTS/CRIBA'
DATAS = [
    (ROOT + '/data', 'data'),
    (ROOT + '/imports/blackforge_v2', 'imports/blackforge_v2'),
]

gui_a = Analysis(
    [ROOT + '/scripts/portable_entry_gui.py'],
    pathex=[ROOT + '/src'],
    binaries=[],
    datas=DATAS,
    hiddenimports=['criba.gui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)

cli_a = Analysis(
    [ROOT + '/scripts/portable_entry.py'],
    pathex=[ROOT + '/src'],
    binaries=[],
    datas=DATAS,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6'],
    noarchive=False,
    optimize=0,
)

MERGE(
    (gui_a, 'CRIBA-Blackforge', 'CRIBA-Blackforge'),
    (cli_a, 'CRIBA-Blackforge-CLI', 'CRIBA-Blackforge-CLI'),
)

gui_pyz = PYZ(gui_a.pure)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=True,
    name='CRIBA-Blackforge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

cli_pyz = PYZ(cli_a.pure)
cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    [],
    exclude_binaries=True,
    name='CRIBA-Blackforge-CLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    gui_exe,
    gui_a.binaries,
    gui_a.datas,
    cli_exe,
    cli_a.binaries,
    cli_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CRIBA-Blackforge',
)
