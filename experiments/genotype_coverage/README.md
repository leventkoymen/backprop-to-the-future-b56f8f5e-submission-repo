# Genotype-aware coverage test (YONG, 7 November 2026)

## Question

Suppose a monthly blood test (ctDNA, circulating tumour DNA) shows the tumour has gained a mutation such as KEAP1. Can the lab data tell us which drug pairs will still work, by looking only at the lung cell lines that carry that mutation?

## Data

- **Drug pairs:** NCI-ALMANAC lung panel (9 non-small cell lung cancer cell lines). Public data from the NCI Developmental Therapeutics Program. The data file is not copied here.
- **Mutations:** `data/cell_line_mutations.csv`, from the Cancer Cell Line Encyclopedia via the cBioPortal API (study `ccle_broad_2019`), downloaded 7 November 2026.
- **Drug names:** `data/drug_names.csv`, from the NCI ComboCompoundNames file.

| Gene | Mutant lung lines |
|---|---|
| KRAS | A549, HOP-62, NCI-H23, NCI-H460 |
| STK11 | A549, EKVX, NCI-H23, NCI-H460 |
| KEAP1 | A549, NCI-H23, NCI-H322M, NCI-H460 |
| TP53 | EKVX, HOP-62, HOP-92, NCI-H23, NCI-H322M, NCI-H522 |
| SMARCA4 | A549, EKVX, NCI-H23, NCI-H522 |

## Run

```
uv run --with pandas python genotype_coverage.py --raw ALMANAC_NSCLC_raw.csv --query KEAP1
```

Outputs go to `results/`: `run_log.txt`, `coverage_all_pairs.csv`, `loo_genotype_test.csv`, `loo_genotype_summary.csv` and `query_KEAP1.csv`.

## Method

1. **Score each pair in each cell line:**
   - Sum the dose scores in each study.
   - Drop grids that are entirely blank (54 were found).
   - Rescale to a 9-dose grid.
   - Take the median across repeat studies.
   - A hit is a ComboScore above 50.
2. **Leave-one-line-out test.** Hide one mutant line, then rank pairs three ways:
   - by hit rate in the **other mutant lines** (genotype-matched);
   - by hit rate in **every other same-size set of lines** (the fair control);
   - by hit rate in **all 8 other lines**.

   Score each ranking by precision in the top 50, measured against the hidden line's real results.

## Result [V: run log in `results/run_log.txt`]

| Gene | Base hit rate | Matched lines | Random same-size lines | All 8 other lines | How often matched beat random |
|---|---|---|---|---|---|
| KEAP1 | 0.075 | 0.705 | 0.658 | **0.825** | 59% |
| KRAS | 0.082 | 0.740 | 0.721 | **0.890** | 54% |
| STK11 | 0.073 | 0.675 | 0.686 | **0.850** | 39% |
| TP53 | 0.069 | 0.763 | 0.742 | **0.803** | 55% |
| SMARCA4 | 0.072 | 0.625 | 0.674 | **0.845** | 28% |

**What it means:**
- Choosing cell lines by mutation does about as well as choosing them at random. It beat random 28% to 59% of the time, and 50% is what you'd expect with no signal at all.
- Using all lines works best every time.
- In this data, a pair's **general strength across all lines** drives the result, not the genotype.
- So **don't claim genotype-specific predictions from NCI-ALMANAC.**

## What this changes in the design [I]

- **Research use:** rank by **coverage**, meaning pairs that work in every genotype tested. Eighteen pairs were hits in every line they were tested in, with at least 5 lines tested. These are the best candidates to "cover off" future mutations in a dish.
- **Mutation-specific knowledge** (for example, KEAP1 and STK11 are linked to primary resistance to immunotherapy) should come from the **evidence agent**, which reads published studies, and should be labelled as literature, not as our data.
- **Testing genotype effects properly** needs many more cell lines per genotype, such as larger combination screens or DepMap-scale panels [U: no suitable lung combination screen checked yet].

## Limits

- Only 9 cell lines, and each gene group has 3 to 6 lines.
- The KRAS, STK11 and KEAP1 groups mostly contain the same three lines (A549, NCI-H23, NCI-H460), so the genes can't be separated.
- Cells in dishes have no immune system and have not evolved under treatment.
- CCLE has NCI-H322; NCI-ALMANAC used the subline NCI-H322M. I assumed they are the same.
- Not every mutation listed changes how the protein works.
- The data are retrospective: every result was already measured.
- My count is 5,239 pairs because I applied no minimum number of cell lines. The team pipeline keeps pairs tested in at least 5 lines, which gives 5,228.
