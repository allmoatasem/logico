#!/usr/bin/env bash
# Full build: Python binary → Electron app → DMG (macOS)
# Run this from the repo root on a Mac.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Step 1: Build Python backend ==="
bash "$REPO_ROOT/scripts/build-backend.sh"

echo ""
echo "=== Step 2: Install Electron dependencies ==="
cd "$REPO_ROOT/app"
npm install

echo ""
echo "=== Step 3: Build Electron app ==="
npm run dist:mac

echo ""
echo "=== Done ==="
echo "Installer: $REPO_ROOT/app/release/"
ls "$REPO_ROOT/app/release/"
