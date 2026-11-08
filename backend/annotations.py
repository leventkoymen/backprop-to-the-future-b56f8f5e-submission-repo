"""
Loads the Gemini annotations, if they exist, and attaches them to API
responses.

This module is deliberately inert when the annotation files are absent: the
API must keep working with no Gemini dependency at all. The annotations are
context around the prediction, never part of it.

Every annotation carries the agreement fraction from self-consistency
sampling and a source field naming the model. A consumer can filter on
agreement; nothing here is presented as measured fact.
"""

import os, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ANN  = os.path.join(HERE, 'annotations')

DRUGS = {}
PAIRS = {}
MODEL_NAME = None
MIN_AGREEMENT = float(os.environ.get('ANNOTATION_MIN_AGREEMENT', '0.6'))


def load():
    """Read the annotation CSVs. Safe to call when they don't exist."""
    global DRUGS, PAIRS, MODEL_NAME
    dp = os.path.join(ANN, 'drug_annotations.csv')
    pp = os.path.join(ANN, 'pair_annotations.csv')

    if os.path.exists(dp):
        d = pd.read_csv(dp)
        DRUGS = {int(r.nsc): {
            'target': r.primary_target,
            'mechanism_class': r.mechanism_class,
            'used_in_nsclc': bool(r.used_in_nsclc),
            'note': r.one_line,
            'agreement': float(r.agreement),
        } for r in d.itertuples()}

    if os.path.exists(pp):
        p = pd.read_csv(pp)
        PAIRS = {(int(r.a), int(r.b)): {
            'rationale_type': r.rationale_type,
            'rationale': r.rationale,
            'known_clinical_use': bool(r.known_clinical_use),
            'agreement': float(r.agreement),
        } for r in p.itertuples()}

    MODEL_NAME = os.environ.get('GEMINI_MODEL', 'gemini-flash-latest')
    return len(DRUGS), len(PAIRS)


def _stamp(d):
    """Mark where this came from, so it is never mistaken for a measurement."""
    out = dict(d)
    out['source'] = f'{MODEL_NAME} (self-consistency over 5 samples)'
    out['is_measurement'] = False
    if out.get('agreement', 1.0) < MIN_AGREEMENT:
        out['low_confidence'] = True
    return out


def for_drug(nsc):
    d = DRUGS.get(int(nsc))
    return _stamp(d) if d else None


def for_pair(a, b):
    lo, hi = min(int(a), int(b)), max(int(a), int(b))
    p = PAIRS.get((lo, hi))
    if not p:
        return None
    out = _stamp(p)
    da, db = DRUGS.get(lo), DRUGS.get(hi)
    if da: out['drug_a_target'] = da['target']
    if db: out['drug_b_target'] = db['target']
    return out


def available():
    return bool(DRUGS or PAIRS)


# ---------------------------------------------------------------- extras
# Functional groups for the 3D viewer, and the pipeline provenance trail.
# Both are inert when their files are absent.

FGROUPS = {}
SMARTS = {}
REACH = {}


def load_extras():
    """Functional groups, the SMARTS library and dose reachability."""
    global FGROUPS, SMARTS, REACH
    fp = os.path.join(ANN, 'functional_groups.csv')
    if os.path.exists(fp):
        d = pd.read_csv(fp)
        FGROUPS = {int(r.nsc): {
            'groups': [g for g in str(r.groups_present).split('|') if g],
            'key_group': r.key_group,
            'why_it_matters': r.why_it_matters,
            'receptor_interaction': r.receptor_interaction,
            'agreement': float(r.agreement),
            'smiles': r.smiles,
        } for r in d.itertuples()}
    try:
        from functional_groups import GROUPS as G
        SMARTS = dict(G)
    except Exception:
        SMARTS = {}

    rp = os.path.join(HERE, 'reachability_by_pair.csv')
    if not os.path.exists(rp):
        rp = os.path.join(HERE, 'merged', 'dose_reachability.csv')
    if os.path.exists(rp):
        d = pd.read_csv(rp)
        for r in d.itertuples():
            REACH[(str(r.drug_a), str(r.drug_b))] = {
                'peak_synergy': float(r.peak_synergy),
                'peak_reachable': r.peak_reachable,
                'share_of_grid_reachable': (None if pd.isna(r.share_of_grid_reachable)
                                            else float(r.share_of_grid_reachable)),
                'share_reachable_unbound': (None if pd.isna(r.share_reachable_unbound)
                                            else float(r.share_reachable_unbound)),
                'flags': '' if pd.isna(r.flags) else str(r.flags),
            }
    return len(FGROUPS), len(REACH)


def structure_for(nsc):
    """Functional groups plus the SMARTS the frontend needs to highlight them.

    The SMARTS are from a fixed library, not generated: the viewer highlights
    what pattern matching finds, and the model only supplies the explanation.
    """
    f = FGROUPS.get(int(nsc))
    if not f:
        return None
    return {
        'smiles': f['smiles'],
        'functional_groups': [{'name': g, 'smarts': SMARTS.get(g)}
                              for g in f['groups'] if SMARTS.get(g)],
        'key_group': f['key_group'],
        'key_group_smarts': SMARTS.get(f['key_group']),
        'why_it_matters': f['why_it_matters'],
        'receptor_interaction': f['receptor_interaction'],
        'explanation_agreement': f['agreement'],
        'explanation_source': f'{MODEL_NAME} — highlighting is pattern-matched, '
                              f'not model-generated',
        'is_measurement': False,
    }


def reach_for(name_a, name_b):
    return REACH.get((name_a, name_b)) or REACH.get((name_b, name_a))
