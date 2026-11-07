"""
Fetch each drug's chemical structure and a 3D model of it, linked by NSC number.

Run on your own laptop (needs internet to PubChem):
    pip install rdkit pandas
    python fetch_structures.py --names nsc_names.csv --data surface_dose_response.csv

Outputs (in --out, default structures/):
    <nsc>_<name>.sdf      one 3D model per drug - open in 3Dmol.js, PyMOL, ChimeraX
    drug_structures.csv   nsc, name, PubChem CID, SMILES, formula, weight, where the 3D came from

Salts (e.g. "Tamoxifen citrate") are mapped to the active parent molecule.
PubChem has no 3D model for some large molecules; for those, RDKit builds one from
the SMILES (marked source_3d = rdkit). Every SMILES is checked against PubChem's own
formula, so a bad lookup is flagged rather than silently used.
"""
import argparse, json, os, re, time, urllib.parse, urllib.request
import pandas as pd

BASE = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug'


def get(url, binary=False, tries=4):
    """PubChem request with retries: timeouts are common, so wait and try again."""
    req = urllib.request.Request(url, headers={'User-Agent': 'lungpair-hackathon/1.0'})
    for attempt in range(tries):
        time.sleep(0.25 + 2 * attempt)                  # PubChem asks for <= 5 requests/s
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
                return b if binary else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1: raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt == tries - 1: raise


def find_cid(nsc, name):
    """CID by NSC synonym first (unambiguous), then by name."""
    for q in [f'NSC{nsc}', f'NSC-{nsc}', f'NSC {nsc}', name]:
        d = get(f'{BASE}/compound/name/{urllib.parse.quote(q)}/cids/JSON')
        if d and d.get('IdentifierList', {}).get('CID'):
            return d['IdentifierList']['CID'][0], q
    return None, None


def parent_cid(cid):
    """Salt -> active parent molecule (citrate, sulfate, sodium salts)."""
    d = get(f'{BASE}/compound/cid/{cid}/cids/JSON?cids_type=parent')
    ids = (d or {}).get('IdentifierList', {}).get('CID', [])
    return ids[0] if ids else cid


def properties(cid):
    for smi in ['SMILES', 'IsomericSMILES']:            # PubChem renamed this field in 2025
        try:
            d = get(f'{BASE}/compound/cid/{cid}/property/{smi},MolecularFormula,'
                    f'MolecularWeight,HeavyAtomCount/JSON')
        except urllib.error.HTTPError:
            continue
        if d:
            p = d['PropertyTable']['Properties'][0]
            p['smiles'] = next(v for k, v in p.items() if 'SMILES' in k)
            return p
    raise RuntimeError(f'no properties for CID {cid}')


# Metals / metalloids that are part of a drug, not a counter-ion. If any appears in the
# SMILES, do NOT strip: cisplatin etc. are written as separate ions (N.[Cl-].[Cl-].[Pt+2]),
# so "keep the biggest fragment" would throw the platinum away.
METALS = {'Pt', 'As', 'Fe', 'Cu', 'Co', 'Ga', 'Gd', 'Ru', 'Au', 'Ag', 'Zn', 'Mn',
          'Ni', 'Pd', 'Hg', 'Sb', 'Bi', 'Li', 'Mg', 'Al', 'Ti', 'V', 'Cr', 'Mo'}


def strip_salt(p):
    """A salt's SMILES has several dot-separated fragments (drug . counter-ion). Keep the
    drug: the fragment with the most atoms. Single-molecule drugs and any structure
    containing a metal/metalloid (cisplatin, carboplatin, oxaliplatin, arsenic trioxide)
    are left exactly as PubChem gave them."""
    from rdkit import Chem
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    from rdkit.Chem.Descriptors import MolWt
    smi = p['smiles']
    if '.' not in smi:
        return p
    m = Chem.MolFromSmiles(smi)
    if m is not None and any(a.GetSymbol() in METALS for a in m.GetAtoms()):
        return p                                    # metal drug - never split
    frags = [f for f in (Chem.MolFromSmiles(x) for x in smi.split('.')) if f is not None]
    if len(frags) < 2:
        return p
    drug = max(frags, key=lambda f: f.GetNumHeavyAtoms())
    p = dict(p)
    p['smiles'] = Chem.MolToSmiles(drug)
    p['MolecularFormula'] = CalcMolFormula(drug)    # now the free drug's formula/weight
    p['MolecularWeight'] = f'{MolWt(drug):.2f}'
    p['salt_stripped'] = True
    return p


