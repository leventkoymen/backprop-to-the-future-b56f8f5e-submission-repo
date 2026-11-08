# Agent event log format (contract between `agent/` and `visual/`)

The agent **writes** one file per run into `data/runs/<run-name>.jsonl`.
The 3D visual **reads** every `*.jsonl` file in that folder automatically.

One JSON object per line. Every line has a `"type"`. Extra fields are allowed and ignored.
Do not rename or remove the fields below without telling the visual owner.

| type        | required fields                                                                 |
|-------------|---------------------------------------------------------------------------------|
| `run_start` | `run_id`, `budget_total`, `budget_unit`, optional `input`, `batch_size`, `label` |
| `propose`   | `round`, `pairs: [{a, b, drug_a, drug_b, reason, sources?}]`                    |
| `approve`   | `round`, `approved_by`, `approved: [[a,b],…]`, optional `rejected`              |
| `reveal`    | `round`, `results: [{a, b, score, hit}]`, `budget_left`, `hits_total`, `random_hits_total` |
| `learn`     | `round`, optional `note`                                                         |
| `run_end`   | `experiments_used`, `hits_total`, `random_hits_total`                            |

Rules
- `a`, `b` = NSC IDs as **integers**; `drug_a`, `drug_b` = names exactly as in `starter/pairs_3d.json`.
- `reveal.score` = the same measured `mean` as in `pairs_3d.json` (so column heights match).
- `random_hits_total` = hits a random strategy gets with the same budget (state whether expected value or simulated in `run_start.label`).

Example
```
{"type":"run_start","run_id":"baseline","input":null,"budget_total":50,"budget_unit":"experiments","batch_size":5,"label":"…"}
{"type":"propose","round":1,"pairs":[{"a":628503,"b":715055,"drug_a":"Docetaxel","drug_b":"Gefitinib","reason":"strong in other cancers (mean 175)","sources":["PMID:…"]}]}
{"type":"approve","round":1,"approved_by":"researcher","approved":[[628503,715055]],"rejected":[]}
{"type":"reveal","round":1,"results":[{"a":628503,"b":715055,"score":182.7,"hit":true}],"budget_left":49,"hits_total":1,"random_hits_total":0.03}
{"type":"run_end","experiments_used":50,"hits_total":24,"random_hits_total":1.6}
```
