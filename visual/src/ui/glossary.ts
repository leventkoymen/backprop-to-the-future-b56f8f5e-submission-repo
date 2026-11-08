import { landscape } from "../data/load";

const n = landscape.file.pairs.length;
const pct = ((landscape.hits / n) * 100).toFixed(1);

/** Plain-language definitions shown by the "?" tooltips in the guided view (2b). */
export const glossary = {
  pair: { term: "Drug pair", text: "Two cancer drugs given to the same cells at the same time." },
  cellLine: { term: "Cell line", text: "A standard lab-grown lung cancer cell type. Each pair was tested on up to 9." },
  comboScore: { term: "ComboScore", text: "How much better two drugs worked together than expected. Above 0 = better together, below 0 = worse." },
  hit: { term: "Hit", text: `A pair with an average ComboScore above 50. ${landscape.hits} of ${n.toLocaleString()} pairs (${pct}%).` },
  synergy: { term: "Synergy", text: "Two drugs working better together than each one alone would suggest." },
  expectedGrowth: { term: "Expected growth", text: "How much cells would grow if the two drugs didn't affect each other." },
  observedGrowth: { term: "Observed growth", text: "How much cells actually grew. 100% = normal, 0% = stopped, below 0 = cells died." },
  budget: { term: "Budget", text: "How many experiments you can afford. One pair = one experiment." },
  random: { term: "Random", text: `Hits you'd expect from picking pairs at random: about ${pct}% of experiments.` },
  approve: { term: "Approve", text: "Your sign-off. A pair is only tested once you approve it." },
  replay: { term: "Replay", text: "All results are real past measurements. Each one stays hidden until its pair is tested." },
} as const;

export type GlossaryKey = keyof typeof glossary;
