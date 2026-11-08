# Data

All data here is **measured, retrospective** NCI-ALMANAC data (non-small cell lung cancer, 9 cell lines), except where a file says otherwise. No patient data.

| Path | What | Who updates it |
|------|------|----------------|
| `starter/pairs_3d.json` | 105 drugs (NSC + name) and 5,228 pairs: mean ComboScore, hit flag (mean > 50), share of lung lines hit, lines measured. 172 hits. Optional per-pair `tier` (T1–T4) once available. | Duncan (pipeline) |
| `starter/shortlist_top50_named.csv` | Model's top 50: `score` = predicted, `lo/hi` = 95% interval, `mean` = measured result, `stability`. | Duncan |
| `starter/surface_dose_response.csv` | Scene C: 3 × 3 dose grids (observed vs expected % growth, synergy) for 12 drug pairs × up to 9 lung lines = 103 grids. **v3** (7 Nov): concentrations un-swapped, drug names added. Format: `schema/3d-data.md`. | Duncan |
| `starter/drugs.csv`, `starter/molecules/*.sdf` | 3D data pack (7 Nov): 13 drugs with target, how it works (AI-written, checked), dose, peak blood level; 3D structures from PubChem/RDKit. **drugs.csv names are used on every screen.** | Teammate |
| `starter/biomarkers.csv`, `starter/marker_guide.csv`, `starter/dose_reachability.csv` | 3D data pack: gene activity per cell line (context, not explanation) and dose reachability per pair. Not shown yet. | Teammate |
| `starter/molecules/` (other files), `pubchem_lookup.csv` | 3D structures for the other drugs, downloaded from PubChem by `visual/scripts/fetch-molecules.py` (looked up by NSC number). 2D-only records get a 3D shape generated with RDKit. Platinum/arsenic drugs and bleomycin are not modelled. | Generated |
| `derived/molecules.json` | Functional groups and atoms that could form bonds, computed from the molecule files by `visual/scripts/functional-groups.py` (RDKit). Properties of each molecule alone, **not** measured receptor contacts. | Generated |
| `runs/*.jsonl` | Agent event logs, one per run. Format: `schema/event-log.md`. `demo.jsonl` is a labelled demo built from the real shortlist. | Duncan (real runs); `visual/scripts/make-demo-log.mjs` (demo) |


Sources: NCI DTP NCI-ALMANAC (ComboDrugGrowth_Nov2017); drug names from NCI's ComboCompoundNames_small.txt. Licence: NCI describes the data as publicly available; licence text being confirmed.
