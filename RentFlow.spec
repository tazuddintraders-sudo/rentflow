# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for RentFlow (Windows desktop app).

Usage (Windows, inside the project virtualenv):
    pip install -r requirements.txt
    python -m django collectstatic --noinspection        # collect static first
    pyinstaller RentFlow.spec --noconfirm

Output: dist/RentFlow/RentFlow.exe
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = os.path.abspath(".")

datas = [
    (os.path.join(ROOT, "templates"), "templates"),
    (os.path.join(ROOT, "static"), "static"),
    (os.path.join(ROOT, "staticfiles"), "staticfiles"),
    (os.path.join(ROOT, "manage.py"), "."),
]

# ReportLab font/metric data files
datas += collect_data_files("reportlab")

hiddenimports = []
hiddenimports += collect_submodules("django")
for app in ("apps.accounts", "apps.properties", "apps.payments", "apps.dashboard"):
    hiddenimports += collect_submodules(app)


a = Analysis(
    ["run_desktop.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL.tests"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RentFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # keeps a small log window handy for first-run diagnostics
    icon=os.path.join(ROOT, "static", "icons", "rentflow.ico")
        if os.path.exists(os.path.join(ROOT, "static", "icons", "rentflow.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="RentFlow",
)
