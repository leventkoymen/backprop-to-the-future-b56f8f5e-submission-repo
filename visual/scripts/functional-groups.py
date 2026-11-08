"""Builds data/derived/molecules.json for the 3D molecule view (tabs 2 and 2b).

For every drug in data/starter/drugs.csv it reads the molecule file and records:
  - atoms (element + 3D position) and bonds, so the app can draw the molecule
  - functional groups found with standard SMARTS chemistry patterns
  - atoms that COULD form bonds with a receptor (hydrogen-bond donors / acceptors,
    aromatic rings), using RDKit's built-in pharmacophore feature rules

These are properties of the molecule on its own. They are NOT measured contacts with
any receptor: the molecule files contain no receptor. The app labels them that way.

Run (needs RDKit: pip install rdkit):
    python3 scripts/functional-groups.py ../data/starter ../data/derived/molecules.json
"""
import csv
import json
import os
import sys

from rdkit import Chem, RDConfig
from rdkit.Chem import AllChem, ChemicalFeatures

# Checked in this order: an atom keeps the FIRST group that claims it
# (so an ester's oxygen counts as "ester", not "ether").
# Atoms marked ":1" are the group's own atoms (coloured); unmarked atoms are only context.
GROUPS = [
    ("phosphate", "Phosphate", "[PX4:1](=[O:1])([OX2,OX1-:1])[OX2,OX1-:1]"),
    ("sulfonyl", "Sulfonyl (SO2)", "[SX4:1](=[O:1])=[O:1]"),
    ("acid", "Carboxylic acid", "[CX3:1](=[O:1])[OX2H1,OX1-:1]"),
    ("ester", "Ester", "[#6][CX3:1](=[O:1])[OX2:1][#6]"),
    ("amide", "Amide", "[CX3:1](=[O:1])[NX3:1]"),
    ("ketone", "Ketone (C=O)", "[#6][CX3:1](=[O:1])[#6]"),
    ("aldehyde", "Aldehyde", "[CX3H1:1](=[O:1])[#6]"),
    ("hydroxyl", "Hydroxyl (OH)", "[OX2H:1]"),
    ("amine", "Amine (N)", "[NX3;!$(N[C,S]=[O,S]);!$(NS(=O)=O):1]"),
    ("ring_n", "Ring nitrogen", "[n:1]"),
    ("ether", "Ether (C-O-C)", "[#6][OX2:1][#6]"),
    ("halogen", "Halogen (F, Cl, Br)", "[F,Cl,Br,I:1]"),
    ("alkene", "C=C double bond", "[CX3:1]=[CX3:1]"),
    ("triple", "Triple bond", "[CX2:1]#[CX2,NX1:1]"),
]


def count_pieces(mol, atom_ids):
    """How many separate places in the molecule a group occurs (connected pieces)."""
    atom_ids, seen, pieces = set(atom_ids), set(), 0
    for start in atom_ids:
        if start in seen:
            continue
        pieces += 1
        stack = [start]
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            stack.extend(n.GetIdx() for n in mol.GetAtomWithIdx(i).GetNeighbors() if n.GetIdx() in atom_ids)
    return pieces


def load_mol(path, flat=False):
    """Read a molecule file. Keeps only the largest piece (drops salt counter-ions).
    For flat 2D files, generates a 3D shape with RDKit (ETKDG + MMFF clean-up)."""
    mol = Chem.MolFromMolFile(path, removeHs=False)
    if mol is None:
        raise ValueError(f"could not read {path}")
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())
    if flat:
        mol = Chem.AddHs(Chem.RemoveHs(mol))
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        if AllChem.EmbedMolecule(mol, params) != 0:
            raise ValueError(f"could not generate a 3D shape for {path}")
        AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
        return mol, "RDKit-generated 3D from PubChem 2D"
    text = open(path).read(600)
    return mol, ("RDKit-generated" if "RDKit" in text else "PubChem 3D conformer")


ORGANIC = {"C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I", "B"}
# PubChem's "parent" step strips the metal from platinum drugs, leaving a misleading
# organic fragment, so these are left out rather than shown wrong.
SKIP = {241240: "carboplatin: the PubChem record lost its platinum atom"}


