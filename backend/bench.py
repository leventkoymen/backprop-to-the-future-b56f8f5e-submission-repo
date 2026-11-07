"""
Which model is best at the one thing our model cannot do?

On drug-disjoint pairs - neither drug ever seen in training - the random
forest sits at 0.040 precision@50. That is chance. This benchmarks several
models on exactly those pairs, against real NCI-ALMANAC labels.

This is a better benchmark than a public leaderboard for one reason: it is
our task, our data, and our baseline. A model that tops the Vals Index may
still be useless at guessing whether two oncology drugs interact.

Baselines, both on the same pairs:
    random ranking   - permutation, 2000 draws
    random forest    - 0.040, measured earlier on a drug-disjoint split

Three random held-out drug sets (they can share drugs, so they are not fully
independent). For an LLM the split only chooses WHICH pairs are scored - it is
never trained on our data. The report shows per-split numbers and a bootstrap
interval for the mean so nobody over-reads it.

Caveats to state with any result:
  - The LLM only knows these drugs because they are approved and published. A
    truly new compound has no literature, so this is NOT a fix for real cold start.
  - NCI-ALMANAC (2017) is public; a model may have seen results for some pairs.
  - The forest's 0.040 was measured on a different split, so it is a reference
    point, not a same-pairs comparison. The random baseline IS on the same pairs.

Gemini names start with models/ and use GEMINI_API_KEY. Anything else goes via
LiteLLM (pip install litellm): anthropic/claude-haiku-5-5, anthropic/claude-sonnet-5-5,
anthropic/claude-opus-5-5 with ANTHROPIC_API_KEY; openai/... with OPENAI_API_KEY.

Usage:
    export GEMINI_API_KEY=...
    python bench.py --dry-run
    python bench.py --models models/gemini-4-argon,models/gemini-3.8-flash,models/gemini-3.5-flash
    export ANTHROPIC_API_KEY=...
    python bench.py --models anthropic/claude-haiku-5-5,anthropic/claude-opus-5-5
    python bench.py --report
"""

import os, sys, json, time, random, argparse
from statistics import median
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
OUT  = os.path.join(HERE, 'bench_out')
os.makedirs(OUT, exist_ok=True)
JSONL = os.path.join(OUT, 'scores.jsonl')

SAMPLES = int(os.environ.get('BENCH_SAMPLES', '3'))
WORKERS = int(os.environ.get('BENCH_WORKERS', '8'))
SEEDS   = [0, 2, 4]
N_HELD  = 30
FOREST_P50 = 0.040        # measured earlier, drug-disjoint, different split

DEFAULT_MODELS = ('models/gemini-4-argon,models/gemini-3.8-flash,'
                  'models/gemini-3.5-flash,models/gemini-3.1-flash-lite')

SCHEMA = {'type': 'object',
          'properties': {'synergy_score': {'type': 'integer'},
                         'reason': {'type': 'string'}},
          'required': ['synergy_score', 'reason']}

PROMPT = """Two cancer drugs were tested together against non-small cell lung
cancer cell lines. You are predicting, from pharmacology alone, how likely
this pair is to show greater-than-additive activity.

Drug A: {name_a}
Drug B: {name_b}

Score 0-100, where 0 means you expect no interaction beyond simple additivity
and 100 means you expect strong synergy. Give one short reason.

You have not been told the experimental result and must not guess at it.
Reason only from what the two drugs target and whether those mechanisms would
be expected to combine favourably. Most drug pairs are not synergistic; score
accordingly rather than being generous."""


def names():
    p = os.path.join(HERE, 'nsc_names.csv')
    if not os.path.exists(p):
        p = os.path.join(DATA, 'nsc_names.csv')
    n = pd.read_csv(p)
    return dict(zip(n.nsc.astype(int), n.name))


def splits():
    p = pd.read_csv(os.path.join(DATA, 'pairs.csv'))
    p['a'] = p.a.astype(int); p['b'] = p.b.astype(int)
    drugs = sorted(set(p.a) | set(p.b))
    out = {}
    for s in SEEDS:
        rng = np.random.default_rng(s)
        held = set(rng.choice(drugs, size=N_HELD, replace=False).tolist())
        out[s] = p[p.a.isin(held) & p.b.isin(held)].reset_index(drop=True)
    return out


# ---------------------------------------------------------------- callers

def gemini_client():
    from google import genai
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        sys.exit('Set GEMINI_API_KEY')
    return genai.Client(api_key=key)


