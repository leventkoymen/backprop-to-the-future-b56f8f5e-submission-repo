"""
What can you actually recover from the biopsies?

The point of a simulator is that you know the answer. These checks say which
questions the observed data can settle and which it cannot - which is exactly
what you need to know before trusting any method on real biopsies.
"""
import json, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

C=pd.read_csv('out/truth_clones.csv'); S=pd.read_csv('out/obs_samples.csv')
M=pd.read_csv('out/obs_markers.csv'); T=pd.read_csv('out/truth_trajectory.csv')
MK=[c for c in M.columns if c not in ('day','patient','tumour_burden')]

print("1. DYNAMICS — does it behave like a treated tumour?")
b=M.pivot_table(index='day',columns='patient',values='tumour_burden')
med=b.median(axis=1)
print(f"   median burden: day 0 {med.iloc[0]:.2e} -> nadir {med.min():.2e} "
      f"(day {med.idxmin()}) -> day {med.index[-1]} {med.iloc[-1]:.2e}")
bb=M.pivot_table(index='patient',columns='day',values='tumour_burden')
r=bb.min(axis=1)/bb.iloc[:,0]
print(f"   deep responders <1% of baseline : {(r<0.01).sum()}  partial 1-50%: {((r>=0.01)&(r<0.5)).sum()}"
      f"  primary refractory: {(r>=0.5).sum()}")
print(f"   progressed >20% off nadir       : {(bb.iloc[:,-1]>bb.min(axis=1)*1.2).sum()} of {len(bb)}")

print("\n2. HOW MUCH OF THE TRUTH SURVIVES A BIOPSY?")
print(f"   true vs observed clone frequency : r = {S.true_freq.corr(S.observed_freq):.3f}")
lost=S[(S.true_freq>0.01)&(S.observed_freq==0)]
print(f"   real subclones missed entirely   : {len(lost)} of {(S.true_freq>0.01).sum()} "
      f"({len(lost)/max((S.true_freq>0.01).sum(),1)*100:.0f}%) at 2000x depth")
small=S[S.true_freq<0.005]
print(f"   subclones under 0.5% frequency   : {(small.observed_freq>0).mean()*100:.0f}% detected")

print("\n3. CAN MARKERS PREDICT WHO PROGRESSES? (the notes' core question)")
bb=S.groupby(['patient','day']).tumour_burden.first().unstack()
prog=((bb.iloc[:,-1]>bb.min(axis=1)*1.2)).astype(int)
base=M[M.day==0].set_index('patient')[MK].reindex(prog.index)
X=base.values; y=prog.values
if len(np.unique(y))>1 and min(np.bincount(y))>=3:
    sc=cross_val_score(RandomForestClassifier(300,random_state=0),X,y,cv=4,scoring='roc_auc')
    print(f"   baseline markers -> progression : AUC {sc.mean():.3f} +/- {sc.std():.3f}")
    print(f"   (truth: progression is driven by resistant subclones that are mostly")
    print(f"    BELOW detection at day 0 — so a baseline biopsy should NOT predict it well)")
else:
    print("   too few of one class to test")

print("\n4. PRE-EXISTING VS ACQUIRED RESISTANCE")
R=C[C.resistant_to!='']
print(f"   resistant subclones total      : {len(R)}")
print(f"   pre-existing (there at day 0)  : {int(R.preexisting.sum())}")
print(f"   acquired during treatment      : {int((~R.preexisting.astype(bool)).sum())}")
pre0=S[(S.day==0)]
det=pre0.merge(R[['patient','clone']],on=['patient','clone'])
print(f"   pre-existing ones a day-0 biopsy actually SAW : {(det.observed_freq>0).sum()} of {int(R.preexisting.sum())}")
print(f"   -> this is the knob that decides whether ANY baseline biomarker can work.")
print(f"      Set n_preexisting=0 for purely acquired resistance and the ceiling")
print(f"      on baseline prediction drops to chance, by construction.")
