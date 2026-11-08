// Run after EVERY `git pull`: checks that the backend's data files still match
// the structure the frontend expects (src/data/schemas.ts).
//
//   npm run check-data
//
// Exit code 0 = safe to keep working. Exit code 1 = the backend changed a file's
// structure: read the messages, then either update src/data/schemas.ts (and the
// components that use the changed field) or ask Duncan/Levent in the WhatsApp group.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { csvHeader, parseCsv } from "../src/data/csv";
import { DOSE_COLUMNS, DoseRow, DRUG_COLUMNS, DrugRow, Event, NAME_COLUMNS, NameRow, PROGRESSION_COLUMNS, PairsFile, ProgressionRow } from "../src/data/schemas";

const dataDir = process.argv[2] ?? "../data";
let problems = 0;
const ok = (msg: string) => console.log(`  ok   ${msg}`);
const bad = (msg: string) => {
  problems += 1;
  console.log(`  FAIL ${msg}`);
};

function checkJson(rel: string, schema: { safeParse: (x: unknown) => any }, describe: (d: any) => string) {
  const path = join(dataDir, rel);
  if (!existsSync(path)) return bad(`${rel}: file missing (renamed or moved?)`);
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return bad(`${rel}: not valid JSON`);
  }
  const r = schema.safeParse(raw);
  if (!r.success) {
    r.error.issues.slice(0, 5).forEach((i: any) => bad(`${rel}: ${i.path.join(".") || "(root)"}: ${i.message}`));
    return;
  }
  ok(`${rel}: ${describe(r.data)}`);
}

console.log(`Checking data in ${dataDir}\n`);

// 1. starter/pairs_3d.json
checkJson("starter/pairs_3d.json", PairsFile, (d) => {
  const hits = d.pairs.filter((p: any) => p.hit).length;
  const tiers = d.pairs.filter((p: any) => p.tier).length;
  const extra = Object.keys(d.pairs[0] ?? {}).filter(
    (k) => !["a", "b", "drug_a", "drug_b", "mean", "hit", "hit_rate", "n_lines", "tier"].includes(k),
  );
  return `${d.drugs.length} drugs, ${d.pairs.length} pairs, ${hits} hits` +
    (tiers ? `, ${tiers} with tier` : ", no tiers yet") +
    (extra.length ? ` · NEW fields not used yet: ${extra.join(", ")}` : "");
});

// 2. starter/surface_dose_response.csv (Scene C)
function checkCsv(rel: string, columns: string[], row: { safeParse: (x: unknown) => any }, optional = false) {
  const path = join(dataDir, rel);
  if (!existsSync(path)) {
    if (!optional) bad(`${rel}: file missing (renamed or moved?)`);
    return null;
  }
  const text = readFileSync(path, "utf8");
  const header = csvHeader(text);
  const missing = columns.filter((c) => !header.includes(c));
  const extra = header.filter((c) => !columns.includes(c));
  if (missing.length) {
    bad(`${rel}: missing columns ${missing.join(", ")} (renamed?)`);
    return null;
  }
  const rows = parseCsv(text);
  const parsed: any[] = [];
  let fails = 0;
  rows.forEach((r, i) => {
    const res = row.safeParse(r);
    if (res.success) parsed.push(res.data);
    else if (fails++ < 3) bad(`${rel} row ${i + 2}: ${res.error.issues[0]?.path.join(".")}: ${res.error.issues[0]?.message}`);
  });
  if (fails > 3) bad(`${rel}: ${fails} bad rows in total`);
  return { parsed, extra, fails };
}

const doseCheck = checkCsv("starter/surface_dose_response.csv", DOSE_COLUMNS, DoseRow);
if (doseCheck && !doseCheck.fails) {
  const grids = new Map<string, number>();
  const unknown = new Set<number>();
  const refNames = new Map<number, string>(
    existsSync(join(dataDir, "starter/pairs_3d.json"))
      ? JSON.parse(readFileSync(join(dataDir, "starter/pairs_3d.json"), "utf8")).drugs.map((d: any) => [d.nsc, d.name])
      : [],
  );
  const known = new Set(refNames.keys());
  const renamed = new Set<string>();
  for (const r of doseCheck.parsed) {
    if (refNames.get(r.drug_a_nsc) && refNames.get(r.drug_a_nsc) !== r.drug_a) renamed.add(`${r.drug_a_nsc}: "${r.drug_a}" vs "${refNames.get(r.drug_a_nsc)}"`);
    if (refNames.get(r.drug_b_nsc) && refNames.get(r.drug_b_nsc) !== r.drug_b) renamed.add(`${r.drug_b_nsc}: "${r.drug_b}" vs "${refNames.get(r.drug_b_nsc)}"`);
    const id = `${r.drug_a_nsc}-${r.drug_b_nsc}|${r.cell_line}`;
    grids.set(id, (grids.get(id) ?? 0) + 1);
    [r.drug_a_nsc, r.drug_b_nsc].forEach((n: number) => known.size && !known.has(n) && unknown.add(n));
  }
  const incomplete = [...grids.values()].filter((n) => n !== 9).length;
  const pairs = new Set([...grids.keys()].map((k) => k.split("|")[0])).size;
  ok(`starter/surface_dose_response.csv: ${doseCheck.parsed.length} rows, ${pairs} pairs, ${grids.size} grids` +
    (incomplete ? `, ${incomplete} incomplete (shown with gaps)` : ", all 3 x 3") +
    (doseCheck.extra.length ? ` · other columns: ${doseCheck.extra.join(", ")}` : ""));
  if (renamed.size) console.log(`  note ${renamed.size} drug name(s) differ between the 3D pack and pairs_3d.json; the app shows the 3D pack (drugs.csv) name everywhere: ${[...renamed].join("; ")}`);
  const reach = doseCheck.parsed.filter((r: any) => r.reachable_in_patients).length;
  if (reach < doseCheck.parsed.length) console.log(`  note starter/surface_dose_response.csv: ${doseCheck.parsed.length - reach} rows have no reachable_in_patients value`);
  if (unknown.size) bad(`starter/surface_dose_response.csv: NSC IDs not in pairs_3d.json (no drug names): ${[...unknown].join(", ")}`);
}

