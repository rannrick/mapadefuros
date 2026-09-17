# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: pyinstaller MapaDeFuros.spec --noconfirm
block_cipher = None

a = Analysis(
    ['src/mapadefuros_app.py'],
    pathex=['src'],
    binaries=[],
    datas=[('references', 'references'), ('assets', 'assets')],
    hiddenimports=['scipy.spatial', 'scipy.spatial._qhull', 'PIL._tkinter_finder'],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'IPython', 'pandas',
              'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_gtk3agg'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='MapaDeFuros',
    icon='assets/mapadefuros.ico',
    console=False,
    upx=False,
    version='installer/version_info.txt',
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, upx=False, name='MapaDeFuros')
