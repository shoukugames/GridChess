# PyInstaller recipe shared by both platforms.
#   Linux:   a folder build, which build_linux.sh wraps into a .deb
#   Windows: a single windowed .exe (with the version details from build_windows.sh)
import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
sys.path.insert(0, ROOT)
from gridchess import __version__  # noqa: E402

IS_WINDOWS = sys.platform == "win32"

analysis = Analysis(
    [os.path.join(ROOT, "run_game.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "assets", "icon.png"), "assets"),
           (os.path.join(ROOT, "assets", "fonts"), os.path.join("assets", "fonts")),
           (os.path.join(ROOT, "assets", "audio"), os.path.join("assets", "audio")),
           (os.path.join(ROOT, "LICENSE"), ".")],
    excludes=["numpy", "tkinter", "unittest", "pydoc", "pygame.examples", "pygame.tests", "pygame.docs"],
)
pyz = PYZ(analysis.pure)

if IS_WINDOWS:
    version_file = os.path.join(ROOT, "build", "version_info.txt")
    exe = EXE(
        pyz, analysis.scripts, analysis.binaries, analysis.datas,
        name=f"GridChess-v{__version__}",
        icon=os.path.join(ROOT, "assets", "icon.ico"),
        version=version_file if os.path.exists(version_file) else None,
        console=False, upx=False, strip=False,
    )
else:
    exe = EXE(
        pyz, analysis.scripts, exclude_binaries=True,
        name="gridchess", console=True, upx=False, strip=False,
    )
    coll = COLLECT(exe, analysis.binaries, analysis.datas, name="gridchess", upx=False, strip=False)
