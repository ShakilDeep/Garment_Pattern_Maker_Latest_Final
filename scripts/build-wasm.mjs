// Builds the Rust core to WebAssembly and copies it to web/public/patternforge.wasm
import { execSync } from 'node:child_process';
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const run = (c) => execSync(c, { cwd: root, stdio: 'inherit' });
try { run('rustup target add wasm32-unknown-unknown'); } catch { console.warn('rustup not available; assuming target is installed'); }
run('cargo build --release --lib --target wasm32-unknown-unknown');
mkdirSync(resolve(root, 'web/public'), { recursive: true });
copyFileSync(resolve(root, 'target/wasm32-unknown-unknown/release/patternforge.wasm'), resolve(root, 'web/public/patternforge.wasm'));
console.log('OK -> web/public/patternforge.wasm');
