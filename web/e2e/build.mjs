import { build } from "/opt/npm-tools/node_modules/esbuild/lib/main.js";
import { writeFileSync, mkdirSync, rmSync } from "node:fs";
rmSync("/tmp/webdist", { recursive: true, force: true });
mkdirSync("/tmp/webdist", { recursive: true });
await build({
  entryPoints: ["/home/claude/patternforge/web/src/main.tsx"],
  bundle: true, splitting: true, format: "esm", outdir: "/tmp/webdist/assets", jsx: "automatic",
  external: ["three", "three/*", "xlsx"], nodePaths: ["/opt/npm-tools/node_modules"],
  define: { "import.meta.env.BASE_URL": '"/"', "process.env.NODE_ENV": '"production"' }, minify: false, logLevel: "info",
});
writeFileSync("/tmp/webdist/index.html", `<!doctype html><html><head><meta charset="utf-8"><title>PatternForge</title><link rel="stylesheet" href="/assets/main.css"></head><body><div id="root"></div><script type="module" src="/assets/main.js"></script></body></html>`);
