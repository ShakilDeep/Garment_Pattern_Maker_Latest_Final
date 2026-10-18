# Windows 11 PowerShell: one-time setup + run
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { winget install Rustlang.Rustup }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { winget install OpenJS.NodeJS.LTS }
cargo test --release
Set-Location web
npm install
npm run build:wasm
npm run dev
