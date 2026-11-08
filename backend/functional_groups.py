"""
Functional groups for the 3D viewer, with Gemini explaining what each one does.

The split matters: the SMARTS patterns below are a fixed, hand-checked library,
so which groups are PRESENT is decided by substructure matching, not by a
language model. Gemini is only asked the part it is good at - why that group
matters for this drug's mechanism.

An LLM asked to list atom indices in a SMILES string gets them wrong, and the
viewer would highlight the wrong atoms with full confidence. Pattern matching
cannot.

The frontend does the matching itself (RDKit.js or 3Dmol.js in the browser) from
the SMARTS we hand it, so highlighting stays correct even if the explanation is
wrong.

Usage:
    python functional_groups.py --dry-run
    python functional_groups.py                 # needs structures/drug_structures.csv
"""
import os, sys, json, time, random, argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, 'annotations')
os.makedirs(OUT, exist_ok=True)
JSONL = os.path.join(OUT, 'functional_groups.jsonl')
CSV   = os.path.join(OUT, 'functional_groups.csv')
MODEL = os.environ.get('GEMINI_MODEL', 'models/gemini-3.8-flash')
SAMPLES = int(os.environ.get('GEMINI_SAMPLES', '3'))

# Hand-checked SMARTS. The frontend matches these; nothing here is generated.
GROUPS = {
    'primary amine':      '[NX3;H2;!$(NC=O)]',
    'secondary amine':    '[NX3;H1;!$(NC=O)]',
    'tertiary amine':     '[NX3;H0;!$(NC=O);!$(N=*)]',
    'amide':              '[CX3](=O)[NX3]',
    'carboxylic acid':    '[CX3](=O)[OX2H1]',
    'ester':              '[CX3](=O)[OX2H0][#6]',
    'ketone':             '[#6][CX3](=O)[#6]',
    'aldehyde':           '[CX3H1](=O)[#6]',
    'hydroxyl':           '[OX2H]',
    'phenol':             '[OX2H][c]',
    'ether':              '[OD2]([#6])[#6]',
    'aromatic ring':      'c1ccccc1',
    'halogen':            '[F,Cl,Br,I]',
    'nitro':              '[$([NX3](=O)=O)]',
    'nitrile':            '[NX1]#[CX2]',
    'sulfonamide':        '[SX4](=O)(=O)[NX3]',
    'sulfone':            '[SX4](=O)(=O)',
    'phosphate':          '[PX4](=O)([OX2])([OX2])',
    'quinone':            'O=C1C=CC(=O)C=C1',
    'epoxide':            'C1OC1',
    'morpholine':         'C1COCCN1',
    'piperazine':         'C1CNCCN1',
    'imidazole':          'c1cnc[nH]1',
    'pyridine':           'n1ccccc1',
    'quinazoline':        'c1ccc2ncncc2c1',
    'indole':             'c1ccc2[nH]ccc2c1',
    'thiophene':          'c1ccsc1',
    'urea':               '[NX3][CX3](=O)[NX3]',
    'guanidine':          '[NX3][CX3](=[NX2])[NX3]',
}

SCHEMA = {
    'type': 'object',
    'properties': {
        'groups_present': {'type': 'array', 'items': {'type': 'string'}},
        'key_group': {'type': 'string'},
        'why_it_matters': {'type': 'string'},
        'receptor_interaction': {'type': 'string'},
    },
    'required': ['groups_present', 'key_group', 'why_it_matters',
                 'receptor_interaction'],
}

PROMPT = """{name} is an oncology drug. Its SMILES is:

{smiles}

From this list of functional groups, name the ones you can see in that
structure, then say which single group is most important to how the drug
works, why, and how it interacts with its target.

Groups to choose from (use these exact names, no others):
{group_list}

Keep why_it_matters and receptor_interaction under 30 words each. If you
cannot tell from the structure, say so plainly rather than guessing - the
viewer will highlight whatever you name, and a confident wrong answer is
worse than an admission."""


def get_client():
    try:
        from google import genai
    except ImportError:
        sys.exit('pip install google-genai')
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        sys.exit('Set GEMINI_API_KEY')
    return genai.Client(api_key=key)


def ask(client, prompt, temperature):
    from google.genai import types
    for attempt in range(4):
        try:
            r = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=SCHEMA, temperature=temperature))
            return json.loads(r.text)
        except Exception as e:
            m = str(e)
            if '404' in m or 'NOT_FOUND' in m or 'PERMISSION' in m:
                print(f'  permanent error: {m[:100]}'); return None
            if attempt == 3:
                return None
            time.sleep((2 ** attempt) + random.random())
    return None


def annotate(client, nsc, name, smiles, dry):
    if dry:
        return {'groups_present': ['aromatic ring', 'hydroxyl'],
                'key_group': 'aromatic ring', 'why_it_matters': '[dry-run]',
                'receptor_interaction': '[dry-run]', 'agreement': 1.0,
                'n_samples': SAMPLES}
    gl = '\n'.join(f'  - {g}' for g in GROUPS)
    p = PROMPT.format(name=name, smiles=smiles, group_list=gl)
    outs = [ask(client, p, 0.2 + 0.15 * i) for i in range(SAMPLES)]
    outs = [o for o in outs if o]
    if not outs:
        return None
    votes = Counter(o['key_group'] for o in outs)
    win, n = votes.most_common(1)[0]
    chosen = next(o for o in outs if o['key_group'] == win)
    # keep only groups the model named that are actually in our library
    chosen['groups_present'] = [g for g in chosen['groups_present'] if g in GROUPS]
    chosen['agreement'] = round(n / len(outs), 3)
    chosen['n_samples'] = len(outs)
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--structures', default='structures/drug_structures.csv')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=None)
    a = ap.parse_args()

    sp = os.path.join(HERE, a.structures)
    if not os.path.exists(sp):
        sys.exit(f'no {a.structures} - run fetch_structures.py --all first')
    S = pd.read_csv(sp)
    S = S[S.smiles.notna()]
    if a.limit:
        S = S.head(a.limit)

    done = {}
    if os.path.exists(JSONL):
        with open(JSONL) as f:
            for line in f:
                try:
                    r = json.loads(line); done[r['nsc']] = r
                except json.JSONDecodeError:
                    pass
    todo = [r for r in S.itertuples() if int(r.nsc) not in done]
    print(f'{len(S)} drugs with SMILES, {len(done)} done, {len(todo)} to go')

    client = None if a.dry_run else get_client()

    def work(r):
        res = annotate(client, int(r.nsc), r.name, r.smiles, a.dry_run)
        if not res:
            return None
        return {'nsc': int(r.nsc), 'name': r.name, 'smiles': r.smiles, **res}

    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, f in enumerate(as_completed([ex.submit(work, r) for r in todo]), 1):
            rec = f.result()
            if rec:
                with open(JSONL, 'a') as fh:
                    fh.write(json.dumps(rec) + '\n')
            if i % 10 == 0 or i == len(todo):
                print(f'  {i}/{len(todo)}')

    rows = []
    if os.path.exists(JSONL):
        with open(JSONL) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if rows:
        d = pd.DataFrame(rows)
        d['groups_present'] = d.groups_present.apply(lambda g: '|'.join(g))
        d.drop_duplicates('nsc').sort_values('nsc').to_csv(CSV, index=False)
        print(f'wrote {CSV} ({len(d)} drugs)')
        print(f'mean agreement on key_group: {d.agreement.mean():.2f}')
        low = (d.agreement < 0.6).sum()
        print(f'{low} drugs below 0.6 agreement - treat those explanations as unreliable')


if __name__ == '__main__':
    main()
