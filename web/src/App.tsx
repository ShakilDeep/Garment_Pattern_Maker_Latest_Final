import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getEngine, type Engine } from "./engine";
import type { Check, DrapeResult, GeoPiece, GradedSize, Measurements, PatternT } from "./types";
import MeasurementsPanel from "./components/MeasurementsPanel";
import SourcePanel, { type PdsSource } from "./components/SourcePanel";
import PatternCanvas, { type EditAction, type Overlay, type Selection } from "./components/PatternCanvas";
import Inspector from "./components/Inspector";
import GradingView, { SIZE_COLORS } from "./components/GradingView";
import ErrorBoundary from "./components/ErrorBoundary";
import AccuracyView, { type AuditEntry, type ValIssueT } from "./components/AccuracyView";
import ImportView, { type SpecResult, type FitReport } from "./components/ImportView";
import MarkerView from "./components/MarkerView";
import { download } from "./util";

const DrapeView = lazy(() => import("./components/DrapeView"));

type Tab = "pattern" | "grading" | "drape" | "import" | "marker" | "accuracy";
const GARMENTS: { id: string; label: string }[] = [
  { id: "bodice", label: "Bodice + sleeve" },
  { id: "skirt", label: "Straight skirt" },
  { id: "trousers", label: "Trousers" },
];
const DEFAULT_OPTS: Record<string, number> = { bust_ease: 8, waist_ease: 6, hip_ease: 5, cap_ease: 3.5, sa: 1, hem_sa: 3 };

function errMsg(e: unknown) { return e instanceof Error ? e.message : String(e); }

