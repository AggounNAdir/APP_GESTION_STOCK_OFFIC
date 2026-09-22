# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gestion_stock.py'],
    pathex=[],
    binaries=[],
    datas=[('profil_config.json', '.')],  # la base est api/gestion_stock.db (créée/reprise au 1er lancement, hors de l'exe)
    hiddenimports=['api', 'api.db', 'api.schema', 'api.stock_journal', 'sqlite3', 'tkinter', 'webbrowser', 'csv', 'json', 'datetime', 're', 'unicodedata', 'tempfile', 'subprocess', 'shutil'],
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
    name='GestionStock',
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
