// All data is bundled at build time from /data (see vite.config.ts alias "@data").
// To add a new agent run: drop a .jsonl file into data/runs/ and restart `npm run dev`.
import pairsRaw from "@data/starter/pairs_3d.json";
import doseCsv from "@data/starter/surface_dose_response.csv?raw";
import drugsCsv from "@data/starter/drugs.csv?raw";
import { parseCsv } from "./csv";
import { DoseRow, DrugRow, Event, PairsFile, type Pair } from "./schemas";

export const pairKey = (a: number, b: number) => (a < b ? `${a}-${b}` : `${b}-${a}`);

// ---------- the landscape (Scenes A + B) ----------
export interface Landscape {
  file: PairsFile;
  drugIndex: Map<number, number>; // NSC -> 0..104 (grid position)
  drugName: Map<number, string>; // NSC -> name
  pairIndex: Map<string, number>; // "a-b" -> index into file.pairs
  hits: number;
}

function loadLandscape(): Landscape {
  const file = PairsFile.parse(pairsRaw);
  return {
    file,
    drugIndex: new Map(file.drugs.map((d, i) => [d.nsc, i])),
    drugName: new Map(file.drugs.map((d) => [d.nsc, d.name])),
    pairIndex: new Map(file.pairs.map((p: Pair, i) => [pairKey(p.a, p.b), i])),
    hits: file.pairs.filter((p) => p.hit).length,
  };
}

export const landscape = loadLandscape();

// ---------- drug details (starter/drugs.csv) ----------
export const drugInfo = new Map(
  parseCsv(drugsCsv).flatMap((raw) => {
    const r = DrugRow.safeParse(raw);
    return r.success ? [[r.data.nsc, r.data] as const] : [];
  }),
);

/**
 * THE one place drug names come from, so a drug has one name on every screen.
 * Team decision (7 Nov): the names in drugs.csv (the 3D data pack) win; for the
 * other drugs, pairs_3d.json; the other file's own name is only a last fallback.
 */
export function drugName(nsc: number, fallback?: string): string {
  return drugInfo.get(nsc)?.name ?? landscape.drugName.get(nsc) ?? fallback ?? `NSC ${nsc}`;
}

// ---------- dose-response grids (Scene C) ----------
export interface DosePoint {
  ia: number; // 0..2 grid column (from dose_index_a)
  ib: number; // 0..2 grid row (from dose_index_b)
  concA: number;
  concB: number;
  logA: number;
  logB: number;
  observed: number;
  expected: number;
  synergy: number;
}
export interface DoseGrid {
  id: string; // "a-b|cell line"
  pair: string; // pairKey
  a: number;
  b: number;
  drugA: string;
  drugB: string;
  cellLine: string;
  points: DosePoint[]; // always 9 when complete
  complete: boolean;
  maxSynergy: number;
}

function loadDoseGrids() {
  const errors: string[] = [];
  const byId = new Map<string, DoseGrid>();
  parseCsv(doseCsv).forEach((raw, i) => {
    const r = DoseRow.safeParse(raw);
    if (!r.success) {
      if (errors.length < 5) errors.push(`row ${i + 2}: ${r.error.issues[0]?.path.join(".")} ${r.error.issues[0]?.message}`);
      return;
    }
    const d = r.data;
    const id = `${d.drug_a_nsc}-${d.drug_b_nsc}|${d.cell_line}`;
    let g = byId.get(id);
    if (!g) {
      g = {
        id,
        pair: pairKey(d.drug_a_nsc, d.drug_b_nsc),
        a: d.drug_a_nsc,
        b: d.drug_b_nsc,
        drugA: drugName(d.drug_a_nsc, d.drug_a),
        drugB: drugName(d.drug_b_nsc, d.drug_b),
        cellLine: d.cell_line,
        points: [],
        complete: false,
        maxSynergy: -Infinity,
      };
      byId.set(id, g);
    }
    g.points.push({
      ia: d.dose_index_a - 1,
      ib: d.dose_index_b - 1,
      concA: d.conc_a_molar,
      concB: d.conc_b_molar,
      logA: d.log10_conc_a,
      logB: d.log10_conc_b,
      observed: d.observed_growth,
      expected: d.expected_growth,
      synergy: d.synergy,
    });
    g.maxSynergy = Math.max(g.maxSynergy, d.synergy);
  });
  const grids = [...byId.values()];
  grids.forEach((g) => (g.complete = g.points.length === 9));
  // grouped for the pickers: one entry per drug pair, its cell lines inside
  const pairs = new Map<string, { a: number; b: number; label: string; grids: DoseGrid[] }>();
  for (const g of grids) {
    const p = pairs.get(g.pair) ?? { a: g.a, b: g.b, label: `${g.drugA} + ${g.drugB}`, grids: [] };
    p.grids.push(g);
    pairs.set(g.pair, p);
  }
  pairs.forEach((p) => p.grids.sort((x, y) => x.cellLine.localeCompare(y.cellLine)));
  return { grids, pairs, errors };
}

export const dose = loadDoseGrids();

/** Default grid for Scene C: the top shortlist pair in its strongest cell line. */
export function defaultGrid(pair?: string): DoseGrid | undefined {
  const list = pair ? dose.pairs.get(pair)?.grids : dose.grids;
  return list?.reduce<DoseGrid | undefined>((best, g) => (!best || g.maxSynergy > best.maxSynergy ? g : best), undefined);
}

// ---------- agent runs ----------
export interface Run {
  name: string; // file name without .jsonl
  events: Event[];
  errors: string[]; // malformed lines are reported, never silently dropped
}

const runFiles = import.meta.glob("../../../data/runs/*.jsonl", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export function parseRun(name: string, text: string): Run {
  const events: Event[] = [];
  const errors: string[] = [];
  text.split(/\r?\n/).forEach((line, i) => {
    if (!line.trim()) return;
    try {
      const parsed = Event.safeParse(JSON.parse(line));
      if (parsed.success) events.push(parsed.data);
      else errors.push(`line ${i + 1}: ${parsed.error.issues[0]?.message ?? "invalid"}`);
    } catch {
      errors.push(`line ${i + 1}: not valid JSON`);
    }
  });
  return { name, events, errors };
}

export const runs: Run[] = Object.entries(runFiles)
  .map(([path, text]) => parseRun(path.split("/").pop()!.replace(/\.jsonl$/, ""), text))
  .sort((x, y) => (x.name === "demo" ? 1 : y.name === "demo" ? -1 : x.name.localeCompare(y.name)));
