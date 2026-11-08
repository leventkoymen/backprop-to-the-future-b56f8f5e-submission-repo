import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useReducer, useState } from "react";
import { labelPortal } from "./three/Label";
import { defaultGrid, dose, landscape, pairKey, runs, type DoseGrid } from "./data/load";
import { usePresenterKeys } from "./hooks/usePresenterKeys";
import { DoseSurface, type DoseView } from "./scenes/DoseSurface";
import { Landscape } from "./scenes/Landscape";
import { compileRun, initialReplay, makeReducer, viewOf } from "./state/replay";
import { colors } from "./theme";
import { CameraRig, type CameraCommand, type CameraPreset } from "./three/CameraRig";
import { columnHeight, pairPosition, type ColorMode } from "./three/PairColumns";
import { AgentPanel } from "./ui/AgentPanel";
import { DosePicker } from "./ui/DosePicker";
import { HoverCard } from "./ui/HoverCard";
import { Legend } from "./ui/Legend";
import { MoleculePanel } from "./ui/MoleculePanel";

type Scene = "A" | "B" | "C";
const TABS: { s: Scene; label: string }[] = [
  { s: "A", label: "1 · Haystack" },
  { s: "B", label: "2 · Agent" },
  { s: "C", label: "3 · Experiment" },
];
const hasTiers = landscape.file.pairs.some((p) => p.tier);
const pct = ((landscape.hits / landscape.file.pairs.length) * 100).toFixed(1);

