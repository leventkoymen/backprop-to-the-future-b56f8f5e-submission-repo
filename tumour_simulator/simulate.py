"""
NSCLC progression simulator: clonal evolution under drug regimens.

This generates SIMULATED OBSERVATIONS FROM A STATED MECHANISM, alongside the
ground truth that produced them. That is the only kind of synthetic data worth
having: you can check whether a method recovers what you know is there.

It is NOT a substitute for patient data. Nothing it outputs is evidence about
real tumours - it is evidence about whether your inference works.

MECHANISM (standard clonal-evolution dynamics, not invented for this project)
  - a tumour is a set of subclones related by a phylogeny
  - each subclone grows logistically toward a shared carrying capacity
  - each drug kills a subclone at a rate set by that subclone's sensitivity
  - subclones mutate into daughters, which may gain resistance at a fitness cost
  - each subclone carries a marker-expression vector; bulk expression is the
    frequency-weighted mixture, which is what a biopsy would measure

WHAT YOU GET
  truth_clones.csv     every subclone: parent, birth time, resistance, fitness
  truth_trajectory.csv true clone frequencies at every timestep
  obs_samples.csv      what a biopsy at each sampling time would report
  obs_markers.csv      bulk marker expression per sample, with noise
  truth_tree.json      the real phylogeny, for scoring tree reconstruction
"""
import argparse, json, os
import numpy as np, pandas as pd

MARKERS = ['PDL1','EGFR','ALK','KRAS','TP53','VIM','CDH1','MKI67','CD8A','FOXP3']

class Regimen:
    """A treatment plan: which drug is on, between which days."""
    def __init__(self, blocks):
        self.blocks = blocks                     # [(drug, start_day, end_day, dose)]
    def active(self, t):
        return [(d, dose) for d, s, e, dose in self.blocks if s <= t < e]
    def drugs(self):
        return sorted({d for d, *_ in self.blocks})


def simulate(regimen, days=720, dt=1.0, n_markers=len(MARKERS),
             carrying=1e10, base_growth=0.035, mut_rate=2e-3,
             resist_cost=0.25, n_preexisting=3, seed=0, detect_limit=1e6):
    rng = np.random.default_rng(seed)
    drugs = regimen.drugs()

    # founding clone: sensitive to everything, baseline markers
    # Patients differ in how sensitive their tumour is to begin with. Without
    # this every simulated patient responds identically, which no real cohort
    # does: some are primary-refractory, some have deep durable responses.
    patient_scale = float(np.clip(rng.lognormal(0, 0.55), 0.18, 2.2))
    founder_markers = rng.normal(0, 1, n_markers)
    clones = [{
        'id': 0, 'parent': -1, 'born': 0.0,
        'growth': base_growth,
        'sens': {d: rng.uniform(0.55, 0.85)*patient_scale for d in drugs},  # kill per unit dose
        'markers': founder_markers,
        'n': 1e7,
    }]
    next_id = 1
    # PRE-EXISTING resistance: real tumours carry resistant subclones before
    # treatment starts, usually below detection. n_preexisting controls how
    # many - set it to 0 to study purely acquired resistance instead.
    for _ in range(n_preexisting):
        if not drugs: break
        tgt = drugs[rng.integers(len(drugs))]
        sens = {d: rng.uniform(0.55, 0.85)*patient_scale for d in drugs}
        sens[tgt] *= rng.uniform(0.02, 0.18)
        f = 10**rng.uniform(-4, -2.3)                      # 0.005% - 0.5% of the tumour
        clones.append({'id': next_id, 'parent': 0, 'born': 0.0,
                       'growth': base_growth*(1-resist_cost*rng.uniform(.2,.7)),
                       'sens': sens,
                       'markers': founder_markers + rng.normal(0, .5, n_markers),
                       'n': 1e7*f, 'resistant_to': tgt, 'preexisting': True})
        next_id += 1
    traj = []

    for step in range(int(days/dt)):
        t = step*dt
        total = sum(c['n'] for c in clones)
        active = regimen.active(t)

        for c in clones:
            if c['n'] <= 0: continue
            # a residual-disease floor: tumours are rarely sterilised outright

            kill = sum(c['sens'][d]*dose for d, dose in active)
            grow = c['growth']*(1 - total/carrying)
            c['n'] *= np.exp((grow - kill)*dt)
            if c['n'] < 1: c['n'] = 0.0

        # mutation: a surviving clone can spawn a daughter
        for c in list(clones):
            if c['n'] < 1e5: continue
            if rng.random() < mut_rate*dt*np.log10(max(c['n'],10)):
                child = {
                    'id': next_id, 'parent': c['id'], 'born': t,
                    # resistance to ONE drug, bought with a growth penalty
                    'growth': c['growth']*(1-resist_cost*rng.uniform(.3,1.0)),
                    'sens': dict(c['sens']),
                    'markers': c['markers'] + rng.normal(0, .35, n_markers),
                    'n': max(c['n']*1e-4, 10),
                }
                if drugs:
                    tgt = drugs[rng.integers(len(drugs))]
                    child['sens'][tgt] = c['sens'][tgt]*rng.uniform(0.02, 0.25)
                    child['resistant_to'] = tgt
                c['n'] -= child['n']
                clones.append(child); next_id += 1

        if step % 5 == 0:
            tot = sum(c['n'] for c in clones)
            for c in clones:
                if c['n'] > 0:
                    traj.append({'t': t, 'clone': c['id'], 'n': c['n'],
                                 'freq': c['n']/tot if tot else 0})
    return clones, pd.DataFrame(traj)


