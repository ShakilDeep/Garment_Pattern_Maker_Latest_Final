import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Dev-only bridge: POST /api runs the native `pf call` binary built from the Rust core.
 * Lets you work on the UI without a wasm toolchain:  cargo build --release && npm run dev
 */
function nativeBridge(): Plugin {
  const exe = process.platform === "win32" ? "pf.exe" : "pf";
  const bin = process.env.PF_BIN ?? resolve(import.meta.dirname, "..", "target", "release", exe);
  return {
    name: "pf-native-bridge",
    configureServer(server) {
      server.middlewares.use("/api", (req, res) => {
        if (req.method !== "POST") { res.statusCode = 405; res.end(); return; }
        if (!existsSync(bin)) {
          res.statusCode = 500;
          res.end(JSON.stringify({ ok: false, error: `native binary not found at ${bin}; run 'cargo build --release'` }));
          return;
        }
        const child = spawn(bin, ["call"]);
        let out = "";
        child.stdout.on("data", (d) => (out += d));
        child.on("close", () => { res.setHeader("content-type", "application/json"); res.end(out); });
        child.on("error", (e) => { res.statusCode = 500; res.end(JSON.stringify({ ok: false, error: String(e) })); });
        req.pipe(child.stdin);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), nativeBridge()],
  server: { port: 5173 },
  build: {
    rolldownOptions: {
      output: {
        // three.js only loads with the lazy DrapeView; give it its own cacheable chunk.
        codeSplitting: { groups: [{ name: "three", test: /node_modules[\\/]three[\\/]/ }] },
      },
    },
  },
});
