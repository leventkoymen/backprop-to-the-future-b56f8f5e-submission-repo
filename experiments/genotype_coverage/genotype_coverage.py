"""
Genotype-aware drug-pair coverage for non-small cell lung cancer (YONG, 7 Nov 2026).

Question: if a blood test shows the tumour has gained a mutation (e.g. KEAP1),
which drug pairs still worked in the lab cell lines that carry it - and does
using only those genotype-matched lines rank pairs better than using all lines?

    uv run --with pandas python genotype_coverage.py --raw ALMANAC_NSCLC_raw.csv
    uv run --with pandas python genotype_coverage.py --raw ALMANAC_NSCLC_raw.csv --query KEAP1

Inputs
  --raw      NCI-ALMANAC raw file (lung rows of ComboDrugGrowth_Nov2017.csv, NCI DTP)
  data/cell_line_mutations.csv  CCLE mutations for the 9 lung lines (cBioPortal, ccle_broad_2019)
  data/drug_names.csv           NSC number -> drug name (NCI ComboCompoundNames)

Method
  1. ComboScore per (pair, cell line): sum of dose SCOREs in each study, BLANK grids
     dropped (sum(min_count=1)), rescaled to a 9-dose grid (x 9 / non-blank doses),
     median over repeat studies. Hit = ComboScore > 50 (NCI convention).
  2. Coverage = share of tested lines where the pair is a hit (robust across genotypes).
  3. Leave-one-line-out test, per gene: for each mutant line L, rank pairs by hit rate in
     the OTHER mutant lines (genotype-matched) vs in ALL other lines (unmatched), and
     score precision@50 against L's measured hits. Random = L's base hit rate.
     Fair control: every other same-size set of lines (matched uses fewer lines, so
     comparing it only with "all lines" mixes up genotype with sample size).

Limits (say these out loud)
  - Only 9 cell lines; each gene group has 3-6 lines. KRAS, STK11 and KEAP1 groups overlap
    heavily (A549, NCI-H23, NCI-H460), so genes are not separable.
  - Cell lines in dishes: no immune system, no evolution under treatment.
  - CCLE has NCI-H322 (parent line); ALMANAC used NCI-H322M (a subline). Assumed equal.
  - Mutation calls are not all functional (e.g. EGFR R309G in NCI-H226 is not a known driver).
  - Retrospective: every result here was already measured.
"""
import argparse
import os
from itertools import combinations

import numpy as np
import pandas as pd

HIT = 50.0
HERE = os.path.dirname(os.path.abspath(__file__))
GENES = ["KRAS", "STK11", "KEAP1", "TP53", "SMARCA4"]


def pair_line_scores(raw_path):
    df = pd.read_csv(raw_path, low_memory=False)
    df["CELLNAME"] = df.CELLNAME.str.replace("\x1a", "", regex=False).str.strip()
    df = df[(df.VALID == "Y") & df.NSC2.notna()].copy()
    df["a"] = df[["NSC1", "NSC2"]].min(axis=1).astype(int)
    df["b"] = df[["NSC1", "NSC2"]].max(axis=1).astype(int)
    g = df.groupby(["a", "b", "CELLNAME", "STUDY"]).SCORE
    st = pd.DataFrame({"cs": g.sum(min_count=1), "n": g.count()}).reset_index()
    blank = int(st.cs.isna().sum())
    st = st.dropna(subset=["cs"])
    st["cs"] = st.cs / st.n * 9
    s = st.groupby(["a", "b", "CELLNAME"]).cs.median().reset_index(name="ComboScore")
    s["hit"] = (s.ComboScore > HIT).astype(int)
    return s, blank


def groups():
    m = pd.read_csv(os.path.join(HERE, "data", "cell_line_mutations.csv"))
    return {g: sorted(m[m.gene == g].almanac_cellname.unique()) for g in GENES}


def names():
    n = pd.read_csv(os.path.join(HERE, "data", "drug_names.csv"))
    return dict(zip(n.nsc, n.name))


def precision_at(rank_scores, truth, k):
    top = rank_scores.sort_values(ascending=False, kind="mergesort").index[:k]
    return truth.loc[top].mean()