def analyse(path, flat=False):
    mol, source = load_mol(path, flat)
    metals = {a.GetSymbol() for a in mol.GetAtoms()} - ORGANIC
    if metals:
        raise ValueError(f"contains {', '.join(sorted(metals))}: metal/inorganic drugs are not modelled")
    conf = mol.GetConformer()
    atoms = [
        {"el": a.GetSymbol(), "x": round(p.x, 3), "y": round(p.y, 3), "z": round(p.z, 3)}
        for a, p in ((a, conf.GetAtomPosition(a.GetIdx())) for a in mol.GetAtoms())
    ]
    bonds = [[b.GetBeginAtomIdx(), b.GetEndAtomIdx(), b.GetBondTypeAsDouble()] for b in mol.GetBonds()]

    group_of = [None] * mol.GetNumAtoms()
    found = []
    for gid, label, smarts in GROUPS:
        patt = Chem.MolFromSmarts(smarts)
        own = [a.GetIdx() for a in patt.GetAtoms() if a.GetAtomMapNum() == 1]
        claimed = set()
        for match in mol.GetSubstructMatches(patt):
            free = [match[k] for k in own if group_of[match[k]] is None]
            for i in free:
                group_of[i] = gid
                claimed.add(i)
        if claimed:
            found.append({"id": gid, "label": label, "count": count_pieces(mol, claimed)})

    # aromatic rings (pi-stacking surfaces), after the specific groups
    ring_atoms = {i for ring in mol.GetRingInfo().AtomRings() if all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring) for i in ring}
    n_rings = sum(1 for ring in mol.GetRingInfo().AtomRings() if all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring))
    for i in ring_atoms:
        if group_of[i] is None:
            group_of[i] = "aromatic"
    if n_rings:
        found.append({"id": "aromatic", "label": "Aromatic ring", "count": n_rings})

    # polar hydrogens (on O or N) take their heavy atom's group; C-H stays plain
    for a in mol.GetAtoms():
        if a.GetSymbol() == "H":
            heavy = a.GetNeighbors()[0]
            if heavy.GetSymbol() in ("O", "N"):
                group_of[a.GetIdx()] = group_of[heavy.GetIdx()]

    # atoms that could form bonds with a receptor (generic chemistry rules)
    factory = ChemicalFeatures.BuildFeatureFactory(os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef"))
    feats = {"donor": set(), "acceptor": set(), "aromatic": set()}
    for f in factory.GetFeaturesForMol(mol):
        fam = f.GetFamily()
        key = {"Donor": "donor", "Acceptor": "acceptor", "Aromatic": "aromatic"}.get(fam)
        if key:
            feats[key].update(f.GetAtomIds())

    heavy = sum(1 for a in mol.GetAtoms() if a.GetSymbol() != "H")
    return {
        "atoms": atoms,
        "bonds": bonds,
        "group": group_of,
        "groups": found,
        "donors": sorted(feats["donor"]),
        "acceptors": sorted(feats["acceptor"]),
        "aromatic": sorted(feats["aromatic"]),
        "heavy_atoms": heavy,
        "source": source,
    }


def main(starter_dir, out_path):
    out = {}

    def add(nsc, name, path, flat=False):
        out[nsc] = {"nsc": nsc, "name": name, **analyse(path, flat)}
        groups = ", ".join(f"{g['label']} x{g['count']}" for g in out[nsc]["groups"])
        print(f"{name:<34} {out[nsc]['heavy_atoms']:>3} heavy atoms | {out[nsc]['source']:<36} | {groups}")

    # 1. the 13 drugs from the 3D data pack (their files win)
    with open(os.path.join(starter_dir, "drugs.csv"), newline="") as fh:
        for row in csv.DictReader(fh):
            add(int(float(row["nsc"])), row["name"], os.path.join(starter_dir, row["structure_file"]))

    # 2. everything fetched from PubChem by fetch-molecules.py (if it has been run)
    lookup = os.path.join(starter_dir, "molecules", "pubchem_lookup.csv")
    if os.path.exists(lookup):
        with open(lookup, newline="") as fh:
            for row in csv.DictReader(fh):
                nsc = int(row["nsc"])
                if nsc in out or row["kind"] not in ("3d", "2d") or not row["file"]:
                    continue
                if nsc in SKIP:
                    print(f"SKIPPED {row['name']}: {SKIP[nsc]}")
                    continue
                try:
                    add(nsc, row["name"], os.path.join(starter_dir, "molecules", row["file"]), flat=row["kind"] == "2d")
                except (ValueError, OSError) as e:
                    print(f"SKIPPED {row['name']}: {e}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump({"_about": "Functional groups and possible bonding atoms, computed with RDKit from the molecule files. Properties of each molecule alone: NOT measured contacts with a receptor.", "drugs": out}, fh, separators=(",", ":"))
    print(f"wrote {out_path}: {len(out)} drugs")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: functional-groups.py <data/starter dir> <out.json>")
    main(sys.argv[1], sys.argv[2])
