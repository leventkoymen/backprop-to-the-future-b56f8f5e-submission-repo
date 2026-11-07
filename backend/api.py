"""
LungPair API — ranks drug pairs by predicted synergy, with evidence tiers.

    python api.py            # serves on http://localhost:8000

Endpoints
    GET  /health                     model version, metrics, status
    GET  /drugs                      the 105 drugs with names
    POST /rank                       {"drugs": [...]} -> tiered ranking
    GET  /pair/<a>/<b>               one pair: prediction, interval, tier
    GET  /pair/<a>/<b>/surface       dose-response grid, for the 3D viewer
    GET  /shortlist?top=N            precomputed top-N
    GET  /submissions                recent requests (audit trail)

All data is public NCI-ALMANAC. No patient data passes through this service.
"""
import json, os, sqlite3, sys, datetime as dt
sys.path.insert(0, os.environ.get('LUNGPAIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lungpair')))
import numpy as np, pandas as pd, joblib
from flask import Flask, request, jsonify, g
try:
    from rank import build_features
except ImportError:
    from features import build_features   # vendored copy, see features.py
HERE = os.path.dirname(os.path.abspath(__file__))

ART  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'artifacts')
DATA = os.environ.get('LUNGPAIR_DATA', '/home/claude/share/lungpair/data')
NAMES_CSV = os.environ.get('NSC_NAMES', os.path.join(HERE, 'nsc_names.csv'))
SURF_CSV  = os.environ.get('SURFACES',  os.path.join(HERE, 'surface_dose_response.csv'))
DB = 'submissions.db'
CONFORMAL_RADIUS = 35.0      # measured: 95.3% coverage on held-out pairs

app = Flask(__name__)

DATA_DIR = os.path.join(HERE, 'data')

def load_model():
    """
    Load the cached model, or fit one from the bundled CSVs.

    The data ships as CSV rather than a pickle because pickles are not portable
    across scikit-learn and pandas versions - a model pickled under sklearn 1.9
    will not load under 1.8. Fitting locally takes under a minute and always
    matches whatever versions are installed.
    """
    from sklearn.ensemble import RandomForestRegressor
    pairs    = pd.read_csv(os.path.join(DATA_DIR, 'pairs.csv'))
    potency  = pd.read_csv(os.path.join(DATA_DIR, 'potency.csv'))
    transfer = pd.read_csv(os.path.join(DATA_DIR, 'transfer.csv'))
    cache = os.path.join(ART, 'model.joblib')
    model = None
    if os.path.exists(cache):
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('error')      # refuse a version-mismatched pickle
                model = joblib.load(cache)
            print('loaded cached model', flush=True)
        except Exception:
            print('cached model is from another library version - refitting', flush=True)
            model = None
    if model is None:
        print('fitting model (about a minute, once)...', flush=True)
        try:
            from rank import oof_features as _oof
        except ImportError:
            from features import oof_features as _oof
        rng = np.random.default_rng(0)
        model = RandomForestRegressor(500, min_samples_leaf=3, random_state=0, n_jobs=-1)
        model.fit(_oof(pairs, potency, transfer, True, rng), pairs['mean'])
        os.makedirs(ART, exist_ok=True)
        joblib.dump(model, cache, compress=3)
        print('model cached for next time', flush=True)
    return model, pairs, potency, transfer

print('loading...', flush=True)
META  = json.load(open(os.path.join(ART, 'meta.json')))
MODEL, PAIRS, POTENCY, TRANSFER = load_model()
NAMES = pd.read_csv(NAMES_CSV).set_index('nsc').name.to_dict() if os.path.exists(NAMES_CSV) else {}
NAME2NSC = {v.lower(): k for k, v in NAMES.items()}
SURFACES = pd.read_csv(SURF_CSV) if os.path.exists(SURF_CSV) else None
KNOWN = sorted(set(PAIRS.a) | set(PAIRS.b))
HAS_TRANSFER = set(zip(TRANSFER.a, TRANSFER.b))
print(f'ready: {len(PAIRS):,} pairs, {len(KNOWN)} drugs, model {META["model_version"]}', flush=True)


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.execute("""CREATE TABLE IF NOT EXISTS submissions(
            id INTEGER PRIMARY KEY, ts TEXT, endpoint TEXT, n_drugs INT,
            n_ranked INT, model_version TEXT)""")
    return g.db

@app.teardown_appcontext
def close(_):
    d = g.pop('db', None)
    if d: d.commit(); d.close()

def log(endpoint, n_drugs, n_ranked):
    db().execute("INSERT INTO submissions(ts,endpoint,n_drugs,n_ranked,model_version) VALUES(?,?,?,?,?)",
                 (dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                  endpoint, n_drugs, n_ranked, META['model_version']))
    db().commit()

def resolve(d):
    """Accept an NSC number or a drug name."""
    if isinstance(d, (int, float)): return int(d)
    s = str(d).strip()
    if s.isdigit(): return int(s)
    return NAME2NSC.get(s.lower())

def tier_of(a, b):
    """Evidence tier - decides what the service is willing to promise."""
    key = (min(a,b), max(a,b))
    if key in HAS_TRANSFER:  return 1, 'pair measured in another cancer', 0.89
    if a in KNOWN and b in KNOWN: return 2, 'both drugs screened here, pair untested', 0.34
    return 4, 'new drugs, no prior measurements', 0.04

def nm(x): return NAMES.get(int(x), f'NSC {int(x)}')


@app.get('/health')
def health():
    return jsonify(status='ok', **META,
                   drugs_loaded=len(KNOWN), surfaces_loaded=bool(SURFACES is not None),
                   data_classification='public — NCI-ALMANAC, no patient data')

