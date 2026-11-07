"""
Adds the 10 drug names missing from nsc_names.csv, then removes only the scores for
pairs that involved an unnamed drug, so `python bench.py` rescores just those pairs.

Names from NCI CellMiner's ALMANAC drug list and NCI DTP's approved-drug pages.
A backup of scores.jsonl is kept as scores_before_names.jsonl.

    python fix_names.py
    python bench.py
"""
import os, json, shutil
import pandas as pd

MISSING = {
    109724: 'Ifosfamide',
    119875: 'Cisplatin',
    218321: 'Pentostatin',
    256439: 'Idarubicin',
    256942: 'Epirubicin hydrochloride',
    266046: 'Oxaliplatin',
    296961: 'Amifostine (ethiofos)',
    609699: 'Topotecan',
    747973: 'Ixabepilone',
    761431: 'Vemurafenib',   # NCI lists this as vemurafenib; 753082 is also vemurafenib - check
}

HERE = os.path.dirname(os.path.abspath(__file__))
# bench.py reads ./nsc_names.csv first, then data/nsc_names.csv - update whichever it uses
path = next(p for p in [os.path.join(HERE, 'nsc_names.csv'),
                        os.path.join(HERE, 'data', 'nsc_names.csv')] if os.path.exists(p))
N = pd.read_csv(path)
N['nsc'] = N.nsc.astype(int)
add = pd.DataFrame([{'nsc': k, 'name': v} for k, v in MISSING.items() if k not in set(N.nsc)])
pd.concat([N, add]).sort_values('nsc').to_csv(path, index=False)
print(f'added {len(add)} names to {path}')

jl = os.path.join(HERE, 'bench_out', 'scores.jsonl')
if os.path.exists(jl):
    shutil.copy(jl, os.path.join(HERE, 'bench_out', 'scores_before_names.jsonl'))
    keep, drop = [], 0
    for line in open(jl):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if int(r['a']) in MISSING or int(r['b']) in MISSING:
            drop += 1
        else:
            keep.append(line if line.endswith('\n') else line + '\n')
    open(jl, 'w').writelines(keep)
    print(f'removed {drop} scores that were made without a drug name '
          f'(kept {len(keep)}); run `python bench.py` to rescore them')
