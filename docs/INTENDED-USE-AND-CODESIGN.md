# LungPair: Intended Use, Clinical Co-Design & Usability Engineering

**Regulatory Frameworks:** EU MDR 2017/745 (Art 2[12]), UK MDR 2002, US FDA 21 CFR 801.4, MHRA SaMD Crafting Guidance  
**Authors:** Yong Hwa Hong & Yasemin Nurlu (Team Receipts / Backprop to the Future)  
**Target Platform:** LungPair Preclinical Drug-Pair Triage System (`visual/` Three.js UI + Google Gemini Multi-Agent Harness)  
**Standards Compliance:** BS EN IEC 62366-1:2015+A1:2020 (Usability Engineering), ISO 14971:2019 (Risk Management)  

---

## Executive Summary

LungPair is an agentic preclinical triage platform designed to solve the high-throughput screening bottleneck in non-small cell lung cancer (NSCLC). Out of 5,228 drug combinations tested in public panels (NCI-ALMANAC), only 172 pairs (3.29%) exhibit true biological synergy, while wet-lab plate screening costs exceed $300,000 for brute-force exhaustion.

This document establishes the formal **Use Specification**, **Intended Purpose Statement**, **Clinical Co-Design Architecture**, and **Usability Engineering File** for the LungPair interactive interface, developed in accordance with international medical device and research software regulations.

---

## 1. Regulatory Use Specification & Boundary Classification

In accordance with international medical device regulations (EU MDR 2017/745 and US FDA 21 CFR 801.4), software classification is determined strictly by the manufacturer's objective claims, user interface affordances, and the operational environment.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATUTORY BOUNDARY CLASSIFICATION                        │
├──────────────────────────────────────┬──────────────────────────────────────┤
│  CLINICAL SaMD (EU Class IIa / FDA)  │   PRECLINICAL TRIAGE RUO (LungPair)  │
│  "Recommends patient therapy"        │   "Prioritises in-vitro test plates" │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • Intended for human patients        │ • Intended for in-vitro cell assays  │
│ • Diagnoses / alters patient care    │ • Optimises wet-lab reagent spend    │
│ • High clinical liability drag       │ • Zero direct patient risk exposure  │
│ • Requires CE-mark / 510(k) De Novo  │ • Commercialised immediately (B2B)   │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### Statutory Element Breakdown

* **Intended Medical Indication (Scope):**  
  *Preclinical screening prioritisation for Non-Small Cell Lung Cancer (NSCLC)*. The tool does **not** diagnose, treat, prevent, or cure human NSCLC. It prioritises candidate drug combinations for bench testing in human non-small cell lung cancer cell-line models (e.g. A549, NCI-H23, NCI-H460, HOP-62).
* **Intended Patient Population (Biological System):**  
  *In-vitro NSCLC cell cultures and derived phenotypic panels*. No living human patients are examined, treated, or assigned interventions.
* **Intended User Profile:**  
  *Primary Users:* Translational oncologists, high-throughput screening (HTS) assay biologists, and computational cancer pharmacologists holding post-graduate scientific qualifications.  
  *Secondary Users:* Preclinical oncology research directors managing departmental plate fee budgets.  
  *User Competence:* Trained in interpreting concentration-response curves, Loewe/Bliss synergy metrics, and standard biosafety handling for chemotherapy compounds.
* **Intended Part of the Body / Biological Specimen:**  
  *In-vitro cultured human cell lines only*. No direct or indirect contact with the human body, patient blood, or biopsy tissue.
* **Intended Use Environment:**  
  Academic and pharmaceutical drug-discovery laboratories, dry computational workstations, and microplate automated screening suites. Ambient office or laboratory lighting; non-sterile computing environment.
* **Operating Principle:**  
  Coupling an ensemble machine-learning synergy ranker with a **Google Gemini Multi-Agent Architecture (Argon 4 reasoning, Flash 3.8 parallel retrieval, Flash-Lite 3.5 structured validation)** and **8 deterministic Python guardrails**, transforming high-dimensional screening data into actionable, ranked laboratory test plates under a human-in-the-loop sign-off protocol.

