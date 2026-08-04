#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

python3 -m PyInstaller --noconfirm --clean --onedir --windowed --name KiroClick main.py
APP_CONFIG="dist/KiroClick.app/Contents/MacOS"
cp config.json "$APP_CONFIG/config.json"
cp README.md "$APP_CONFIG/README.md"
mkdir -p "$APP_CONFIG/templates"
cp templates/README.txt "$APP_CONFIG/templates/README.txt"
find templates -maxdepth 1 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -exec cp {} "$APP_CONFIG/templates/" \;
echo "Built: $PROJECT_DIR/dist/KiroClick.app"