def loo_test(hits, lines_by_gene, k=50):
    """hits: pairs x lines matrix of 0/1 (NaN = not tested)."""
    rows = []
    for gene, mut in lines_by_gene.items():
        if len(mut) < 3:
            continue
        for L in mut:
            truth = hits[L].dropna()
            others_mut = [x for x in mut if x != L]
            others_all = [x for x in hits.columns if x != L]
            matched = hits.loc[truth.index, others_mut].mean(axis=1).fillna(0)
            unmatched = hits.loc[truth.index, others_all].mean(axis=1).fillna(0)
            # fair control: every same-size set of OTHER lines that is not the matched set
            pool = [x for x in others_all]
            same_size = [c for c in combinations(pool, len(others_mut)) if set(c) != set(others_mut)]
            ctrl = [precision_at(hits.loc[truth.index, list(c)].mean(axis=1).fillna(0), truth, k)
                    for c in same_size]
            rows.append({
                "gene": gene, "held_out_line": L, "n_matched_lines": len(others_mut),
                "pairs": len(truth), "base_rate": round(truth.mean(), 3),
                f"p@{k}_matched": round(precision_at(matched, truth, k), 3),
                f"p@{k}_all_lines": round(precision_at(unmatched, truth, k), 3),
                f"p@{k}_same_size_random": round(float(np.mean(ctrl)), 3),
                "matched_beats_share": round(float(np.mean(
                    [precision_at(matched, truth, k) > c for c in ctrl])), 3),
            })
    return pd.DataFrame(rows)


def query(hits, scores, gene, lines_by_gene, nm, top=20):
    mut = lines_by_gene[gene]
    wt = [x for x in hits.columns if x not in mut]
    t = pd.DataFrame({
        "hit_rate_mutant": hits[mut].mean(axis=1),
        "n_mutant_tested": hits[mut].notna().sum(axis=1),
        "hit_rate_other": hits[wt].mean(axis=1),
        "coverage_all": hits.mean(axis=1),
    })
    t = t[t.n_mutant_tested >= 2]
    t = t.sort_values(["hit_rate_mutant", "coverage_all"], ascending=False).head(top).reset_index()
    t.insert(0, "drug_b_name", t.b.map(nm))
    t.insert(0, "drug_a_name", t.a.map(nm))
    return t.round(3), mut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--query", choices=GENES, help="gene gained in the blood test")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    scores, blank = pair_line_scores(a.raw)
    hits = scores.pivot_table(index=["a", "b"], columns="CELLNAME", values="hit")
    lbg = groups()
    nm = names()
    print(f"pair x line results: {len(scores)} | pairs: {len(hits)} | blank grids dropped: {blank}")
    print("lines per gene:", {g: len(v) for g, v in lbg.items()})

    cov = pd.DataFrame({"lines_tested": hits.notna().sum(axis=1),
                        "lines_hit": hits.sum(axis=1)})
    cov["coverage"] = (cov.lines_hit / cov.lines_tested).round(3)
    cov = cov[cov.lines_tested >= 5].sort_values(["coverage", "lines_hit"], ascending=False).reset_index()
    cov.insert(2, "drug_a_name", cov.a.map(nm))
    cov.insert(3, "drug_b_name", cov.b.map(nm))
    cov.to_csv(f"{a.out}/coverage_all_pairs.csv", index=False)
    print(f"pairs hit in ALL tested lines (>=5 tested): {(cov.coverage == 1).sum()}")

    res = loo_test(hits, lbg)
    res.to_csv(f"{a.out}/loo_genotype_test.csv", index=False)
    summ = res.groupby("gene")[["base_rate", "p@50_matched", "p@50_same_size_random",
                                "p@50_all_lines", "matched_beats_share"]].mean().round(3)
    summ.to_csv(f"{a.out}/loo_genotype_summary.csv")
    print("\nLeave-one-line-out, precision@50 (mean over held-out mutant lines):")
    print(summ.to_string())

    if a.query:
        t, mut = query(hits, scores, a.query, lbg, nm)
        t.to_csv(f"{a.out}/query_{a.query}.csv", index=False)
        print(f"\nTop pairs in {a.query}-mutant lines {mut}:")
        print(t[["drug_a_name", "drug_b_name", "hit_rate_mutant", "n_mutant_tested",
                 "hit_rate_other", "coverage_all"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