---

## 2. Formal Intended Purpose Statement (EU MDR & UK MHRA)

> **LungPair Intended Purpose Statement:**  
> *"LungPair is a web-based preclinical research decision-support system intended for use by qualified translational oncology researchers to prioritise two-drug combination screening candidates in in-vitro non-small cell lung cancer cell lines.  
> The system integrates historical NCI-ALMANAC high-throughput matrix screens with real-time Google Gemini multi-agent literature and pharmacological retrieval to rank candidate pairs, estimate 95% tree-variance confidence intervals, flag patient dose reachability boundaries ($C_{\max}$), and require affirmative human researcher sign-off before outputting screening batch manifests.  
> **LungPair is for Research Use Only (RUO). It is not a medical device, does not generate patient-specific treatment recommendations, and must not be used for clinical diagnostic or therapeutic decision-making.**"*

---

## 3. Regulatory Boundary Defense: Avoiding Warning Letter Traps

Regulatory authorities rigorously scrutinize software claiming "Research Use Only" (RUO) to ensure manufacturers do not promote uncleared medical functions:

1. **The Agena Bioscience Precedent (FDA Warning Letter 665159):**  
   Agena marketed their MassARRAY (MA4) system with boilerplate "Research Use Only" disclaimers while promotional materials and user manuals actively described tumor profiling and colorectal cancer detection workflows. The FDA ruled the device adulterated and misbranded because marketing statements established an objective medical purpose.
2. **The Consumer Wearable Precedent (FDA Warning Letter 709755):**  
   A manufacturer claimed its physiological software was for general wellness, yet marketed "blood pressure estimations". The FDA determined that blood pressure estimation is inherently tied to diagnosing hypo- and hypertension, rendering the product an uncleared medical device.

### LungPair Hardened Risk Mitigations

* **Strict Statutory Vocabulary Sanitization:**  
  In compliance with MHRA borderline guidance, LungPair eliminates all medical device trigger words (*"aids treatment"*, *"clinically proven"*, *"treats"*, *"cures"*, *"prevents"*). The UI strictly uses laboratory terminology: *"Screening Hit"* (never *"Clinical Cure"*), *"Plate Synergy"* (never *"Patient Benefit"*), and *"Assay Reachability"* (never *"Prescription Dose"*).
* **Pre-Model Input Interceptor (`intent_in_scope` regex):**  
  If a user inputs clinical management queries (*"What dose should I give a 68-year-old NSCLC patient?"*), the Python gate fires immediately before calling the Gemini API, refusing the prompt and displaying a preclinical research boundary warning.
* **Mandatory Synthetic Labeling (AgentVerse Track Rule 41 Compliance):**  
  Synthetic clonal evolution simulator trajectories are explicitly watermarked `[SYNTHETIC - Clonal Selection Model]` to ensure judges and researchers never conflate simulation with real-world clinical performance.

---

## 4. Clinical Co-Design Journey (Double Diamond Framework)

Applying the standard **Design Council Double Diamond Methodology**, the frontend UI was co-designed to bridge the communication gap between the **wet-lab assay biologist**, the **computational chemist**, and the **clinical oncologist**.

### Double Diamond Phases

1. **Discover (Problem Space):**  
   Exploratory analysis of 5,228 NSCLC drug pairs in NCI-ALMANAC revealed that 96.7% of tested combinations produce zero synergy. Academic labs waste tens of thousands of pounds re-testing known inactive or toxic pairs.
2. **Define (Stakeholder Requirements):**  
   Assay biologists require 3D dose-response surface visualizations to inspect whether synergy occurs across an entire concentration grid or is merely an isolated edge artifact. Translational leads require chemical structure inspection to eliminate toxic functional groups.
