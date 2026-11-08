"""Download a 3D structure from PubChem for every drug in pairs_3d.json.

Run once on a computer with normal internet (no extra packages needed):
    cd visual
    python3 scripts/fetch-molecules.py

It writes into data/starter/molecules/:
    <nsc>_<name>.sdf        3D structure from PubChem (when PubChem has one)
    2d/<nsc>_<name>.sdf     flat 2D structure (PubChem has no 3D for very large or
                            flexible molecules, or for salts); a 3D shape is then
                            generated from it with RDKit in a later step
    pubchem_lookup.csv      what was found for each drug and how, to check by eye

Files already in molecules/ (the 13 from the 3D data pack) are kept, not replaced.
Each drug is looked up by its NSC number first (unambiguous), then by name.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data", "starter"))
OUT = os.path.join(DATA, "molecules")


def get(url, retries=3):
    """GET with polite pacing (PubChem asks for <= 5 requests/second). None on 404.

    Uses the system `curl` (on a Mac it trusts the same certificates as Safari, which
    matters on networks that inspect HTTPS); falls back to Python if curl is missing.
    Certificate checks always stay on.
    """
    for attempt in range(retries):
        time.sleep(0.3)
        if shutil.which("curl"):
            p = subprocess.run(
                ["curl", "-sS", "-L", "-m", "30", "-A", "lungpair-fetch/1.0", "-w", "\n%{http_code}", url],
                capture_output=True, text=True,
            )
            if p.returncode != 0:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                raise urllib.error.URLError(p.stderr.strip() or f"curl exit {p.returncode}")
            body, _, code = p.stdout.rpartition("\n")
            if code in ("400", "404"):
                return None
            if code == "503" and attempt < retries - 1:
                time.sleep(2 + attempt * 2)
                continue
            if code != "200":
                raise urllib.error.URLError(f"HTTP {code} for {url}")
            return body
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lungpair-fetch/1.0"}), timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            if e.code == 503 and attempt < retries - 1:
                time.sleep(2 + attempt * 2)
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise
    return None


def cids_from(text):
    try:
        return json.loads(text)["IdentifierList"]["CID"] if text else []
    except (KeyError, ValueError):
        # substance lookups return InformationList
        try:
            out = []
            for info in json.loads(text)["InformationList"]["Information"]:
                out += info.get("CID", [])
            return out
        except (KeyError, ValueError):
            return []


def find_cid(nsc, name):
    tries = [
        ("NSC number (NCI deposit)", f"{API}/substance/sourceid/DTP.NCI/{nsc}/cids/JSON"),
        ("NSC synonym", f"{API}/compound/name/{urllib.parse.quote(f'NSC{nsc}')}/cids/JSON"),
        ("drug name", f"{API}/compound/name/{urllib.parse.quote(name)}/cids/JSON"),
    ]
    for how, url in tries:
        cids = cids_from(get(url))
        if cids:
            return cids[0], how
    return None, "not found"


def parent_of(cid):
    """The active part of a salt (e.g. vinblastine for vinblastine sulfate)."""
    cids = cids_from(get(f"{API}/compound/cid/{cid}/cids/JSON?cids_type=parent"))
    return cids[0] if cids else cid


def title_of(cid):
    t = get(f"{API}/compound/cid/{cid}/property/Title/JSON")
    try:
        return json.loads(t)["PropertyTable"]["Properties"][0].get("Title", "")
    except (TypeError, KeyError, ValueError, IndexError):
        return ""


def safe(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:60]


def main():
    drugs = json.load(open(os.path.join(DATA, "pairs_3d.json")))["drugs"]
    os.makedirs(os.path.join(OUT, "2d"), exist_ok=True)
    have = {int(f.split("_")[0]) for f in os.listdir(OUT) if f.endswith(".sdf") and f.split("_")[0].isdigit()}
    rows = []
    for i, d in enumerate(drugs, 1):
        nsc, name = d["nsc"], d["name"]
        tag = f"[{i:>3}/{len(drugs)}] {name} (NSC {nsc})"
        if nsc in have:
            print(f"{tag}: already have it, kept")
            rows.append({"nsc": nsc, "name": name, "cid": "", "pubchem_title": "", "found_by": "3D data pack", "kind": "3d (pack)", "file": ""})
            continue
        cid, how = find_cid(nsc, name)
        if not cid:
            print(f"{tag}: NOT FOUND")
            rows.append({"nsc": nsc, "name": name, "cid": "", "pubchem_title": "", "found_by": how, "kind": "missing", "file": ""})
            continue
        pcid = parent_of(cid)
        title = title_of(pcid)
        fname = f"{nsc}_{safe(name)}.sdf"
        sdf3d = get(f"{API}/compound/cid/{pcid}/SDF?record_type=3d")
        if sdf3d:
            open(os.path.join(OUT, fname), "w").write(sdf3d)
            kind, path = "3d", fname
        else:
            sdf2d = get(f"{API}/compound/cid/{pcid}/SDF")
            if not sdf2d:
                print(f"{tag}: found CID {pcid} but no structure file")
                rows.append({"nsc": nsc, "name": name, "cid": pcid, "pubchem_title": title, "found_by": how, "kind": "missing", "file": ""})
                continue
            open(os.path.join(OUT, "2d", fname), "w").write(sdf2d)
            kind, path = "2d", f"2d/{fname}"
        print(f"{tag}: CID {pcid} '{title}' via {how} -> {kind}")
        rows.append({"nsc": nsc, "name": name, "cid": pcid, "pubchem_title": title, "found_by": how, "kind": kind, "file": path})

    with open(os.path.join(OUT, "pubchem_lookup.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["nsc", "name", "cid", "pubchem_title", "found_by", "kind", "file"])
        w.writeheader()
        w.writerows(rows)
    n = {k: sum(r["kind"].startswith(k) for r in rows) for k in ("3d", "2d", "missing")}
    print(f"\nDone: {n['3d']} with 3D, {n['2d']} 2D-only (3D generated in the next step), {n['missing']} not found.")
    print(f"Details: {os.path.join(OUT, 'pubchem_lookup.csv')}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach PubChem ({e}). Check your internet connection and try again.")
