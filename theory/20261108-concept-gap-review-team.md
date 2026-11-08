# LungPair: gaps against the judging criteria, and options to close them

Team Receipts, AgentVerse 2026 Biotech track. Theodore, with Claude, 8 Nov 2026 (checks run 01:00–02:30).

This is a proposal. Nothing in the build has been changed. It reads the five judging criteria (slide 43) through the slide-41 data sources, with most weight on criteria 2 (real-world need), 3 (science, data, evaluation) and 4 (agent and live demo). Each gap for today comes with three options: no build change (A), a small change (B) or a big change (C). Effort figures are rough estimates. It reflects `main` after PR #2 (agent pipeline, merged 01:47) and `backend-pipeline` at 5cc9833.

## Summary

1. **Weakest point.** The top-50 shortlist is mostly a sorted list of pairs ALMANAC has already measured in lung, and the model is weak where it has to predict. Pitch LungPair as triage of a noisy public screen, not as a predictor.
2. **Best example pair.** Paclitaxel + lapatinib:
   - rank 9 on the shortlist;
   - a hit in Merck's independent lung screen;
   - the only pair synergistic across its whole dose grid at doses patients reach;
   - both drugs approved, per ChEMBL;
   - one ClinicalTrials.gov study lists both drugs in lung cancer.
3. **Avoid docetaxel + gefitinib as a discovery example.** 22 lung cancer studies on ClinicalTrials.gov list both drugs, and it's the README's demo pair.
4. **Fix the write-up claims that conflict with the repo or the checks** before submission (T2).
5. **Biggest gain for little build risk.** Add `studies_in_lung`, `max_phase` and `merck_loewe` fields to the shortlist and the agent's tool output. Two of the three are already computed (files attached).

## The weakest point

- All 50 shortlist pairs were measured in 7 to 9 of ALMANAC's 9 lung lines (37 in 9, 6 in 8, 7 in 7). Every row's evidence field says "measured in other cancers" (`results/shortlist_top50_named.csv`).
- Pairs where neither drug was screened score at chance: precision 0.04 against 0.03 (`README.md`, Known limitations).
- On the 5 Merck lung lines ALMANAC never tested, the model's top 10 held 20% hits against a 20% base rate (p = 0.658; `backend/external_test_results.txt`, Test 2).

A judge can fairly say "this is a lookup of a public table." The answer is what a lab can't get from the table:
- **which measured hits hold up:** ALMANAC's single tests repeat 41% of the time;
- **which work at doses patients reach:** `LungPair_3D_data/README.md`;
- **which use approved drugs:** ChEMBL;
- **which have never been trialled in lung:** ClinicalTrials.gov.

## What the checks found

