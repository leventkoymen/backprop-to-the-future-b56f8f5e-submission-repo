"""
Gemini annotation layer for LungPair.

Adds pharmacological context to the ranking WITHOUT touching the ranking.
Nothing in this file influences a predicted score. It reads the model's
output and attaches what is known about the drugs involved.

Two stages:
  1. drugs  - for each NSC, the primary molecular target and mechanism class
  2. pairs  - for the top-N ranked pairs, why the combination is or is not
              mechanistically plausible

Both use self-consistency: each question is asked k times and only the
majority answer is kept, with the agreement fraction recorded alongside.
An annotation at 5/5 agreement is a different object from one at 2/5, and
the output says which it is.

Usage:
    export GEMINI_API_KEY=...
    python annotate.py --dry-run           # no API calls, checks plumbing
    python annotate.py --stage drugs
    python annotate.py --stage pairs --limit 200
    python annotate.py --stage all

Resumable: results append to JSONL as they complete. Re-running skips
whatever is already done, so a crash or a Ctrl-C costs you nothing.
"""

import os, sys, json, time, argparse, random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
OUT  = os.path.join(HERE, 'annotations')
os.makedirs(OUT, exist_ok=True)

DRUG_JSONL = os.path.join(OUT, 'drugs.jsonl')
PAIR_JSONL = os.path.join(OUT, 'pairs.jsonl')
DRUG_CSV   = os.path.join(OUT, 'drug_annotations.csv')
PAIR_CSV   = os.path.join(OUT, 'pair_annotations.csv')

MODEL   = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')
SAMPLES = int(os.environ.get('GEMINI_SAMPLES', '5'))
WORKERS = int(os.environ.get('GEMINI_WORKERS', '8'))

MECHANISM_CLASSES = [
    'alkylating agent', 'antimetabolite', 'topoisomerase inhibitor',
    'microtubule agent', 'protein kinase inhibitor', 'hormonal agent',
    'proteasome inhibitor', 'HDAC inhibitor', 'DNA intercalator',
    'differentiating agent', 'other', 'unknown',
]

RATIONALE_TYPES = [
    'chemotherapy plus targeted agent',
    'two agents on the same pathway',
    'complementary pathways',
    'one agent reverses resistance to the other',
    'additive cytotoxicity, no specific interaction',
    'no clear mechanistic rationale',
]

DRUG_SCHEMA = {
    'type': 'object',
    'properties': {
        'primary_target':   {'type': 'string'},
        'mechanism_class':  {'type': 'string', 'enum': MECHANISM_CLASSES},
        'used_in_nsclc':    {'type': 'boolean'},
        'one_line':         {'type': 'string'},
    },
    'required': ['primary_target', 'mechanism_class', 'used_in_nsclc', 'one_line'],
}

PAIR_SCHEMA = {
    'type': 'object',
    'properties': {
        'rationale_type': {'type': 'string', 'enum': RATIONALE_TYPES},
        'rationale':      {'type': 'string'},
        'known_clinical_use': {'type': 'boolean'},
    },
    'required': ['rationale_type', 'rationale', 'known_clinical_use'],
}

DRUG_PROMPT = """You are annotating a drug for a cancer pharmacology database.

Drug: {name} (NCI NSC number {nsc})

Give its primary molecular target, its mechanism class, whether it is used
in non-small cell lung cancer specifically, and one short factual line about
how it works.

If you are not confident which drug this is, set mechanism_class to
"unknown" and say so in one_line. Do not guess. An honest "unknown" is more
useful here than a plausible invention."""

PAIR_PROMPT = """You are annotating a drug COMBINATION for a cancer pharmacology database.

Drug A: {name_a} (NSC {a}) - target: {target_a}, class: {class_a}
Drug B: {name_b} (NSC {b}) - target: {target_b}, class: {class_b}

This pair was measured in the NCI-ALMANAC screen against non-small cell lung
cancer cell lines. Classify why these two might work together, give one
sentence of mechanistic rationale, and say whether this combination is
already used clinically in any cancer.

Judge the biology, not the screen result. If there is no sensible
mechanistic story, say "no clear mechanistic rationale" - that is a real and
useful answer, not a failure. Do not invent a pathway connection to make the
pair look better than it is."""


