"""
Toxicity: the thing the simulator was missing, and the thing your goal needs.

The notes say the aim is "better-tolerated treatment regimens" and "fewer side
effects". The simulator so far models only tumour kill, so it cannot express
that goal at all - every question it answers is about efficacy.

This adds the other half. It matters because the 2026 Med review found that
synergy does not predict clinical success and that highly synergistic
combinations often FAIL on toxicity: TMZ + PARP inhibitors needed an 80% TMZ
dose reduction, negating the benefit; MEK + HER-family needed reductions below
the active single-agent dose.

MODEL
  each drug contributes toxicity at a rate per unit dose, to one or more organ
  systems; toxicity accumulates and recovers with a half-life; when an organ
  system crosses a patient's tolerance threshold, the dose is reduced or held,
  exactly as happens in clinic. Two drugs hitting the SAME system stack.
"""
import numpy as np, pandas as pd

# toxicity rate per unit dose, per system. Illustrative, not drug-label values -
# replace with real CTCAE grade-3+ rates per drug before any claim is made.
# NSC numbers tie these to the ranking pipeline's drug universe, so a pair the
# model ranks can be simulated directly. All four are in NCI-ALMANAC.
NSC = {'gefitinib': 715055, 'carboplatin': 241240,
       'pemetrexed': 698037, 'docetaxel': 628503}

# calibrated so single-agent dose intensity lands near 0.85, as in real trials.
# gefitinib is an EGFR TKI: rash and GI dominate, little myelosuppression.
TOX = {
 'gefitinib': {'haem': 0.04, 'gi': 0.09, 'skin': 0.18, 'cardiac': 0.05},
 'carboplatin': {'haem': 0.23, 'gi': 0.14, 'skin': 0.03, 'cardiac': 0.01},
 'pemetrexed':  {'haem': 0.15, 'gi': 0.10, 'skin': 0.06, 'cardiac': 0.01},
 'docetaxel':   {'haem': 0.21, 'gi': 0.11, 'skin': 0.08, 'cardiac': 0.04},
}
SYSTEMS = ['haem','gi','skin','cardiac']
RECOVERY_HL = {'haem': 14.0, 'gi': 7.0, 'skin': 21.0, 'cardiac': 120.0}  # days


class Patient:
    """Tracks accumulated toxicity and the dose modifications it forces."""
    def __init__(self, tolerance=1.0, rng=None):
        rng = rng or np.random.default_rng(0)
        # patients differ in what they can take
        self.tol = {s: tolerance*float(np.clip(rng.lognormal(0,.3),.4,2.2)) for s in SYSTEMS}
        self.level = {s: 0.0 for s in SYSTEMS}
        self.dose_factor = 1.0
        self.holds = 0; self.reductions = 0; self.days_held = 0
        self.history = []

    def step(self, active, dt=1.0):
        """active = [(drug, dose)]. Returns the dose factor actually delivered."""
        for s in SYSTEMS:
            self.level[s] *= 0.5**(dt/RECOVERY_HL[s])        # recovery
        for drug, dose in active:
            for s, rate in TOX.get(drug, {}).items():
                self.level[s] += rate*dose*self.dose_factor*dt  # OVERLAP stacks here

        worst = max(self.level[s]/self.tol[s] for s in SYSTEMS)
        if worst > 1.3:                                      # grade 3/4: hold
            self.dose_factor = 0.0; self.holds += 1; self.days_held += dt
        elif worst > 1.0:                                    # reduce
            if self.dose_factor > 0.5: self.reductions += 1
            self.dose_factor = max(0.5, self.dose_factor*0.75)
        elif worst < 0.6 and self.dose_factor < 1.0:         # recovered: re-escalate
            self.dose_factor = min(1.0, self.dose_factor+0.25) if self.dose_factor>0 else 0.5
        self.history.append({'worst_grade_frac': worst, 'dose_factor': self.dose_factor,
                             **{f'tox_{s}': self.level[s] for s in SYSTEMS}})
        return self.dose_factor

    def summary(self):
        h = pd.DataFrame(self.history)
        return {'dose_intensity': h.dose_factor.mean(),
                'days_held': self.days_held,
                'dose_reductions': self.reductions,
                'peak_toxicity': h.worst_grade_frac.max(),
                'days_grade3plus': int((h.worst_grade_frac>1.3).sum())}


def simulate_with_tox(regimen, days=720, seed=0, base_growth=0.035,
                      carrying=1e10, n_preexisting=3, resist_cost=0.25, mut_rate=2e-3):
    """Same clonal dynamics, but the delivered dose is what toxicity allows."""
    rng = np.random.default_rng(seed)
    drugs = regimen.drugs()
    pt = Patient(rng=rng)
    ps = float(np.clip(rng.lognormal(0,.55),.18,2.2))
    cl = [{'id':0,'growth':base_growth,'sens':{d:rng.uniform(.55,.85)*ps for d in drugs},'n':1e7}]
    nid=1
    for _ in range(n_preexisting):
        if not drugs: break
        tgt = drugs[rng.integers(len(drugs))]
        s = {d: rng.uniform(.55,.85)*ps for d in drugs}; s[tgt] *= rng.uniform(.02,.18)
        cl.append({'id':nid,'growth':base_growth*(1-resist_cost*rng.uniform(.2,.7)),
                   'sens':s,'n':1e7*10**rng.uniform(-4,-2.3)}); nid+=1
    burden=[]
    for t in range(days):
        tot = sum(c['n'] for c in cl)
        planned = regimen.active(t)
        factor = pt.step(planned)
        delivered = [(d, dose*factor) for d, dose in planned]
        for c in cl:
            if c['n']<=0: continue
            kill = sum(c['sens'][d]*dz for d,dz in delivered)
            c['n'] *= np.exp(c['growth']*(1-tot/carrying) - kill)
            if c['n']<1: c['n']=0.
        for c in list(cl):
            if c['n']<1e5: continue
            if rng.random() < mut_rate*np.log10(max(c['n'],10)):
                s2=dict(c['sens'])
                if drugs: s2[drugs[rng.integers(len(drugs))]] *= rng.uniform(.02,.25)
                ch={'id':nid,'growth':c['growth']*(1-resist_cost*rng.uniform(.3,1.)),
                    's':None,'sens':s2,'n':max(c['n']*1e-4,10)}
                c['n']-=ch['n']; cl.append(ch); nid+=1
        burden.append(sum(c['n'] for c in cl))
    b=np.array(burden)
    return {'nadir':b.min(),'final':b[-1],'b0':b[0],
            'progressed':int(b[-1]>b.min()*1.2), **pt.summary()}
