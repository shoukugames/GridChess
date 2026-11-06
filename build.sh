#!/usr/bin/env bash
# Builds both installers into dist/: the Debian package and the Windows .exe
set -euo pipefail
cd "$(dirname "$0")"
packaging/build_linux.sh
packaging/build_windows.sh
