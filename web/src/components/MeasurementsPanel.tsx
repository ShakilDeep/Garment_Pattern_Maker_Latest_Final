import { useRef, useState } from "react";
import type { Measurements } from "../types";
import { CM_PER_IN, MEASURE_GROUPS, SIZE_TEMPLATE_CSV, download, fmt } from "../util";

interface Props {
  values: Measurements;
  units: "cm" | "in";
  onUnits: (u: "cm" | "in") => void;
  onChange: (key: string, cm: number) => void;
  onImport: (text: string, units: "cm" | "in") => Promise<string[]>;
  opts: Record<string, number>;
  onOpts: (k: string, v: number) => void;
}

export default function MeasurementsPanel({ values, units, onUnits, onChange, onImport, opts, onOpts }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [paste, setPaste] = useState("");
  const [msgs, setMsgs] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const factor = units === "in" ? 1 / CM_PER_IN : 1;

  async function doImport(text: string) {
    try {
      const w = await onImport(text, units);
      setMsgs(w.length ? w : ["Imported."]);
    } catch (e) {
      setMsgs([e instanceof Error ? e.message : String(e)]);
    }
  }

  return (
    <section className="panel" aria-label="Measurements">
      <div className="panel-head">
        <h2>Measurements</h2>
        <div className="seg" role="group" aria-label="Units">
          {(["cm", "in"] as const).map((u) => (
            <button key={u} className={units === u ? "on" : ""} onClick={() => onUnits(u)} aria-pressed={units === u}>{u}</button>
          ))}
        </div>
      </div>

      <div className="import-row">
        <button className="btn" onClick={() => fileRef.current?.click()}>Import file…</button>
        <button className="btn ghost" onClick={() => setOpen((o) => !o)} aria-expanded={open}>Paste</button>
        <button className="btn ghost" onClick={() => download("measurements-template.csv", SIZE_TEMPLATE_CSV, "text/csv")}>Template</button>
        <input
          ref={fileRef} type="file" accept=".csv,.txt,.json" hidden data-testid="measure-file"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (f) await doImport(await f.text());
            e.target.value = "";
          }}
        />
      </div>
      {open && (
        <div className="paste">
          <textarea
            value={paste} onChange={(e) => setPaste(e.target.value)} rows={5} spellCheck={false} data-testid="measure-paste"
            placeholder={"bust,92\nwaist,74\nhip,98\n— or a JSON object —"}
          />
          <button className="btn" onClick={() => doImport(paste)} data-testid="measure-apply">Apply</button>
        </div>
      )}
      {msgs.length > 0 && (
        <ul className="msgs" role="status">{msgs.slice(0, 6).map((m, i) => <li key={i}>{m}</li>)}</ul>
      )}

      {MEASURE_GROUPS.map((g) => (
        <fieldset key={g.title}>
          <legend>{g.title}</legend>
          {g.keys.map(([k, label]) => (
            <label key={k} className="field">
              <span>{label}</span>
              <input
                type="number" step={units === "in" ? 0.125 : 0.5} min={1} data-testid={`m-${k}`}
                value={Number.isFinite(values[k]) ? Number((values[k] * factor).toFixed(2)) : ""}
                onChange={(e) => { const v = parseFloat(e.target.value); if (Number.isFinite(v) && v > 0) onChange(k, v / factor); }}
              />
              <em>{units}</em>
            </label>
          ))}
        </fieldset>
      ))}

      <fieldset>
        <legend>Ease & allowances (cm)</legend>
        {([["bust_ease", "Bust ease"], ["waist_ease", "Waist ease"], ["hip_ease", "Hip ease"], ["cap_ease", "Sleeve cap ease"], ["sa", "Seam allowance"], ["hem_sa", "Hem allowance"]] as const).map(([k, label]) => (
          <label key={k} className="field">
            <span>{label}</span>
            <input type="number" step={0.5} min={0} value={opts[k]} onChange={(e) => { const v = parseFloat(e.target.value); if (Number.isFinite(v) && v >= 0) onOpts(k, v); }} />
            <em>cm</em>
          </label>
        ))}
      </fieldset>
      <p className="hint">Bust {fmt(values.bust)} · waist {fmt(values.waist)} · hip {fmt(values.hip)} cm</p>
    </section>
  );
}
