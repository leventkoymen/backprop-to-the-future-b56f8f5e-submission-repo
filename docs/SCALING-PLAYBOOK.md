# 🫁 LungPair: The 4-Pillar Scaling Playbook (Commercial, Technical & Data Flywheel)

**Objective:** A concrete, fact-checked roadmap explaining how LungPair scales from a hackathon prototype to a **$15.5M ARR market leader** across four interconnected dimensions.

---

## Pillar 1: Commercial Scaling (The 3-Phase Land-and-Expand)

```
PHASE 1 (Months 0–12): ACADEMIC BEACHHEAD
Target: 250 Academic Screening Cores & Translation Institutes
Sales Motion: Bottom-up researcher adoption ➔ Departmental recharge account
Contract Value: $35,000 / year / facility (5 seats)
Regulatory Drag: ZERO (Strictly Research Use Only / RUO)
ARR Milestones: Year 1: $540k ARR (15 cores) ➔ Year 2: $2.5M ARR (60 cores)

PHASE 2 (Months 12–24): BIOPHARMA & PRECLINICAL CROS
Target: 1,100 Clinical-Stage Oncology Biotechs & CROs (Charles River, WuXi, Evotec)
Sales Motion: Lead optimization SaaS licence for active doublet pipelines
Contract Value: $120,000 / year / pipeline + custom compound library integration
Value Proposition: Pre-screening 50 pairs in silico saves $147k in robotics/reagents
ARR Milestones: Year 3: $8.2M ARR (120 cores + 28 biopharma)

PHASE 3 (Months 24–48): CLINICAL COMPANION SAMD
Target: Hospital Oncology Centers & Serial Liquid Biopsy Laboratories
Sales Motion: Clinical Decision Support integration alongside blood ctDNA panels
Contract Value: $500 / serial liquid biopsy patient test (Reimbursed via NHS/Private)
Regulatory Drag: Formal MHRA / FDA SaMD clinical investigation
ARR Milestones: Year 4: $15.5M+ ARR (220 cores + 65 biopharma + ctDNA pilots)
```

### Why This Sales Motion Scales Rapidly
* **No Hospital Procurement Bottleneck:** In Phase 1 and 2, LungPair sells out of departmental research consumable budgets. Unlike hospital clinical IT systems (which take 18–36 months to procure), academic recharge software closes in **4 to 8 weeks**.
* **Immediate Payback:** A core facility running two 50-pair campaigns per year saves **$294,000 in consumable waste**—an 8.4x return on their $35,000 annual licence.

---

## Pillar 2: Technical & Compute Scaling (Handling 1,000,000 Queries at Zero Marginal Cost)

Can our AI architecture handle enterprise scale without crashing or burning millions in cloud bills? **Yes, because we decouple prediction from language generation.**

| Pipeline Layer | Scaling Mechanism | Latency at Scale | Marginal Cost |
| :--- | :--- | :---: | :---: |
| **Offline ML Ranker** | Scikit-learn Random Forest compiled into optimized C-extensions. Runs on local CPU. | **< 5 ms** | **$0.00** |
| **Entity Resolution** | PubChem PUG-REST API with local SQLite cache of 105 panel structures and SMILES. | **< 50 ms** | **$0.00** |
| **Google Gemini Routing** | **Context Caching:** System prompt templates and ChEMBL target dictionaries are cached in Gemini RAM, cutting input token fees by 75–90%. | **1.2 s** | **<$0.025** |
| **Bulk Combinatorial Sweeps** | **Google Batch API:** Bulk 10,000-compound combinatorial library sweeps run asynchronously at 50% discount ($1.00/M in, $5.00/M out for Argon). | **Batch (hours)** | **<$0.01** |
| **3D Visualization Client** | Three.js WebGL canvas rendered entirely client-side on the user's GPU. Zero server GPU load. | **60 FPS** | **$0.00** |

* **Total Scaling Verdict:** Even at **100,000 enterprise queries per month**, our monthly cloud/API bill is under **$2,500**, sustaining software gross margins above **92%**.

---

## Pillar 3: The Data Flywheel Scaling (The Self-Reinforcing Moat)

```
        ┌────────────────────────────────────────────────────────┐
        │       1. LungPair Triage Ranks Top 50 Doublets         │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │    2. Partner Core Pipettes & Measures Biological Hits │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │  3. Cryptographic JSONL Receipts Feed Back into Vault  │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │ 4. Tier 2 Pairs (34% Precision) Promoted to Tier 1     │
        │    (89% Precision) ➔ Widening the Empirical Moat       │
        └────────────────────────────────────────────────────────┘
```

1. **Every Assay Enhances the Network:** Currently, 200 pairs sit in Tier 1 (cross-cancer data, 0.89 precision) and 5,028 pairs sit in Tier 2 (untested in lung, 0.34 precision).
2. **Recursive Data Ingestion:** As partner laboratories run LungPair shortlists, validated hits and dead ends are cryptographically deposited into our model store.
3. **Compound Flywheel:** Each year of customer usage converts ~300 Tier 2 pairs into Tier 1 pairs. Within 3 years, LungPair holds the world’s densest validated oncology synergy network, making it impossible for new entrants to compete.

---

## Pillar 4: Biological & Indication Scaling (Beyond NSCLC)

* **Phase A: Pan-Cancer Cell-Line Expansion (NCI-60):**  
  Our pipeline is pre-configured to ingest all 60 cell lines in NCI-ALMANAC:
  * Breast Cancer (MCF7, MDA-MB-231)
  * Melanoma (SK-MEL-28, MALME-3M)
  * Ovarian & Colorectal Cancers (OVCAR-8, HCT-116)
  * *Scale:* 5,228 pairs × 60 cell lines = **313,680 experimental conditions** triaged in the same pipeline.
* **Phase B: Beyond Small Molecules to Novel Modalities:**  
  * Antibody-Drug Conjugate (ADC) payloads + targeted kinase inhibitors.
  * Epigenetic modulators + standard chemotherapy doublets.
* **Phase C: Clinical Serial ctDNA Monitoring:**  
  * Re-ranking combination options from liquid biopsy blood samples as resistance mutations (like KEAP1 or STK11) appear during patient therapy.

---

## Summary Script for Judges on Scaling (15 Seconds):
> *"We scale across three distinct horizons: commercially, our beachhead targets 250 academic screening cores ($12.5M SOM) closing in 4–8 weeks out of departmental consumable budgets, expanding to a $132M biopharma SAM. Technically, our Random Forest runs locally in under 5 milliseconds while Gemini context caching keeps query costs under $0.05, sustaining 92% gross margins. And biologically, every wet-lab batch feeds back into our cryptographic audit vault, converting Tier 2 untested pairs into Tier 1 confirmed hits."*
