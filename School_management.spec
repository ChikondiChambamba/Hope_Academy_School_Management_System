# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Define which modules to include/exclude
hiddenimports = [
    'mysql.connector',
    'mysql.connector.pooling',
    'mysql.connector.locales.eng.client_error',
    'mysql.connector.locales.eng.client_error._CMESSAGES',
    'mysql.connector.locales.eng.client_error._ERR_NO',
    'mysql.connector.locales.eng.client_error._SQLSTATE',
    'mysql.connector.locales.eng.client_error._ERROR_TYPES',
    'reportlab',
    'reportlab.graphics.barcode',
    'reportlab.graphics.samples',
    'reportlab.graphics.charts',
    'reportlab.graphics.widgets',
    'reportlab.graphics',
    'reportlab.pdfbase',
    'reportlab.pdfgen',
    'reportlab.lib',
    'reportlab.platypus',
    'pandas',
    'pandas._libs',
    'pandas.io',
    'pandas._version',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'PIL',
    'PIL.Image',
    'PIL.ImageFile',
    'PIL.ImageOps',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'datetime',
    'decimal',
    'json',
    'csv',
    'io',
    'os',
    'sys',
    'pathlib',
    'typing',
    'collections',
    'itertools',
    'functools',
    'threading',
    'logging',
    're',
    'math',
    'statistics',
    'hashlib',
    'base64',
    'zipfile',
    'subprocess',
    'shutil',
    'tempfile',
    'platform',
    'psutil',
    'webbrowser',
    'time',
    'warnings',
    'dataclasses',
    'enum',
    'calendar',
]

# Exclude unnecessary modules to reduce size
excludes = [
    'matplotlib',
    'numpy',
    'scipy',
    'PyQt5',
    'PyQt6',
    'wx',
    'pygame',
    'pytest',
    'unittest',
    'test',
    'tests',
    'setuptools',
    'pip',
    'wheel',
    'virtualenv',
    'ipython',
    'jupyter',
    'notebook',
    'spyder',
    'pycparser',
    'pyodbc',
    'sqlite3',  # We're using MySQL
    'tcl',
    'tk',
    'ttk',
    'idlelib',
    'turtle',
    'ensurepip',
    'venv',
    'pydoc',
    'doctest',
    'difflib',
    'email',
    'html',
    'http',
    'xml',
    'urllib',
    'ftplib',
    'poplib',
    'imaplib',
    'smtplib',
    'telnetlib',
    'uuid',
    'ssl',
    'cryptography',
    'asyncio',
    'multiprocessing',
    'concurrent',
    'ctypes',
    'mmap',
    'selectors',
    'socket',
    'socketserver',
    'subprocess',
    '_multiprocessing',
    '_socket',
    '_ssl',
    'win32com',
    'comtypes',
    'pywintypes',
    'win32api',
    'win32con',
    'win32gui',
    'win32security',
    'pywin',
    'pywin.dialogs',
    'pywin.mfc',
]

# Add datas (non-Python files)
datas = []

# Include icons
icon_dir = project_root / 'assets' / 'icons'
if icon_dir.exists():
    for icon_file in icon_dir.glob('*.png'):
        datas.append((str(icon_file), 'assets/icons'))
    for icon_file in icon_dir.glob('*.ico'):
        datas.append((str(icon_file), 'assets/icons'))

# Include SQL files
db_dir = project_root / 'database'
if db_dir.exists():
    for sql_file in db_dir.glob('*.sql'):
        datas.append((str(sql_file), 'database'))

# Include report templates
reports_dir = project_root / 'reports' / 'templates'
if reports_dir.exists():
    for template_file in reports_dir.glob('*'):
        datas.append((str(template_file), 'reports/templates'))

# Include config files
config_file = project_root / 'config.py'
if config_file.exists():
    datas.append((str(config_file), '.'))

# Include setup database script
setup_script = project_root / 'setup_database.py'
if setup_script.exists():
    datas.append((str(setup_script), '.'))

# Include requirements.txt
requirements_file = project_root / 'requirements.txt'
if requirements_file.exists():
    datas.append((str(requirements_file), '.'))

# Include README
readme_file = project_root / 'README.md'
if readme_file.exists():
    datas.append((str(readme_file), '.'))

# Define binaries (DLLs, etc.)
binaries = []

# Add MySQL connector DLLs if needed
mysql_dll_path = None
try:
    import mysql.connector
    mysql_dir = Path(mysql.connector.__file__).parent
    # Look for DLLs in mysql connector package
    for dll_file in mysql_dir.glob('*.dll'):
        binaries.append((str(dll_file), '.'))
except ImportError:
    pass

# Configure the build
a = Analysis(
    ['main.py'],  # Main script
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,  # Optimization level
)

# Set application icon
icon_path = str(project_root / 'assets' / 'icons' / 'app_icon.ico')
pyz = PYZ(a.pure)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SchoolManagementSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Use UPX compression to reduce size
    upx_exclude=[],  # Exclude certain files from UPX compression
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging, False for windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
    version_file=None,  # You can create a version file for Windows
)

# If you want a single executable (onefile)
# For onefile build, we need to collect everything
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SchoolManagementSystem',
)