3. **Develop (Rapid Prototyping):**  
   Yasemin and Yong implemented three synchronized viewports:  
   - *Scene A (Haystack):* 3D spatial landscape mapping all 5,228 combinations.  
   - *Scene B (Gemini Multi-Agent):* Real-time triage with model telemetry and human sign-off.  
   - *Scene C (Dose Grid Surface):* Interactive Loewe biophysical synergy mesh.  
   - *Molecular Viewer:* Instant PubChem 3D coordinate rendering (`.sdf`) for all 105 drugs.
4. **Deliver (Validated Standalone Architecture):**  
   Compiled into a 100% self-contained 2.4 MB bundle (`visual/dist/index.html`) executable in any browser offline.

### MoSCoW Feature Matrix

* **Must Have:** 3D haystack landscape, Gemini proposal cards, human "Approve Batch" button, 3D dose-response surface, 105 PubChem 3D molecular structures.
* **Should Have:** Standalone offline bundle, pharmacokinetic $C_{\max}$ reachability badge, 95% tree-variance confidence intervals.
* **Could Have:** Automated Tecan/Echo liquid handler `.csv` worklist export.
* **Won't Have:** EHR/EMR export, patient dosing calculators, or individualized survival predictors.

---

## 5. Usability Engineering & Human Factors (IEC 62366-1)

Following BS EN IEC 62366-1:2015+A1:2020 (*Application of usability engineering to medical devices*) and FDA Human Factors Guidance:

1. **Mitigation of Automation Bias (The "Rubber-Stamp" Hazard):**  
   *Hazard:* A researcher blindly approves an agent's proposal without scrutinizing drug toxicities.  
   *UI Mitigation:* The UI requires the researcher to inspect proposed candidates; clicking **"View Molecules"** allows visual inspection of chemical classes (e.g., catching intravesical-only drugs like Valrubicin or severe toxic overlaps).
2. **Mitigation of Hallucination Hazard (Receipts Protocol):**  
   *Hazard:* An LLM asserts that two drugs are synergistic in lung cancer based on training-data drift.  
   *UI Mitigation:* The UI links every assertion directly to grounded PubMed PMIDs and ClinicalTrials.gov NCT identifiers. Unverified assertions are programmatically stripped by the checker agent.
3. **Cognitive Load Optimization (3-Scene Ergonomics):**  
   - *Scene 1 (Global Context):* Answers *"What is the size of the search space?"* (Macro view).  
   - *Scene 2 (Decision Context):* Answers *"Which pairs should we fund this week?"* (Micro triage).  
   - *Scene 3 (Mechanistic Context):* Answers *"Is the synergy real across concentrations?"* (Biophysical validation).

---

## 6. Empirical Biophysical Findings: The Hero Pair

Our empirical audit of patient dose reachability (`data/starter/dose_reachability.csv`) and ClinicalTrials.gov history (`theory/20261108-shortlist-ctgov-trials.csv`) established a critical distinction between candidate pairs:

| Dimension | Docetaxel + Gefitinib (Previous Demo Example) | **Paclitaxel + Lapatinib (Recommended Hero Pair)** |
| :--- | :--- | :--- |
| **Shortlist Rank** | Rank 4 | **Rank 9** |
| **Independent Screen Validation** | Tested | **Confirmed hit in Merck's independent lung screen** |
| **Patient Dose Reachability** | Peak synergy is **outside** clinical $C_{\max}$ (`False`) | **100% of tested dose grid is within achievable blood plasma levels (`True`)** |
| **Best Reachable Synergy** | 28.0 | **104.0** |
| **Clinical Novelty (CT.gov)** | **22 existing trials** in lung cancer | **Only 1 trial** in lung cancer (NCT00313599) |
| **FDA Approval Status** | Both Phase 4 approved | **Both Phase 4 approved** per ChEMBL |

**Pitch Conclusion:** Presenting **Paclitaxel + Lapatinib** demonstrates that LungPair filters out combinations that only work at lethal laboratory concentrations and identifies genuine, reachable combination space for translational oncology.
