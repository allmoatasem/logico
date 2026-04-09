#!/usr/bin/env bash
# Build the Python backend into a self-contained binary for macOS.
# Output: app/resources/logico-server  (bundled into the Electron app by electron-builder)
#
# Requirements:
#   pip install pyinstaller
#   pip install -e .   (logico package itself)

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$REPO_ROOT/app/resources"

echo "Building Python backend with PyInstaller…"
cd "$REPO_ROOT"

pyinstaller \
  --noconfirm \
  --onedir \
  --name logico-server \
  --distpath "$OUT_DIR" \
  --workpath /tmp/pyinstaller-build \
  --specpath /tmp/pyinstaller-specs \
  --hidden-import logico \
  --hidden-import logico.cli \
  --hidden-import logico.server \
  --hidden-import logico.model \
  --hidden-import logico.mapping \
  --hidden-import logico.watcher \
  --hidden-import logico.sync.snapshot \
  --hidden-import logico.sync.diff \
  --hidden-import logico.dorico.dtn \
  --hidden-import logico.dorico.parser \
  --hidden-import logico.dorico.extractor \
  --hidden-import logico.dorico.writer \
  --hidden-import logico.staffpad.parser \
  --hidden-import logico.staffpad.extractor \
  --hidden-import logico.staffpad.writer \
  --hidden-import logico.logic.parser \
  --hidden-import logico.logic.extractor \
  --hidden-import logico.logic.writer \
  --hidden-import uvicorn \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import fastapi \
  --collect-all watchdog \
  src/logico/server.py

echo ""
echo "Done. Binary at: $OUT_DIR/logico-server/logico-server"
echo "Next: cd app && npm run dist:mac"
