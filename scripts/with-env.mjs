// Cross-platform "VAR=value command..." runner (replaces cross-env, which relies on .bin symlinks).
import { spawn } from "node:child_process";
const args = process.argv.slice(2), env = { ...process.env };
while (args.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(args[0])) { const [k, ...v] = args.shift().split("="); env[k] = v.join("="); }
const p = spawn(args[0], args.slice(1), { stdio: "inherit", env, shell: false });
p.on("exit", (c) => process.exit(c ?? 1));
