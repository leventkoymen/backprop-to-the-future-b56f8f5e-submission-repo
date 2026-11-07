import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from simulate import Regimen
from toxicity import simulate_with_tox

ARMS = {
 # rank #4 from the LungPair shortlist (score 182, stability 100%)
 'docetaxel + gefitinib':  Regimen([('docetaxel',0,720,0.09),('gefitinib',0,720,0.09)]),
 'gefitinib continuous':        Regimen([('gefitinib',0,720,0.12)]),
 'gefitinib + carbo continuous':Regimen([('gefitinib',0,720,0.10),('carboplatin',0,720,0.07)]),
 'gefitinib + carbo sequential':Regimen([('gefitinib',0,360,0.12),('carboplatin',360,720,0.12)]),
 'gefitinib intermittent':      Regimen([('gefitinib',s,s+60,0.15) for s in range(0,720,120)]),
}
rows=[]
for name,reg in ARMS.items():
    for seed in range(40):
        rows.append({'arm':name,'seed':seed,**simulate_with_tox(reg,seed=seed)})
D=pd.DataFrame(rows)
D['tumour_control']=np.log10(D.b0/np.maximum(D.final,1))     # higher = better
S=D.groupby('arm').agg(
  control=('tumour_control','median'),
  progressed=('progressed','sum'),
  dose_intensity=('dose_intensity','mean'),
  days_grade3plus=('days_grade3plus','median'),
  dose_reductions=('dose_reductions','median'),
).round(2)
S['control_per_tox_day']=(S.control/np.maximum(S.days_grade3plus,1)*100).round(2)
print("40 simulated patients per arm, 720 days, toxicity-limited dosing\n")
print(S.to_string())
print("\ncontrol  = log10 fold reduction in tumour burden (higher better)")
print("progressed = of 40 patients")
print("days_grade3plus = days at grade 3/4 toxicity, when dosing is held")
print("control_per_tox_day = tumour control bought per 100 days of severe toxicity")
