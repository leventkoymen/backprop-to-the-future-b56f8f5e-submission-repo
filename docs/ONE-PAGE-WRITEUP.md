# LungPair: Preclinical Drug-Pair Triage Powered by Multi-Agent Gemini

**AgentVerse 2026 · Biotech Track Submission**  
**Team:** Backprop to the Future (Duncan, Levent, Yasemin, Theo, Yong & Gemini CLI)  
**Deliverable:** One-Page Summary (Slide 42)

---

### 1. The Problem
Bringing novel cancer combinations to clinic takes over a decade and billions of pounds, yet combinations exponentially expand the search space. In the National Cancer Institute's **NCI-ALMANAC** screen across non-small cell lung cancer (NSCLC) lines, only **172 of 5,228 tested drug pairs (3.3%)** demonstrated synergy. High-throughput wet-lab screening is severely constrained by reagent costs, cell passage limits, and robot time. Randomly choosing combinations wastes >96% of screening capacity. Preclinical researchers lack a calibrated triage system that prioritizes viable pairs while explicitly communicating when data is insufficient.

### 2. Who It Helps & Real-World Need
- **Primary Users:** Cancer biology researchers, core screening facilities, and academic translational labs focusing on NSCLC combinations.
- **Immediate Value:** Reduces wasted screening wells by pre-filtering high-probability synergistic combinations (Tier 1 precision: 89% vs 3% random base rate), cutting experimental screening costs and accelerating time-to-hit.
- **Plausible Path to Use:** Designed for direct drop-in integration into academic screening cores. Before a multi-well assay is programmed, LungPair ranks candidate partners, fetches verified mechanistic literature, and outputs an auditable batch sign-off sheet for the principal investigator.

### 3. Data & Permitted Biotech APIs
All data sources strictly adhere to the hackathon's permitted data policy:
- **NCI-ALMANAC (DTP):** 5,228 measured pairs across 9 NSCLC lines (A549, EKVX, HOP-62, HOP-92, NCI-H226, NCI-H23, NCI-H322M, NCI-H460, NCI-H522). Rescaled to 9-dose response matrices.
- **PubChem PUG-REST API:** Real-time resolution of free-text drug names to canonical SMILES, CID, molecular formula, and molecular weights (`tools.resolve_pubchem`).
- **EMBL-EBI ChEMBL Web Services:** REST API retrieval of validated mechanisms of action and molecular target IDs (e.g. EGFR, TUBB1) to prime research agents (`tools.get_chembl_mechanism`).
- **NCBI PubMed / E-utilities:** Dynamic citation retrieval and title co-occurrence validation.
- **CCLE / cBioPortal:** Public baseline mutations for the 9 lung cell lines (`experiments/genotype_coverage/`).

### 4. Agent Architecture & Technical Evaluation
Built according to Google DeepMind's "Harness²" paradigm—prioritizing deterministic external gates over unconstrained generation:
- **Orchestrator (`gemini-4-argon`):** Resolves drug entities and drives native function calling (`resolve_drugs`, `rank_partners`, `resolve_pubchem`, `get_chembl_mechanism`).
- **Random Forest Ranker:** Offline machine-learning ranker predicting synergy scores, 95% confidence intervals, and assigning Evidence Tiers (1–4). The LLM never computes scores.
- **Parallel Research Pool (`gemini-3.8-flash`):** Spawns parallel subagents under a 90 s wall-clock budget with Google Search grounding and URL citation tracking.
- **Checker Agent (`gemini-3.5-flash-lite`):** Structured JSON validator auditing against ungrounded assertions.

**Held-Out Benchmark Results:**
- *Cross-Cancer to Lung Transfer:* **AUPRC 0.818**, **top-20 precision 0.89**, **top-50 precision 0.608 (MCC 0.709)** vs random baseline 0.028.
- *Unseen Tumour Generalization (Leave-One-Cell-Line-Out):* **p@50 0.784** (strong held-out generalization across lines).
- *Honest Negative Results Published:*
  - *Genotype-Matched Lines:* KRAS/TP53 mutation matching showed no signal over random same-size lines (win rate 28–59%).
  - *Merck O'Neil External Benchmark (132 pairs):* NCI lookup (50%, $p=0.019$) beat complex model predictions (40%, $p=0.087$). No external lift demonstrated.
  - *Brand-New Pairs:* Precision at chance (0.040 vs 0.029) $\rightarrow$ strictly withheld under Tier 4.

### 5. Limits & Responsible Safeguards
- **Pre-Model Intent Refusal:** Deterministic regex intercepts patient treatment questions (*"What dose should my patient take?"*) prior to making any model call.
- **Calibrated Evidence Tiers:**
  - *Tier 1 (other-cancer data):* Precision 0.89 $\rightarrow$ Ranked with confidence.
  - *Tier 2 (both drugs known):* Precision 0.34 $\rightarrow$ Ranked with moderate confidence.
  - *Tier 3 (single-drug data):* Precision 0.06 $\rightarrow$ Flagged as weak evidence.
  - *Tier 4 (no screen data):* Precision 0.04 $\rightarrow$ **REFUSED**: *"Test each drug alone first."*
- **Exact-Match Numbers Gate:** Decimal scores and intervals in natural language must match tool outputs bit-for-bit.
- **Grounded Citations Gate:** Any cited PMID/PMCID not verified in search redirects is automatically stripped.
- **Human-in-the-Loop Sign-off:** Sign-off gate programmatically restricts approval exclusively to passed candidates.
- **Cryptographic Audit Trail:** Thread-safe JSONL receipts (`runs/<id>.jsonl`) log exact tokens, costs, tool calls, and sign-offs.
- **Real Messy Screen Data vs Synthetic Controls:** Trained strictly on real experimental measurements (NCI-ALMANAC) where assay replicate agreement is ~51%. We model real biological variance directly rather than relying on clean synthetic data. The tumour simulator is strictly an internal software test harness labelled `[SYNTHETIC]`, never presented as real-world performance.
- **Preclinical Boundary:** Strictly in vitro cell-line screening prioritization. Not for clinical, patient, or diagnostic use.