export default function App() {
  const [engine, setEngine] = useState<Engine | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [garment, setGarment] = useState("bodice");
  const [meas, setMeas] = useState<Measurements>({});
  const [units, setUnits] = useState<"cm" | "in">("cm");
  const [opts, setOpts] = useState<Record<string, number>>(DEFAULT_OPTS);

  const [pattern, setPattern] = useState<PatternT | null>(null);
  const [geo, setGeo] = useState<GeoPiece[]>([]);
  const [checks, setChecks] = useState<Check[]>([]);
  const [edited, setEdited] = useState(false);
  const editedRef = useRef(false); // read by timers so they never act on a stale `edited`
  const [stale, setStale] = useState(false);
  const [selection, setSelection] = useState<Selection>({ piece: null, node: null });
  const [histVer, setHistVer] = useState(0);

  const [tab, setTab] = useState<Tab>("import");
  const [showCut, setShowCut] = useState(true);
  const [showNodes, setShowNodes] = useState(true);
  const [showSeamTags, setShowSeamTags] = useState(false);
  const [showSizes, setShowSizes] = useState(true);

  const [steps, setSteps] = useState<number[]>([-1, 0, 1]);
  const [sizes, setSizes] = useState<GradedSize[]>([]);
  const [sizeGeos, setSizeGeos] = useState<Record<string, GeoPiece[]>>({});
  const [gradeBusy, setGradeBusy] = useState(false);

  const [drape, setDrape] = useState<DrapeResult | null>(null);
  const [drapeBusy, setDrapeBusy] = useState(false);
  const [drapeStale, setDrapeStale] = useState(false);

  const [pdsMsg, setPdsMsg] = useState<string | null>(null);
  const [spec, setSpec] = useState<SpecResult | null>(null);
  const [fit, setFit] = useState<FitReport | null>(null);
  const [issues, setIssues] = useState<ValIssueT[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>(() => { try { return JSON.parse(localStorage.getItem("pf-audit") ?? "[]"); } catch { return []; } });
  const [gate, setGate] = useState<{ file: string; blockers: string[]; run: () => Promise<void> } | null>(null);
  const [gateReason, setGateReason] = useState("");
  const [panelMode, setPanelMode] = useState<"start" | "body" | "spec" | "pds">("start");
  const panelModeRef = useRef<"start" | "body" | "spec" | "pds">("start");
  panelModeRef.current = panelMode;
  const [specSize, setSpecSize] = useState("");
  const [specKind, setSpecKind] = useState<"pant" | "shirt">("pant");
  const [pdsSrc, setPdsSrc] = useState<PdsSource | null>(null);
  const pdsPatterns = useRef<{ size: string; pattern: PatternT }[]>([]);
  const editTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const patRef = useRef<PatternT | null>(null);
  const past = useRef<PatternT[]>([]);
  const future = useRef<PatternT[]>([]);
  const queue = useRef<{ action: EditAction; live: boolean }[]>([]);
  const running = useRef(false);
  const engineRef = useRef<Engine | null>(null);
  const initDone = useRef(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDetailsElement>(null);
  const closeMenu = () => { if (menuRef.current) menuRef.current.open = false; };

  // close the export menu on outside click / Escape
  useEffect(() => {
    const onDown = (e: MouseEvent) => { if (menuRef.current?.open && !menuRef.current.contains(e.target as Node)) menuRef.current.open = false; };
    const onEsc = (e: KeyboardEvent) => { if (e.key === "Escape" && menuRef.current?.open) menuRef.current.open = false; };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onEsc); };
  }, []);

  // ---- engine boot ----
  useEffect(() => {
    getEngine().then(async (e) => {
      engineRef.current = e;
      const d = await e.call<{ measurements: Measurements }>({ op: "defaults" });
      setMeas(d.measurements);
      setEngine(e);
    }).catch((e) => setFatal(errMsg(e)));
  }, []);

  const call = useCallback(async <T,>(req: Record<string, unknown>): Promise<T> => {
    const e = engineRef.current;
    if (!e) throw new Error("engine not ready");
    return e.call<T>(req);
  }, []);

  const installPattern = useCallback(async (p: PatternT) => {
    patRef.current = p;
    setPattern(p);
    const g = await call<{ pieces: GeoPiece[] }>({ op: "geometry", pattern: p });
    setGeo(g.pieces);
    try { const v = await call<{ issues: ValIssueT[] }>({ op: "validate", pattern: p }); setIssues(v.issues ?? []); } catch { setIssues([]); }
  }, [call]);

  const generate = useCallback(async (g: string, m: Measurements, o: Record<string, number>) => {
    try {
      const r = await call<{ pattern: PatternT; checks: Check[] }>({ op: "draft", garment: g, measurements: m, opts: o });
      past.current = []; future.current = []; setHistVer((v) => v + 1);
      await installPattern(r.pattern);
      setChecks(r.checks);
      setEdited(false); editedRef.current = false;
      setStale(false);
      setSizes([]); setSizeGeos({});
      setDrapeStale(true);
      setSelection({ piece: r.pattern.pieces[0]?.name ?? null, node: null });
      setError(null);
    } catch (e) {
      setError(errMsg(e));
    }
  }, [call, installPattern]);

  // Nothing is drawn at start-up: the user imports a spec sheet / PDS, or opts in to body measurements.
  const startBody = useCallback(() => {
    setPanelMode("body");
    const need = !patRef.current;          // keep an imported / spec drawing; only draw the block if nothing is loaded
    initDone.current = true;
    if (need) void generate(garment, meas, opts);
    setTab("pattern");
  }, [generate, garment, meas, opts]);

  // regenerate (debounced) when inputs change and there are no manual edits to lose
  useEffect(() => {
    if (!initDone.current) return;
    const t = setTimeout(() => {
      if (editedRef.current) { if (panelModeRef.current === "body") setStale(true); return; }
      void generate(garment, meas, opts);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meas, opts]);

  function switchGarment(g: string) {
    if (g === garment) return;
    if (edited && !window.confirm("Switching garment replaces the pattern and discards your manual edits. Continue?")) return;
    setGarment(g);
    void generate(g, meas, opts);
  }

  // ---- editing ----
  const pump = useCallback(async () => {
    if (running.current) return;
    running.current = true;
    try {
      while (queue.current.length) {
        const { action } = queue.current.shift()!;
        const cur = patRef.current;
        if (!cur) break;
        try {
          const r = await call<{ pattern: PatternT }>({ op: "edit", pattern: cur, action });
          await installPattern(r.pattern);
          setEdited(true); editedRef.current = true;
          setDrapeStale(true);
          setSizes((s) => (s.length ? [] : s));
          setError(null);
        } catch (e) {
          setError(errMsg(e));
          queue.current = [];
        }
      }
    } finally {
      running.current = false;
    }
  }, [call, installPattern]);

  const beginHistory = useCallback(() => {
    if (!patRef.current) return;
    past.current.push(structuredClone(patRef.current));
    if (past.current.length > 100) past.current.shift();
    future.current = [];
    setHistVer((v) => v + 1);
  }, []);

  const applyEdit = useCallback((action: EditAction, live: boolean) => {
    const q = queue.current;
    const last = q[q.length - 1];
    if (live && last?.live && last.action.type === action.type && last.action.piece === action.piece && last.action.index === action.index) q[q.length - 1] = { action, live };
    else q.push({ action, live });
    void pump();
  }, [pump]);

  const inspectorEdit = useCallback((a: EditAction) => { beginHistory(); applyEdit(a, false); }, [beginHistory, applyEdit]);

  const undo = useCallback(async () => {
    const prev = past.current.pop();
    if (!prev || !patRef.current) return;
    future.current.push(structuredClone(patRef.current));
    await installPattern(prev);
    setHistVer((v) => v + 1);
    setDrapeStale(true);
    setEdited(past.current.length > 0 || edited);
  }, [installPattern, edited]);

  const redo = useCallback(async () => {
    const nxt = future.current.pop();
    if (!nxt || !patRef.current) return;
    past.current.push(structuredClone(patRef.current));
    await installPattern(nxt);
    setHistVer((v) => v + 1);
    setDrapeStale(true);
  }, [installPattern]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); void (e.shiftKey ? redo() : undo()); }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); void redo(); }
      else if ((e.key === "Delete" || e.key === "Backspace") && selection.piece && selection.node !== null) {
        e.preventDefault();
        inspectorEdit({ type: "delete_node", piece: selection.piece, index: selection.node });
        setSelection({ piece: selection.piece, node: null });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, selection, inspectorEdit]);

  // ---- measurements ----
  const importMeasurements = useCallback(async (text: string, u: "cm" | "in") => {
    const r = await call<{ measurements: Measurements; warnings: string[] }>({ op: "parse_measurements", text, units: u, base: meas });
    setMeas(r.measurements);
    return r.warnings;
  }, [call, meas]);

  // ---- grading ----
  const runGrade = useCallback(async () => {
    setGradeBusy(true);
    try {
      const r = await call<{ sizes: GradedSize[] }>({ op: "grade", garment, measurements: meas, opts, steps });
      const geos: Record<string, GeoPiece[]> = {};
      for (const s of r.sizes) geos[s.label] = (await call<{ pieces: GeoPiece[] }>({ op: "geometry", pattern: s.pattern })).pieces;
      setSizes(r.sizes);
      setSizeGeos(geos);
      setError(null);
    } catch (e) { setError(errMsg(e)); } finally { setGradeBusy(false); }
  }, [call, garment, meas, opts, steps]);

  const overlays: Overlay[] = useMemo(
    () => (showSizes ? sizes.map((s, i) => ({ label: s.label, color: SIZE_COLORS[i % SIZE_COLORS.length], geo: sizeGeos[s.label] ?? [] })) : []),
    [sizes, sizeGeos, showSizes]
  );

  // ---- PDS import ----
  const onPdsImported = useCallback(async (r: { pattern: PatternT; patterns?: { size: string; pattern: PatternT }[]; sizes?: string[]; base_size?: string; size?: string; style?: any; source?: string }) => {
    editedRef.current = true;
    past.current = []; future.current = []; setHistVer((v) => v + 1);
    await installPattern(r.pattern);
    setChecks([]); setEdited(true); editedRef.current = true; setStale(false); setDrapeStale(true);
    setSelection({ piece: r.pattern.pieces[0]?.name ?? null, node: null });
    const list = r.patterns ?? [];
    if (list.length) {
      const geos: Record<string, GeoPiece[]> = {};
      for (const e of list) geos[e.size] = (await call<{ pieces: GeoPiece[] }>({ op: "geometry", pattern: e.pattern })).pieces;
      const bi = Math.max(0, list.findIndex((e) => e.size === (r.base_size ?? r.size)));
      setSizes(list.map((e, i) => ({ label: e.size, step: i - bi, measurements: {}, pattern: e.pattern, table: [] })));
      setSizeGeos(geos);
    } else { setSizes([]); setSizeGeos({}); }
    pdsPatterns.current = list;
    setPdsSrc({ style: r.style?.name ?? (typeof r.style === "string" ? r.style : "PDS file"), sizes: r.sizes ?? list.map((e) => e.size), size: r.base_size ?? r.size ?? list[0]?.size ?? "", source: r.source ?? "" });
    setFit(null); setPanelMode("pds");
    setError(null); setTab("pattern");
  }, [call, installPattern]);

  const onPdsSize = useCallback(async (z: string) => {
    const e = pdsPatterns.current.find((x) => x.size === z);
    if (!e) return;
    past.current = []; future.current = []; setHistVer((v) => v + 1);
    await installPattern(e.pattern);
    setPdsSrc((p) => (p ? { ...p, size: z } : p));
  }, [installPattern]);

  const draftFromSpec = useCallback(async (size: string, kind: "pant" | "shirt", specOverride?: SpecResult) => {
    const sp = specOverride ?? spec;
    if (!sp) return;
    editedRef.current = true;
    try {
      const r = await call<any>({ op: "fit_spec", garment: kind, spec: sp.spec, size });
      past.current = []; future.current = []; setHistVer((v) => v + 1);
      await installPattern(r.pattern);
      setChecks(r.checks ?? []); setEdited(true); editedRef.current = true; setStale(false); setDrapeStale(true);
      const geos: Record<string, GeoPiece[]> = {};
      for (const z of r.sizes as GradedSize[]) geos[z.label] = (await call<{ pieces: GeoPiece[] }>({ op: "geometry", pattern: z.pattern })).pieces;
      setSizes(r.sizes); setSizeGeos(geos);
      setFit({ size: r.size, rows: r.fit ?? [], max_abs_error: r.max_abs_error ?? 0, converged: !!r.converged,
        perSize: (r.sizes as any[]).map((z) => ({ label: z.label, max_abs_error: z.max_abs_error ?? 0, converged: !!z.converged })), warnings: r.warnings ?? [] });
      setSelection({ piece: r.pattern.pieces[0]?.name ?? null, node: null });
      setSpec(sp); setSpecSize(r.size ?? size); setSpecKind(kind); setPanelMode("spec");
      setError(null); setTab("pattern");
    } catch (e) { setError(errMsg(e)); }
  }, [call, spec, installPattern]);

  const [targets, setTargets] = useState<{ key: string; label: string }[]>([]);
  useEffect(() => {
    if (!engine || panelMode !== "spec") return;
    void call<{ targets: { key: string; label: string }[] }>({ op: "map_targets", garment: specKind }).then((r) => setTargets(r.targets)).catch(() => setTargets([]));
  }, [engine, panelMode, specKind, call]);

  const onSpecMap = useCallback((row: number, key: string) => {
    if (!spec) return;
    const rows = spec.spec.rows.map((r, i) => (i === row ? { ...r, map_to: key, canonical: key || null } : r));
    const next: SpecResult = { ...spec, spec: { ...spec.spec, rows } };
    setSpec(next);
    void draftFromSpec(specSize, specKind, next);
  }, [spec, specSize, specKind, draftFromSpec]);

  const onSpecKind = useCallback((k: "pant" | "shirt") => {
    setSpecKind(k);
    if (spec) void draftFromSpec(specSize, k, spec);
  }, [spec, specSize, draftFromSpec]);

  // editing a spec value in the side panel re-draws the pattern (debounced)
  const onSpecEdit = useCallback((row: number, sizeIdx: number, cm: number) => {
    if (!spec) return;
    const rows = spec.spec.rows.map((r, i) => (i === row ? { ...r, values: r.values.map((v, k) => (k === sizeIdx ? cm : v)) } : r));
    const next: SpecResult = { ...spec, spec: { ...spec.spec, rows } };
    setSpec(next);
    if (editTimer.current) clearTimeout(editTimer.current);
    editTimer.current = setTimeout(() => void draftFromSpec(specSize, specKind, next), 600);
  }, [spec, specSize, specKind, draftFromSpec]);

  // ---- drape ----
  const runDrape = useCallback(async () => {
    if (!patRef.current) return;
    setDrapeBusy(true);
    try {
      const r = await call<DrapeResult>({ op: "drape", pattern: patRef.current, measurements: meas });
      setDrape(r);
      setDrapeStale(false);
      setError(null);
    } catch (e) { setError(errMsg(e)); } finally { setDrapeBusy(false); }
  }, [call, meas]);

  useEffect(() => { if (tab === "drape" && pattern && (drapeStale || !drape) && !drapeBusy) void runDrape(); },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tab, pattern, drapeStale]);

  // ---- export / project ----
  const logAudit = useCallback((e: Omit<AuditEntry, "time">) => {
    setAudit((a) => {
      const n = [...a, { time: new Date().toISOString(), ...e }].slice(-200);
      try { localStorage.setItem("pf-audit", JSON.stringify(n)); } catch { /* storage unavailable */ }
      return n;
    });
  }, []);
  const worstErr = fit ? Math.max(0, ...fit.perSize.map((z) => z.max_abs_error)) : undefined;

  /** Production gate: block while any POM is outside tolerance or validation reports an error; an override needs a reason and is logged. */
  function productionBlockers(): string[] {
    const b: string[] = [];
    if (fit) for (const r of fit.rows) if (!r.ok) b.push(`${r.code} ${r.name}: ${r.error >= 0 ? "+" : ""}${r.error.toFixed(2)} cm off spec`);
    for (const i of issues) if (String(i.severity).toLowerCase() === "error") b.push(`${i.rule}: ${i.detail}`);
    return b;
  }
  async function exportDxf(all: boolean) {
    if (!pattern) return;
    const file = all && sizes.length ? `${garment}-graded.dxf` : `${garment}-${pattern.size}.dxf`;
    const run = async () => {
      const style = `${garment}-${pattern.size}`;
      const req = all && sizes.length
        ? { op: "export_dxf", style: `${garment}-graded`, sizes: sizes.map((s) => ({ label: s.label, pattern: s.pattern })) }
        : { op: "export_dxf", style, pattern };
      const r = await call<{ dxf: string; filename: string }>(req);
      download(r.filename, r.dxf, "application/dxf");
    };
    const blockers = productionBlockers();
    try {
      if (blockers.length) { logAudit({ action: "export DXF", file, status: "blocked", worst: worstErr, note: `${blockers.length} issue(s)` }); setGateReason(""); setGate({ file, blockers, run }); return; }
      await run(); logAudit({ action: "export DXF", file, status: "ok", worst: worstErr });
    } catch (e) { setError(errMsg(e)); }
  }
  async function confirmOverride() {
    if (!gate || !gateReason.trim()) return;
    const g = gate; setGate(null);
    try { await g.run(); logAudit({ action: "export DXF", file: g.file, status: "override", reason: gateReason.trim(), worst: worstErr, note: g.blockers.join(" | ").slice(0, 300) }); }
    catch (e) { setError(errMsg(e)); }
  }
  async function exportSvg() {
    if (!pattern) return;
    try { const r = await call<{ svg: string }>({ op: "export_svg", pattern, cut: true }); download(`${garment}.svg`, r.svg, "image/svg+xml"); }
    catch (e) { setError(errMsg(e)); }
  }
  async function exportPds() {
    if (!pattern) return;
    try { await call({ op: "export_pds", pattern }); setPdsMsg("PDS export succeeded."); }
    catch (e) { setPdsMsg(errMsg(e)); }
  }
  function saveProject() {
    if (!pattern) return;
    download(`${garment}.patternforge.json`, JSON.stringify({ app: "patternforge", version: 1, garment, measurements: meas, opts, pattern, audit, saved: new Date().toISOString() }, null, 1), "application/json");
  }
  async function loadProject(text: string) {
    try {
      const j = JSON.parse(text);
      if (j.app !== "patternforge" || !j.pattern) throw new Error("Not a PatternForge project file.");
      initDone.current = true; setPanelMode("body"); if (Array.isArray(j.audit)) setAudit(j.audit);
      setGarment(j.garment); setMeas(j.measurements); setOpts({ ...DEFAULT_OPTS, ...j.opts });
      past.current = []; future.current = []; setHistVer((v) => v + 1);
      await installPattern(j.pattern);
      setChecks([]); setEdited(true); editedRef.current = true; setStale(false); setSizes([]); setDrapeStale(true);
      setSelection({ piece: j.pattern.pieces?.[0]?.name ?? null, node: null });
      setError(null);
    } catch (e) { setError(`Could not open project: ${errMsg(e)}`); }
  }

  const canUndo = past.current.length > 0 && histVer >= 0;
  const canRedo = future.current.length > 0 && histVer >= 0;

  if (fatal) {
    return (
      <div className="fatal" role="alert">
        <h1>PatternForge</h1>
        <p>The pattern engine could not start.</p>
        <pre>{fatal}</pre>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="top">
        <div className="brand"><span className="logo" aria-hidden>✂</span><b>PatternForge</b><small>{engine ? `engine: ${engine.kind}` : "starting engine…"}</small></div>
        <label className="inline">Garment
          <select value={garment} onChange={(e) => switchGarment(e.target.value)} data-testid="garment">
            {GARMENTS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
          </select>
        </label>
        <div className="grow" />
        <button className="btn ghost" onClick={() => void undo()} disabled={!canUndo} title="Undo (Ctrl+Z)">Undo</button>
        <button className="btn ghost" onClick={() => void redo()} disabled={!canRedo} title="Redo (Ctrl+Y)">Redo</button>
        <span className="sep" />
        <button className="btn" onClick={() => fileRef.current?.click()}>Open project</button>
        <button className="btn" onClick={saveProject} disabled={!pattern}>Save project</button>
        <input ref={fileRef} type="file" accept=".json" hidden onChange={async (e) => { const f = e.target.files?.[0]; if (f) await loadProject(await f.text()); e.target.value = ""; }} />
        <details className="menu" ref={menuRef}>
          <summary className="btn primary" data-testid="export-menu">Export ▾</summary>
          <div className="menu-pop" role="menu">
            <button role="menuitem" onClick={() => { closeMenu(); void exportDxf(false); }} data-testid="export-dxf">Optitex-ready DXF (AAMA/ASTM) — this size</button>
            <button role="menuitem" onClick={() => { closeMenu(); void exportDxf(true); }} disabled={!sizes.length} data-testid="export-dxf-all">Optitex-ready DXF — all graded sizes{!sizes.length ? " (grade first)" : ""}</button>
            <button role="menuitem" onClick={() => { closeMenu(); void exportSvg(); }}>SVG (cut + sew lines)</button>
            <hr />
            <button role="menuitem" onClick={() => { closeMenu(); void exportPds(); }} data-testid="export-pds">Optitex .PDS (native)…</button>
          </div>
        </details>
      </header>

      {error && <div className="banner err" role="alert" data-testid="error">{error}<button onClick={() => setError(null)} aria-label="Dismiss">×</button></div>}
      {fit && pattern && tab === "pattern" && (
        <div className={"banner " + (fit.converged ? "ok" : "warn")} data-testid="fit-banner">
          Drawn from your spec (size {fit.size}): {fit.converged ? "every measurement matches the spec" : "some measurements are outside tolerance"} · worst error {fit.max_abs_error.toFixed(3)} cm.
          <button className="btn" onClick={() => setTab("import")}>See spec vs measured</button>
        </div>
      )}
      {spec && panelMode === "spec" && tab === "pattern" && pattern && spec.spec.rows.every((r) => !(r.map_to ?? r.canonical)) && (
        <div className="banner warn" data-testid="unmapped-banner">
          None of the {spec.spec.rows.length} measurements in this sheet are recognised, so the drawing cannot follow them. In the left panel, choose what each row controls (the dropdown under each name), or tell me the sheet's layout.
        </div>
      )}
      {stale && <div className="banner warn">Measurements changed but you have manual edits. <button className="btn" onClick={() => void generate(garment, meas, opts)}>Regenerate (discard edits)</button></div>}

      <main className="main">
        <div className="side">
          {(spec || pdsSrc || panelMode === "body") && (
            <div className="seg side-switch" role="group" aria-label="Measurement source">
              {spec && <button className={panelMode === "spec" ? "on" : ""} onClick={() => setPanelMode("spec")} data-testid="mode-spec">Spec</button>}
              {pdsSrc && <button className={panelMode === "pds" ? "on" : ""} onClick={() => setPanelMode("pds")} data-testid="mode-pds">PDS</button>}
              <button className={panelMode === "body" ? "on" : ""} onClick={startBody} data-testid="mode-body">Body</button>
            </div>
          )}
          {panelMode === "start" ? (
            <section className="panel start-panel" aria-label="Measurements" data-testid="start-panel">
              <div className="panel-head"><h2>Measurements</h2></div>
              <p className="hint">Nothing loaded yet. Import a garment spec sheet (Excel / CSV) or an Optitex <b>.PDS</b> file in the <b>Import &amp; spec</b> tab: its measurements will appear here and the pattern is drawn from them.</p>
              <button className="btn" onClick={startBody} data-testid="start-body">Use body measurements instead</button>
              <p className="hint">Body measurements draw a basic bodice, skirt or trousers block (bust, waist, hip …).</p>
            </section>
          ) : panelMode === "body" ? (
            <MeasurementsPanel
              values={meas} units={units} onUnits={setUnits} opts={opts}
              onChange={(k, v) => setMeas((m) => ({ ...m, [k]: v }))}
              onOpts={(k, v) => setOpts((o) => ({ ...o, [k]: v }))}
              onImport={importMeasurements}
            />
          ) : (
            <section className="panel" aria-label="Measurements">
              <div className="seg units-seg" role="group" aria-label="Units">
                {(["cm", "in"] as const).map((u) => <button key={u} className={units === u ? "on" : ""} onClick={() => setUnits(u)} aria-pressed={units === u}>{u}</button>)}
              </div>
              <SourcePanel mode={panelMode as "spec" | "pds"} units={units} spec={spec} specSize={specSize} fit={fit}
                onSpecSize={(z) => void draftFromSpec(z, specKind, spec ?? undefined)} onSpecEdit={onSpecEdit}
                kind={specKind} onKind={onSpecKind} targets={targets} onMap={onSpecMap}
                pds={pdsSrc} onPdsSize={(z) => void onPdsSize(z)} geo={geo} pattern={pattern} />
            </section>
          )}
        </div>

        <section className="stage">
          <div className="tabs" role="tablist">
            {([["pattern", "2D pattern"], ["grading", "Grading"], ["drape", "3D drape"], ["import", "Import & spec"], ["marker", "Marker"], ["accuracy", "Accuracy"]] as [Tab, string][]).map(([id, label]) => (
              <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "tab on" : "tab"} onClick={() => setTab(id)} data-testid={`tab-${id}`}>{label}</button>
            ))}
            <div className="grow" />
            {tab === "pattern" && (
              <div className="toggles">
                <label className="inline"><input type="checkbox" checked={showCut} onChange={(e) => setShowCut(e.target.checked)} /> Seam allowance</label>
                <label className="inline"><input type="checkbox" checked={showNodes} onChange={(e) => setShowNodes(e.target.checked)} /> Points</label>
                <label className="inline"><input type="checkbox" checked={showSeamTags} onChange={(e) => setShowSeamTags(e.target.checked)} /> Edge names</label>
                {sizes.length > 0 && <label className="inline"><input type="checkbox" checked={showSizes} onChange={(e) => setShowSizes(e.target.checked)} /> Graded overlay</label>}
              </div>
            )}
          </div>

          {(tab === "pattern" || tab === "grading") && pattern && (
            <div className={tab === "grading" ? "split" : "full"}>
              <PatternCanvas
                pattern={pattern} geo={geo} selection={selection} onSelect={setSelection}
                onEditBegin={beginHistory} onEdit={applyEdit}
                showCut={showCut} showNodes={showNodes && tab === "pattern"} showSeamTags={showSeamTags}
                overlays={tab === "grading" || sizes.length ? overlays : []}
                onlyPiece={tab === "grading" ? selection.piece : null}
              />
              {tab === "grading" && (
                <GradingView steps={steps} onSteps={setSteps} sizes={sizes} geos={sizeGeos} pieceName={selection.piece} busy={gradeBusy} onRun={() => void runGrade()} />
              )}
            </div>
          )}

          <div className="full scroll-pane" style={tab === "import" ? undefined : { display: "none" }}>
            <ImportView call={call} onPds={onPdsImported} spec={spec} onSpec={setSpec} onDraftFromSpec={(z, k, sp) => draftFromSpec(z, k, sp)} fit={fit} onError={setError} />
          </div>
          {tab === "accuracy" && (
            <div className="full scroll-pane"><AccuracyView fit={fit} issues={issues} audit={audit} /></div>
          )}
          {tab === "marker" && (
            <div className="full scroll-pane"><MarkerView call={call} pattern={pattern} sizes={sizes.map((z) => ({ label: z.label, pattern: z.pattern }))} onError={setError} /></div>
          )}

          {tab === "drape" && (
            <div className="full drape-pane">
              {drapeBusy && <div className="overlay">Simulating drape…</div>}
              {drape && (
                <ErrorBoundary label="The 3D viewer">
                  <Suspense fallback={<div className="overlay">Loading 3D viewer…</div>}>
                    <DrapeView result={drape} />
                  </Suspense>
                </ErrorBoundary>
              )}
              {drape && drapeStale && !drapeBusy && <div className="banner warn floating">Pattern changed. <button className="btn" onClick={() => void runDrape()}>Re-drape</button></div>}
              <p className="hint pad">Preview only: pieces are wrapped onto a parametric mannequin and relaxed with a position-based cloth solver (stretch, stitches, body collision). It shows fit and balance, not fabric physics, and does not model layer-to-layer collision.</p>
            </div>
          )}
        </section>

        {pattern && (tab === "pattern" || tab === "grading") && (
          <Inspector pattern={pattern} geo={geo} checks={checks} edited={edited} selection={selection} onSelect={setSelection} onEdit={inspectorEdit} />
        )}
      </main>

      {gate && (
        <div className="modal-bg" onClick={() => setGate(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Production export blocked" onClick={(e) => e.stopPropagation()} data-testid="gate-dialog">
            <h2>Production export blocked</h2>
            <p>The pattern has problems that should be fixed before it is cut:</p>
            <ul className="warnlist">{gate.blockers.slice(0, 12).map((b, i) => <li key={i}>{b}</li>)}</ul>
            <label className="inline">Reason for exporting anyway (recorded in the audit log)
              <input type="text" value={gateReason} onChange={(e) => setGateReason(e.target.value)} data-testid="gate-reason" placeholder="e.g. sample only, buyer approved" />
            </label>
            <div className="btn-row">
              <button className="btn primary" onClick={() => setGate(null)}>Cancel</button>
              <button className="btn" disabled={!gateReason.trim()} onClick={() => void confirmOverride()} data-testid="gate-override">Export anyway (logged)</button>
            </div>
          </div>
        </div>
      )}

      {pdsMsg && (
        <div className="modal-bg" onClick={() => setPdsMsg(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-label="Optitex PDS export" onClick={(e) => e.stopPropagation()} data-testid="pds-dialog">
            <h2>Native .PDS export isn't available yet</h2>
            <p>{pdsMsg}</p>
            <p>What works today: <b>Export → Optitex-ready DXF (AAMA/ASTM)</b>, which Optitex imports (File → Import → DXF AAMA/ASTM) and can re-save as .PDS.</p>
            <p>See <code>docs/PDS-SAMPLES.md</code> for exactly which sample files would let us build and verify a real writer.</p>
            <div className="btn-row"><button className="btn primary" onClick={() => setPdsMsg(null)}>Close</button><button className="btn" onClick={() => { setPdsMsg(null); void exportDxf(false); }}>Export DXF instead</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
