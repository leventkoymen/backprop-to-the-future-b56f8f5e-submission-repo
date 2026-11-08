"""
Vendored from the lungpair pipeline so the API runs standalone.
Keep in sync with rank.py if the feature set changes.
"""
import numpy as np
import pandas as pd


def drug_marginal(train):
    """Average synergy each drug shows with its other partners. The additive baseline."""
    long = pd.concat([train[['a', 'mean']].rename(columns={'a': 'd'}),
                      train[['b', 'mean']].rename(columns={'b': 'd'})])
    return long.groupby('d')['mean'].mean()


def build_features(df, train, potency, transfer, use_transfer):
    """Features for df, estimated ONLY from train. Never pass the full set as train."""
    m = drug_marginal(train)
    fallback = train['mean'].mean()
    pot = potency.set_index('drug').potency
    pot_mean = pot.mean()

    X = pd.DataFrame(index=df.index)
    X['marg_a'] = df.a.map(m).fillna(fallback)
    X['marg_b'] = df.b.map(m).fillna(fallback)
    X['marg_sum'] = X.marg_a + X.marg_b
    X['marg_max'] = X[['marg_a', 'marg_b']].max(axis=1)
    X['marg_min'] = X[['marg_a', 'marg_b']].min(axis=1)
    X['pot_a'] = df.a.map(pot).fillna(pot_mean)
    X['pot_b'] = df.b.map(pot).fillna(pot_mean)
    X['pot_min'] = X[['pot_a', 'pot_b']].min(axis=1)     # the more potent of the two
    X['pot_sum'] = X.pot_a + X.pot_b

    if use_transfer:
        t = transfer.set_index(['a', 'b'])
        idx = pd.MultiIndex.from_arrays([df.a, df.b])
        for col in ['other_mean', 'other_hit', 'other_n']:
            X[col] = t[col].reindex(idx).values
        X[['other_mean', 'other_hit']] = X[['other_mean', 'other_hit']].fillna(0)
        X['other_n'] = X.other_n.fillna(0)
    return X.reset_index(drop=True)


def oof_features(train, potency, transfer, use_transfer, rng, folds=5):
    """Training features built out-of-fold, so no pair contributes to its own marginal."""
    parts = []
    order = rng.permutation(len(train))
    for f in np.array_split(order, folds):
        hold = train.iloc[f]
        rest = train.drop(train.index[f])
        parts.append(build_features(hold, rest, potency, transfer, use_transfer)
                     .set_index(hold.index))
    return pd.concat(parts).loc[train.index].reset_index(drop=True)
