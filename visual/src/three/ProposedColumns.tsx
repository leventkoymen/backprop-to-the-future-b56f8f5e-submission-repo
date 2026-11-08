import { Label } from "./Label";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { pairKey } from "../data/load";
import { colors } from "../theme";
import { pairPosition, STUB } from "./PairColumns";

/** The agent's current picks: sand columns that rise out of the floor, awaiting approval. */
export function ProposedColumns({ picks }: { picks: { a: number; b: number; drug_a: string; drug_b: string }[] }) {
  return (
    <group>
      {picks.map((p, i) => (
        <RisingColumn key={`${pairKey(p.a, p.b)}`} pick={p} delay={i * 0.12} label={i + 1} />
      ))}
    </group>
  );
}

function RisingColumn({ pick, delay, label }: { pick: { a: number; b: number }; delay: number; label: number }) {
  const ref = useRef<THREE.Mesh>(null!);
  const start = useRef<number | null>(null);
  const [x, z] = pairPosition(pick.a, pick.b);
  // Height shown while proposed is a fixed "candidate" marker, NOT the true result
  // (the result is only revealed after approval).
  const markerH = 14;
  const base = STUB;

  useFrame(({ clock }) => {
    if (start.current === null) start.current = clock.elapsedTime;
    const t = Math.min(Math.max((clock.elapsedTime - start.current - delay) / 0.7, 0), 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const h = Math.max(markerH * eased, 0.01);
    ref.current.scale.y = h;
    ref.current.position.y = base + h / 2;
  });

  return (
    <group position={[x, 0, z]}>
      <mesh ref={ref}>
        <boxGeometry args={[1.3, 1, 1.3]} />
        <meshStandardMaterial color={colors.proposed} emissive={colors.proposed} emissiveIntensity={0.6} transparent opacity={0.85} toneMapped={false} />
      </mesh>
      <Label position={[0, base + markerH + 3, 0]} center className="pick-tag">
        {label}
      </Label>
    </group>
  );
}