export default function App() {
  const [scene, setScene] = useState<Scene>("A");
  const [modeA, setModeA] = useState<ColorMode>("dark"); // pitch opens dark, then hits light up
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [cam, setCam] = useState<CameraCommand>({ preset: "top", nonce: 0 });
  // ---- dose grid (Scene C) ----
  const [grid, setGrid] = useState<DoseGrid | undefined>(() => defaultGrid());
  const [doseView, setDoseView] = useState<DoseView>("growth");
  const stepCellLine = (d: number) => {
    if (!grid) return;
    const list = dose.pairs.get(grid.pair)!.grids;
    setGrid(list[(list.indexOf(grid) + d + list.length) % list.length]);
  };

  const go = (preset: CameraPreset, target?: [number, number, number]) => setCam((c) => ({ preset, target, nonce: c.nonce + 1 }));

  // ---- agent replay (Scene B) ----
  const [runName, setRunName] = useState(runs[0]?.name ?? "");
  const run = runs.find((r) => r.name === runName) ?? runs[0];
  const compiled = useMemo(() => compileRun(run?.events ?? []), [run]);
  const reducer = useMemo(() => makeReducer(compiled), [compiled]);
  const [replay, dispatch] = useReducer(reducer, initialReplay);
  useEffect(() => dispatch({ type: "reset" }), [compiled]);
  const view = useMemo(() => viewOf(compiled, replay), [compiled, replay]);
  const [molPair, setMolPair] = useState<{ a: number; b: number } | null>(null);
  const isAgent = scene === "B";
  const landscapeMode: ColorMode = scene === "A" ? modeA : "replay";
  const replayOn = isAgent;

  const switchScene = (s: Scene) => {
    // opening Scene C from a selected pair shows that pair's experiment, if it was measured as a grid
    if (s === "C") {
      const idx = selected ?? hovered;
      const p = idx !== null ? landscape.file.pairs[idx] : undefined;
      const g = p && defaultGrid(pairKey(p.a, p.b));
      if (g) setGrid(g);
    }
    setScene(s);
    setHovered(null);
    setSelected(null);
    setMolPair(null);
    go(s === "A" ? "top" : s === "C" ? "dose" : "angled");
  };

  const focus = () => {
    const idx = selected ?? hovered;
    const pick = view.current?.propose.pairs[0];
    let target: [number, number, number] | undefined;
    if (isAgent && pick) {
      const [x, z] = pairPosition(pick.a, pick.b);
      target = [x, 5, z];
    } else if (idx !== null) {
      const p = landscape.file.pairs[idx];
      const [x, z] = pairPosition(p.a, p.b);
      target = [x, Math.max(columnHeight(p.mean), 0), z];
    }
    if (target) go("focus", target);
  };

  const nextOrApprove = () => dispatch({ type: replay.phase === "proposed" ? "approve" : "next" });

  usePresenterKeys({
    "1": () => switchScene("A"),
    "2": () => switchScene("B"),
    "3": () => switchScene("C"),
    escape: () => setMolPair(null),
    h: () => setModeA((m) => (m === "dark" ? "hits" : "dark")),
    t: () => go("top"),
    a: () => go(scene === "C" ? "dose" : "angled"),
    l: () => go("low"),
    f: focus,
    Space: () => (isAgent ? nextOrApprove() : scene === "A" ? setModeA((m) => (m === "dark" ? "hits" : m)) : undefined),
    r: () => (isAgent ? dispatch({ type: "reset" }) : setModeA("dark")),
    v: () => scene === "C" && setDoseView((v) => (v === "growth" ? "synergy" : "growth")),
    arrowright: () => scene === "C" && stepCellLine(1),
    arrowleft: () => scene === "C" && stepCellLine(-1),
  });

  // In Scene B a pair's result stays hidden until the agent has "bought" it.
  const revealedKeys = useMemo(() => new Set(view.revealed.map((r) => `${r.a}-${r.b}`)), [view]);
  const cardIndex = hovered ?? selected;
  const cardHidden =
    replayOn &&
    cardIndex !== null &&
    !revealedKeys.has(`${landscape.file.pairs[cardIndex].a}-${landscape.file.pairs[cardIndex].b}`) &&
    !revealedKeys.has(`${landscape.file.pairs[cardIndex].b}-${landscape.file.pairs[cardIndex].a}`);

  const title = {
    A: { h: "The haystack", sub: `${landscape.file.pairs.length.toLocaleString()} measured drug pairs · ${landscape.hits} real hits (${pct}%) · a lab can afford to test maybe 50` },
    B: { h: "The agent at work", sub: "Agent proposes a batch → researcher approves → the real result is revealed → the model learns" },
    C: grid
      ? { h: `Inside one experiment: ${grid.drugA} + ${grid.drugB}`, sub: `Cell line ${grid.cellLine} · 3 × 3 doses · measured on one plate · the gap between expected and observed is the synergy` }
      : { h: "Inside one experiment", sub: "No dose-response data found in data/starter/surface_dose_response.csv" },
  }[scene];

  return (
    <div className="app">
      <Canvas camera={{ position: [0, 165, 0.01], fov: 45, near: 0.5, far: 2000 }} dpr={[1, 2]}>
        <color attach="background" args={[colors.bg]} />
        <CameraRig cmd={cam} />
        {scene === "C" ? (
          grid && <DoseSurface grid={grid} view={doseView} />
        ) : (
          <Landscape
            mode={landscapeMode}
            view={replayOn ? view : undefined}
            hovered={hovered}
            onHover={setHovered}
            onSelect={(i) => setSelected((s) => (s === i ? null : i))}
          />
        )}
      </Canvas>
      <div className="label-layer" ref={(el) => { if (el) labelPortal.current = el; }} />

      <header className="top">
        <div>
          <div className="kicker">LungPair · Scene {TABS.find((t) => t.s === scene)!.label.split(" · ")[0]}</div>
          <h1>{title.h}</h1>
          <p className="sub">{title.sub}</p>
        </div>
        <nav className="tabs">
          {TABS.map(({ s, label }) => (
            <button key={s} className={s === scene ? "active" : ""} onClick={() => switchScene(s)}>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <div className="toolbar panel">
        <span className="muted small">Camera</span>
        <button onClick={() => go("top")}>Top (T)</button>
        <button onClick={() => go(scene === "C" ? "dose" : "angled")}>Angled (A)</button>
        {scene !== "C" && <button onClick={() => go("low")}>Low (L)</button>}
        {scene !== "C" && <button onClick={focus}>Fly to (F)</button>}
        {scene === "A" && (
          <>
            <span className="sep" />
            <button className={modeA === "hits" ? "active" : ""} onClick={() => setModeA(modeA === "dark" ? "hits" : "dark")}>
              {modeA === "dark" ? `Light up ${landscape.hits} hits (H)` : "Hide hits (H)"}
            </button>
            {hasTiers && (
              <button className={modeA === "tier" ? "active" : ""} onClick={() => setModeA("tier")}>
                Colour by tier
              </button>
            )}
          </>
        )}
      </div>

      {scene !== "C" && !molPair && <Legend mode={landscapeMode} />}
      {scene !== "C" && !molPair && <HoverCard index={cardIndex} revealedOnly={cardHidden} />}

      {replayOn && run && scene === "B" && (
        <AgentPanel
          runs={runs}
          runName={run.name}
          onRun={setRunName}
          compiled={compiled}
          run={run}
          state={replay}
          view={view}
          onApprove={() => dispatch({ type: "approve" })}
          onNext={() => dispatch({ type: "next" })}
          onReset={() => dispatch({ type: "reset" })}
          onMolecules={(a, b) => setMolPair({ a, b })}
        />
      )}
      {isAgent && molPair && <MoleculePanel a={molPair.a} b={molPair.b} onClose={() => setMolPair(null)} />}
      {scene === "C" && grid && <DosePicker grid={grid} onGrid={setGrid} view={doseView} onView={setDoseView} />}
      {scene === "C" && dose.errors.length > 0 && <div className="dose-errors panel error">Dose data problems: {dose.errors.join("; ")}</div>}
      {isAgent && !run && <div className="agent-panel panel error">No agent runs found in data/runs/.</div>}

      <footer className="caption">
        Replay of measured NCI-ALMANAC results (non-small cell lung cancer, 9 cell lines). Not predictions. No patient data.
        <span className="keys"> · Keys: 1/2/3 scenes · Space next · R reset · T/A/L/F camera</span>
      </footer>
    </div>
  );
}
