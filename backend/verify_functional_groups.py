"""
Check Gemini's functional-group list against RDKit substructure matching.

functional_groups.py asks Gemini which groups are present and keeps any name
that is in the SMARTS library. That lets Gemini list a group the molecule does
not have (e.g. busulfan "ester": it is a sulfonate). This script makes the
pattern match the source of truth:

- groups_present  = groups whose SMARTS really matches the SMILES (RDKit)
- key_group       = Gemini's choice, kept only if it is in groups_present
- why_it_matters / receptor_interaction = Gemini text, kept, but marked
  key_group_verified = no when Gemini's key group does not match
- gemini_claimed_not_matched / matched_not_claimed = the disagreements

No language model is called here. Usage:
    python verify_functional_groups.py
Writes annotations/functional_groups_verified.csv and prints a summary.
"""
import os
import pandas as pd
from rdkit import Chem, RDLogger

from functional_groups import GROUPS

RDLogger.DisableLog("rdApp.*")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "annotations", "functional_groups.csv")
OUT = os.path.join(HERE, "annotations", "functional_groups_verified.csv")
PATTERNS = {g: Chem.MolFromSmarts(s) for g, s in GROUPS.items()}


def matched_groups(smiles):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return [g for g, p in PATTERNS.items() if m.HasSubstructMatch(p)]


def main():
    d = pd.read_csv(SRC)
    rows = []
    for _, r in d.iterrows():
        true = matched_groups(r.smiles)
        claimed = [g for g in str(r.groups_present).split("|") if g and g != "nan"]
        if true is None:
            rows.append({**r.to_dict(), "groups_present": "", "key_group_verified": "no",
                         "gemini_claimed_not_matched": "", "matched_not_claimed": "",
                         "check": "SMILES could not be parsed"})
            continue
        ok = r.key_group in true
        rows.append({**r.to_dict(),
                     "groups_present": "|".join(true),
                     "gemini_groups_present": "|".join(claimed),
                     "key_group": r.key_group if ok else "",
                     "key_group_verified": "yes" if ok else "no",
                     "gemini_claimed_not_matched": "|".join(sorted(set(claimed) - set(true))),
                     "matched_not_claimed": "|".join(sorted(set(true) - set(claimed))),
                     "check": "rdkit substructure match"})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    n = len(out)
    bad = (out.gemini_claimed_not_matched.fillna("") != "").sum()
    kv = (out.key_group_verified == "yes").sum()
    print(f"{n} drugs; Gemini listed a group the pattern does not find in {bad}; "
          f"key group confirmed by pattern in {kv}/{n}. Wrote {OUT}")


if __name__ == "__main__":
    main()
