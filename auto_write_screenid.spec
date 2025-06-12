# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['auto_write_screenid.py'],
    pathex=[],
    binaries=[],
    datas=[('resource/software_init.sh', 'resource')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'html', 'xml', 'pydoc', 'distutils', 'setuptools',
        'aiohappyeyeballs', 'aiohttp', 'aioquic', 'aiosignal', 'altgraph', 'appdirs', 'Appium-Python-Client',
        'asgiref', 'attrs', 'Babel', 'beautifulsoup4', 'blinker', 'booleanOperations', 'Brotli',
        'cffi', 'cffsubr', 'chardet', 'charset-normalizer', 'click', 'colorama', 'colorlog', 'comtypes',
        'contourpy', 'crayons', 'cryptography', 'customtkinter', 'cycler', 'darkdetect', 'decorator',
        'defusedxml', 'docx2pdf', 'dotenv', 'dukpy', 'easyofd', 'et-xmlfile', 'filelock', 'Flask', 'fontMath',
        'fonttools', 'frozenlist', 'fs', 'fsspec', 'googletrans', 'greenlet', 'h11', 'h2', 'hpack',
        'hstspreload', 'httpcore', 'httpx', 'huggingface-hub', 'hyperframe', 'imageio', 'imageio-ffmpeg',
        'install', 'itsdangerous', 'Jinja2', 'Js2Py', 'kaitaistruct', 'kiwisolver', 'ldap3', 'libretranslatepy',
        'loguru', 'lxml', 'MarkupSafe', 'matplotlib', 'mitmproxy', 'mitmproxy_rs', 'mitmproxy-windows',
        'moviepy', 'mpmath', 'msgpack', 'multidict', 'mysql-connector-python', 'networkx', 'Nuitka', 'numpy',
        'odfpy', 'opencv-contrib-python', 'opencv-python', 'openpyxl', 'ordered-set', 'outcome', 'packaging',
        'paho-mqtt', 'pandas', 'passlib', 'pbkdf2', 'pefile', 'piexif', 'pillow', 'pillow_heif', 'proglog',
        'propcache', 'publicsuffix2', 'pyasn1', 'pyasn1_modules', 'pyclipper', 'pycparser', 'pydivert',
        'pyinstaller', 'pyinstaller-hooks-contrib', 'pyjsparser', 'pylsqpack', 'PyMuPDF', 'PyMySQL',
        'pyOpenSSL', 'pyparsing', 'pyperclip', 'PyQt5', 'PyQt5-Qt5', 'PyQt5_sip', 'PyQt5-stubs', 'PyQt6',
        'PyQt6-Qt6', 'PyQt6-sip', 'pyserial', 'PySide6', 'PySide6_Addons', 'PySide6_Essentials', 'PySocks',
        'pystray', 'python-dateutil', 'python-dotenv', 'python-vlc', 'pytz', 'pywin32', 'pywin32-ctypes',
        'PyYAML', 'qasync', 'rawpy', 'regex', 'reportlab', 'rfc3986', 'ruamel.yaml', 'ruamel.yaml.clib',
        'safetensors', 'scapy', 'selenium', 'service-identity', 'shiboken6', 'six', 'sniffio', 'sortedcontainers',
        'soupsieve', 'speedtest', 'SQLAlchemy', 'stegano', 'sympy', 'telnetlib3', 'tokenizers', 'torch',
        'torchvision', 'tornado', 'tqdm', 'transformers', 'translate', 'translator', 'trio', 'trio-websocket',
        'typing_extensions', 'tzdata', 'tzlocal', 'ufo2ft', 'urwid', 'wcwidth', 'websocket-client',
        'Werkzeug', 'wheel', 'wifi', 'win32_setctime', 'wsproto', 'xmltodict', 'yarl', 'you-get', 'zstandard'
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='auto_write_screenid',
    debug=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resource/icon/autowriteId.ico',
    onefile=True
)
