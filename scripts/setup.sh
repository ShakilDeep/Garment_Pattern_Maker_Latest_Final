#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."
cargo test --release
cd web && npm install && npm run build:wasm && npm run dev
