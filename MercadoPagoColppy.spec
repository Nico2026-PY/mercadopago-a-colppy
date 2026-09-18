# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

openpyxl_data, openpyxl_binaries, openpyxl_hidden = collect_all("openpyxl")
xlwt_data, xlwt_binaries, xlwt_hidden = collect_all("xlwt")
xlrd_data, xlrd_binaries, xlrd_hidden = collect_all("xlrd")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=openpyxl_binaries + xlwt_binaries + xlrd_binaries,
    datas=openpyxl_data + xlwt_data + xlrd_data + [("assets/app-icon.png", "assets")],
    hiddenimports=openpyxl_hidden + xlwt_hidden + xlrd_hidden,
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
    name="MercadoPagoColppy",
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
    icon=["assets/app-icon.ico"],
)
