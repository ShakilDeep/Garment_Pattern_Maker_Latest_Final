import { useRef, useState } from "react";
import { fmt } from "../util";

export interface SpecRow { code: string; name: string; name_local: string; values: (number | null)[]; tol_plus: number | null; tol_minus: number | null; canonical?: string | null; map_to?: string | null }
export interface SpecT { style: string; description: string; brand: string; fit: string; season: string; sizes: string[]; base_size: string; rows: SpecRow[] }
export interface SpecResult { spec: SpecT; warnings: string[] }
export interface FitRowT { code: string; name: string; target: number; measured: number; error: number; tol_plus: number; tol_minus: number; ok: boolean; input_only: boolean }
export interface FitReport { size: string; rows: FitRowT[]; max_abs_error: number; converged: boolean; perSize: { label: string; max_abs_error: number; converged: boolean }[]; warnings: string[] }

/** Guess pant vs shirt from the style description and the POM names/codes. */
export function guessKind(sp: SpecT): "pant" | "shirt" {
  const count = (t: string, re: RegExp) => (t.match(re) || []).length;
  const PANT = /\b(pants?|trousers?|jeans?|shorts?|skirt|bottoms?|inseam|rise|leg opening|thigh|crotch)\b/gi;
  const SHIRT = /\b(shirt|top|blouse|polo|tee|chest|sleeve|collar|cuff|shoulder|armhole|bicep|yoke|placket)\b/gi;
  const head = `${sp.description} ${sp.fit}`;
  const names = sp.rows.map((r) => r.name).join(" ");
  // header text (garment description) counts triple; a lone "waist" row no longer makes a shirt a pant
  const p = count(head, PANT) * 3 + count(names, PANT);
  const sh = count(head, SHIRT) * 3 + count(names, SHIRT);
  if (p === sh) return /waist/i.test(names) ? "pant" : "shirt";
  return sh > p ? "shirt" : "pant";
}

interface Props {
  call: <T = any>(req: Record<string, unknown>) => Promise<T>;
  onPds: (r: any) => Promise<void>;
  spec: SpecResult | null;
  onSpec: (s: SpecResult) => void;
  onDraftFromSpec?: (size: string, kind: "pant" | "shirt", spec?: SpecResult) => void | Promise<void>;
  fit?: FitReport | null;
  onError: (m: string) => void;
}

function toB64(buf: ArrayBuffer): string {
  const u8 = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000));
  return btoa(s);
}

