"""
Merge LungPair's drug-pair data with drug structures, cell-line biomarkers and the
independent Merck (O'Neil 2016) screen into one set of tables.

Run from lungpair_api/backend, after (optionally) fetching structures on your laptop:
    python fetch_structures.py --all                 # 3D files + SMILES for all drugs
    python merge_dataset.py

Inputs
  data/pairs.csv, data/transfer.csv        NCI-ALMANAC lung results + other-cancer lookup
  nsc_names.csv, surface_dose_response.csv
  external/mtl_*.csv                        Merck screen, drug synonyms, cell-line expression
                                            (MTLSynergy repo, github.com/TOJSSE-iData/MTLSynergy)
  structures/drug_structures.csv            optional - from fetch_structures.py
  drug_dosing_filled.csv                    optional - clinical dose + peak blood level, cited
  reachability_by_pair.csv                  optional - from compare_dosing.py

Outputs (merged/)
  drugs.csv                one row per drug: names, in Merck screen?, SMILES, 3D file,
                           clinical dose, route, peak blood level (Cmax) with sources
  dose_reachability.csv    per 3D-surface pair: is the peak synergy at doses patients reach?
  cell_lines.csv           13 lung lines: which screen, key marker genes (z-scored expression)
  cell_line_expression.csv the same 13 lines, all 5,000 genes
  pairs.csv                one row per NCI-ALMANAC pair: lung result, other-cancer lookup,
                           Merck lung result where the pair is shared, drug structures
  per_cell_line.csv        one row per (pair, lung cell line) measurement from either screen,
                           with that line's marker genes - the table for biomarker questions

Limits: expression is z-scored activity of the 5,000 most variable genes, not mutations;
KRAS, STK11 and KEAP1 are not in it. Synergy scores differ between screens (ComboScore vs
Loewe) - compare within a screen, not across.
"""
import os, re
import pandas as pd

EXT = 'external'
OUT = 'merged'
LUNG_ALMANAC = {'A549': 'A549', 'EKVX': 'EKVX', 'HOP-62': 'HOP-62', 'HOP-92': 'HOP-92',
                'NCI-H226': 'NCI-H226', 'NCI-H23': 'NCIH23', 'NCI-H322M': None,
                'NCI-H460': 'NCIH460', 'NCI-H522': 'NCI-H522'}   # NCI-60 name -> expression name
LUNG_MERCK = ['A427', 'NCIH1650', 'NCIH2122', 'NCIH23', 'NCIH460', 'NCIH520', 'SKMES1']
MARKERS = ['EGFR', 'TP53', 'MET', 'ERBB2', 'NKX2-1', 'CDKN2A', 'PTEN', 'RET', 'NRAS',
           'MYC', 'SOX2', 'CD274', 'VIM', 'CDH1', 'TUBB3', 'ABCB1']

def ensure_external(folder='external'):
    """Check the Merck files are already on disk. Never download here.

    This used to fetch from GitHub on every run. That is fine on a laptop with
    a connection and fatal in front of judges on conference wifi, so the
    download moved to vendor.py, which is run once and its output committed.
    """
    import os
    need = ['drugs.csv', 'cell_lines.csv', 'oneil_summary_idx.csv',
            'cell_line_features.csv']
    missing = [f for f in need
               if not os.path.exists(os.path.join(folder, 'mtl_' + f))]
    if missing:
        raise SystemExit(
            'missing external files: ' + ', '.join(missing) +
            '\nRun:  python vendor.py     (needs a connection, once)\n'
            'Then commit external/ so the repo is self-contained.')


MANUAL_NSC = {'OXALIPLATIN': 266046, 'VINBLASTINE': 49842, 'VINORELBINE': 608210}


