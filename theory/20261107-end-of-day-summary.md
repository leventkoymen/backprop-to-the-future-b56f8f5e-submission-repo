# End of day summary, 7 November 2026 (Theodore)

Team-only working notes for LungPair, AgentVerse 2026 Biotech track. Facts are from the team branches and Theodore's handoff notes; anything unchecked is marked.

## Earlier today
- **Event:** the Biotech brief and judging criteria arrived. The criteria are uniqueness, real-world need, science/data/evaluation, a multi-step agent, and risks. The rules ban real patient data.
- **Idea:** LungPair, which ranks NSCLC drug pairs for labs from NCI-ALMANAC.
- **Data fix:** at about 14:30 Theodore retracted an earlier plate-averaging fix and recomputed the numbers: hit rate 7.71%, NSCLC top-20 lookup 16.7 of 20. The Yong handoff went out as v6 with the corrected numbers.
- **Duncan's lung file:** it matches the corrected data on 45,764 of 45,797 results. 54 results with a blank SCORE should be dropped.
- **Documents:** business case v1, v2 and v3 (v3 adds an immunotherapy roadmap as Part D), and roadmap slide v1.
- **This branch (`theory`):** pushed with Theodore's notes, the roadmap .md, the slide, business case v3 and 6 papers. The PDFs were removed from the repo and its history on 8 Nov; links are in `theory/papers/README.md`.

## Evening
- **Yong handoff v7:** layout fix only. The section 7 table no longer splits across pages.
- **Roadmap slide v2:** built with seven wording fixes. It is superseded because the immunotherapy angle was dropped (see Decisions), so it was not pushed.
- **Branch review:**
  - **`yong/claude-1-genotype-coverage`:** ranking pairs from the lung lines that carry a given mutation did no better than random line sets (matched beat random 28% to 59% of the time, where 50% means no signal). Ranking on all lines did best for every gene. The roadmap should therefore rank by coverage (pairs that hit in every genotype tested), not by genotype match.
  - **`backend-pipeline`** (Duncan): ranker API with four evidence tiers, plus a synthetic tumour simulator.
  - **`yasemin/3d-visual`:** 3D replay of measured results.
  - **`Levent`:** Gemini test script.
- **Mismatches a judge could catch:**
  - Hit prevalence: 3.3% in `backend-pipeline/README.md`, 3.6% (189 of 5,228) in the LungPair doc and the Yong handoff.
  - Docetaxel + gefitinib: score 182 in `tumour_simulator/README.md`, 160.1 in `backend/README.md`. Both call it rank 4.
  - Simulator patient counts: 30 (layout section), 40 (regimen table), 25 (sweep).
- **Note added:** the drug repurposing note (Kulkarni et al. 2023) was added to `theory/paper-comments.txt` (b587092 after the 8 Nov history rewrite).
- **Demo bug, not fixed:**
  - In `backend/api.py` on `backend-pipeline`, `/rank` with a drug outside the 105 (e.g. pembrolizumab) plus one known drug returns HTTP 400 "could not resolve two or more drugs" instead of a refusal (lines 149-150).
  - `/pair` only accepts NSC numbers, so a drug name gets an HTML 404.
  - `/pair` also returns a score for an NSC number outside the 105, although tier 4 is meant to be refused.
  - This was found by reading the code; it has not been run.

## Decisions
- Drop the immunotherapy angle from the roadmap.
- The roadmap becomes backup material, not part of the 4-minute pitch. Its new framing: repurposing existing drugs plus coverage ranking.
- The LLM benchmark on the tumour simulator (`agent_bench.py`) is on hold.

## Open
1. **Roadmap rework:** the backup slide and roadmap .md (repurposing + coverage) are not started. The claim that NCI-ALMANAC's drugs are approved drugs is unchecked.
2. **Stale files on this branch:** `NEED TO CORRECT20261107-lungpair-roadmap-slide.pptx` and `20261107-lungpair-roadmap.md` still carry the immunotherapy version.
3. **Business case v3:** Part D is still the immunotherapy roadmap.
4. **Headline from feedback:** it needs the share of LungPair picks that were real hits, against random (about 3%) and a plain lookup, from tonight's run. The feedback suggests the Merck O'Neil screen as an unseen test set. Owner: unknown.
5. **Not checked:** the style of all of today's written documents.