def biopsy(clones, traj, times, depth=2000, marker_noise=0.4, seed=0):
    """What a real biopsy would see: a noisy, depth-limited sample."""
    rng = np.random.default_rng(seed+1)
    by_id = {c['id']: c for c in clones}
    samples, markers = [], []
    for t in times:
        snap = traj[np.isclose(traj.t, t, atol=2.6)]
        if snap.empty: continue
        snap = snap.groupby('clone', as_index=False).agg(freq=('freq','mean'), n=('n','mean'))
        f = snap.freq.values/snap.freq.sum()
        drawn = rng.multinomial(depth, f)/depth           # sequencing sampling noise
        burden = snap.n.sum()
        for cl, tf, of in zip(snap.clone, f, drawn):
            samples.append({'day': t, 'clone': int(cl), 'true_freq': tf,
                            'observed_freq': of, 'tumour_burden': burden})
        mix = np.zeros(len(MARKERS))
        for cl, of in zip(snap.clone, drawn):
            mix += of*by_id[int(cl)]['markers']
        mix += rng.normal(0, marker_noise, len(MARKERS))
        markers.append({'day': t, **{m: round(v,4) for m,v in zip(MARKERS, mix)},
                        'tumour_burden': burden})
    return pd.DataFrame(samples), pd.DataFrame(markers)


SCENARIOS = {
 'single_agent':   Regimen([('gefitinib', 0, 720, 0.12)]),
 'doublet':        Regimen([('gefitinib', 0, 720, 0.10), ('carboplatin', 0, 720, 0.07)]),
 'sequential':     Regimen([('gefitinib', 0, 240, 0.16), ('carboplatin', 240, 720, 0.12)]),
 'intermittent':   Regimen([('gefitinib', s, s+60, 0.15) for s in range(0, 720, 120)]),
 'untreated':      Regimen([]),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', default='sequential', choices=list(SCENARIOS))
    ap.add_argument('--patients', type=int, default=20)
    ap.add_argument('--days', type=int, default=720)
    ap.add_argument('--out', default='out')
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    reg = SCENARIOS[a.scenario]
    times = list(range(0, a.days+1, 90))

    allc, allt, alls, allm, trees = [], [], [], [], {}
    for p in range(a.patients):
        clones, traj = simulate(reg, days=a.days, seed=a.seed*1000+p)
        smp, mrk = biopsy(clones, traj, times, seed=a.seed*1000+p)
        for c in clones:
            allc.append({'patient':p,'clone':c['id'],'parent':c['parent'],
                         'born_day':round(c['born'],1),'growth':round(c['growth'],4),
                         'resistant_to':c.get('resistant_to',''),'preexisting':c.get('preexisting',False),
                         'final_n':round(c['n'],1),
                         **{f'sens_{k}':round(v,3) for k,v in c['sens'].items()}})
        allt.append(traj.assign(patient=p)); alls.append(smp.assign(patient=p))
        allm.append(mrk.assign(patient=p))
        trees[p]=[{'id':c['id'],'parent':c['parent'],'born':round(c['born'],1)} for c in clones]

    pd.DataFrame(allc).to_csv(f'{a.out}/truth_clones.csv',index=False)
    pd.concat(allt).to_csv(f'{a.out}/truth_trajectory.csv',index=False)
    pd.concat(alls).to_csv(f'{a.out}/obs_samples.csv',index=False)
    pd.concat(allm).to_csv(f'{a.out}/obs_markers.csv',index=False)
    json.dump(trees,open(f'{a.out}/truth_tree.json','w'))

    C=pd.DataFrame(allc); S=pd.concat(alls)
    print(f"scenario={a.scenario}  patients={a.patients}  days={a.days}")
    print(f"  subclones per patient : median {C.groupby('patient').size().median():.0f} "
          f"(range {C.groupby('patient').size().min()}-{C.groupby('patient').size().max()})")
    print(f"  resistant subclones   : {(C.resistant_to!='').sum()} of {len(C)}")
    bb=S.groupby(['patient','day']).tumour_burden.first().unstack()
    nadir=bb.min(axis=1); fin=bb.iloc[:,-1]; ini=bb.iloc[:,0]
    print(f"  best response (median): {(nadir/ini).median()*100:.0f}% of baseline burden")
    print(f"  progressed (>20% up from nadir, RECIST-like): {((fin>nadir*1.2)).sum()} of {a.patients}")
    print(f"  written to {a.out}/")

if __name__=='__main__':
    main()
