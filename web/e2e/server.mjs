import http from "node:http";
import { spawn } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { extname, join } from "node:path";
const root = "/tmp/webdist", pf = "/home/claude/patternforge/target/release/pf";
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css" };
http.createServer((req, res) => {
  if (req.url === "/api" && req.method === "POST") {
    const c = spawn(pf, ["call"]); let out = "";
    c.stdout.on("data", (d) => (out += d)); c.on("close", () => { res.setHeader("content-type", "application/json"); res.end(out); });
    req.pipe(c.stdin); return;
  }
  let p = req.url.split("?")[0]; if (p === "/") p = "/index.html";
  const f = join(root, p);
  if (!existsSync(f)) { res.statusCode = 404; res.end("nf"); return; }
  res.setHeader("content-type", types[extname(f)] ?? "application/octet-stream"); res.end(readFileSync(f));
}).listen(5199, () => console.log("up"));
