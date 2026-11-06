#!/usr/bin/env bash
# Builds dist/GridChess-v<version>.exe from Linux, with Windows Python under Wine.
# The first run downloads Python from python.org into a private Wine prefix in build/.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PYVER="${WIN_PYTHON_VERSION:-3.11.9}"
export WINEPREFIX="$ROOT/build/wine" WINEDEBUG=-all WINEARCH=win64
WINPY='C:\Python311\python.exe'
# Wine's Python can't start on some stdin/stdout handles, such as in CI or background
# shells, so it always gets a plain empty input and a pipe for its output.
run() { xvfb-run -a "$@" </dev/null 2>&1 | cat; }

if [ ! -f "$WINEPREFIX/drive_c/Python311/python.exe" ]; then
  INSTALLER="$ROOT/build/python-$PYVER-amd64.exe"
  mkdir -p build
  [ -f "$INSTALLER" ] || curl -fsSL -o "$INSTALLER" "https://www.python.org/ftp/python/$PYVER/python-$PYVER-amd64.exe"
  run wineboot -i >/dev/null 2>&1 || true
  run winecfg -v win10   # the Python installer refuses the default Windows 7 setting
  run wine "$INSTALLER" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_doc=0 \
    Include_launcher=0 TargetDir='C:\Python311'
fi
run wine "$WINPY" -m pip install --quiet --disable-pip-version-check -r requirements-build.txt

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' gridchess/__init__.py)"
IFS=. read -r V1 V2 V3 <<< "$VERSION"
cat > build/version_info.txt <<VERSIONINFO
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($V1, $V2, $V3, 0), prodvers=($V1, $V2, $V3, 0), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Shouku Games'),
      StringStruct('FileDescription', 'Grid Chess: Blitz Edition'),
      StringStruct('FileVersion', '$VERSION'),
      StringStruct('InternalName', 'GridChess'),
      StringStruct('LegalCopyright', 'Shawn Rapaz. GNU GPL v3.'),
      StringStruct('OriginalFilename', 'GridChess-v$VERSION.exe'),
      StringStruct('ProductName', 'Grid Chess: Blitz Edition'),
      StringStruct('ProductVersion', '$VERSION')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
VERSIONINFO

run wine "$WINPY" -m PyInstaller --noconfirm --clean --log-level WARN \
  --distpath "$(winepath -w "$ROOT/dist")" --workpath "$(winepath -w "$ROOT/build/pyi-win")" \
  "$(winepath -w "$ROOT/packaging/gridchess.spec")"

# Prove the .exe really runs, on a virtual display under Wine
SMOKE="$ROOT/build/smoke-win.txt"
rm -f "$SMOKE"
SDL_AUDIODRIVER=dummy GRIDCHESS_DATA='C:\users\Public\gridchess-check' \
  run wine "dist/GridChess-v$VERSION.exe" --smoke-test "$(winepath -w "$SMOKE")"
echo "Smoke test: $(cat "$SMOKE")"
echo "Built dist/GridChess-v$VERSION.exe ($(du -h "dist/GridChess-v$VERSION.exe" | cut -f1))"
