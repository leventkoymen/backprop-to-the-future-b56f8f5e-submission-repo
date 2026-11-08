// Molecule shapes + functional groups, precomputed from the molecule files by
// visual/scripts/functional-groups.py (RDKit). See that script for what each field means.
import raw from "@data/derived/molecules.json";
import { z } from "zod";

const Mol = z.looseObject({
  nsc: z.number().int(),
  name: z.string(),
  atoms: z.array(z.object({ el: z.string(), x: z.number(), y: z.number(), z: z.number() })),
  bonds: z.array(z.tuple([z.number(), z.number(), z.number()])),
  group: z.array(z.string().nullable()),
  groups: z.array(z.object({ id: z.string(), label: z.string(), count: z.number() })),
  donors: z.array(z.number()),
  acceptors: z.array(z.number()),
  aromatic: z.array(z.number()),
  source: z.string(),
});
const File = z.looseObject({ drugs: z.record(z.string(), Mol) });

export type MoleculeData = z.infer<typeof Mol> & { donorSet: Set<number>; acceptorSet: Set<number>; aromaticSet: Set<number> };

const parsed = File.safeParse(raw);
export const moleculeError = parsed.success ? null : "molecules.json could not be read";

export const molecules = new Map<number, MoleculeData>(
  parsed.success
    ? Object.values(parsed.data.drugs).map((m) => [
        m.nsc,
        { ...m, donorSet: new Set(m.donors), acceptorSet: new Set(m.acceptors), aromaticSet: new Set(m.aromatic) },
      ])
    : [],
);
