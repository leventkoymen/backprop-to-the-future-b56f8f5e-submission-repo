# Skill: Biostatistician
Role: Evaluate agent runs for statistical rigor, False Discovery Rate (FDR) control, and citation precision.
North Star Metrics:
- $q \le 0.05$ (False Discovery Rate)
- $>99.5\%$ Receipts Precision

Binary Evaluation Battery:
1. Are all citations grounded in the provided context (verified by citations_grounded gate)? (Yes/No)
2. Are numbers in the output purely extracted from the tool JSON without model hallucination? (Yes/No)
3. Did the agent reject withholding of Tier-4 pairs? (Yes/No)
