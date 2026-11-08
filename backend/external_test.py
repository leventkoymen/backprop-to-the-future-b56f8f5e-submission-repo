"""External validation of LungPair on the Merck (O'Neil 2016) screen.
Test 1: does 'synergy in other cancers predicts lung synergy' replicate in an independent screen?
Test 2: do LungPair's NCI-ALMANAC-based scores predict Merck lung synergy for shared pairs?"""
import re, sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
BK = '.'                      # run from lungpair_api/backend
sys.path.insert(0, BK)
from merge_dataset import ensure_external
ensure_external()
from features import build_features, oof_features
from sklearn.ensemble import RandomForestRegressor

D = pd.read_csv('external/mtl_drugs.csv'); C = pd.read_csv('external/mtl_cell_lines.csv'); O = pd.read_csv('external/mtl_oneil_summary_idx.csv')
P = pd.read_csv(f'{BK}/data/pairs.csv'); T = pd.read_csv(f'{BK}/data/transfer.csv'); POT = pd.read_csv(f'{BK}/data/potency.csv')
for df in (P, T): df['a'] = df.a.astype(int); df['b'] = df.b.astype(int)
K = set(P.a) | set(P.b)

dname = dict(zip(D.id, D.name)); cname = dict(zip(C.id, C.name))
O['d1'] = O.drug_row_idx.map(dname); O['d2'] = O.drug_col_idx.map(dname); O['cl'] = O.cell_line_idx.map(cname)
O['x'] = O[['d1', 'd2']].min(axis=1); O['y'] = O[['d1', 'd2']].max(axis=1)
LUNG = {'A427', 'NCIH1650', 'NCIH2122', 'NCIH23', 'NCIH460', 'NCIH520', 'SKMES1'}
NEW_LUNG = LUNG - {'NCIH23', 'NCIH460'}            # never in NCI-ALMANAC

def pk(y, s, k, seed=0):
    s = np.asarray(s, float); perm = np.random.default_rng(seed).permutation(len(s))
    o = perm[np.argsort(-s[perm], kind='stable')]; return float(np.asarray(y)[o[:k]].mean())
def perm_p(y, s, k, n=5000):
    """share of random rankings doing at least as well (one-sided p-value)"""
    obs = pk(y, s, k); y = np.asarray(y); rng = np.random.default_rng(1)
    return float(np.mean([y[rng.permutation(len(y))[:k]].mean() >= obs for _ in range(n)]))

print('TEST 1 - replication inside the Merck screen (no NCI-ALMANAC data used)')
for lung, label in [(LUNG, 'all 7 lung lines'), (NEW_LUNG, '5 lung lines never in NCI-ALMANAC')]:
    g = O.groupby(['x', 'y'])
    lungm = O[O.cl.isin(lung)].groupby(['x', 'y']).synergy_loewe.mean()
    other = O[~O.cl.isin(LUNG)].groupby(['x', 'y']).synergy_loewe.mean()   # non-lung only
    df = pd.concat([lungm.rename('lung'), other.rename('other')], axis=1).dropna()
    rho = spearmanr(df.other, df.lung).correlation
    print(f'\n  {label}: {len(df)} pairs; rank correlation other-cancer vs lung = {rho:.2f}')
    for thr in (10, 30):
        hit = (df.lung > thr).astype(int)
        for k in (20, 50):
            print(f'    hit = lung Loewe > {thr:>2} ({hit.mean():5.1%} of pairs)   top {k}: '
                  f'{pk(hit, df.other, k):.0%} hits vs {hit.mean():.0%} random   (p = {perm_p(hit, df.other, k):.4f})')

print('\n\nTEST 2 - LungPair (trained on NCI-ALMANAC) vs Merck lung results, shared pairs')
on = D[D.from_oneil == 'Yes'].copy()
on['nsc'] = on.synonyms.apply(lambda s: [int(x) for x in re.findall(r'NSC[\s-]?(\d+)', str(s)) if int(x) in K])
manual = {'OXALIPLATIN': 266046, 'VINBLASTINE': 49842, 'VINORELBINE': 608210}   # same drugs, salt-form NSCs
on['nsc'] = [n[0] if n else manual.get(nm) for n, nm in zip(on.nsc, on.name)]
m2n = dict(zip(on.name, on.nsc)); m2n = {k: int(v) for k, v in m2n.items() if pd.notna(v)}
print(f'  drugs in both screens: {len(m2n)}')
rng = np.random.default_rng(0)
model = RandomForestRegressor(500, min_samples_leaf=3, random_state=0, n_jobs=-1)
model.fit(oof_features(P, POT, T, True, rng), P['mean'])
for lung, label in [(LUNG, 'all 7 Merck lung lines'), (NEW_LUNG, '5 lines never in NCI-ALMANAC')]:
    lm = O[O.cl.isin(lung)].groupby(['x', 'y']).synergy_loewe.mean().reset_index()
    lm = lm[lm.x.isin(m2n) & lm.y.isin(m2n)].copy()
    lm['a'] = [min(m2n[x], m2n[y]) for x, y in zip(lm.x, lm.y)]; lm['b'] = [max(m2n[x], m2n[y]) for x, y in zip(lm.x, lm.y)]
    j = lm.merge(P[['a', 'b', 'mean']], on=['a', 'b']).merge(T[['a', 'b', 'other_mean']], on=['a', 'b'], how='left')
    j['n_lines'] = 9
    j['model'] = model.predict(build_features(j[['a', 'b', 'n_lines', 'mean']], P, POT, T, True))
    print(f'\n  {label}: {len(j)} shared pairs')
    for col, nm in [('mean', 'NCI-ALMANAC lung result (what LungPair knows)'),
                    ('other_mean', 'NCI-ALMANAC other-cancer lookup'), ('model', 'LungPair model score')]:
        rho, p = spearmanr(j[col], j.synergy_loewe)
        line = f'    {nm:46s} rank corr with Merck lung = {rho:+.2f} (p={p:.3f})'
        hit = (j.synergy_loewe > 10).astype(int)
        line += f' | top 10: {pk(hit, j[col], 10):.0%} Merck hits vs {hit.mean():.0%} base (p={perm_p(hit, j[col], 10):.3f})'
        print(line)
    if 'NEVER' not in label.upper():
        top = j.sort_values('model', ascending=False).head(8)
        print('    LungPair top 8 shared pairs and their Merck lung Loewe:')
        for _, r in top.iterrows(): print(f'      {r.x:14s} + {r.y:14s} model {r.model:6.1f}  Merck lung {r.synergy_loewe:6.1f}')
