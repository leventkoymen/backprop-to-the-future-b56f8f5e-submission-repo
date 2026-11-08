# Roadmap: repurposing drugs as resistance appears (backup, research use)

Backup material, not in the pitch. Research use by labs. Not built for the hackathon. The build uses no patient data.

## The loop

1. **Blood sequencing.** ctDNA at baseline, then at set intervals. Blood suits repeat testing: it is easier to sample serially and one draw pools DNA from several metastatic sites, while a biopsy covers one site at one time (Pascual et al., 2022).
2. **New mutation flagged.** A change appears in a tracked gene, for example KEAP1 or STK11.
3. **LungPair re-ranks pairs.** It favours existing drug pairs from NCI-ALMANAC that work across every genotype tested. Links between a mutation and a drug come from published studies through the evidence agent, labelled as literature.
4. **Human approves.** The lab tests the top pairs in preclinical models, and the results feed the next ranking. This follows the repurposing pathway: identify the drug, evaluate it in preclinical models, then move to phase II trials (Kulkarni et al., 2023).

## Why coverage, not genotype matching

The team's genotype test (Yong's branch) held out one lung line at a time and checked precision at 50. Cell lines carrying the mutation beat random same-size sets of lines only 28-59% of the time, where 50% means no signal: KEAP1 0.586, KRAS 0.541, SMARCA4 0.282, STK11 0.391, TP53 0.554. For every gene, the full set of the other 8 lines did best.

18 pairs were hits in every lung line they were tested in, with at least 5 lines each. That is the basis for ranking by coverage.

## Limits

- NCI-ALMANAC has 9 lung lines. The KRAS, STK11 and KEAP1 groups mostly share the same three (A549, NCI-H23, NCI-H460), so the groups are not independent.
- Blood assays detect copy-number changes and fusions poorly (Pascual et al., 2022).
- Dish results have no immune system and say nothing about toxicity.
- This stage needs consented serial ctDNA and outcome data. The hackathon build uses no patient data.

## References

- Pascual J, Attard G, Bidard F-C, et al. ESMO recommendations on the use of circulating tumour DNA assays for patients with cancer: a report from the ESMO Precision Medicine Working Group. *Ann Oncol*. 2022;33(8). doi:10.1016/j.annonc.2022.05.520
- Kulkarni VS, Alagarsamy V, Solomon VR, et al. Drug Repurposing: An Effective Tool in Modern Drug Discovery. *Russ J Bioorg Chem*. 2023;49(2):157-166. doi:10.1134/S1068162023020139
- Team genotype test: branch `yong/claude-1-genotype-coverage` (commit 0476aa6), `experiments/genotype_coverage/results/run_log.txt`. NCI-ALMANAC lung panel; mutation calls from CCLE (ccle_broad_2019) via cBioPortal.

Checked 8 Nov 2026. Pascual: full text read. Kulkarni: abstract only (quoted in paper-comments.txt) plus a web-fetch summary, not the full paper. Genotype figures: copied from run_log.txt as read on 7 Nov, not re-run. Mutation calls not checked independently.

Replaces the immunotherapy roadmap of 7 Nov, now in `theory/old/`.