@app.get('/drugs')
def drugs():
    return jsonify(count=len(KNOWN),
                   drugs=[{'nsc': int(d), 'name': nm(d)} for d in KNOWN])

@app.post('/rank')
def rank():
    body = request.get_json(silent=True) or {}
    raw = body.get('drugs', [])
    if not isinstance(raw, list) or len(raw) < 2:
        return jsonify(error='send {"drugs": [...]} with at least two drugs'), 400
    top = int(body.get('top', 20))

    resolved, unknown = [], []
    for d in raw:
        r = resolve(d)
        (resolved if r is not None else unknown).append(r if r is not None else d)
    resolved = sorted(set(resolved))
    if len(resolved) < 2:
        return jsonify(error='could not resolve two or more drugs', unknown=unknown), 400

    cand = pd.DataFrame([{'a': min(x,y), 'b': max(x,y)}
                         for i, x in enumerate(resolved) for y in resolved[i+1:]])
    cand['n_lines'] = 9; cand['mean'] = 0.0
    X = build_features(cand, PAIRS, POTENCY, TRANSFER, True)
    cand['score'] = MODEL.predict(X)

    out, withheld = [], []
    for _, r in cand.iterrows():
        t, why, prec = tier_of(r.a, r.b)
        row = {'drug_a': nm(r.a), 'drug_b': nm(r.b),
               'nsc_a': int(r.a), 'nsc_b': int(r.b),
               'tier': t, 'evidence': why}
        if t >= 4:
            # the service refuses to rank tier 4 - 1.9x baseline is not a ranking
            row['ranked'] = False
            row['reason'] = 'below the evidence threshold; measure monotherapy first'
            withheld.append(row)
        else:
            row.update(ranked=True,
                       score=round(float(r.score), 1),
                       interval_95=[round(float(r.score-CONFORMAL_RADIUS),1),
                                    round(float(r.score+CONFORMAL_RADIUS),1)],
                       expected_precision_at_20=prec)
            out.append(row)
    out.sort(key=lambda x: -x['score'])
    for i, r in enumerate(out, 1): r['rank'] = i
    log('/rank', len(resolved), len(out))
    return jsonify(model_version=META['model_version'],
                   requested=len(raw), resolved=len(resolved), unknown=unknown,
                   pairs_evaluated=len(cand),
                   ranked=out[:top], withheld=withheld,
                   note='Tier 4 pairs are deliberately not ranked. Measured precision there '
                        'is 0.04 against a 0.03 baseline.')

@app.get('/pair/<int:a>/<int:b>')
def pair(a, b):
    lo, hi = min(a,b), max(a,b)
    cand = pd.DataFrame([{'a': lo, 'b': hi, 'n_lines': 9, 'mean': 0.0}])
    score = float(MODEL.predict(build_features(cand, PAIRS, POTENCY, TRANSFER, True))[0])
    t, why, prec = tier_of(lo, hi)
    m = PAIRS[(PAIRS.a==lo)&(PAIRS.b==hi)]
    log('/pair', 2, 1)
    return jsonify(drug_a=nm(lo), drug_b=nm(hi), nsc_a=lo, nsc_b=hi,
                   tier=t, evidence=why,
                   predicted_score=round(score,1),
                   interval_95=[round(score-CONFORMAL_RADIUS,1), round(score+CONFORMAL_RADIUS,1)],
                   measured=None if m.empty else {
                       'mean_combo_score': round(float(m['mean'].iloc[0]),1),
                       'hit_rate_across_lines': round(float(m.hit_rate.iloc[0]),2),
                       'n_cell_lines': int(m.n_lines.iloc[0])},
                   has_surface=bool(SURFACES is not None and
                       len(SURFACES[(SURFACES.drug_a_nsc==lo)&(SURFACES.drug_b_nsc==hi)])>0))

@app.get('/pair/<int:a>/<int:b>/surface')
def surface(a, b):
    if SURFACES is None: return jsonify(error='surface data not loaded'), 404
    lo, hi = min(a,b), max(a,b)
    s = SURFACES[(SURFACES.drug_a_nsc==lo)&(SURFACES.drug_b_nsc==hi)]
    if s.empty: return jsonify(error='no surface for this pair', drug_a=nm(lo), drug_b=nm(hi)), 404
    cl = request.args.get('cell_line')
    if cl: s = s[s.cell_line==cl]
    log('/surface', 2, len(s))
    return jsonify(drug_a=nm(lo), drug_b=nm(hi),
                   cell_lines=sorted(s.cell_line.unique().tolist()),
                   points=json.loads(s.to_json(orient='records')))

@app.get('/shortlist')
def shortlist():
    top = int(request.args.get('top', 20))
    p = PAIRS.copy()
    p['score'] = MODEL.predict(build_features(p, PAIRS, POTENCY, TRANSFER, True))
    p = p.nlargest(top, 'score')
    return jsonify(top=top, pairs=[{
        'rank': i+1, 'drug_a': nm(r.a), 'drug_b': nm(r.b),
        'score': round(float(r.score),1),
        'interval_95': [round(float(r.score-CONFORMAL_RADIUS),1),
                        round(float(r.score+CONFORMAL_RADIUS),1)],
        'measured_mean': round(float(r['mean']),1),
        'hit_rate': round(float(r.hit_rate),2)} for i,(_,r) in enumerate(p.iterrows())])

@app.get('/submissions')
def submissions():
    rows = db().execute("SELECT ts,endpoint,n_drugs,n_ranked,model_version FROM submissions "
                        "ORDER BY id DESC LIMIT 50").fetchall()
    return jsonify(count=len(rows), submissions=[
        dict(zip(['ts','endpoint','n_drugs','n_ranked','model_version'], r)) for r in rows])


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 8000)), debug=False)
