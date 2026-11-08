import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import toxicity as T
from simulate import Regimen

BASE = {k: dict(v) for k, v in T.TOX.items()}
ARMS = {
 'docetaxel+gefitinib (ranked #4)': Regimen([('docetaxel',0,720,0.09),('gefitinib',0,720,0.09)]),
 'gefitinib alone':      Regimen([('gefitinib',0,720,0.12)]),
 'doublet':        Regimen([('gefitinib',0,720,0.10),('carboplatin',0,720,0.07)]),
 'sequential':     Regimen([('gefitinib',0,360,0.12),('carboplatin',360,720,0.12)]),
 'intermittent':   Regimen([('gefitinib',s,s+60,0.15) for s in range(0,720,120)]),
}
rows=[]
for scale in [0.5, 1, 2, 4, 8, 16]:
    T.TOX = {d: {s: v*scale for s, v in sys_.items()} for d, sys_ in BASE.items()}
    for name, reg in ARMS.items():
        r=[T.simulate_with_tox(reg, seed=s) for s in range(25)]
        d=pd.DataFrame(r); d['ctrl']=np.log10(d.b0/np.maximum(d.final,1))
        rows.append({'tox_scale':scale,'arm':name,
                     'control':round(d.ctrl.median(),2),
                     'progressed':int(d.progressed.sum()),
                     'dose_int':round(d.dose_intensity.mean(),2),
                     'g3_days':int(d.days_grade3plus.median())})
D=pd.DataFrame(rows)
print("Tumour control (log10 fold reduction) as toxicity gets worse\n")
print(D.pivot(index='tox_scale',columns='arm',values='control').to_string())
print("\nPatients progressing (of 25)\n")
print(D.pivot(index='tox_scale',columns='arm',values='progressed').to_string())
print("\nDose intensity actually delivered\n")
print(D.pivot(index='tox_scale',columns='arm',values='dose_int').to_string())
best=D.loc[D.groupby('tox_scale').control.idxmax()][['tox_scale','arm','control','dose_int','g3_days']]
print("\nBEST REGIMEN at each toxicity level:\n"+best.to_string(index=False))
