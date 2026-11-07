"""
Is the synergy reachable in a patient? Compares the doses where each pair is most
synergistic in NCI-ALMANAC with the blood concentrations the drugs reach in patients.

1. Fill in drug_dosing_template.csv (one row per drug, cite every value):
     standard_dose, schedule  <- prescribing label, "Dosage and Administration"
     cmax_value, cmax_unit    <- label, "Clinical Pharmacology > Pharmacokinetics",
                                 at the standard dose. Units: ng/mL, ug/mL, mg/L, nM, uM, M
     protein_binding_pct      <- same section (optional; enables the unbound check)
     grade3plus_*             <- label, "Adverse Reactions" table
2. Run fetch_structures.py first (needs molecular weight to convert ng/mL to molar).
3. python compare_dosing.py --dosing drug_dosing_template.csv \
        --structures structures/drug_structures.csv --data surface_dose_response.csv

Writes reachability_by_pair.csv. Caveats to state alongside any result: ALMANAC cells
sit in a constant dose for 48 h, while blood levels peak and fall; and much of a drug
in blood is protein-bound, so the unbound column is the stricter test.
"""
import argparse
import numpy as np, pandas as pd

TO_MOLAR = {'nm': 1e-9, 'um': 1e-6, 'µm': 1e-6, 'm': 1.0}        # already molar
MASS = {'ng/ml': 1e-6, 'ug/ml': 1e-3, 'µg/ml': 1e-3, 'mg/l': 1e-3}  # -> g/L


def cmax_molar(row):
    v, u = row.cmax_value, str(row.cmax_unit).strip().lower()
    if pd.isna(v) or v == '': return np.nan
    v = float(v)
    if u in TO_MOLAR: return v*TO_MOLAR[u]
    if u in MASS:
        if pd.isna(row.mol_weight): raise ValueError(f'{row["name"]}: need mol_weight for {u}')
        return v*MASS[u]/row.mol_weight
    raise ValueError(f'{row["name"]}: unknown unit {row.cmax_unit!r}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dosing', default='drug_dosing_template.csv')
    ap.add_argument('--structures', default='structures/drug_structures.csv')
    ap.add_argument('--data', default='surface_dose_response.csv')
    ap.add_argument('--out', default='reachability_by_pair.csv')
    a = ap.parse_args()

    dz = pd.read_csv(a.dosing)
    if 'mol_weight' not in dz: dz['mol_weight'] = np.nan
    try:   # template weights first: they match the form each blood level was measured in
           # (the free drug, not its salt). PubChem weights only fill gaps.
        st = pd.read_csv(a.structures)[['nsc', 'mol_weight']].rename(columns={'mol_weight': 'mw_pubchem'})
        dz = dz.merge(st, on='nsc', how='left')
        dz['mol_weight'] = dz.mol_weight.fillna(dz.mw_pubchem)
    except FileNotFoundError:
        pass
    dz['cmax_M'] = dz.apply(cmax_molar, axis=1)
    pb = pd.to_numeric(dz.get('protein_binding_pct'), errors='coerce')
    dz['cmax_unbound_M'] = dz.cmax_M*(1 - pb/100)
    missing = dz[dz.cmax_M.isna()]['name'].tolist()
    if missing: print(f"no Cmax yet for: {', '.join(missing)} - those pairs show as unknown\n")
    cm = dz.set_index('nsc')[['cmax_M', 'cmax_unbound_M']]
    route = dz.set_index('nsc').get('route', pd.Series(dtype=str)).fillna('').astype(str)
    def flag(n):
        r = route.get(n, '')
        return 'NOT SYSTEMIC: ' + r if 'INTRAVESICAL' in r.upper() or 'TOPICAL' in r.upper() else ''

    D = pd.read_csv(a.data)
    rows = []
    for (na, nb, la, lb), g in D.groupby(['drug_a_nsc', 'drug_b_nsc', 'drug_a', 'drug_b']):
        ca, cb = cm.loc[na] if na in cm.index else (np.nan,)*2, cm.loc[nb] if nb in cm.index else (np.nan,)*2
        g = g.assign(ok=(g.conc_a_molar <= ca.cmax_M) & (g.conc_b_molar <= cb.cmax_M),
                     ok_unbound=(g.conc_a_molar <= ca.cmax_unbound_M) & (g.conc_b_molar <= cb.cmax_unbound_M))
        best = g.loc[g.synergy.idxmax()]
        known = not (np.isnan(ca.cmax_M) or np.isnan(cb.cmax_M))
        rows.append({
            'drug_a': la, 'drug_b': lb, 'cell_lines': g.cell_line.nunique(),
            'peak_synergy': best.synergy, 'peak_conc_a_M': best.conc_a_molar,
            'peak_conc_b_M': best.conc_b_molar,
            'cmax_a_M': ca.cmax_M, 'cmax_b_M': cb.cmax_M,
            'peak_reachable': bool(best.ok) if known else 'unknown',
            'best_synergy_at_reachable_doses': g[g.ok].synergy.max() if known and g.ok.any() else np.nan,
            'share_of_grid_reachable': g.ok.mean() if known else np.nan,
            'share_reachable_unbound': g.ok_unbound.mean() if known and not (np.isnan(ca.cmax_unbound_M)
                                         or np.isnan(cb.cmax_unbound_M)) else np.nan,
            'flags': '; '.join(f for f in (flag(na), flag(nb)) if f),
        })
    R = pd.DataFrame(rows).sort_values('peak_synergy', ascending=False)
    R.to_csv(a.out, index=False)
    pd.set_option('display.width', 220)
    print(R[['drug_a', 'drug_b', 'peak_synergy', 'peak_reachable', 'best_synergy_at_reachable_doses',
             'share_of_grid_reachable', 'share_reachable_unbound', 'flags']].round(2).to_string(index=False))
    print(f"\nwrote {a.out}")


if __name__ == '__main__':
    main()
