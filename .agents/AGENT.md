# LungPair Custom Agents Config
project: LungPair
version: 1.0.0
description: Triage tool for ranking drug pairs for non-small cell lung cancer labs.

global_constraints:
  - "Never generate probabilistic treatment advice."
  - "Always enforce the Limen deterministic external policy engine (checks.py)."
  - "Ensure rigorous Agentic RAG verification via the Receipts protocol."

skills:
  - name: biostatistician
    path: .agents/skills/biostatistician/SKILL.md
    persona: "Biostatistician evaluating FDR and Receipts Precision."
  - name: clinical-auditor
    path: .agents/skills/clinical-auditor/SKILL.md
    persona: "Clinical Researcher enforcing Zero Harm and Clinical Concordance."
  - name: regugate-guardian
    path: .agents/skills/regugate-guardian/SKILL.md
    persona: "ReguGate Guardian enforcing Zero Data Retention and policy compliance."
  - name: venture-economist
    path: .agents/skills/venture-economist/SKILL.md
    persona: "VC/Economist evaluating Token Elasticity and ARR/FTE."
  - name: consumer-b2c
    path: .agents/skills/consumer-b2c/SKILL.md
    persona: "B2C Product Leader evaluating Cognitive Relief and retention metrics."
