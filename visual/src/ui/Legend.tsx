import { colors, NEG_CLAMP } from "../theme";
import type { ColorMode } from "../three/PairColumns";

const items: Record<ColorMode, [string, string][]> = {
  dark: [[colors.base, "Measured pair"]],
  hits: [[colors.hit, "Real hit (mean ComboScore > 50)"], [colors.base, "Not a hit"]],
  tier: [
    [colors.tier.T1, "T1 pair measured elsewhere"],
    [colors.tier.T2, "T2 drugs known, pair new"],
    [colors.tier.T3, "T3 new drugs, monotherapy run"],
    [colors.tier.T4, "T4 nothing measured: not ranked"],
  ],
  replay: [
    [colors.proposed, "Agent's pick, awaiting approval"],
    [colors.revealedHit, "Tested: real hit"],
    [colors.revealedMiss, "Tested: not a hit"],
    [colors.unknown, "Not tested yet"],
  ],
};

export function Legend({ mode }: { mode: ColorMode }) {
  return (
    <div className="legend panel">
      {items[mode].map(([c, label]) => (
        <div key={label} className="legend-item">
          <i style={{ background: c }} /> {label}
        </div>
      ))}
      <div className="muted small">Floor = drug A × drug B (105 × 105, each pair once). Height = mean ComboScore. Below the floor = drugs work against each other (cut at {NEG_CLAMP}).</div>
    </div>
  );
}
