# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


def collect_optional_binaries():
    root = Path(sys.prefix)
    candidates = [
        root / "Library" / "bin" / "ffi-8.dll",
        root / "Library" / "bin" / "ffi-7.dll",
        root / "Library" / "bin" / "ffi.dll",
        root / "Library" / "bin" / "libmpdec-4.dll",
        root / "Library" / "bin" / "libcrypto-3-x64.dll",
        root / "Library" / "bin" / "liblzma.dll",
        root / "Library" / "bin" / "libbz2.dll",
        root / "vcruntime140.dll",
        root / "vcruntime140_1.dll",
        root / "vcruntime140_threads.dll",
    ]
    binaries = []
    for path in candidates:
        if path.exists():
            binaries.append((str(path), "."))
    return binaries


a = Analysis(
    ["app_hotkey_manager.py"],
    pathex=[],
    binaries=collect_optional_binaries(),
    datas=[("app_hotkey_config.json", ".")],
    hiddenimports=[],
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
    name="app_hotkey_manager",
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
