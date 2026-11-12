# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\Luna\\AppData\\Roaming\\Cindy\\owners\\fcb0728ecdfaf54ecc33\\bots\\cindy-default\\workspace\\live_log_analyzer\\build_pack\\stage\\app.enc', '.'), ('C:\\Users\\Luna\\AppData\\Roaming\\Cindy\\owners\\fcb0728ecdfaf54ecc33\\bots\\cindy-default\\workspace\\live_log_analyzer\\build_pack\\stage\\src', 'src'), ('C:\\Users\\Luna\\AppData\\Roaming\\Cindy\\owners\\fcb0728ecdfaf54ecc33\\bots\\cindy-default\\workspace\\live_log_analyzer\\build_pack\\stage\\.streamlit', '.streamlit')]
binaries = []
hiddenimports = ['pandas', 'matplotlib', 'openpyxl', 'fpdf2']
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('plotly')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('altair')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\Luna\\AppData\\Roaming\\Cindy\\owners\\fcb0728ecdfaf54ecc33\\bots\\cindy-default\\workspace\\live_log_analyzer\\build_pack\\stage\\loader.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='LiveLogAnalyzer',
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
    icon=['C:\\Users\\Luna\\AppData\\Roaming\\Cindy\\owners\\fcb0728ecdfaf54ecc33\\bots\\cindy-default\\workspace\\live_log_analyzer\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LiveLogAnalyzer',
)
