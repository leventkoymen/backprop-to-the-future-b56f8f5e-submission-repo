"""
Download everything the project fetches at runtime, once, so a fresh clone
runs with no network.

Judges open this on their own laptop on conference wifi. Anything that
reaches out mid-demo is a demo that fails in front of them. Run this on a
machine with a connection, commit what it writes, and the repo is
self-contained.

    python vendor.py          # external CSVs + check structures
    python vendor.py --check  # report only, download nothing
"""
import os, sys, argparse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
EXT  = os.path.join(HERE, 'external')
MTL  = 'https://raw.githubusercontent.com/TOJSSE-iData/MTLSynergy/main/data/'
FILES = ['drugs.csv', 'cell_lines.csv', 'oneil_summary_idx.csv',
         'cell_line_features.csv']
STRUCT = os.path.join(HERE, 'structures', 'drug_structures.csv')


def check():
    missing = [f for f in FILES
               if not os.path.exists(os.path.join(EXT, 'mtl_' + f))]
    print(f'external/: {len(FILES)-len(missing)}/{len(FILES)} present'
          + (f'  missing: {", ".join(missing)}' if missing else ''))
    print(f'structures/drug_structures.csv: '
          f'{"present" if os.path.exists(STRUCT) else "MISSING — run fetch_structures.py --all"}')
    ok = not missing and os.path.exists(STRUCT)
    print('\nself-contained' if ok else
          '\nNOT self-contained — a fresh clone will try to download at runtime')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)

    os.makedirs(EXT, exist_ok=True)
    for f in FILES:
        p = os.path.join(EXT, 'mtl_' + f)
        if os.path.exists(p):
            print(f'  have {f}'); continue
        print(f'  downloading {f} ...', flush=True)
        try:
            urllib.request.urlretrieve(MTL + f, p)
        except Exception as e:
            print(f'    FAILED: {e}')
    print()
    check()
    print('\nNow commit external/ and structures/ so the repo needs no network.')


if __name__ == '__main__':
    main()