def main():
    os.makedirs(OUT, exist_ok=True)
    ensure_external(EXT)
    P = pd.read_csv('data/pairs.csv'); T = pd.read_csv('data/transfer.csv')
    for df in (P, T):
        df['a'] = df.a.astype(int); df['b'] = df.b.astype(int)
    N = pd.read_csv('nsc_names.csv'); names = dict(zip(N.nsc.astype(int), N.name))
    K = sorted(set(P.a) | set(P.b))

    # ---- Merck screen, linked to our NSC numbers
    MD = pd.read_csv(f'{EXT}/mtl_drugs.csv'); MC = pd.read_csv(f'{EXT}/mtl_cell_lines.csv')
    MO = pd.read_csv(f'{EXT}/mtl_oneil_summary_idx.csv')
    on = MD[MD.from_oneil == 'Yes'].copy()
    on['nsc'] = [next((int(x) for x in re.findall(r'NSC[\s-]?(\d+)', str(s)) if int(x) in set(K)),
                      MANUAL_NSC.get(n)) for s, n in zip(on.synonyms, on.name)]
    merck2nsc = {r['name']: int(r.nsc) for _, r in on.iterrows() if pd.notna(r.nsc)}
    dname = dict(zip(MD.id, MD.name)); cname = dict(zip(MC.id, MC.name))
    MO['d1'] = MO.drug_row_idx.map(dname); MO['d2'] = MO.drug_col_idx.map(dname)
    MO['cell_line'] = MO.cell_line_idx.map(cname)
    MO = MO[MO.d1.isin(merck2nsc) & MO.d2.isin(merck2nsc)].copy()
    MO['a'] = [min(merck2nsc[x], merck2nsc[y]) for x, y in zip(MO.d1, MO.d2)]
    MO['b'] = [max(merck2nsc[x], merck2nsc[y]) for x, y in zip(MO.d1, MO.d2)]

    # ---- cell-line expression (rows of the features file follow cell_lines.csv ids)
    F = pd.read_csv(f'{EXT}/mtl_cell_line_features.csv')
    assert len(F) == len(MC) and (MC.id.values == range(len(MC))).all(), 'row order changed'
    F.index = MC.name.values
    lines = sorted({v for v in LUNG_ALMANAC.values() if v} | set(LUNG_MERCK))
    E = F.loc[lines]
    in_alm = {v for v in LUNG_ALMANAC.values() if v}
    cl = pd.DataFrame({'cell_line': lines,
                       'in_nci_almanac': [l in in_alm for l in lines],
                       'in_merck': [l in LUNG_MERCK for l in lines]})
    cl = cl.join(E[[g for g in MARKERS if g in E.columns]].reset_index(drop=True))
    cl.to_csv(f'{OUT}/cell_lines.csv', index=False)
    E.rename_axis('cell_line').to_csv(f'{OUT}/cell_line_expression.csv')

    # ---- drugs (+ structures if fetched)
    drugs = pd.DataFrame({'nsc': K, 'name': [names.get(k, f'NSC {k}') for k in K]})
    drugs['in_merck'] = drugs.nsc.isin(set(merck2nsc.values()))
    drugs['merck_name'] = drugs.nsc.map({v: k for k, v in merck2nsc.items()})
    sp = 'structures/drug_structures.csv'
    if os.path.exists(sp):
        S = pd.read_csv(sp)[['nsc', 'parent_cid', 'smiles', 'formula', 'mol_weight', 'source_3d', 'file']]
        drugs = drugs.merge(S.rename(columns={'file': 'structure_3d_file'}), on='nsc', how='left')
        print(f'structures joined for {drugs.smiles.notna().sum()} of {len(drugs)} drugs')
    else:
        print('no structures/drug_structures.csv yet - run fetch_structures.py --all, then rerun')
    dp = 'drug_dosing_filled.csv'
    if os.path.exists(dp):
        DZ = pd.read_csv(dp)
        cols = ['nsc', 'route', 'standard_dose', 'schedule', 'used_in_nsclc', 'cmax_value', 'cmax_unit',
                'cmax_conditions', 'protein_binding_pct', 'source_dose', 'source_cmax', 'notes']
        DZ = DZ[[c for c in cols if c in DZ]].rename(columns={'notes': 'dosing_notes'})
        drugs = drugs.merge(DZ, on='nsc', how='left')
        print(f'dosing joined for {drugs.cmax_value.notna().sum()} drugs with a cited peak blood level')
    drugs.to_csv(f'{OUT}/drugs.csv', index=False)

    # ---- pair table
    merck_lung = (MO[MO.cell_line.isin(LUNG_MERCK)].groupby(['a', 'b'])
                  .synergy_loewe.agg(['mean', 'count']).rename(columns={'mean': 'merck_lung_loewe',
                                                                        'count': 'merck_lung_lines'}))
    pairs = (P.merge(T, on=['a', 'b'], how='left')
              .merge(merck_lung.reset_index(), on=['a', 'b'], how='left'))
    pairs.insert(2, 'drug_b', pairs.b.map(names)); pairs.insert(2, 'drug_a', pairs.a.map(names))
    pairs = pairs.rename(columns={'mean': 'almanac_lung_comboscore', 'hit': 'almanac_lung_hit',
                                  'other_mean': 'almanac_other_cancer_comboscore'})
    keep = [c for c in drugs.columns if c in ('nsc', 'smiles', 'structure_3d_file')]
    if len(keep) > 1:
        for side in ('a', 'b'):
            pairs = pairs.merge(drugs[keep].rename(columns={c: f'{c}_{side}' for c in keep})
                                .rename(columns={f'nsc_{side}': side}), on=side, how='left')
    pairs.to_csv(f'{OUT}/pairs.csv', index=False)

    # ---- per (pair, lung cell line): both screens, with biomarkers
    rows = []
    if os.path.exists('surface_dose_response.csv'):
        SF = pd.read_csv('surface_dose_response.csv')
        g = SF.groupby(['drug_a_nsc', 'drug_b_nsc', 'cell_line']).synergy.agg(['max', 'mean']).reset_index()
        for _, r in g.iterrows():
            rows.append({'a': int(r.drug_a_nsc), 'b': int(r.drug_b_nsc), 'screen': 'NCI-ALMANAC',
                         'cell_line_screen_name': r.cell_line,
                         'cell_line': LUNG_ALMANAC.get(r.cell_line.split('/')[0]),
                         'metric': 'ComboScore-style synergy, grid max', 'synergy': r['max']})
    for _, r in MO[MO.cell_line.isin(LUNG_MERCK)].iterrows():
        rows.append({'a': r.a, 'b': r.b, 'screen': 'Merck (O\'Neil 2016)', 'cell_line_screen_name': r.cell_line,
                     'cell_line': r.cell_line, 'metric': 'Loewe', 'synergy': r.synergy_loewe})
    pl = pd.DataFrame(rows)
    pl.insert(2, 'drug_b', pl.b.map(names)); pl.insert(2, 'drug_a', pl.a.map(names))
    pl = pl.merge(cl.drop(columns=['in_nci_almanac', 'in_merck']), on='cell_line', how='left')
    pl.to_csv(f'{OUT}/per_cell_line.csv', index=False)

    rp = 'reachability_by_pair.csv'
    if os.path.exists(rp):
        pd.read_csv(rp).to_csv(f'{OUT}/dose_reachability.csv', index=False)
    print(f'wrote {OUT}/: {len(drugs)} drugs ({drugs.in_merck.sum()} also in Merck), '
          f'{len(cl)} lung cell lines with {len(E.columns)} genes, {len(pairs)} pairs '
          f'({pairs.merck_lung_loewe.notna().sum()} with a Merck lung result), '
          f'{len(pl)} per-cell-line measurements')


if __name__ == '__main__':
    main()
