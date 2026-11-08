import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import type { MoleculeData } from "../data/molecules";

// Ball-and-stick drawing of one molecule. Colours come from the functional group
// (or the bonding role) of each atom; everything else is plain grey.
export type MolMode = "groups" | "bonding";

export const groupColors: Record<string, string> = {
  phosphate: "#ea580c",
  sulfonyl: "#ca8a04",
  acid: "#be123c",
  ester: "#fb923c",
  amide: "#c026d3",
  ketone: "#ef4444",
  aldehyde: "#ef4444",
  hydroxyl: "#f472b6",
  amine: "#2563eb",
  ring_n: "#0d9488",
  ether: "#a16207",
  halogen: "#16a34a",
  alkene: "#38bdf8",
  triple: "#38bdf8",
  aromatic: "#8b5cf6",
};
export const bondingColors = { donor: "#2563eb", acceptor: "#ef4444", aromatic: "#f59e0b" };

const PLAIN: Record<string, string> = { C: "#8b909c", H: "#e5e5e5" };
const RADIUS: Record<string, number> = { H: 0.22, C: 0.36, N: 0.36, O: 0.36, S: 0.45, P: 0.45, F: 0.34, Cl: 0.42, Br: 0.46 };

function atomColor(mol: MoleculeData, i: number, mode: MolMode, focus: string | null): { color: string; dim: boolean } {
  if (mode === "bonding") {
    const role = mol.donorSet.has(i) ? "donor" : mol.acceptorSet.has(i) ? "acceptor" : mol.aromaticSet.has(i) ? "aromatic" : null;
    if (role) return { color: bondingColors[role], dim: !!focus && focus !== role };
    return { color: PLAIN[mol.atoms[i].el] ?? "#b9bcc6", dim: !!focus };
  }
  const g = mol.group[i];
  if (g) return { color: groupColors[g] ?? "#999", dim: !!focus && focus !== g };
  return { color: PLAIN[mol.atoms[i].el] ?? "#b9bcc6", dim: !!focus };
}

function Molecule({ mol, mode, focus }: { mol: MoleculeData; mode: MolMode; focus: string | null }) {
  // centre the molecule on the origin
  const { pts, centre } = useMemo(() => {
    const pts = mol.atoms.map((a) => new THREE.Vector3(a.x, a.y, a.z));
    const centre = pts.reduce((c, p) => c.add(p), new THREE.Vector3()).divideScalar(pts.length);
    return { pts: pts.map((p) => p.clone().sub(centre)), centre };
  }, [mol]);
  void centre;

  const bonds = useMemo(
    () =>
      mol.bonds.map(([i, j, order]) => {
        const a = pts[i], b = pts[j];
        const mid = a.clone().add(b).multiplyScalar(0.5);
        const len = a.distanceTo(b);
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
        return { i, j, mid, len, q, r: order >= 2 ? 0.13 : 0.09 };
      }),
    [mol, pts],
  );

  return (
    <group>
      {pts.map((p, i) => {
        const { color, dim } = atomColor(mol, i, mode, focus);
        return (
          <mesh key={i} position={p}>
            <sphereGeometry args={[RADIUS[mol.atoms[i].el] ?? 0.4, 20, 20]} />
            <meshStandardMaterial color={color} transparent opacity={dim ? 0.15 : 1} roughness={0.45} />
          </mesh>
        );
      })}
      {bonds.map((b, k) => {
        const dim = !!focus && (atomColor(mol, b.i, mode, focus).dim || atomColor(mol, b.j, mode, focus).dim);
        return (
          <mesh key={k} position={b.mid} quaternion={b.q}>
            <cylinderGeometry args={[b.r, b.r, b.len, 10]} />
            <meshStandardMaterial color="#9aa0ad" transparent opacity={dim ? 0.12 : 0.9} />
          </mesh>
        );
      })}
    </group>
  );
}

/** A small self-contained 3D canvas: drag to rotate, scroll to zoom, slowly auto-rotates. */
export function MoleculeView({ mol, mode, focus, light }: { mol: MoleculeData; mode: MolMode; focus: string | null; light?: boolean }) {
  const radius = useMemo(() => {
    const xs = mol.atoms.map((a) => a.x), ys = mol.atoms.map((a) => a.y), zs = mol.atoms.map((a) => a.z);
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), Math.max(...zs) - Math.min(...zs));
    return span / 2 + 1;
  }, [mol]);
  return (
    <Canvas key={mol.nsc} camera={{ position: [0, 0, radius * 2.6], fov: 40 }} dpr={[1, 2]}>
      <color attach="background" args={[light ? "#ffffff" : "#0d1724"]} />
      <ambientLight intensity={0.75} />
      <directionalLight position={[5, 8, 10]} intensity={1.3} />
      <Molecule mol={mol} mode={mode} focus={focus} />
      <OrbitControls autoRotate autoRotateSpeed={1.2} enablePan={false} />
    </Canvas>
  );
}
