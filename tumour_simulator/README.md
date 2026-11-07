# NSCLC progression simulator

**Drug universe matches the ranking pipeline.** All four agents are in
NCI-ALMANAC, with their NSC numbers in `toxicity.py`, so a pair the model
ranks can be simulated directly:

| Drug | NSC | Role |
|---|---|---|
| Gefitinib | 715055 | EGFR TKI — appears 6 times in the top-50 shortlist |
| Docetaxel | 628503 | Taxane |
| Carboplatin | 241240 | Platinum |
| Pemetrexed | 698037 | Antifolate |

The earlier version used osimertinib, which is **not** in ALMANAC — it was
approved in 2015 and the screening data is 2009-2013. Swapped to gefitinib so
the two halves of the project share one drug universe.

Generates longitudinal tumour data under drug regimens, **together with the
ground truth that produced it**.

    python simulate.py --scenario sequential --patients 30
    python validate.py

## What this is, and what it is not

It is a **mechanistic simulator with known answers**. You set the dynamics, it
produces biopsies, and you can then check whether a method recovers what you
know is there. That is a legitimate and useful thing.

It is **not a stand-in for patient data**. Nothing it outputs is evidence about
real tumours — only about whether your inference works. If you train a model on
this and report its accuracy as a finding, you have measured your own
assumptions.

Real longitudinal NSCLC-under-treatment data does exist and should be the
primary source:

| Source | What it is | Access |
|---|---|---|
| Maynard et al. 2020 (PRJNA591860) | Patient-matched longitudinal scRNA-seq through gefitinib resistance | public; pre-processed `.h5ad` on Zenodo record 23512899 |
| GSE131907 | NSCLC scRNA-seq atlas | public (GEO) |
| GSE207422, GSE179994, GSE176021 | NSCLC immunotherapy cohorts | public (GEO) |
| Nature Genetics 2024 immuno-chemo | 19 patients, scRNA-seq + spatial | Zenodo record 8227624 |
| TRACERx | 421+ patients, multi-region longitudinal WES through therapy | EGA EGAS00001006494, data access committee |
| OAK / POPLAR | Immunotherapy trial RNA-seq | EGA EGAS00001005013 |

## The mechanism

Standard clonal-evolution dynamics — nothing invented for this project:

- a tumour is subclones related by a phylogeny
- each grows logistically toward a shared carrying capacity
- each drug kills a subclone at a rate set by that subclone's sensitivity
- subclones mutate into daughters that may gain resistance at a fitness cost
- some resistant subclones **pre-exist** at low frequency, as in real tumours
- patients differ in baseline sensitivity, so the cohort spans deep responders
  to primary-refractory
- each subclone has a marker-expression vector; a biopsy sees the
  frequency-weighted mixture, with sampling and measurement noise

## Knobs that change the scientific question

| Parameter | What it decides |
|---|---|
| `n_preexisting` | pre-existing vs acquired resistance — **this sets the ceiling on any baseline biomarker** |
| `mut_rate` | how fast new resistance appears |
| `resist_cost` | fitness penalty of resistance, so whether resistant clones persist off-treatment |
| `depth` (in `biopsy`) | sequencing depth, hence which subclones are visible |
| `marker_noise` | assay noise |
| scenario | single agent, doublet, sequential, intermittent, untreated |

## Outputs per scenario

| File | Contents |
|---|---|
| `truth_clones.csv` | every subclone: parent, birth day, resistance, fitness, pre-existing flag |
| `truth_trajectory.csv` | true clone frequencies at every timestep |
| `truth_tree.json` | the real phylogeny, for scoring tree reconstruction |
| `obs_samples.csv` | what a biopsy at each sampling day would report |
| `obs_markers.csv` | bulk marker expression per sample, with noise |

## Toxicity — the other half

`toxicity.py` adds what the efficacy model could not express: the stated goal
is "better-tolerated regimens", and a model with no toxicity cannot represent
that at all.

Each drug contributes toxicity per unit dose to haematological, GI, skin and
cardiac systems. It accumulates and recovers with a half-life. When a system
crosses the patient's tolerance, the dose is reduced or held, as in clinic.
Two drugs hitting the SAME system stack — which is how real combinations fail.

    python compare_regimens.py   # four regimens, efficacy and tolerability
    python tox_sweep.py          # where the best regimen changes

**The TOX rates are illustrative, not drug-label values.** Replace them with
real CTCAE grade-3+ rates per drug before making any claim.

### Connecting the two halves

`compare_regimens.py` includes **docetaxel + gefitinib**, which the ranking
model placed 4th of 5,228 pairs (score 182, stability 100%). The simulator then
asks what the ranking cannot: what happens when you actually give it over 720
days?

| Arm | Control | Progressed | Dose intensity | Dose reductions |
|---|---|---|---|---|
| docetaxel + gefitinib (ranked #4) | 6.88 | 12/40 | **0.67** | 3 |
| gefitinib + carboplatin | 6.91 | 8/40 | **0.85** | 1 |

Near-identical tumour control, but the ranked pair is **harder to deliver** —
0.67 of planned dose against 0.85, and three dose reductions against one. The
synergy score cannot see that, because it is measured in a dish over 48 hours
with no patient to tolerate it.

That is the end-to-end claim: **the ranking says which pair, the simulator says
whether you can actually give it.**

### What the sweep shows

Tumour control (log10 fold reduction, higher better), 25 patients per cell:

| toxicity scale | doublet | sequential | gefitinib alone | intermittent | dose intensity (doublet) |
|---|---|---|---|---|---|
| 0.5x | **6.91** | 1.38 | −2.96 | −3.01 | 0.99 |
| 1x | **6.91** | 0.83 | −2.98 | −3.02 | 0.82 |
| 2x | **5.38** | −0.20 | −2.98 | −3.03 | 0.53 |
| 4x | **−0.11** | −1.89 | −3.00 | −3.03 | 0.33 |
| 8x | −2.74 | **−2.63** | −2.98 | −3.03 | 0.17 |
| 16x | −2.90 | **−2.78** | −2.97 | −3.02 | 0.09 |

**The best regimen flips.** The doublet is far and away the best up to 4x
toxicity, then loses to sequential. The mechanism is visible in the last
column: toxicity forces the doublet's delivered dose down to 9% of planned, so
the more active combination stops being deliverable.

That is the 2026 Med finding reproduced from first principles — synergy does
not predict clinical success, because the most synergistic combinations are
often the ones toxicity will not let you give.

## What validate.py already shows

On the default sequential regimen, 30 patients:

- 22 deep responders, 6 partial, 2 primary refractory; 18 of 30 progress
- subclones under 0.5% frequency: only ~34% detected at 2000x depth
- **baseline markers predict progression at AUC ~0.52 — chance**

That last one is the useful result, and it is true *by construction*: most
resistance here is acquired after treatment starts, so no day-0 biopsy can see
it. Set `n_preexisting` higher and the ceiling rises. This is how you find out
what a biomarker study could possibly achieve before running one.