def ask_gemini(client, model, prompt, temperature):
    from google.genai import types
    for attempt in range(4):
        try:
            r = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=SCHEMA, temperature=temperature))
            return json.loads(r.text)
        except Exception as e:
            m = str(e)
            if '404' in m or 'NOT_FOUND' in m or 'PERMISSION' in m:
                print(f'  {model}: permanent error, skipping - {m[:90]}')
                return 'FATAL'
            if attempt == 3:
                return None
            time.sleep((2 ** attempt) + random.random())
    return None


def ask_litellm(model, prompt, temperature):
    import litellm
    for attempt in range(4):
        try:
            r = litellm.completion(
                drop_params=True,      # e.g. Claude 5.5 models only accept their default temperature
                model=model,
                messages=[{'role': 'user', 'content': prompt +
                           '\n\nReply with ONLY JSON: '
                           '{"synergy_score": <0-100>, "reason": "<short>"}'}],
                temperature=temperature, max_tokens=200)
            txt = r.choices[0].message.content or ''
            import re
            m = re.search(r'\{.*\}', txt, re.S)
            return json.loads(m.group(0))
        except Exception as e:
            name = type(e).__name__
            if name in ('NotFoundError', 'AuthenticationError', 'PermissionDeniedError') \
                    or 'model' in str(e).lower() and 'not' in str(e).lower() and 'found' in str(e).lower():
                print(f'  {model}: permanent error, skipping - {name}: {str(e)[:90]}')
                return 'FATAL'
            if attempt == 3:
                if model not in _WARNED:               # never fail silently
                    _WARNED.add(model)
                    print(f'  {model}: call failed after retries - {name}: {str(e)[:120]}')
                return None
            time.sleep((2 ** attempt) + random.random())
    return None


_WARNED = set()


def score_pair(model, client, a, b, NAMES, dry):
    if dry:
        return {'score': float(random.randint(0, 100)), 'n_samples': SAMPLES,
                'spread': 0.0}
    prompt = PROMPT.format(name_a=NAMES.get(a, f'NSC {a}'),
                           name_b=NAMES.get(b, f'NSC {b}'))
    vals = []
    for i in range(SAMPLES):
        t = 0.3 + 0.15 * i
        r = (ask_gemini(client, model, prompt, t) if model.startswith('models/')
             else ask_litellm(model, prompt, t))
        if r == 'FATAL':
            return 'FATAL'
        if r:
            try:
                vals.append(int(r['synergy_score']))
            except Exception:
                pass
    if not vals:
        return None
    return {'score': float(median(vals)), 'n_samples': len(vals),
            'spread': float(max(vals) - min(vals))}


# ---------------------------------------------------------------- metrics

def p_at_k(y, s, k=50, seed=0):
    # Shuffle first, then a STABLE sort: tied scores land in random order.
    # Without this, ties keep the file's row order - and a model that gives every
    # pair the same score scored 0.28 (9x chance) on a file listing hits first.
    s = np.asarray(s, dtype=float)
    perm = np.random.default_rng(seed).permutation(len(s))
    o = perm[np.argsort(-s[perm], kind='stable')]
    k = min(k, len(o))
    return float(np.asarray(y)[o[:k]].mean())


def boot_ci(groups, k=50, n=1000, seed=0):
    """95% CI for the MEAN of per-split p@k (the number the report prints):
    resample pairs within each split, recompute each split, average."""
    rng = np.random.default_rng(seed)
    groups = [(np.asarray(y), np.asarray(s, dtype=float)) for y, s in groups]
    vals = []
    for b in range(n):
        per = []
        for y, s in groups:
            i = rng.integers(0, len(y), len(y))
            per.append(p_at_k(y[i], s[i], k, seed=b))
        vals.append(np.mean(per))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def rand_base(y, k=50, trials=2000, seed=0):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    return float(np.mean([y[rng.permutation(len(y))[:min(k, len(y))]].mean()
                          for _ in range(trials)]))


# ---------------------------------------------------------------- run

def load_done():
    d = {}
    if os.path.exists(JSONL):
        with open(JSONL) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d[(r['model'], r['a'], r['b'])] = r
    return d


