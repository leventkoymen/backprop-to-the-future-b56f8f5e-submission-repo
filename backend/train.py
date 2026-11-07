"""
Fit the model ONCE and persist it, so the API does not refit on every request.

    python train.py

Writes artifacts/ :
    model.joblib      the fitted random forest
    features.joblib   the feature-building state (drug marginals, potency, transfer)
    meta.json         version, training date, metrics, row counts
"""
import json, os, sys, hashlib, datetime as dt
sys.path.insert(0, os.environ.get('LUNGPAIR', '/home/claude/share/lungpair'))
import numpy as np, pandas as pd, joblib
from sklearn.ensemble import RandomForestRegressor
from rank import build_features, oof_features, score_ranking

DATA = os.environ.get('LUNGPAIR_DATA', '/home/claude/share/lungpair/data')
OUT = 'artifacts'

def main():
    os.makedirs(OUT, exist_ok=True)
    pairs    = pd.read_csv(f'{DATA}/pairs.csv')
    potency  = pd.read_csv(f'{DATA}/potency.csv')
    transfer = pd.read_csv(f'{DATA}/transfer.csv')
    rng = np.random.default_rng(0)

    # honest held-out metrics, reported with the model so the API can serve them
    idx = rng.permutation(len(pairs)); n = int(.2*len(pairs))
    te, tr = pairs.iloc[idx[:n]].reset_index(drop=True), pairs.iloc[idx[n:]].reset_index(drop=True)
    m = RandomForestRegressor(500, min_samples_leaf=3, random_state=0, n_jobs=-1)
    m.fit(oof_features(tr, potency, transfer, True, rng), tr['mean'])
    metrics = score_ranking(te.hit.values,
                            m.predict(build_features(te, tr, potency, transfer, True)), ks=(20,50))

    # final model on everything
    model = RandomForestRegressor(500, min_samples_leaf=3, random_state=0, n_jobs=-1)
    model.fit(oof_features(pairs, potency, transfer, True, rng), pairs['mean'])
    joblib.dump(model, f'{OUT}/model.joblib')
    joblib.dump({'pairs': pairs, 'potency': potency, 'transfer': transfer},
                f'{OUT}/features.joblib')

    h = hashlib.sha256(open(f'{OUT}/model.joblib','rb').read()).hexdigest()[:12]
    meta = {'model_version': h,
            'trained_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'n_pairs': int(len(pairs)), 'n_hits': int(pairs.hit.sum()),
            'hit_rate': round(float(pairs.hit.mean()), 4),
            'holdout_metrics': {k: round(float(v), 4) for k, v in metrics.items()},
            'note': 'Trained on public NCI-ALMANAC NSCLC data. No patient data.'}
    json.dump(meta, open(f'{OUT}/meta.json','w'), indent=1)
    print(json.dumps(meta, indent=1))

if __name__ == '__main__':
    main()