def rdkit_3d(smiles, seed=42):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    m = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ps = AllChem.ETKDGv3(); ps.randomSeed = seed
    if AllChem.EmbedMolecule(m, ps) != 0:              # large flexible molecules
        ps.useRandomCoords = True
        if AllChem.EmbedMolecule(m, ps) != 0:
            raise RuntimeError('3D embedding failed')
    AllChem.MMFFOptimizeMolecule(m, maxIters=2000)
    return Chem.MolToMolBlock(m) + '$$$$\n'


def formula_matches(smiles, pubchem_formula):
    from rdkit import Chem
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    return CalcMolFormula(Chem.MolFromSmiles(smiles)) == pubchem_formula


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', default='nsc_names.csv')
    ap.add_argument('--data', default='surface_dose_response.csv',
                    help='only fetch drugs that appear here; use --all for every NSC')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--out', default='structures')
    ap.add_argument('--fresh', action='store_true', help='ignore previous results and fetch everything')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    N = pd.read_csv(a.names)
    if not a.all:
        D = pd.read_csv(a.data)
        keep = set(D.drug_a_nsc.astype(int)) | set(D.drug_b_nsc.astype(int))
        N = N[N.nsc.isin(keep)]
    # Resume: keep drugs already fetched successfully, only (re)try the rest.
    out_csv = f'{a.out}/drug_structures.csv'
    done = {}
    if os.path.exists(out_csv) and not a.fresh:
        prev = pd.read_csv(out_csv)
        for _, p in prev.iterrows():
            ok = ('error' not in prev or pd.isna(p.get('error'))) and isinstance(p.get('file'), str) \
                 and os.path.exists(p['file'])
            if ok: done[int(p.nsc)] = p.to_dict()
        print(f'{len(done)} drugs already fetched - skipping them (use --fresh to redo all)')
    rows = []
    for _, r in N.iterrows():
        nsc, name = int(r.nsc), r['name']
        if nsc in done:
            rows.append(done[nsc]); continue
        row = {'nsc': nsc, 'name': name}
        try:
            cid, matched = find_cid(nsc, name)
            if cid is None: raise RuntimeError('not found in PubChem')
            pcid = parent_cid(cid)
            p = strip_salt(properties(pcid))      # tamoxifen citrate -> tamoxifen, etc.
            row.update(cid=cid, parent_cid=pcid, matched_on=matched, smiles=p['smiles'],
                       formula=p['MolecularFormula'], mol_weight=float(p['MolecularWeight']),
                       heavy_atoms=p.get('HeavyAtomCount'),
                       formula_check='ok' if formula_matches(p['smiles'], p['MolecularFormula'])
                       else 'MISMATCH - check by hand')
            sdf = get(f'{BASE}/compound/cid/{pcid}/record/SDF?record_type=3d', binary=True)
            if sdf:
                row['source_3d'] = 'pubchem'; sdf = sdf.decode()
            else:
                row['source_3d'] = 'rdkit'; sdf = rdkit_3d(p['smiles'])
            fn = f"{a.out}/{nsc}_{re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_')}.sdf"
            open(fn, 'w').write(sdf); row['file'] = fn
            print(f"ok   {name:35s} CID {pcid:<10} 3D from {row['source_3d']:7s} {row['formula_check']}")
        except Exception as e:
            row['error'] = str(e)[:200]
            print(f"FAIL {name:35s} {row['error']}")
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    failed = df[df.get('error', pd.Series(index=df.index, dtype=object)).notna()] if 'error' in df else df.iloc[0:0]
    print(f"\nwrote {out_csv}: {len(df) - len(failed)} of {len(df)} drugs have a structure")
    if len(failed):
        print(f"{len(failed)} failed ({', '.join(failed.name)}) - just run this again to retry only those")


if __name__ == '__main__':
    main()
