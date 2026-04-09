# Build the Python backend into a self-contained binary for Windows.
# Output: app\resources\logico-server\logico-server.exe
#
# Requirements:
#   pip install pyinstaller
#   pip install -e .

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $RepoRoot "app\resources"

Write-Host "Building Python backend with PyInstaller..." -ForegroundColor Cyan
Set-Location $RepoRoot

pyinstaller `
  --noconfirm `
  --onedir `
  --name logico-server `
  --distpath $OutDir `
  --workpath "$env:TEMP\pyinstaller-build" `
  --specpath "$env:TEMP\pyinstaller-specs" `
  --hidden-import logico `
  --hidden-import logico.cli `
  --hidden-import logico.server `
  --hidden-import logico.model `
  --hidden-import logico.mapping `
  --hidden-import logico.watcher `
  --hidden-import logico.sync.snapshot `
  --hidden-import logico.sync.diff `
  --hidden-import logico.dorico.dtn `
  --hidden-import logico.dorico.parser `
  --hidden-import logico.dorico.extractor `
  --hidden-import logico.dorico.writer `
  --hidden-import logico.staffpad.parser `
  --hidden-import logico.staffpad.extractor `
  --hidden-import logico.staffpad.writer `
  --hidden-import logico.logic.parser `
  --hidden-import logico.logic.extractor `
  --hidden-import logico.logic.writer `
  --hidden-import uvicorn `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.loops `
  --hidden-import uvicorn.loops.auto `
  --hidden-import uvicorn.protocols `
  --hidden-import uvicorn.protocols.http `
  --hidden-import uvicorn.protocols.http.auto `
  --hidden-import uvicorn.protocols.websockets `
  --hidden-import uvicorn.protocols.websockets.auto `
  --hidden-import uvicorn.lifespan `
  --hidden-import uvicorn.lifespan.on `
  --hidden-import fastapi `
  --collect-all watchdog `
  src\logico\server.py

Write-Host ""
Write-Host "Done. Binary at: $OutDir\logico-server\logico-server.exe" -ForegroundColor Green
Write-Host "Next: cd app && npm run dist:win"
