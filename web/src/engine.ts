/** Engine = the Rust core. Production: WebAssembly. Dev fallback: HTTP bridge to the native binary. */
export interface Engine {
  kind: "wasm" | "native-bridge";
  call<T = any>(req: Record<string, unknown>): Promise<T>;
}

interface WasmExports {
  memory: WebAssembly.Memory;
  pf_alloc(len: number): number;
  pf_free(ptr: number, cap: number): void;
  pf_call(ptr: number, len: number): number;
}

const enc = new TextEncoder();
const dec = new TextDecoder();

async function loadWasm(url: string): Promise<Engine> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`wasm not found (${resp.status})`);
  const bytes = await resp.arrayBuffer();
  const { instance } = await WebAssembly.instantiate(bytes, {});
  const ex = instance.exports as unknown as WasmExports;
  if (typeof ex.pf_call !== "function") throw new Error("wasm module does not export pf_call");
  return {
    kind: "wasm",
    async call(req) {
      const input = enc.encode(JSON.stringify(req));
      const inPtr = ex.pf_alloc(input.length);
      new Uint8Array(ex.memory.buffer, inPtr, input.length).set(input);
      const outPtr = ex.pf_call(inPtr, input.length);
      ex.pf_free(inPtr, input.length);
      const len = new DataView(ex.memory.buffer).getUint32(outPtr, true);
      const text = dec.decode(new Uint8Array(ex.memory.buffer, outPtr + 4, len));
      ex.pf_free(outPtr, len + 4);
      return parse(text);
    },
  };
}

function parse(text: string): any {
  const j = JSON.parse(text);
  if (!j.ok) throw new Error(j.error ?? "engine error");
  return j;
}

async function loadBridge(): Promise<Engine> {
  const probe = await fetch("/api", { method: "POST", body: JSON.stringify({ op: "version" }) });
  if (!probe.ok) throw new Error(`bridge unavailable (${probe.status})`);
  parse(await probe.text());
  return {
    kind: "native-bridge",
    async call(req) {
      const r = await fetch("/api", { method: "POST", body: JSON.stringify(req) });
      return parse(await r.text());
    },
  };
}

let cached: Promise<Engine> | null = null;
export function getEngine(): Promise<Engine> {
  if (!cached) {
    const base = import.meta.env.BASE_URL ?? "/";
    const preferNative = new URLSearchParams(location.search).get("engine") === "native";
    cached = (async () => {
      const errors: string[] = [];
      const order = preferNative ? [() => loadBridge(), () => loadWasm(`${base}patternforge.wasm`)] : [() => loadWasm(`${base}patternforge.wasm`), () => loadBridge()];
      for (const f of order) {
        try { return await f(); } catch (e) { errors.push(String(e instanceof Error ? e.message : e)); }
      }
      throw new Error(
        "The Rust engine could not be loaded.\n" + errors.join("\n") +
        "\n\nBuild it once:  npm run build:wasm   (needs rustup target add wasm32-unknown-unknown)\n" +
        "or for development:  cargo build --release  then  npm run dev  (native bridge)."
      );
    })();
  }
  return cached;
}
