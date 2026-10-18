# PatternForge

Garment pattern-design app inspired by Optitex PDS 2D/3D. Rust core (zero dependencies, compiled to WebAssembly) + React/TypeScript/three.js frontend.

## Features
- **Measurements** import (CSV/JSON/paste) → auto-drafted bodice, skirt, trousers; editable in 2D (nodes, handles, seam allowance, darts, notches, undo/redo).
- **Open Optitex .PDS files**: reads the binary geometry of PDS 21.4 files (validated against the file's own XML: perimeter ≤0.3%, area ≤0.6%), all graded sizes. Falls back to the base-size marker preview when the binary part can't be validated (e.g. a file mangled by upload).
- **Spec sheets (POM charts)**: import Excel/CSV/pasted graded measurement charts; draft a production-style **shirt** (FRT, back, yoke, collar, stand bands, sleeve) or **pant** (waistband, front/back, pocket bag, facings, drawstring) for any size, graded across the sheet's sizes.
- **Grading** with size overlay; **Marker (nesting)** on a given fabric width with a no-overlap checker, efficiency, SVG and DXF export.
- **3D drape** preview (cloth simulation on a parametric body).
- **Export**: SVG, AAMA/ASTM DXF (Optitex-importable, unverified), marker SVG/DXF.
- **Native .PDS export is NOT implemented** — see `docs/PDS-FORMAT.md` (what is proven) and `docs/PDS-SAMPLES.md` (what is needed).

## Windows 11 + WSL (Ubuntu) quick start
```bash
sudo apt update && sudo apt install -y build-essential curl
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
rustup target add wasm32-unknown-unknown
cd /mnt/f/optitex
cargo test --release          # 98+ tests
cd web && npm install && npm run build:wasm && npm run dev
```
(PowerShell users: `scripts\setup.ps1`.) Builds on `/mnt/f` are slow; `export CARGO_TARGET_DIR=$HOME/pf-target` helps.
Excel import needs the `xlsx` npm package (installed by `npm install`).

## Docs
`docs/SAMPLE-FINDINGS.md` (your sample files), `docs/PDS-FORMAT.md`, `docs/PDS-IMPORT.md`, `docs/SPEC-IMPORT.md`, `docs/GARMENTS.md`, `docs/MARKER.md`, `docs/INVESTIGATION.md`.

## Status / honesty
Rust: all tests pass. Browser end-to-end (`web/e2e/`, needs playwright; uses the native bridge): 27 + 12 checks pass with the sample files. The web typecheck (`npm run typecheck`) and the three.js viewer have not been run here (no npm registry access) — run `npm install` and `npm run typecheck` first and send me any errors.
Drafted shirt/pant patterns are parametric re-creations (sew dimensions within ~3% of the sample PDS), not the factory's hand-drawn curves. Marker nesting is heuristic.

-----------Run-------------------
cd /mnt/f/optitex/web
npm install
npm run typecheck
npm run build:wasm
npm run dev