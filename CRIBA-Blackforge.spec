# -*- mode: python ; coding: utf-8 -*-
# CRIBA + BLACKFORGE portable build: two windowed applications + CLI.
# CRIBA.exe launches the sibling BLACKFORGE.exe with QProcess; neither app is
# embedded inside the other and no shell command is constructed.
# Data bundled at _MEIPASS root so constants.PACKAGE_ROOT (sys._MEIPASS) resolves
# data/ and imports/blackforge_v2/ (723-record catalog) correctly.

# PyInstaller injects SPECPATH as the directory containing this spec. Resolve
# every input from it so builds work from clones, worktrees, and paths with
# spaces instead of silently reading another checkout.
ROOT = SPECPATH.replace('\\', '/')
DATAS = [
    (ROOT + '/data', 'data'),
    (ROOT + '/imports/blackforge_v2', 'imports/blackforge_v2'),
]

gui_a = Analysis(
    [ROOT + '/scripts/portable_entry_gui.py'],
    pathex=[ROOT + '/src'],
    binaries=[],
    datas=DATAS,
    hiddenimports=[
        'criba.gui',
        'criba.ui', 'criba.ui.main_window', 'criba.ui.app_bridge',
        'criba.ui.panels', 'criba.ui.theme', 'criba.ui.tokens',
        'criba.ui.widgets', 'criba.ui.actions', 'criba.ui.dialogs',
        'criba.ui.i18n', 'criba.ui.interpreter', 'criba.ui.ranking',
        'criba.blackforge_catalog', 'criba.storage', 'criba.lottery',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtCharts',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)

blackforge_a = Analysis(
    [ROOT + '/scripts/blackforge_entry_gui.py'],
    pathex=[ROOT + '/src'],
    binaries=[],
    datas=DATAS,
    hiddenimports=[
        'criba.blackforge_gui',
        'criba.ui', 'criba.ui.blackforge_window',
        'criba.ui.interpreter', 'criba.ui.tokens',
        'criba.blackforge_catalog', 'criba.lottery',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    ],
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
    (gui_a, 'CRIBA', 'CRIBA'),
    (blackforge_a, 'BLACKFORGE', 'BLACKFORGE'),
    (cli_a, 'CRIBA-CLI', 'CRIBA-CLI'),
)

gui_pyz = PYZ(gui_a.pure)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=True,
    name='CRIBA',
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

blackforge_pyz = PYZ(blackforge_a.pure)
blackforge_exe = EXE(
    blackforge_pyz,
    blackforge_a.scripts,
    [],
    exclude_binaries=True,
    name='BLACKFORGE',
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
    name='CRIBA-CLI',
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
    blackforge_exe,
    blackforge_a.binaries,
    blackforge_a.datas,
    cli_exe,
    cli_a.binaries,
    cli_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CRIBA-Blackforge',
)
