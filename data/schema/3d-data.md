# LungPair: data for the 3D model

All drug-response data is **real, measured data** from the NCI-ALMANAC screen
(lung cancer cell lines). Doses and blood levels come from drug labels and
published studies, cited in `drugs.csv`.

## The main visual: one dose-response surface per drug pair and cell line

`surface_dose_response.csv`: 927 rows, 12 drug pairs, 103 surfaces
(pair × cell line). Each surface is a 3×3 grid.

| Column | Meaning |
|---|---|
| `drug_a`, `drug_b` | Drug names. Use these for labels |
| `drug_a_nsc`, `drug_b_nsc` | Drug ID numbers |
| `cell_line` | One of 9 lung cancer cell lines |
| `dose_index_a`, `dose_index_b` | Grid position 1–3. **Use for X and Y** |
| `conc_a_molar`, `conc_b_molar` | Actual dose of that drug, in molar |
| `log10_conc_a`, `log10_conc_b` | Log dose, for true spacing on the axes |
| `observed_growth` | Tumour cell growth measured (100 = no effect, below 0 = cells killed) |
| `expected_growth` | Growth expected if the two drugs simply added up |
| `synergy` | `expected − observed`. **Z axis.** Positive = the drugs work better together |
| `reachable_in_patients` | `yes` / `no` / `unknown`: are both doses at or below what patients' blood actually reaches? |

Rendering:

- **X** = dose of drug A, **Y** = dose of drug B, **Z** = synergy.
  Range −88 to +186. Set the axis range from the data; don't hard-code it.
- Draw `expected_growth` as a flat reference sheet. The gap between it and the
  observed surface *is* the synergy.
- **Colour grid points by `reachable_in_patients`** (e.g. green yes, grey no,
  outline only for unknown). This is the key message: most high synergy sits at
  doses patients never reach. Only **Paclitaxel + Lapatinib** is synergistic
  across its whole grid at reachable doses.
- Not every pair has all 9 cell lines (three have 7 or 8). Build the cell-line
  dropdown from the data.

## Optional: the molecules

`molecules/*.sdf`: one 3D structure per drug (13 files). File name is listed
per drug in `drugs.csv` (`structure_file`). Open in 3Dmol.js (a few lines of
JavaScript in a web page) to show each drug next to its surface.

These are computed structures from PubChem (or generated with RDKit where
PubChem had none). They show the molecule's shape, **not** where the drug sits
in the tumour or how it binds its target.

## Interaction flow

1. **Pick a drug pair and a cell line** → show the dose-response surface.
2. **Click a drug** → show its molecule (`molecules/`) and a panel from
   `drugs.csv`: target, how it works, route, standard dose, peak blood level.
3. **Biomarker panel for the selected cell line** → bars from `biomarkers.csv`.
   Highlight the markers whose `related_drugs_in_this_data` (in
   `marker_guide.csv`) include the drugs on screen. For example, with
   gefitinib selected, highlight EGFR and MET; with paclitaxel, highlight
   TUBB3 and ABCB1.

### Biomarker tables

`biomarkers.csv`: one row per cell line, **same names as the surface file**,
so it joins directly on `cell_line`.

- 16 marker genes. Each number is that gene's activity in this cell line,
  scaled against about 175 cancer cell lines: 0 = typical, +1 = clearly
  above typical, −1 = clearly below.
- Each marker also has a `_level` column: `high` (> +0.5), `low` (< −0.5) or
  `average`. Use it for colouring.
- **NCI-H322M has no gene data.** Show "no biomarker data" for it.

`marker_guide.csv`: a plain-English line for each marker, and which drugs
in this data it relates to.

**Label the panel as context, not explanation.** These are gene activity
levels, not mutations, and some key lung cancer genes (KRAS, STK11, KEAP1)
aren't in the data. With 9 cell lines we have not shown that any marker
predicts synergy. A good caption: "What these cells look like", not "Why the
drugs work".

The `how_it_works` text in `drugs.csv` was written by an AI model and checked
against standard pharmacology.

## Supporting tables

- `drugs.csv`: per drug: route, standard dose, peak blood level in molar
  (`cmax_molar`), sources. Blank `cmax_molar` = no reliable figure found
  (vinblastine, estramustine). Valrubicin is bladder-only and never reaches the
  blood.
- `dose_reachability.csv`: per pair: peak synergy, whether that peak is
  reachable in patients, and the best synergy at reachable doses.

## Labelling

- Say "3D dose-response surface", not "3D tumour model".
- Treat the "reachable" flag as a guide: cells in the screen sat in a constant
  dose for 48 h, while blood levels rise and fall.