export default function ImportView({ call, onPds, spec, onSpec, onDraftFromSpec, fit, onError }: Props) {
  const pdsRef = useRef<HTMLInputElement>(null);
  const specRef = useRef<HTMLInputElement>(null);
  const [pdsInfo, setPdsInfo] = useState<{ source: string; style: string; sizes: string[]; warnings: string[] } | null>(null);
  const [paste, setPaste] = useState("");
  const [sheets, setSheets] = useState<{ name: string; text: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [draftSize, setDraftSize] = useState<string>("");
  const [kind, setKind] = useState<"pant" | "shirt">("pant");

  async function loadPds(f: File) {
    setBusy(true);
    try {
      const r = await call<any>({ op: "import_pds", data_b64: toB64(await f.arrayBuffer()) });
      setPdsInfo({ source: r.source, style: r.style?.name ?? r.style ?? f.name, sizes: r.sizes ?? [], warnings: r.warnings ?? [] });
      await onPds(r);
    } catch (e) { onError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }

  async function parseText(text: string) {
    setBusy(true);
    try {
      const r = await call<any>({ op: "parse_spec", text });
      const res: SpecResult = { spec: r.spec, warnings: r.warnings ?? [] };
      onSpec(res);
      setDraftSize(r.spec.base_size);
      const k = guessKind(r.spec);
      setKind(k);
      // Draw the pattern straight away from the imported measurements (exact-fit solver).
      if (onDraftFromSpec) await onDraftFromSpec(r.spec.base_size, k, res);
    } catch (e) { onError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }

  async function loadSpecFile(f: File) {
    const lower = f.name.toLowerCase();
    if (lower.endsWith(".xls")) { onError("Old .xls files are not supported. In Excel use File > Save As > .xlsx and import that."); return; }
    if (lower.endsWith(".xlsx") || lower.endsWith(".xlsm")) {
      try {
        const r = await call<{ sheets: { name: string; tsv: string }[] }>({ op: "xlsx_to_tsv", data_b64: toB64(await f.arrayBuffer()) });
        const all = r.sheets.filter((x) => x.tsv.trim()).map((x) => ({ name: x.name.trim(), text: x.tsv }));
        // Try every sheet and keep the ones that really contain a measurement table
        // (a workbook can hold photos, notes or reports next to the spec).
        const good: { name: string; text: string }[] = [];
        for (const sh of all) {
          try { const r = await call<any>({ op: "parse_spec", text: sh.text }); if (r?.spec?.rows?.length) good.push(sh); } catch { /* not a spec sheet */ }
        }
        if (!good.length) {
          onError(`No measurement table found in "${f.name}" (sheets: ${all.map((x) => x.name).join(", ") || "none"}). A spec sheet needs a header row like "POM | Measurement points | S | M | L ..." followed by one row per measurement.`);
          return;
        }
        setSheets(good);
        const pick = good.find((s) => /graded/i.test(s.name)) ?? good[0];
        await parseText(pick.text);
      } catch (e) { onError("Could not read the Excel file: " + (e instanceof Error ? e.message : String(e))); }
    } else {
      setSheets([]);
      await parseText(await f.text());
    }
  }

  const s = spec?.spec;
  return (
    <div className="import-view" data-testid="import-view">
      <section className="card">
        <h3>Open an Optitex .PDS file</h3>
        <p className="hint">Reads the style, sizes, pieces and geometry. If the binary part validates against the file's own XML, you get every graded size; otherwise the base-size marker outlines are shown.</p>
        <input ref={pdsRef} type="file" accept=".pds,.PDS" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void loadPds(f); e.target.value = ""; }} data-testid="pds-file" />
        <button className="btn primary" disabled={busy} onClick={() => pdsRef.current?.click()}>Choose .PDS file…</button>
        {pdsInfo && (
          <div className="result" data-testid="pds-info">
            <b>{pdsInfo.style}</b> · {pdsInfo.sizes.join(", ")} · <span className={pdsInfo.source === "pds_binary" ? "ok" : "warn-text"}>{pdsInfo.source === "pds_binary" ? "decoded from binary (validated)" : "marker preview only"}</span>
            <ul className="warnlist">{pdsInfo.warnings.slice(0, 8).map((w, i) => <li key={i}>{w}</li>)}</ul>
          </div>
        )}
      </section>

      <section className="card">
        <h3>Garment spec sheet (POM chart)</h3>
        <p className="hint">Excel (.xlsx), CSV/TSV, or paste straight from Excel. Expected: <code>POM | Measurement | … | XS | S | M … | tolerance</code>.</p>
        <input ref={specRef} type="file" accept=".xlsx,.xlsm,.xls,.csv,.tsv,.txt" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void loadSpecFile(f); e.target.value = ""; }} data-testid="spec-file" />
        <div className="btn-row">
          <button className="btn primary" disabled={busy} onClick={() => specRef.current?.click()}>Choose spec file…</button>
          {sheets.length > 1 && (
            <select aria-label="Sheet" onChange={(e) => { const sh = sheets.find((x) => x.name === e.target.value); if (sh) void parseText(sh.text); }}>
              {sheets.map((x) => <option key={x.name}>{x.name}</option>)}
            </select>
          )}
        </div>
        <textarea rows={4} placeholder="…or paste the spec table here" value={paste} onChange={(e) => setPaste(e.target.value)} data-testid="spec-paste" />
        <button className="btn" disabled={busy || !paste.trim()} onClick={() => void parseText(paste)}>Parse pasted text</button>

        {s && spec && (
          <div className="result" data-testid="spec-result">
            <div className="spec-head"><b>{s.style || "(no style #)"}</b> {s.description} · {s.brand} · {s.fit} · {s.season} · base size <b>{s.base_size}</b></div>
            {spec.warnings.length > 0 && <ul className="warnlist">{spec.warnings.slice(0, 10).map((w, i) => <li key={i}>{w}</li>)}</ul>}
            <div className="table-wrap">
              <table className="spec-table">
                <thead><tr><th>POM</th><th>Measurement point</th>{s.sizes.map((z) => <th key={z} className={z === s.base_size ? "base" : ""}>{z}</th>)}<th>Tol ±</th></tr></thead>
                <tbody>
                  {s.rows.map((r) => (
                    <tr key={r.code + r.name}>
                      <td>{r.code}</td><td title={r.name_local}>{r.name}</td>
                      {r.values.map((v, i) => <td key={i} className={s.sizes[i] === s.base_size ? "base" : ""}>{v == null ? "" : fmt(v, 2)}</td>)}
                      <td>{r.tol_plus == null ? "" : fmt(r.tol_plus, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {fit && (
              <div className="fit-report" data-testid="fit-report">
                <h4>Spec vs measured on the drafted pattern (size {fit.size})</h4>
                <p className={fit.converged ? "ok" : "warn-text"}>
                  {fit.converged ? "All measurements match the spec" : "Some measurements are outside tolerance"} · worst error {fit.max_abs_error.toFixed(3)} cm
                  {fit.perSize.length > 1 && <> · per size: {fit.perSize.map((z) => `${z.label} ${z.max_abs_error.toFixed(3)}`).join(", ")}</>}
                </p>
                <div className="table-wrap">
                  <table className="spec-table fit-table">
                    <thead><tr><th>POM</th><th>Measurement point</th><th>Spec</th><th>Measured</th><th>Diff</th><th>Tol ±</th><th></th></tr></thead>
                    <tbody>
                      {fit.rows.map((r) => (
                        <tr key={r.code + r.name} className={r.ok ? "" : "bad"}>
                          <td>{r.code}</td><td>{r.name}{r.input_only ? " (input, not measured)" : ""}</td>
                          <td>{fmt(r.target, 2)}</td><td>{fmt(r.measured, 2)}</td><td>{r.error >= 0 ? "+" : ""}{r.error.toFixed(3)}</td>
                          <td>{fmt(Math.max(r.tol_plus, r.tol_minus), 1)}</td><td>{r.ok ? "OK" : "OUT"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {onDraftFromSpec && (
              <div className="btn-row">
                <label className="inline">Draft pattern for size
                  <select value={draftSize || s.base_size} onChange={(e) => setDraftSize(e.target.value)}>{s.sizes.map((z) => <option key={z}>{z}</option>)}</select>
                </label>
                <label className="inline">Garment
                  <select value={kind} onChange={(e) => setKind(e.target.value as "pant" | "shirt")} data-testid="spec-kind"><option value="pant">Pant (waistband, pockets)</option><option value="shirt">Shirt (yoke, collar, sleeve)</option></select>
                </label>
                <button className="btn primary" onClick={() => void onDraftFromSpec(draftSize || s.base_size, kind, spec)} data-testid="draft-from-spec">Redraw from spec</button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
