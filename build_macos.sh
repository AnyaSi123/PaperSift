#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$(uname -s)" != "Darwin" ]; then
  echo "Build the macOS package on a Mac."
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "Create .venv first: python3 -m venv .venv"
  exit 1
fi
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m PyInstaller --noconfirm PaperSift.spec
# ditto preserves executable permissions and the bundle's symbolic links.
ditto -c -k --sequesterRsrc --keepParent dist/PaperSift.app dist/PaperSift-macOS.zip
echo "Ready: dist/PaperSift-macOS.zip"
