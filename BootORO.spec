# -*- mode: python ; coding: utf-8 -*-
# Auto-generado por BootOroBuilder - 2026-02-11 10:47:01

block_cipher = None

a = Analysis(
    [r'c:\python\boot-oro\main.py'],
    pathex=[
        r'c:\python\boot-oro',
        r'c:\python\boot-oro\src',
    ],
    binaries=[],
    datas=[
    (r'c:\python\boot-oro\endpoint.env', r'.'),
    (r'c:\python\boot-oro\resources\keys', r'resources/keys'),
    (r'c:\python\boot-oro\resources\images', r'resources/images'),
    (r'c:\python\boot-oro\src', r'src'),
    ],
    hiddenimports=[
    'cryptography',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.hazmat.primitives.asymmetric.ed25519',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'cryptography.fernet',
    'requests',
    'fitz',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'pytest',
    'black',
    'flake8',
    'colorlog',
    'pydantic',
    'notebook',
    'IPython'
    ],
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
    name='BootORO',
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
