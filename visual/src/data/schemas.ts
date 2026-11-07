import { z } from "zod";

// ---------- starter/pairs_3d.json ----------
export const Tier = z.enum(["T1", "T2", "T3", "T4"]);
export type Tier = z.infer<typeof Tier>;

export const Drug = z.object({ nsc: z.number().int(), name: z.string() });
export type Drug = z.infer<typeof Drug>;

export const Pair = z.looseObject({
  a: z.number().int(),
  b: z.number().int(),
  drug_a: z.string(),
  drug_b: z.string(),
  mean: z.number(), // mean ComboScore across lung lines (measured)
  hit: z.union([z.literal(0), z.literal(1), z.boolean()]).transform(Boolean),
  hit_rate: z.number(), // share of lung lines where it was a hit
  n_lines: z.number().int(),
  tier: Tier.optional(), // added by Duncan later; Scene A can colour by it
});
export type Pair = z.infer<typeof Pair>;

export const PairsFile = z.looseObject({
  _about: z.string().optional(),
  drugs: z.array(Drug),
  pairs: z.array(Pair),
});
export type PairsFile = z.infer<typeof PairsFile>;

// ---------- starter/surface_dose_response.csv (see data/schema/3d-data.md) ----------
// One row = one dose point. 9 rows (3 x 3) per (drug pair, cell line).
// CSV values arrive as strings, so numbers are coerced; NSC IDs like "3053.0" become 3053.
const num = z.coerce.number().refine(Number.isFinite, "not a number");
const nsc = num.transform((n) => Math.round(n));
const doseIndex = z.coerce.number().int().min(1).max(3);

export const DoseRow = z.looseObject({
  drug_a_nsc: nsc,
  drug_b_nsc: nsc,
  drug_a: z.string().min(1), // names added in data v3
  drug_b: z.string().min(1),
  cell_line: z.string().min(1),
  dose_index_a: doseIndex,
  dose_index_b: doseIndex,
  conc_a_molar: num,
  conc_b_molar: num,
  log10_conc_a: num,
  log10_conc_b: num,
  observed_growth: num, // % growth: 100 = no effect, 0 = stopped, negative = cells killed
  expected_growth: num, // NCI's no-interaction (modified Bliss) prediction
  synergy: num, // expected - observed; positive = synergy
});
export type DoseRow = z.infer<typeof DoseRow>;
export const DOSE_COLUMNS = Object.keys(DoseRow.shape);

// ---------- starter/nsc_names.csv (official NCI CellMiner ALMANAC names, 90 drugs) ----------
export const NameRow = z.looseObject({ nsc, name: z.string().min(1) });
export const NAME_COLUMNS = ["nsc", "name"];

// ---------- simulated/progression_clones.csv (SIMULATED: not rendered yet) ----------
export const ProgressionRow = z.looseObject({
  patient: z.coerce.number().int(),
  day: num,
  clone: z.coerce.number().int(),
  parent: z.coerce.number().int(),
  born_day: num,
  cell_count: num,
  clone_fraction: num,
  resistant_to: z.string(), // blank = sensitive
});
export const PROGRESSION_COLUMNS = Object.keys(ProgressionRow.shape);

// ---------- runs/*.jsonl (see data/schema/event-log.md) ----------
const Id = z.number().transform((n) => Math.round(n)); // tolerate 3053.0
const PairRef = z.tuple([Id, Id]);

export const RunStart = z.looseObject({
  type: z.literal("run_start"),
  run_id: z.string(),
  input: z.unknown().optional(),
  budget_total: z.number(),
  budget_unit: z.string(),
  batch_size: z.number().optional(),
  label: z.string().optional(),
});
export const Propose = z.looseObject({
  type: z.literal("propose"),
  round: z.number().int(),
  pairs: z.array(
    z.looseObject({
      a: Id,
      b: Id,
      drug_a: z.string(),
      drug_b: z.string(),
      reason: z.string(),
      sources: z.array(z.string()).optional(),
    }),
  ),
});
export const Approve = z.looseObject({
  type: z.literal("approve"),
  round: z.number().int(),
  approved_by: z.string(),
  approved: z.array(PairRef),
  rejected: z.array(PairRef).optional(),
});
export const Reveal = z.looseObject({
  type: z.literal("reveal"),
  round: z.number().int(),
  results: z.array(z.looseObject({ a: Id, b: Id, score: z.number(), hit: z.boolean() })),
  budget_left: z.number(),
  hits_total: z.number(),
  random_hits_total: z.number(),
});
export const Learn = z.looseObject({
  type: z.literal("learn"),
  round: z.number().int(),
  note: z.string().optional(),
});
export const RunEnd = z.looseObject({
  type: z.literal("run_end"),
  experiments_used: z.number(),
  hits_total: z.number(),
  random_hits_total: z.number(),
});

export const Event = z.discriminatedUnion("type", [RunStart, Propose, Approve, Reveal, Learn, RunEnd]);
export type Event = z.infer<typeof Event>;
export type RunStartEvent = z.infer<typeof RunStart>;
export type ProposeEvent = z.infer<typeof Propose>;
export type RevealEvent = z.infer<typeof Reveal>;