**ChEMBL max phase for the 105 ALMANAC drugs** (attached: `20261108-almanac-drugs-chembl-phase.csv`, matched by name through the ChEMBL API):
- 97 are at max phase 4, counting either the salt record or its parent.
- 5 didn't match by name (6-mercaptopurine, nitrogen mustard, 8-methoxypsoralen, fludarabine base, amifostine).
- SN-38 (irinotecan's active metabolite) and triethylenemelamine are at phase 2. Estramustine matched a phase-3 parent record; the phosphate salt record wasn't checked.
- ChEMBL flags quinacrine and thalidomide as withdrawn.

**ClinicalTrials.gov for the 50 shortlist pairs** (attached: `20261108-shortlist-ctgov-trials.csv`, API v2, interventions `"A" AND "B"`):
- For 41 pairs, no study listing both drugs has a lung cancer condition. For 11, no study lists both drugs at all.
- A count means both drugs appear in one study, not that they were given together (NCT01755923 compares gefitinib with docetaxel). "Lung cancer" also covers small-cell. So nonzero counts overstate combination testing, and zero is a signal, not proof.

Pairs with lung studies:

| Pair | Lung studies |
|---|---|
| Docetaxel + gefitinib | 22 |
| Paclitaxel + gefitinib | 13 |
| Paclitaxel + sorafenib | 5 |
| Tretinoin + paclitaxel | 4 |
| Docetaxel + sorafenib | 2 |
| Paclitaxel + lapatinib, bortezomib + erlotinib, tretinoin + docetaxel, paclitaxel + celecoxib | 1 each |

**External test** (`backend/external_test_results.txt`):
- **Test 1, inside the Merck screen.** Other-cancer results predict lung results: rank correlation 0.81 on all 7 lung lines and 0.82 on 5 lines ALMANAC never tested. At Loewe > 30, the top 20 holds 70–80% hits against a 3–4% base. This supports tier 1 in an independent screen.
- **Test 2, ALMANAC-trained model against Merck lung results** (132 shared pairs). Rank correlation is +0.27–0.29. Top-10 hits are 40% against a 19% base on all lines (p = 0.087), and 20% against 20% on the unseen lines. This is the limit.

**Licences** (pages read 8 Nov):

| Source | Licence as stated | Commercial use |
|---|---|---|
| TDC: OncoPolyPharmacology (O'Neil 2016, Merck; 583 combinations, 39 lines) | "Not Specified. CC BY 4.0" | Allowed under CC BY 4.0, with attribution |
| TDC: DrugComb (NCI-60; 129 drugs, 59 lines) | "Not Specified. CC BY 4.0" | As above |
| ChEMBL | CC BY-SA 3.0 | Allowed; share-alike applies to adaptations |
| Open Targets Platform | CC0 1.0 | Yes. Some included sources (Cancer Gene Census, PanelApp, Project Score) are marked "Commercial use for Open Targets" |
| NCI-ALMANAC (not on slide 41) | No licence text found; NCI calls it "publicly available" | Unknown |
| DepMap, Europe PMC, ClinicalTrials.gov | Terms pages could not be retrieved | Unknown |

## Today, before judging

### T1. Publisher PDFs on the `theory` branch (done; one step left)
- **Done:** the 6 journal PDFs were removed from `theory` and from its history (force-pushed 8 Nov; `theory` now at 91023eb). Links to each paper are in `theory/papers/README.md`.
- **Left:** GitHub still serves the old commits if someone asks for their SHA. GitHub's guide to removing sensitive data says Support can remove cached views and run garbage collection. Give them:
  - the repo: `leventkoymen/backprop-to-the-future-b56f8f5e-submission-repo`;
  - affected pull requests: none;
  - first changed commits: 5082031 and 58ab230.
- **Who:** the repo owner (Levent) should ask before the repo goes public. Support's guide says it helps where the risk "can't be mitigated by rotating" credentials, so whether it takes copyright cases is unknown.

### T2. Write-up claims that conflict with the repo or the checks (criterion 3)
**A only:**
- **"105 approved cancer drugs"** becomes "105 drugs; ChEMBL lists at least 97 at its highest phase". Some aren't cancer drugs (celecoxib, for example), and SN-38 is a metabolite.
- **"No patient data and no synthetic data"** becomes the README wording: the simulator data are synthetic and labelled, and no patient data is used anywhere.
- **"Seven times random"** for scenario 2 becomes "about 5.6 times" (0.20 / 0.036).
- **Hit prevalence:** pick one figure (3.6% in the write-up, 3.3% in the README) and define it.
- **Scenario 2 (0.20) against tier 2 (0.34, "both drugs screened, pair untested"):** confirm which is current before quoting either.
- **Docetaxel + gefitinib's score** is 160.1 in `backend/README.md` and 182 in `tumour_simulator/README.md`. Pick one.
- **Part C, "evidence only from retrieved sources":** now true for the agent, through the `citations_grounded` gate (`agent/README.md`). Cite the gate. The drug target and mechanism labels in `backend/annotations/` are still Gemini's own knowledge, majority-voted and marked `is_measurement: false`, so say so.

### T3. "What does a lab get that ALMANAC's table doesn't?" (criteria 2 and 1)
- **A:** Pitch and write-up: "LungPair turns a noisy public screen into a short follow-up list a lab can check". Show prediction (tiers 2–3) as an extension, with its measured precision. Lead with paclitaxel + lapatinib.
- **B:** Add `studies_in_lung`, `max_phase` and `merck_loewe` to the shortlist, to `/pair`, and to what the orchestrator's tools return. They come from static CSVs; the first two are attached. Rough effort 1–2 h, low demo risk.
- **C:** Make confirmation the product: rank measured hits by how likely they are to replicate, using ALMANAC's repeats. Not today.

### T4. Evidence sources: Google Search rather than the slide-41 literature sources (criteria 3 and 5)
- **Gap:** the research agent grounds on Google Search, and the gate checks citations against that metadata (`agent/README.md`). Slide 41 lists PubMed, Europe PMC, bioRxiv, medRxiv and OpenAlex. Web results are harder to reproduce and to licence-check.
- **A:** In Q&A, say the gate only lets through identifiers backed by grounding, and that PMIDs can also be checked through NCBI E-utilities (the optional check already in the agent).
- **B:** Show ChEMBL drug mechanisms next to the Gemini annotations, flagging disagreements. Or make the NCBI E-utilities check the default rather than optional. Rough effort 1–2 h, low demo risk.
- **C:** A literature tool built on PubMed or Europe PMC search as the primary evidence source, with Google Search as a fallback. Not today.

### T5. The live demo on a judge's input (criterion 4)
- **Now:** the agent on `main` meets the bar on paper. It has function calling (`resolve_drugs`, `rank_partners`, `rank_pairs`, `get_pair`), a research agent, a checker model, deterministic gates, human sign-off and a JSONL receipt. Osimertinib (not in ALMANAC) is reported as unknown.
- **A:** Rehearse three inputs and name each step aloud, ending at sign-off:
  1. "Which partner should a lab screen with gefitinib next?" (the README example);
  2. an untested pair of screened drugs, which returns tier 2;
  3. osimertinib.
- **Fallback:** keep `--no-llm` ready for a Wi-Fi failure.
- **B:** Same as T3 B. When docetaxel comes up for gefitinib, the output then shows "22 lung studies list both", which makes the agent look informed rather than naive.
- **C:** Add `check_trials` (live ClinicalTrials.gov API) and `check_approval` (ChEMBL) as orchestrator tools. Strongest for criterion 4, but the riskiest on judging day.
- **Check:** `/rank` with fewer than two resolvable drugs returned HTTP 400 as of 7 Nov (`backend/api.py`). Confirm the agent doesn't hit that path with a single-drug question.

### T6. External validation and the licence route (criterion 3)
- **A:** Put both external tests in the write-up and backup slides. Test 1 supports tier 1; Test 2 is the limit. Cite O'Neil 2016 through TDC (CC BY 4.0; its 583 combinations match the test's 583). For ALMANAC, write: "NCI: publicly available; no licence text found; TDC lists its DrugComb NCI-60 data as CC BY 4.0". Earlier feedback said to drop "any model benchmarks" from the pitch, and it's unclear whether that covers baselines. Until the team agrees, keep baselines in the write-up and backup.
- **B:** Confirm that `backend/external/mtl_oneil_summary_idx.csv` is TDC's O'Neil copy, or swap it in and rerun `external_test.py`. Rough effort 1 h.
- **C:** Rebuild on TDC's DrugComb copy of the NCI-60 data. Numbers may shift. Not today.

## Ask list, ranked

| # | Ask | Criteria | Effort | Demo risk |
|---|---|---|---|---|
| 1 | Repo owner asks GitHub Support to purge the cached PDF commits before the repo goes public (T1) | Submit | Minutes | None |
| 2 | Reconcile hit prevalence (3.3 vs 3.6%) and scenario 2 against tier 2 (0.20 vs 0.34) (T2) | 3 | 30 min | None |
| 3 | Add `studies_in_lung`, `max_phase` and `merck_loewe` to the shortlist, `/pair` and the agent's tool output (T3 B, T5 B) | 2, 4 | 1–2 h | Low |
| 4 | Check that a single-drug question doesn't hit the `/rank` 400 path (T5) | 4 | Under 1 h | Low |
| 5 | ChEMBL mechanisms next to the Gemini annotations, or the E-utilities check on by default (T4 B) | 3, 5 | 1–2 h | Low |
| 6 | Confirm or swap the O'Neil source to TDC; rerun the external test (T6 B) | 3 | 1 h | None |
| 7 | `check_trials` and `check_approval` as live agent tools (T5 C) | 4 | Half a day or more | High |

## Later (start-up or undecided)

- **L1. Literature baseline.** Count Europe PMC or PubMed co-mentions of each pair, limited to papers before 2017 so ALMANAC can't leak in, and score that ranking the same way as the model. It tests the claim that labs choose "by literature review and intuition". About 5,000 API calls. Not run yet.
- **L2. Cold start (tiers 3–4 at or near chance).** Use drug features from ChEMBL targets and mechanisms (CC BY-SA 3.0) and Open Targets (CC0). It's the main route to real prediction for new drugs.
- **L3. A lab's own cell lines.** DepMap could place them among ALMANAC's lines by mutation and expression. Test it first: the leave-one-line-out genotype test and Test 2 both found no line-specific signal.
- **L4. Commercial licence audit.** For a product, use only CC0 or CC BY sources, or clear the rest. ALMANAC has no licence text. ChEMBL's share-alike affects any database you redistribute. Open Targets passes some sources through for "commercial use for Open Targets" only. Europe PMC articles mix CC BY, CC BY-NC and CC0.
- **L5. More independent screens** through TDC and DrugComb, so validation doesn't rest on 22 shared drugs.
- **L6. Differentiation.** A September 2026 figshare record titled "PAIRWISE: Deep Learning-based Prediction of Effective Personalized Drug Combinations in Cancer Response" suggests the prediction space is crowded (title only, not read). Differentiate on triage, refusal tiers, dose reachability and the audit receipt.

**Slide-41 sources not worth adding:**
- UniProt, PDB and AlphaFold: ALMANAC synergy is measured at the level of whole cells, so structure doesn't help rank pairs.
- ClinVar and gnomAD: germline variants.
- MIMIC-IV, PhysioNet and Synthea: patient data, excluded by design.
- GTEx, GEO and CELLxGENE: later at most.

## Limits of this review

- ChEMBL matches were by name; the 5 misses and the estramustine salt need a manual lookup.
- Whether ClinicalTrials.gov search expands drug synonyms wasn't checked.
- Agent behaviour comes from `agent/README.md` and the PR #2 description. The code wasn't read or run.
- The DepMap, Europe PMC and ClinicalTrials.gov terms pages couldn't be retrieved.