# ---------------------------------------------------------------- client

def get_client():
    try:
        from google import genai
    except ImportError:
        sys.exit("google-genai not installed. Run:  pip install google-genai")
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        sys.exit("Set GEMINI_API_KEY (get one at aistudio.google.com/apikey)")
    return genai.Client(api_key=key)


def ask_once(client, prompt, schema, temperature):
    """One call. Returns the parsed dict, or None if the call failed."""
    from google.genai import types
    for attempt in range(5):
        try:
            r = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=schema,
                    temperature=temperature,
                ),
            )
            return json.loads(r.text)
        except Exception as e:
            msg = str(e)
            if '429' in msg or 'RESOURCE_EXHAUSTED' in msg or '503' in msg:
                time.sleep((2 ** attempt) + random.random())
                continue
            if attempt == 4:
                print(f'  giving up after 5 attempts: {msg[:120]}')
                return None
            time.sleep(1 + random.random())
    return None


def ask_consistent(client, prompt, schema, vote_field, k=SAMPLES, dry=False):
    """Ask k times, keep the majority answer, record how much it agreed.

    Self-consistency only works on a field with a fixed set of values, so the
    vote runs on `vote_field` (an enum) and the free text is taken from a
    sample that voted with the majority. Reporting agreement on prose would
    be meaningless - two different sentences are not a disagreement.
    """
    if dry:
        fake = {f['name'] if isinstance(f, dict) else f: None for f in []}
        fake = {p: ('unknown' if p == 'mechanism_class'
                    else RATIONALE_TYPES[-1] if p == 'rationale_type'
                    else False if schema['properties'][p]['type'] == 'boolean'
                    else f'[dry-run {p}]')
                for p in schema['properties']}
        return fake, 1.0, k

    samples = [ask_once(client, prompt, schema, 0.3 + 0.1 * i) for i in range(k)]
    samples = [s for s in samples if s]
    if not samples:
        return None, 0.0, 0

    votes = Counter(s.get(vote_field) for s in samples)
    winner, n = votes.most_common(1)[0]
    agreement = n / len(samples)
    chosen = next(s for s in samples if s.get(vote_field) == winner)
    return chosen, agreement, len(samples)


# ---------------------------------------------------------------- io

def load_done(path, key_fields):
    done = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done[tuple(rec[k] for k in key_fields)] = rec
    return done


def append(path, rec):
    with open(path, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def names():
    p = os.path.join(HERE, 'nsc_names.csv')
    if not os.path.exists(p):
        p = os.path.join(DATA, 'nsc_names.csv')
    n = pd.read_csv(p)
    return dict(zip(n.nsc.astype(int), n.name))


# ---------------------------------------------------------------- stages

def stage_drugs(client, dry=False, limit=None):
    NAMES = names()
    pairs = pd.read_csv(os.path.join(DATA, 'pairs.csv'))
    nscs = sorted(set(pairs.a.astype(int)) | set(pairs.b.astype(int)))
    if limit:
        nscs = nscs[:limit]

    done = load_done(DRUG_JSONL, ['nsc'])
    todo = [n for n in nscs if (n,) not in done]
    print(f'drugs: {len(nscs)} total, {len(done)} already done, {len(todo)} to do')

    def work(nsc):
        nm = NAMES.get(nsc, f'NSC {nsc}')
        ans, agr, n = ask_consistent(
            client, DRUG_PROMPT.format(name=nm, nsc=nsc),
            DRUG_SCHEMA, 'mechanism_class', dry=dry)
        if ans is None:
            return None
        return {'nsc': nsc, 'name': nm, 'agreement': round(agr, 3),
                'n_samples': n, **ans}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, n): n for n in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            if rec:
                append(DRUG_JSONL, rec)
            if i % 10 == 0 or i == len(todo):
                print(f'  {i}/{len(todo)}')

    rows = list(load_done(DRUG_JSONL, ['nsc']).values())
    if rows:
        pd.DataFrame(rows).sort_values('nsc').to_csv(DRUG_CSV, index=False)
        print(f'wrote {DRUG_CSV}  ({len(rows)} drugs)')
    return rows


