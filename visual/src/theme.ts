// 85% 2-Color Foundation (Midnight Space Navy + Electric Mint-Teal)
// + 15% Unexpected Accent (Cantaloupe Orange #FC734D from Canva & Design Architecture)
export const colors = {
  // Foundation: Deep Midnight Navy (matches Canva slide background)
  bg: "#080e1e",
  floor: "#0d1527",
  grid: "#1e293b",
  base: "#24324d", // ordinary pair (positive score, muted background)
  baseNegative: "#172033", // pair whose drugs work against each other
  unknown: "#1c263d", // Scene B: result not yet "bought"
  doseBase: "#1e293b", // Scene C colour scale starts here

  // Color 2: Electric Mint-Cyan / Teal (from Canva 5,032 & glowing hit columns)
  hit: "#00dfa2", // real hit (luminous cyan/teal glow)
  revealedHit: "#00dfa2",
  revealedMiss: "#8292ab",
  hover: "#ffffff",
  violet: "#38bdf8", // Sky cyan reference in Scene C
  tier: { T1: "#00dfa2", T2: "#38bdf8", T3: "#a3b3cc", T4: "#475569" },

  // Color 3 (15%): Unexpected Cantaloupe Orange (matches Canva 'Budget for 50' & video)
  proposed: "#fc734d", // agent's pick awaiting approval (Cantaloupe Orange)
  accent: "#fc734d", // high-impact action CTA & budget indicators
} as const;

// Column heights: 1 ComboScore point = HEIGHT_SCALE scene units.
// 79% of pairs score below zero (down to -755), so negative columns are cut at NEG_CLAMP
// to keep the hits readable. This is stated on screen in the legend.
export const HEIGHT_SCALE = 0.1;
export const NEG_CLAMP = -150;
export const GRID = 105;
export const HALF = (GRID - 1) / 2;
