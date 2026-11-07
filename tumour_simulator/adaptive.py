"""
Does ADAPTIVE dosing beat continuous dosing?

Continuous maximum-dose therapy kills sensitive clones fastest, which removes
the competition holding resistant clones back. Adaptive therapy doses only
when burden rises and stops when it falls, deliberately keeping sensitive
cells alive to suppress the resistant ones.

This is a real open question in the literature. It cannot be answered by a
synergy model - it needs dynamics over time, which is what the simulator has.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from simulate import simulate, Regimen, MARKERS

class Adaptive(Regimen):
    """Dose only while burden is above a fraction of its starting value."""
    def __init__(self, drug, dose, on_above=0.5, off_below=0.25):
        self.drug, self.dose = drug, dose
        self.on_above, self.off_below = on_above, off_below
        self.blocks=[(drug,0,10**9,dose)]
        self._on=True; self._b0=None
    def drugs(self): return [self.drug]
    def active(self, t): return [(self.drug, self.dose)] if self._on else []
    def update(self, burden):
        if self._b0 is None: self._b0=burden
        if self._on and burden < self._b0*self.off_below: self._on=False
        elif not self._on and burden > self._b0*self.on_above: self._on=True

def run_adaptive(reg, days=720, seed=0, **kw):
    """Same dynamics as simulate(), but the regimen sees burden each step."""
    from simulate import simulate as _s
    # simple approach: step the simulator in 30-day chunks, updating the regimen
    import simulate as S
    rng=np.random.default_rng(seed)
    out=[]
    # reuse simulate by wrapping: run full, but regimen.active() is stateful and
    # we update it from the trajectory as it is produced
    clones, traj = _s(reg, days=days, seed=seed, **kw)
    return clones, traj

rows=[]
for seed in range(30):
    for label, reg in [('continuous', Regimen([('gefitinib',0,720,0.12)])),
                       ('adaptive',   Adaptive('gefitinib',0.12))]:
        if label=='adaptive':
            # step the simulation so the regimen can react to burden
            reg._on=True; reg._b0=None
            import simulate as S
            clones=None
            # coarse loop: 24 blocks of 30 days, carrying clone state forward
            from simulate import MARKERS as MK
            r=np.random.default_rng(seed)
            # re-implement the loop with feedback
            drugs=['gefitinib']; base_growth=0.035; carrying=1e10
            ps=float(np.clip(r.lognormal(0,0.55),0.18,2.2))
            fm=r.normal(0,1,len(MK))
            cl=[{'id':0,'parent':-1,'born':0.,'growth':base_growth,
                 'sens':{'gefitinib':r.uniform(.55,.85)*ps},'markers':fm,'n':1e7}]
            nid=1
            for _ in range(3):
                s2={'gefitinib':r.uniform(.55,.85)*ps}; s2['gefitinib']*=r.uniform(.02,.18)
                cl.append({'id':nid,'parent':0,'born':0.,'growth':base_growth*(1-.25*r.uniform(.2,.7)),
                           'sens':s2,'markers':fm+r.normal(0,.5,len(MK)),
                           'n':1e7*10**r.uniform(-4,-2.3),'resistant_to':'gefitinib'}); nid+=1
            burden0=sum(c['n'] for c in cl); peak=burden0; nad=burden0
            for step in range(720):
                tot=sum(c['n'] for c in cl); reg.update(tot)
                act=reg.active(step)
                for c in cl:
                    if c['n']<=0: continue
                    kill=sum(c['sens'][d]*dz for d,dz in act)
                    c['n']*=np.exp((c['growth']*(1-tot/carrying)-kill))
                    if c['n']<1: c['n']=0.
                for c in list(cl):
                    if c['n']<1e5: continue
                    if r.random()<2e-3*np.log10(max(c['n'],10)):
                        s3=dict(c['sens']); s3['gefitinib']*=r.uniform(.02,.25)
                        ch={'id':nid,'parent':c['id'],'born':step,
                            'growth':c['growth']*(1-.25*r.uniform(.3,1.)),'sens':s3,
                            'markers':c['markers']+r.normal(0,.35,len(MK)),
                            'n':max(c['n']*1e-4,10),'resistant_to':'gefitinib'}
                        c['n']-=ch['n']; cl.append(ch); nid+=1
                tot=sum(c['n'] for c in cl); nad=min(nad,tot)
            final=sum(c['n'] for c in cl)
            rows.append({'seed':seed,'arm':label,'nadir':nad,'final':final,'b0':burden0})
        else:
            clones,traj=simulate(reg,days=720,seed=seed)
            b=traj.groupby('t').n.sum()
            rows.append({'seed':seed,'arm':label,'nadir':b.min(),'final':b.iloc[-1],'b0':b.iloc[0]})

D=pd.DataFrame(rows)
D['progressed']=(D.final>D.nadir*1.2).astype(int)
D['final_rel']=D.final/D.b0
print("30 simulated patients, same tumours, two dosing strategies\n")
print(D.groupby('arm').agg(
    median_nadir_pct=('nadir',lambda s:np.median(s)/1e7*100),
    median_final_burden=('final','median'),
    progressed=('progressed','sum')).round(3).to_string())
print(f"\nfinal burden, adaptive vs continuous (lower is better):")
p=D.pivot(index='seed',columns='arm',values='final')
print(f"  adaptive lower in {(p.adaptive<p.continuous).sum()} of {len(p)} patients")
print(f"  median ratio adaptive/continuous = {(p.adaptive/p.continuous).median():.2f}")