// 2c. starter/drugs.csv (names + drug details for the 3D pack)
const drugs = checkCsv("starter/drugs.csv", DRUG_COLUMNS, DrugRow);
if (drugs && !drugs.fails) {
  const missing = drugs.parsed.filter((d: any) => !existsSync(join(dataDir, "starter", d.structure_file)));
  if (missing.length) bad(`starter/drugs.csv: molecule files missing: ${missing.map((d: any) => d.structure_file).join(", ")}`);
  else ok(`starter/drugs.csv: ${drugs.parsed.length} drugs, all molecule files present`);
}

// 2a. starter/nsc_names.csv (reference names; not required by the app)
const names = checkCsv("starter/nsc_names.csv", NAME_COLUMNS, NameRow, true);
if (names && !names.fails) ok(`starter/nsc_names.csv: ${names.parsed.length} official drug names`);

// 2b. simulated/progression_clones.csv: SIMULATED, not rendered yet; only checked if present
const prog = checkCsv("simulated/progression_clones.csv", PROGRESSION_COLUMNS, ProgressionRow, true);
if (prog && !prog.fails) ok(`simulated/progression_clones.csv: ${prog.parsed.length} rows (SIMULATED: must be labelled if shown)`);

// 3. starter/shortlist_top50_named.csv (only the columns the frontend reads)
const csvRel = "starter/shortlist_top50_named.csv";
const csvPath = join(dataDir, csvRel);
const needCols = ["rank", "drug_a", "drug_b", "a", "b", "score", "lo", "hi", "mean"];
if (!existsSync(csvPath)) bad(`${csvRel}: file missing`);
else {
  const [header, ...rows] = readFileSync(csvPath, "utf8").trim().split(/\r?\n/);
  const cols = header.split(",");
  const missing = needCols.filter((c) => !cols.includes(c));
  const extra = cols.filter((c) => !needCols.includes(c));
  if (missing.length) bad(`${csvRel}: missing columns ${missing.join(", ")} (renamed?)`);
  else ok(`${csvRel}: ${rows.length} rows` + (extra.length ? ` · other columns: ${extra.join(", ")}` : ""));
}

// 4. runs/*.jsonl (agent event logs)
const runsDir = join(dataDir, "runs");
const runFiles = existsSync(runsDir) ? readdirSync(runsDir).filter((f) => f.endsWith(".jsonl")) : [];
if (!runFiles.length) bad("runs/: no .jsonl agent logs found");
for (const f of runFiles) {
  const lines = readFileSync(join(runsDir, f), "utf8").split(/\r?\n/).filter((l) => l.trim());
  let fails = 0;
  const types = new Map<string, number>();
  lines.forEach((line, i) => {
    try {
      const r = Event.safeParse(JSON.parse(line));
      if (r.success) types.set(r.data.type, (types.get(r.data.type) ?? 0) + 1);
      else if (fails++ < 3) bad(`runs/${f} line ${i + 1}: ${r.error.issues[0]?.path.join(".")}: ${r.error.issues[0]?.message}`);
    } catch {
      if (fails++ < 3) bad(`runs/${f} line ${i + 1}: not valid JSON`);
    }
  });
  if (!fails) ok(`runs/${f}: ${lines.length} events (${[...types].map(([t, n]) => `${n} ${t}`).join(", ")})`);
  else if (fails > 3) bad(`runs/${f}: ${fails} bad lines in total`);
}

console.log(problems ? `\n${problems} problem(s). The backend changed the data structure: see above.` : "\nAll data files match the frontend's expected structure.");
process.exit(problems ? 1 : 0);