def run(models, dry, limit):
    NAMES = names(); sp = splits(); done = load_done()
    # only ask for a Gemini key if a Gemini model is actually requested
    need_gemini = any(m.startswith('models/') for m in models)
    client = gemini_client() if (need_gemini and not dry) else None

    allpairs = sorted({(int(r.a), int(r.b)) for df in sp.values() for r in df.itertuples()})
    for model in models:
        # an LLM's score for a pair doesn't depend on the split - score it once
        todo = [(None, a, b) for a, b in allpairs if (model, a, b) not in done]
        if limit:
            todo = todo[:limit]
        if not todo:
            print(f'{model}: already complete'); continue
        print(f'{model}: {len(todo)} pairs (~{len(todo)*SAMPLES} calls)')

        fatal = [False]

        def work(item):
            if fatal[0]:
                return None
            s, a, b = item
            r = score_pair(model, client, a, b, NAMES, dry)
            if r == 'FATAL':
                fatal[0] = True
                return None
            if not r:
                return None
            return {'model': model, 'a': a, 'b': b,
                    'drug_a': NAMES.get(a, f'NSC {a}'),
                    'drug_b': NAMES.get(b, f'NSC {b}'), **r}

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = [ex.submit(work, t) for t in todo]
            for i, f in enumerate(as_completed(futs), 1):
                rec = f.result()
                if rec:
                    with open(JSONL, 'a') as fh:
                        fh.write(json.dumps(rec) + '\n')
                if i % 100 == 0 or i == len(todo):
                    print(f'  {i}/{len(todo)}')
        if fatal[0]:
            print(f'  {model} unavailable on this key - skipped')


def report():
    done = load_done()
    if not done:
        print('nothing scored yet'); return
    sc = pd.DataFrame(done.values())
    sp = splits()

    print('\nprecision@50 on drug-disjoint pairs (neither drug seen in training)')
    print('=' * 78)
    hdr = f'{"model":<34}' + ''.join(f'{"split "+str(s):>10}' for s in SEEDS) \
          + f'{"mean":>8}{"95% CI":>16}'
    print(hdr); print('-' * 78)

    rows = []
    for model, g in sc.groupby('model'):
        per, groups, cover = [], [], []
        g = g.drop_duplicates(['a', 'b'])
        for s in SEEDS:
            df = sp[s]
            m = df.merge(g[['a', 'b', 'score']], on=['a', 'b'])
            cover.append(f'{len(m)}/{len(df)}')
            if len(m) < 0.9*len(df):             # missing calls are not random (rate limits)
                per.append(None); continue
            per.append(p_at_k(m.hit.values, m.score.values))
            groups.append((m.hit.values, m.score.values))
        print(f'   {model}: pairs scored per split {", ".join(cover)}'
              + ('' if len(groups) == len(SEEDS) else '  (<90% scored -> split left out)'))
        if not groups:
            continue
        ally = [v for y, _ in groups for v in y]
        mean = float(np.mean([x for x in per if x is not None]))
        lo, hi = boot_ci(groups)
        rows.append({'model': model, 'per': per, 'mean': mean,
                     'lo': lo, 'hi': hi, 'n': len(ally),
                     'spread': g.spread.mean()})
        cells = ''.join(f'{(f"{x:.3f}" if x is not None else "-"):>10}' for x in per)
        print(f'{model.replace("models/",""):<34}{cells}{mean:>8.3f}'
              f'{f"[{lo:.3f}, {hi:.3f}]":>16}')

    # baselines on the pooled held-out pairs
    anyg = sc.groupby('model').first().index[0]
    g = sc[sc.model == anyg]
    pooled_y = []
    for s in SEEDS:
        pooled_y += list(sp[s].hit.values)
    rb = rand_base(pooled_y)
    print('-' * 78)
    print(f'{"random ranking":<34}{"":>30}{rb:>8.3f}')
    print(f'{"random forest (cold start)":<34}{"":>30}{FOREST_P50:>8.3f}'
          f'{"  different split - reference only":>36}')
    print()

    if not rows:
        return
    best = max(rows, key=lambda r: r['mean'])
    wins = sum(1 for i, s in enumerate(SEEDS)
               if best['per'][i] is not None and
               all(r['per'][i] is None or best['per'][i] >= r['per'][i]
                   for r in rows))
    print(f'best: {best["model"]}  mean {best["mean"]:.3f}, '
          f'won {wins} of {len([p for p in best["per"] if p is not None])} splits')
    print(f'mean sample spread {best["spread"]:.1f} points '
          f'(high = the model is guessing, not reasoning)')

    if best['lo'] <= rb:
        print('\nThe best model\'s confidence interval includes the random '
              'baseline.\nDo not claim it beats chance on this evidence.')
    elif wins < 2:
        print('\nThe best model does not win consistently across splits.\n'
              'Report the spread, not the mean alone.')
    else:
        print('\nBeats chance, consistently across splits. Report it - and '
              'say it is a\nranking prior from pharmacological knowledge, '
              'not a measurement.')
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', default=DEFAULT_MODELS)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.report:
        report(); return
    if a.dry_run:
        print('DRY RUN - no API calls\n')
    models = [m.strip() for m in a.models.split(',') if m.strip()]
    run(models, a.dry_run, a.limit)
    report()


if __name__ == '__main__':
    main()