def stage_pairs(client, dry=False, limit=200):
    NAMES = names()
    pairs = pd.read_csv(os.path.join(DATA, 'pairs.csv'))
    pairs = pairs.sort_values('mean', ascending=False)
    if limit:
        pairs = pairs.head(limit)

    drug_ann = {}
    if os.path.exists(DRUG_CSV):
        d = pd.read_csv(DRUG_CSV)
        drug_ann = {int(r.nsc): r for r in d.itertuples()}
    else:
        print('note: no drug annotations yet - run --stage drugs first for '
              'better pair prompts. Continuing without them.')

    done = load_done(PAIR_JSONL, ['a', 'b'])
    todo = [(int(r.a), int(r.b)) for r in pairs.itertuples()
            if (int(r.a), int(r.b)) not in done]
    print(f'pairs: {len(pairs)} selected, {len(done)} already done, {len(todo)} to do')

    def info(nsc, field, default='unknown'):
        r = drug_ann.get(nsc)
        return getattr(r, field, default) if r is not None else default

    def work(ab):
        a, b = ab
        prompt = PAIR_PROMPT.format(
            name_a=NAMES.get(a, f'NSC {a}'), a=a,
            target_a=info(a, 'primary_target'), class_a=info(a, 'mechanism_class'),
            name_b=NAMES.get(b, f'NSC {b}'), b=b,
            target_b=info(b, 'primary_target'), class_b=info(b, 'mechanism_class'))
        ans, agr, n = ask_consistent(
            client, prompt, PAIR_SCHEMA, 'rationale_type', dry=dry)
        if ans is None:
            return None
        return {'a': a, 'b': b,
                'drug_a': NAMES.get(a, f'NSC {a}'), 'drug_b': NAMES.get(b, f'NSC {b}'),
                'agreement': round(agr, 3), 'n_samples': n, **ans}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, ab): ab for ab in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            if rec:
                append(PAIR_JSONL, rec)
            if i % 10 == 0 or i == len(todo):
                print(f'  {i}/{len(todo)}')

    rows = list(load_done(PAIR_JSONL, ['a', 'b']).values())
    if rows:
        pd.DataFrame(rows).to_csv(PAIR_CSV, index=False)
        print(f'wrote {PAIR_CSV}  ({len(rows)} pairs)')
    return rows


def summarise():
    """What the annotation layer actually produced, including its failures."""
    if os.path.exists(DRUG_CSV):
        d = pd.read_csv(DRUG_CSV)
        print(f'\ndrugs: {len(d)}')
        print(f'  mean agreement        {d.agreement.mean():.2f}')
        print(f'  unanimous (5/5)       {(d.agreement == 1.0).sum()}')
        print(f'  shaky (<0.6)          {(d.agreement < 0.6).sum()}')
        print(f'  self-declared unknown {(d.mechanism_class == "unknown").sum()}')
    if os.path.exists(PAIR_CSV):
        p = pd.read_csv(PAIR_CSV)
        print(f'\npairs: {len(p)}')
        print(f'  mean agreement  {p.agreement.mean():.2f}')
        print(f'  unanimous       {(p.agreement == 1.0).sum()}')
        print(f'  shaky (<0.6)    {(p.agreement < 0.6).sum()}')
        print('\n  rationale types:')
        for k, v in p.rationale_type.value_counts().items():
            print(f'    {v:4d}  {k}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['drugs', 'pairs', 'all', 'summary'],
                    default='all')
    ap.add_argument('--limit', type=int, default=None,
                    help='cap how many items to annotate (pairs defaults to 200)')
    ap.add_argument('--dry-run', action='store_true',
                    help='no API calls; verifies files, schema and output paths')
    args = ap.parse_args()

    if args.stage == 'summary':
        summarise(); return

    client = None if args.dry_run else get_client()
    if args.dry_run:
        print('DRY RUN - no API calls, no credits spent\n')

    if args.stage in ('drugs', 'all'):
        stage_drugs(client, dry=args.dry_run, limit=args.limit)
    if args.stage in ('pairs', 'all'):
        stage_pairs(client, dry=args.dry_run,
                    limit=args.limit if args.limit else 200)
    summarise()


if __name__ == '__main__':
    main()
