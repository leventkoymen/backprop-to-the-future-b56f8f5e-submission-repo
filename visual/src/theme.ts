// One place for colours and scales, so the look matches the organisers' slides
// (dark navy, teal/violet accents) and the mock-ups.
export const colors = {
  // Palette: deep cold navy background, cool grey-blue neutrals, one coral accent.
  // Coral vs blue is the one pairing that stays distinct for colour-blind viewers.
  bg: "#0d1724", // deep cold navy
  floor: "#132236",
  grid: "#2b4262",
  base: "#a3b4cc", // ordinary pair (positive score)
  baseNegative: "#6b7f9c", // pair whose drugs work against each other
  unknown: "#6b7f9c", // Scene B: result not yet "bought"
  doseBase: "#2b4262", // Scene C colour scale starts here
  hit: "#e77054", // real hit (coral accent)
  proposed: "#dcccb7", // agent's pick awaiting approval (sand)
  revealedHit: "#e77054",
  revealedMiss: "#e8eef6",
  hover: "#ffffff",
  violet: "#a9b8cf", // reference planes in Scene C
  tier: { T1: "#e77054", T2: "#6fa8dc", T3: "#dcccb7", T4: "#4a6080" },
} as const;

// Column heights: 1 ComboScore point = HEIGHT_SCALE scene units.
// 79% of pairs score below zero (down to -755), so negative columns are cut at NEG_CLAMP
// to keep the hits readable. This is stated on screen in the legend.
export const HEIGHT_SCALE = 0.1;
export const NEG_CLAMP = -150;
export const GRID = 105;
export const HALF = (GRID - 1) / 2;
