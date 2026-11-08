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
import { GuidedTour, tourSteps } from "./ui/GuidedTour";
import { GlossaryPanel } from "./ui/Term";
import { LabPanel } from "./ui/LabPanel";
import { MoleculePanel } from "./ui/MoleculePanel";

// "G" = 2b: the agent scene with a guided introduction and "?" explanations, for comparison with B.
type Scene = "A" | "B" | "G" | "C";
const TABS: { s: Scene; label: string }[] = [
  { s: "A", label: "1 · Haystack" },
  { s: "B", label: "2 · Agent" },
  { s: "G", label: "2b · Guided" },
  { s: "C", label: "3 · Experiment" },
];
// the highest-scoring measured pair, used by the guide's first step
const topPairIndex = landscape.file.pairs.reduce((best, p, i, all) => (p.mean > all[best].mean ? i : best), 0);
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
  const logView = useMemo(() => viewOf(compiled, replay), [compiled, replay]);

  // 2b only: the lab user can untick pairs before approving. Rejected pairs are never tested,
  // so they're removed from what's revealed (and from the counts in LabPanel).
  const [unticked, setUnticked] = useState<Set<string>>(new Set());
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  useEffect(() => (setUnticked(new Set()), setRejected(new Set())), [compiled]);
  const toggle = (k: string) => setUnticked((u) => { const n = new Set(u); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const approve = () => {
    if (scene === "G" && replay.phase === "proposed") {
      setRejected((r) => new Set([...r, ...unticked]));
      setUnticked(new Set());
    }
    dispatch({ type: "approve" });
  };
  const resetRun = () => (setUnticked(new Set()), setRejected(new Set()), dispatch({ type: "reset" }));
  const view = useMemo(
    () => (scene === "G" && rejected.size ? { ...logView, revealed: logView.revealed.filter((r) => !rejected.has(pairKey(r.a, r.b))) } : logView),
    [logView, rejected, scene],
  );

  // ---- guided view (2b) ----
  const steps = useMemo(
    () => tourSteps(compiled.start?.batch_size ?? compiled.rounds[0]?.propose.pairs.length ?? 5, compiled.start?.budget_total ?? 50),
    [compiled],
  );
  const [tourIdx, setTourIdx] = useState<number | null>(null);
  const [showGlossary, setShowGlossary] = useState(false);
  const [molPair, setMolPair] = useState<{ a: number; b: number } | null>(null);
  const step = scene === "G" && tourIdx !== null ? steps[tourIdx] : undefined;
  const isAgent = scene === "B" || scene === "G";
  const landscapeMode: ColorMode = scene === "A" ? modeA : step ? step.mode : "replay";
  const replayOn = isAgent && landscapeMode === "replay";

  // each guide step sets up the scene so the picture matches the words
  useEffect(() => {
    if (!step) return;
    if (step.focusTopPair) {
      const p = landscape.file.pairs[topPairIndex];
      const [x, z] = pairPosition(p.a, p.b);
      setSelected(topPairIndex);
      go("focus", [x, Math.max(columnHeight(p.mean), 0) / 2, z]);
    } else {
      setSelected(null);
      go(step.camera);
    }
    if (step.mode !== "replay" && replay.phase !== "ready") dispatch({ type: "reset" });
    if (step.startAgent && replay.phase === "ready") dispatch({ type: "next" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

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
    setShowGlossary(false);
    setMolPair(null);
    if (s === "G") {
      resetRun();
      setTourIdx(0); // the guide starts every time 2b opens
    } else setTourIdx(null);
    go(s === "A" ? "top" : s === "C" ? "dose" : "angled");
  };

  const focus = () => {
    const idx = selected ?? hovered;
    const pick = view.current?.propose.pairs[0];
    let target: [number, number, number] | undefined;
    if (isAgent && replayOn && pick) {
      const [x, z] = pairPosition(pick.a, pick.b);
      target = [x, 5, z];
    } else if (idx !== null) {
      const p = landscape.file.pairs[idx];
      const [x, z] = pairPosition(p.a, p.b);
      target = [x, Math.max(columnHeight(p.mean), 0), z];
    }
    if (target) go("focus", target);
  };

  const nextOrApprove = () => (replay.phase === "proposed" ? approve() : dispatch({ type: "next" }));

  usePresenterKeys({
    "1": () => switchScene("A"),
    "2": () => switchScene("B"),
    "3": () => switchScene("C"),
    "4": () => switchScene("G"),
    g: () => switchScene("G"),
    escape: () => (setTourIdx(null), setShowGlossary(false), setMolPair(null)),
    h: () => setModeA((m) => (m === "dark" ? "hits" : "dark")),
    t: () => go("top"),
    a: () => go(scene === "C" ? "dose" : "angled"),
    l: () => go("low"),
    f: focus,
    Space: () =>
      step
        ? setTourIdx((i) => (i !== null && i < steps.length - 1 ? i + 1 : null))
        : isAgent
          ? nextOrApprove()
          : scene === "A"
            ? setModeA((m) => (m === "dark" ? "hits" : m))
            : undefined,
    r: () => (isAgent ? resetRun() : setModeA("dark")),
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
    G: { h: "Plan your next experiments", sub: "The agent suggests drug pairs to test. You choose which ones. Underlined words explain themselves." },
    C: grid
      ? { h: `Inside one experiment: ${grid.drugA} + ${grid.drugB}`, sub: `Cell line ${grid.cellLine} · 3 × 3 doses · measured on one plate · the gap between expected and observed is the synergy` }
      : { h: "Inside one experiment", sub: "No dose-response data found in data/starter/surface_dose_response.csv" },
  }[scene];

  return (
    <div className={scene === "G" ? "app lab-mode" : "app"}>
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
        {scene === "G" && (
          <>
            <span className="sep" />
            <button onClick={() => setTourIdx(0)}>Restart guide</button>
            <button className={showGlossary ? "active" : ""} onClick={() => setShowGlossary((v) => !v)}>Glossary</button>
          </>
        )}
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
      {scene !== "C" && !molPair && <HoverCard index={cardIndex} revealedOnly={cardHidden} guided={scene === "G"} light={scene === "G"} />}

      {replayOn && run && scene === "G" && (
        <LabPanel
          runs={runs}
          runName={run.name}
          onRun={setRunName}
          compiled={compiled}
          run={run}
          state={replay}
          view={view}
          unticked={unticked}
          onToggle={toggle}
          rejected={rejected}
          onApprove={approve}
          onNext={() => dispatch({ type: "next" })}
          onReset={resetRun}
          onMolecules={(a, b) => setMolPair({ a, b })}
        />
      )}
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
      {isAgent && molPair && !step && <MoleculePanel a={molPair.a} b={molPair.b} light={scene === "G"} onClose={() => setMolPair(null)} />}
      {step && tourIdx !== null && <GuidedTour steps={steps} index={tourIdx} onIndex={setTourIdx} onClose={() => setTourIdx(null)} />}
      {scene === "G" && showGlossary && <GlossaryPanel onClose={() => setShowGlossary(false)} />}
      {scene === "C" && grid && <DosePicker grid={grid} onGrid={setGrid} view={doseView} onView={setDoseView} />}
      {scene === "C" && dose.errors.length > 0 && <div className="dose-errors panel error">Dose data problems: {dose.errors.join("; ")}</div>}
      {isAgent && !run && <div className="agent-panel panel error">No agent runs found in data/runs/.</div>}

      <footer className="caption">
        Replay of measured NCI-ALMANAC results (non-small cell lung cancer, 9 cell lines). Not predictions. No patient data.
        <span className="keys"> · Keys: 1/2/3 scenes · 4 guided · Space next · R reset · T/A/L/F camera</span>
      </footer>
    </div>
  );
}
