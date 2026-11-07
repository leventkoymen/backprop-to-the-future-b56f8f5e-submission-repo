// One place for colours and scales, so the look matches the organisers' slides
// (dark navy, teal/violet accents) and the mock-ups.
export const colors = {
  bg: "#0b1029",
  floor: "#121838",
  grid: "#232a55",
  base: "#3b4170", // ordinary pair (positive score)
  baseNegative: "#2a2f55", // pair whose drugs work against each other
  unknown: "#2f3560", // Scene B: result not yet "bought"
  hit: "#2ee6c5", // real hit (teal)
  proposed: "#ffc53d", // agent's pick awaiting approval (gold)
  revealedHit: "#3ddc84",
  revealedMiss: "#a3a8c3",
  hover: "#ffffff",
  violet: "#8b7cf6",
  tier: { T1: "#2ee6c5", T2: "#4c8dff", T3: "#f5b83d", T4: "#5d6282" },
} as const;

// Column heights: 1 ComboScore point = HEIGHT_SCALE scene units.
// 79% of pairs score below zero (down to -755), so negative columns are cut at NEG_CLAMP
// to keep the hits readable. This is stated on screen in the legend.
export const HEIGHT_SCALE = 0.1;
export const NEG_CLAMP = -150;
export const GRID = 105;
export const HALF = (GRID - 1) / 2;
