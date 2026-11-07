// Builds a clearly labelled DEMO agent log from REAL data, so Scene B can be built
// before Duncan's real agent log exists. Nothing is invented:
//   - picks = the retrospective top-50 shortlist, in rank order
//   - revealed scores/hits = the measured values from pairs_3d.json
//   - random baseline = expected value (experiments used x 172/5228)
//
// Usage: node scripts/make-demo-log.mjs <shortlist.csv> <pairs_3d.json> <out.jsonl>
import { readFileSync, writeFileSync } from "node:fs";

const [csvPath, pairsPath, outPath] = process.argv.slice(2);
if (!csvPath || !pairsPath || !outPath) {
  console.error("usage: make-demo-log.mjs <shortlist.csv> <pairs_3d.json> <out.jsonl>");
  process.exit(1);
}

const BATCH = 5;
const ROUNDS = 10;
const BUDGET = BATCH * ROUNDS;

const pairsFile = JSON.parse(readFileSync(pairsPath, "utf8"));
const key = (a, b) => (a < b ? `${a}-${b}` : `${b}-${a}`);
const measured = new Map(pairsFile.pairs.map((p) => [key(p.a, p.b), p]));
const hitRate = pairsFile.pairs.filter((p) => p.hit).length / pairsFile.pairs.length;

const [header, ...rows] = readFileSync(csvPath, "utf8").trim().split(/\r?\n/);
const cols = header.split(",");
const shortlist = rows.map((line) => {
  const cells = line.split(",");
  const r = Object.fromEntries(cols.map((c, i) => [c, cells[i]]));
  return {
    rank: Number(r.rank),
    a: Math.round(Number(r.a)),
    b: Math.round(Number(r.b)),
    drug_a: r.drug_a,
    drug_b: r.drug_b,
    predicted: Number(r.score),
    lo: Number(r.lo),
    hi: Number(r.hi),
  };
});

const out = [];
out.push({
  type: "run_start",
  run_id: "demo",
  input: null,
  budget_total: BUDGET,
  budget_unit: "experiments",
  batch_size: BATCH,
  label:
    "DEMO LOG: picks are the retrospective top-50 shortlist in rank order; results are measured NCI-ALMANAC values; random = expected value. Replace with the agent's real log.",
});

let used = 0;
let hits = 0;
for (let round = 1; round <= ROUNDS; round++) {
  const batch = shortlist.slice((round - 1) * BATCH, round * BATCH);
  out.push({
    type: "propose",
    round,
    pairs: batch.map((p) => ({
      a: p.a,
      b: p.b,
      drug_a: p.drug_a,
      drug_b: p.drug_b,
      reason: `Shortlist rank #${p.rank}: predicted score ${p.predicted.toFixed(0)} (95% interval ${p.lo.toFixed(0)}–${p.hi.toFixed(0)})`,
      sources: [],
    })),
  });
  out.push({
    type: "approve",
    round,
    approved_by: "researcher",
    approved: batch.map((p) => [p.a, p.b]),
    rejected: [],
  });
  const results = batch.map((p) => {
    const m = measured.get(key(p.a, p.b));
    if (!m) throw new Error(`pair ${p.a}-${p.b} not found in pairs_3d.json`);
    used += 1;
    if (m.hit) hits += 1;
    return { a: p.a, b: p.b, score: m.mean, hit: Boolean(m.hit) };
  });
  out.push({
    type: "reveal",
    round,
    results,
    budget_left: BUDGET - used,
    hits_total: hits,
    random_hits_total: Number((used * hitRate).toFixed(2)),
  });
}
out.push({
  type: "run_end",
  experiments_used: used,
  hits_total: hits,
  random_hits_total: Number((used * hitRate).toFixed(2)),
});

writeFileSync(outPath, out.map((o) => JSON.stringify(o)).join("\n") + "\n");
console.log(`wrote ${out.length} events to ${outPath}: ${hits}/${used} hits, random ≈ ${(used * hitRate).toFixed(1)}`);
