# Data

All data here is **measured, retrospective** NCI-ALMANAC data (non-small cell lung cancer, 9 cell lines), except where a file says otherwise. No patient data.

| Path | What | Who updates it |
|------|------|----------------|
| `starter/pairs_3d.json` | 105 drugs (NSC + name) and 5,228 pairs: mean ComboScore, hit flag (mean > 50), share of lung lines hit, lines measured. 172 hits. Optional per-pair `tier` (T1–T4) once available. | Duncan (pipeline) |
| `starter/shortlist_top50_named.csv` | Model's top 50: `score` = predicted, `lo/hi` = 95% interval, `mean` = measured result, `stability`. | Duncan |
| `starter/surface_dose_response.csv` | Scene C: 3 × 3 dose grids (observed vs expected % growth, synergy) for 12 drug pairs × up to 9 lung lines = 103 grids. **v3** (7 Nov): concentrations un-swapped, drug names added. Format: `schema/3d-data.md`. | Duncan |
| `runs/*.jsonl` | Agent event logs, one per run. Format: `schema/event-log.md`. `demo.jsonl` is a labelled demo built from the real shortlist. | Duncan (real runs); `visual/scripts/make-demo-log.mjs` (demo) |


Sources: NCI DTP NCI-ALMANAC (ComboDrugGrowth_Nov2017); drug names from NCI's ComboCompoundNames_small.txt. Licence: NCI describes the data as publicly available; licence text being confirmed.
