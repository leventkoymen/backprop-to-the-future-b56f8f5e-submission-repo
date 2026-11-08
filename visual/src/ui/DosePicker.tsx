import { dose, type DoseGrid } from "../data/load";
import type { DoseView } from "../scenes/DoseSurface";

/** Scene C controls: pick a drug pair and a cell line, and switch growth/synergy view. */
export function DosePicker({ grid, onGrid, view, onView }: { grid: DoseGrid; onGrid: (g: DoseGrid) => void; view: DoseView; onView: (v: DoseView) => void }) {
  const pair = dose.pairs.get(grid.pair)!;
  return (
    <aside className="dose-panel panel">
      <label className="field">
        Drug pair ({dose.pairs.size})
        <select
          value={grid.pair}
          onChange={(e) => {
            const p = dose.pairs.get(e.target.value)!;
            onGrid(p.grids.find((g) => g.cellLine === grid.cellLine) ?? p.grids[0]);
          }}
        >
          {[...dose.pairs.entries()].map(([k, p]) => (
            <option key={k} value={k}>{p.label}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Cell line ({pair.grids.length} measured)
        <select value={grid.id} onChange={(e) => onGrid(pair.grids.find((g) => g.id === e.target.value)!)}>
          {pair.grids.map((g) => (
            <option key={g.id} value={g.id}>
              {g.cellLine} · peak synergy {g.maxSynergy.toFixed(0)}
            </option>
          ))}
        </select>
      </label>
      <div className="seg">
        <button className={view === "growth" ? "active" : ""} onClick={() => onView("growth")}>Growth: observed vs expected</button>
        <button className={view === "synergy" ? "active" : ""} onClick={() => onView("synergy")}>Synergy only</button>
      </div>
      {!grid.complete && <div className="error">Only {grid.points.length} of 9 dose points measured: missing cells are left blank.</div>}
      <div className="muted small">
        {view === "growth"
          ? "Teal = measured growth. Violet = expected if the drugs didn't interact. The white lines are the synergy."
          : "Height = synergy (expected − observed). Teal above the floor = synergy; blue below = the drugs work against each other."}
      </div>
      <div className="muted small keys">V = switch view · ←/→ = cell line</div>
    </aside>
  );
}
