# Data for the 3D model — spec and files

> **v2, corrected 7 Nov.** Three fixes after review:
> 1. **Concentrations were swapped on 2,300 of 5,239 pairs.** The raw file
>    sometimes stores a pair as (B,A); canonicalising the drug IDs without
>    swapping the dose columns put each drug's concentrations on the other
>    drug's axis. Caught by noticing Dactinomycin at micromolar doses when it
>    is a nanomolar agent. **Only the axis labels were affected** — the
>    surfaces, the ranking, the stress tests and the shortlist are unchanged,
>    because ComboScore is a sum over the whole grid and does not depend on
>    which drug is called "first".
> 2. Synergy range corrected: **−88 to +186** (was stated as −30 to +60).
> 3. Surface count corrected: **103, not 108** — three pairs were measured in
>    only 7 or 8 lung cell lines, not all 9.
>
> **v3:** drug names added. Every row now carries `drug_a` and `drug_b`
> alongside the NSC numbers, from the official NCI CellMiner ALMANAC list.

Two candidate visuals, both with real files attached. Pick one; the first is
lower risk for a 2pm deadline.

---

## Option A — dose-response surface (RECOMMENDED)

`surface_dose_response.csv` — 927 rows, 12 drug pairs, 103 surfaces.

One **3x3 grid per (pair, cell line)**. Render as a surface: dose of drug A on
X, dose of drug B on Y, response on Z.

| Column | Type | Meaning |
|---|---|---|
| `drug_a_nsc`, `drug_b_nsc` | int | Drug IDs (NSC numbers) |
| `drug_a`, `drug_b` | string | Drug names — **use these for labels** |
| `cell_line` | string | One of 9 NSCLC lines |
| `dose_index_a`, `dose_index_b` | int 1-3 | Grid position — **use these for X/Y** |
| `conc_a_molar`, `conc_b_molar` | float | Actual concentration of **that drug**, 1e-9 to 1e-4 M. Ranges differ per drug — a nanomolar agent and a micromolar one in the same pair is normal |
| `log10_conc_a`, `log10_conc_b` | float | Log scale — better for axis labels |
| `observed_growth` | float | % tumour growth measured. 100 = no effect, 0 = growth stopped, negative = cells killed |
| `expected_growth` | float | What the two drugs would do independently |
| `synergy` | float | `expected − observed`. **Positive = synergy. This is the Z axis.** |

**Rendering notes**
- Z axis = `synergy`, range **−88 to +186** across this subset
- Draw the `expected_growth` plane as a flat reference surface; the gap between
  the two surfaces IS the synergy. That is the whole visual.
- Use `dose_index_*` for a regular 3x3 grid; use `log10_conc_*` if you want
  true spacing
- **103 surfaces** (9 pairs x 9 lines, 1 x 8, 2 x 7). Let the user pick pair
  and cell line — do not assume every pair has all 9.

---

## Option B — clonal progression over time

`progression_clones.csv` — 5,361 rows, 6 simulated patients.

Render as a 3D "fish plot" / muller diagram: time on X, clone fraction stacked
on Y, patients as separate scenes or a Z axis.

| Column | Type | Meaning |
|---|---|---|
| `patient` | int | 0-5 |
| `day` | float | 0 to 720, every 5 days |
| `clone` | int | Subclone ID |
| `parent` | int | Parent clone ID, −1 for the founder — **gives you the tree** |
| `born_day` | float | When this clone appeared |
| `cell_count` | float | Absolute size |
| `clone_fraction` | float | Share of the tumour, sums to 1 per day |
| `resistant_to` | string | Drug it resists, blank if sensitive |

**Rendering notes**
- Colour by `resistant_to` — the story is resistant clones taking over
- `parent` lets you nest/stack children inside their parent's band
- Treatment switches at day 360 in this scenario (osimertinib → carboplatin)

**This data is SIMULATED.** It must be labelled as such anywhere it appears.

---

## What the 3D team needs to decide

1. **Which option.** A is real measured data and lower risk. B is more visually
   dramatic but must carry a "simulated" label.
2. **Framework.** Three.js if you want full control; Plotly's 3D surface if you
   want it working in an hour. For a 2pm deadline I would use Plotly.
3. **Interaction.** Minimum viable: rotate, and a dropdown to switch pair or
   patient. Anything more is a bonus.

Both files are plain CSV, no dependencies, under 300 KB.
