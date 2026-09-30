$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $projectRoot 'backend')
conda run --no-capture-output -n patter-codex python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
