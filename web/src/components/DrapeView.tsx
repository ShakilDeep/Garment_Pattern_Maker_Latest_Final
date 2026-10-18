import { useEffect, useMemo, useRef, useState } from "react";
import {
  BufferAttribute, BufferGeometry, DirectionalLight, DoubleSide, Float32BufferAttribute, GridHelper, Group,
  HemisphereLight, type Material, Mesh, MeshStandardMaterial, PerspectiveCamera, Scene, WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { Column, DrapeResult } from "../types";
import { pieceColor } from "../util";

/** Build an elliptical stack surface for a body column (y-up, cm). */
function columnGeometry(c: Column, segs = 48, levels = 28): BufferGeometry {
  const top = c.ys[0], bot = c.ys[c.ys.length - 1];
  const at = (y: number): [number, number] => {
    for (let i = 0; i + 1 < c.ys.length; i++) {
      if (y <= c.ys[i] && y >= c.ys[i + 1]) {
        const t = (c.ys[i] - y) / Math.max(1e-9, c.ys[i] - c.ys[i + 1]);
        return [c.a[i] + (c.a[i + 1] - c.a[i]) * t, c.b[i] + (c.b[i + 1] - c.b[i]) * t];
      }
    }
    return [c.a[0], c.b[0]];
  };
  const pos: number[] = [];
  const idx: number[] = [];
  for (let l = 0; l <= levels; l++) {
    const y = top + ((bot - top) * l) / levels;
    const [a, b] = at(y);
    for (let s = 0; s < segs; s++) {
      const th = (s / segs) * Math.PI * 2;
      pos.push(c.cx + a * Math.sin(th), y, c.cz + b * Math.cos(th));
    }
  }
  for (let l = 0; l < levels; l++) {
    for (let s = 0; s < segs; s++) {
      const i0 = l * segs + s, i1 = l * segs + ((s + 1) % segs), j0 = i0 + segs, j1 = i1 + segs;
      idx.push(i0, j0, i1, i1, j0, j1);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute("position", new Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

interface Props { result: DrapeResult }

export default function DrapeView({ result }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [wire, setWire] = useState(false);
  const [showBody, setShowBody] = useState(true);
  const nFrames = result.meshes[0]?.frames.length ?? 1;
  const api = useRef<{ setFrame: (t: number) => void; setWire: (w: boolean) => void; setBody: (b: boolean) => void } | null>(null);

  const center = useMemo(() => {
    let lo = Infinity, hi = -Infinity;
    for (const m of result.meshes) {
      const f = m.frames[m.frames.length - 1];
      for (let i = 1; i < f.length; i += 3) { lo = Math.min(lo, f[i]); hi = Math.max(hi, f[i]); }
    }
    return { y: (lo + hi) / 2, h: hi - lo };
  }, [result]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const renderer = new WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const scene = new Scene();
    const camera = new PerspectiveCamera(35, 1, 1, 3000);
    camera.position.set(0, center.y, Math.max(180, center.h * 2.1));
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, center.y, 0);
    controls.enableDamping = true;
    scene.add(new HemisphereLight(0xffffff, 0x8a8f99, 1.1));
    const sun = new DirectionalLight(0xffffff, 1.4);
    sun.position.set(80, 160, 220);
    scene.add(sun);

    const body = new Group();
    const bodyMat = new MeshStandardMaterial({ color: 0xd9c9b8, roughness: 0.9, transparent: true, opacity: 0.85, side: DoubleSide });
    for (const c of [result.body.torso, ...result.body.legs, ...result.body.arms]) body.add(new Mesh(columnGeometry(c), bodyMat));
    scene.add(body);

    const cloth: { frames: Float32Array[]; geom: BufferGeometry }[] = [];
    const mats: MeshStandardMaterial[] = [];
    for (const m of result.meshes) {
      const geom = new BufferGeometry();
      const frames = m.frames.map((f) => new Float32Array(f));
      geom.setAttribute("position", new BufferAttribute(new Float32Array(frames[frames.length - 1]), 3));
      geom.setIndex(m.tris);
      geom.computeVertexNormals();
      const mat = new MeshStandardMaterial({ color: pieceColor(m.name), roughness: 0.75, side: DoubleSide, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
      mats.push(mat);
      scene.add(new Mesh(geom, mat));
      cloth.push({ frames, geom });
    }

    const grid = new GridHelper(300, 30, 0x888888, 0xcccccc);
    grid.position.y = center.y - center.h / 2 - 12;
    (grid.material as Material).opacity = 0.35;
    (grid.material as Material).transparent = true;
    scene.add(grid);

    const setFrame = (t: number) => {
      for (const c of cloth) {
        const last = c.frames.length - 1;
        const f = Math.min(last, Math.max(0, t * last));
        const i = Math.floor(f), j = Math.min(last, i + 1), k = f - i;
        const attr = c.geom.getAttribute("position") as BufferAttribute;
        const arr = attr.array as Float32Array;
        for (let q = 0; q < arr.length; q++) arr[q] = c.frames[i][q] * (1 - k) + c.frames[j][q] * k;
        attr.needsUpdate = true;
        c.geom.computeVertexNormals();
      }
    };
    api.current = {
      setFrame,
      setWire: (w) => mats.forEach((m) => (m.wireframe = w)),
      setBody: (b) => (body.visible = b),
    };

    const resize = () => {
      const w = el.clientWidth || 600, h = el.clientHeight || 400;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    let raf = 0;
    const loop = () => { controls.update(); renderer.render(scene, camera); raf = requestAnimationFrame(loop); };
    loop();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      scene.traverse((o) => {
        const m = o as Mesh;
        if (m.geometry) m.geometry.dispose();
      });
      bodyMat.dispose();
      mats.forEach((m) => m.dispose());
      renderer.dispose();
      renderer.domElement.remove();
      api.current = null;
    };
  }, [result, center]);

  useEffect(() => { api.current?.setFrame(progress); }, [progress, result]);
  useEffect(() => { api.current?.setWire(wire); }, [wire, result]);
  useEffect(() => { api.current?.setBody(showBody); }, [showBody, result]);

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let t0 = performance.now();
    const base = progress >= 1 ? 0 : progress;
    const tick = (now: number) => {
      const p = base + (now - t0) / 2500;
      if (p >= 1) { setProgress(1); setPlaying(false); return; }
      setProgress(p);
      raf = requestAnimationFrame(tick);
    };
    t0 = performance.now();
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  const s = result.stats;
  return (
    <div className="drape">
      <div className="drape-canvas" ref={host} data-testid="drape-canvas" />
      <div className="drape-controls">
        <button className="btn" onClick={() => { setProgress(0); setPlaying(true); }}>{playing ? "Playing…" : "Replay drape"}</button>
        <label className="inline">Drape <input type="range" min={0} max={1} step={0.01} value={progress} onChange={(e) => { setPlaying(false); setProgress(parseFloat(e.target.value)); }} aria-label="Drape progress" /></label>
        <label className="inline"><input type="checkbox" checked={showBody} onChange={(e) => setShowBody(e.target.checked)} /> Mannequin</label>
        <label className="inline"><input type="checkbox" checked={wire} onChange={(e) => setWire(e.target.checked)} /> Wireframe</label>
        <span className="hint">{nFrames} frames · {s.particles} particles · stitch gap {s.stitch_mean_final.toFixed(2)} cm · typical stretch ×{s.stretch_p95.toFixed(2)}</span>
      </div>
    </div>
  );
}
