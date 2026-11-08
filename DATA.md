# LungPair: Data Sources, APIs & Licences

All datasets and application programming interfaces (APIs) utilized in **LungPair** strictly comply with the **AgentVerse 2026 Biotech Track Permitted Data Policy** (Slide 41).

Zero personal health data (PHD) or patient-identifiable data is ingested, stored, or processed. All cell-line data is derived from immortalized in vitro laboratory cell cultures.

---

## 1. Primary Screening & Genomic Datasets

| Dataset | Source / Reference | Description & Role in LungPair | Terms of Use & Licence |
|---|---|---|---|
| **NCI-ALMANAC** | National Cancer Institute (NCI DTP)<br>Holbeck et al., *Cancer Res* 2017 | **5,228 measured drug pairs** across 9 non-small cell lung cancer cell lines (A549, EKVX, HOP-62, HOP-92, NCI-H226, NCI-H23, NCI-H322M, NCI-H460, NCI-H522). Primary training and validation matrix. | **Public Domain** (U.S. Government Work, 35 U.S.C. §105). Publicly accessible via NCI DTP and Therapeutics Data Commons (TDC). |
| **Merck Combination Screen** | O'Neil et al., *Mol Cancer Ther* 2016 | **Held-out external benchmark (132 shared pairs)** across 7 lung cancer cell lines (including 5 lines completely unseen by NCI-ALMANAC). Used for independent external validation. | **Open Academic Access** / Distributed under Therapeutics Data Commons (TDC) open terms. |
| **CCLE (Cancer Cell Line Encyclopedia)** | Broad Institute / Novartis<br>Ghandi et al., *Nature* 2019 | Baseline mutation status (EGFR, KRAS, TP53, STK11, KEAP1, SMARCA4) for the 9 lung lines. Used in `experiments/genotype_coverage/`. | **Creative Commons Attribution 4.0 International (CC BY 4.0)** via cBioPortal / DepMap. |

---

## 2. Permitted Programmatic Biotech APIs

| API & Service | Provider / Endpoint | Information Retrieved | Access Policy & Terms |
|---|---|---|---|
| **PubChem PUG-REST API** | NCBI / NLM / NIH<br>`https://pubchem.ncbi.nlm.nih.gov/rest/pug/` | Resolves free-text drug names to canonical SMILES, PubChem CID, molecular weight, and molecular formula (`tools.resolve_pubchem`). | **Public Domain** / Free programmatic access under NIH/NLM Terms of Service. Zero authentication required. |
| **EMBL-EBI ChEMBL API** | European Molecular Biology Laboratory (EBI)<br>`https://www.ebi.ac.uk/chembl/api/` | Resolves verified biological mechanisms of action and molecular target IDs (e.g., EGFR, TUBB1, TOP2A) (`tools.get_chembl_mechanism`). | **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Zero authentication required. |
| **NCBI PubMed E-utilities** | National Center for Biotechnology Information<br>`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | Dynamic citation grounding validation and co-occurrence lookup (`tools.check_pubmed_citation`). | **Public Domain** (NLM API Terms of Service; $\le 3$ requests/s without API key). |
| **Google Search Grounding** | Google DeepMind / Google GenAI SDK | Dynamic URL citation extraction and grounding metadata for `gemini-3.8-flash` research subagents. | Governed by Google Cloud / Gemini API Terms of Service. |

---

## 3. Synthetic Controls & Engineering Test Harness

| Software Module | File Path | Purpose & Limitations | Licence |
|---|---|---|---|
| **NSCLC Tumour Progression Simulator** | `tumour_simulator/` | Mechanistic clonal evolution simulator (logistic subclone growth, mutation trees, and toxicity-limited dosing). Evaluates inference recovery under known ground truth. | **MIT Licence** (matching repository). |

**Mandatory Scientific Disclosure (Slide 41 Compliance):**
1. **Explicit Labelling:** All synthetic outputs are strictly labelled `[SYNTHETIC]`.
2. **Never Presented as Real Clinical Performance:** The simulator is strictly an engineering control for algorithmic benchmarking. Real-world performance is evaluated solely on empirical biological screens (NCI-ALMANAC and Merck O'Neil).
3. **Zero Patient Data:** No patient biopsies or clinical records were used to generate synthetic models.
