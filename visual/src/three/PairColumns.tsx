import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { ThreeEvent } from "@react-three/fiber";
import { landscape, pairKey } from "../data/load";
import { colors, HALF, HEIGHT_SCALE, NEG_CLAMP } from "../theme";

export type ColorMode = "dark" | "hits" | "tier" | "replay";

/** Grid position of a pair: drug A index on x, drug B index on z. */
export function pairPosition(a: number, b: number): [number, number] {
  const ia = landscape.drugIndex.get(a) ?? 0;
  const ib = landscape.drugIndex.get(b) ?? 0;
  const [x, z] = ia < ib ? [ia, ib] : [ib, ia]; // upper triangle
  return [x - HALF, z - HALF];
}

export function columnHeight(mean: number) {
  return Math.max(mean, NEG_CLAMP) * HEIGHT_SCALE;
}

interface Props {
  mode: ColorMode;
  revealed?: Map<string, boolean>; // pairKey -> hit (Scene B)
  hovered: number | null;
  onHover: (index: number | null) => void;
  onSelect?: (index: number) => void;
}

export const STUB = 0.3; // height of an untested column in Scene B
const tmp = new THREE.Object3D();
const tmpColor = new THREE.Color();

/** All 5,228 measured pairs drawn as ONE InstancedMesh (one GPU draw call). */
export function PairColumns({ mode, revealed, hovered, onHover, onSelect }: Props) {
  const ref = useRef<THREE.InstancedMesh>(null!);
  const pairs = landscape.file.pairs;
  const geometry = useMemo(() => new THREE.BoxGeometry(0.72, 1, 0.72), []);

  // Positions and heights. In replay mode (Scene B) untested pairs are flat stubs:
  // the agent hasn't "bought" them, so the audience must not see their result either.
  useLayoutEffect(() => {
    const mesh = ref.current;
    pairs.forEach((p, i) => {
      const [x, z] = pairPosition(p.a, p.b);
      const hidden = mode === "replay" && !revealed?.has(pairKey(p.a, p.b));
      const h = hidden ? STUB : columnHeight(p.mean);
      tmp.position.set(x, h / 2, z);
      tmp.scale.set(1, Math.max(Math.abs(h), 0.05), 1);
      tmp.updateMatrix();
      mesh.setMatrixAt(i, tmp.matrix);
    });
    mesh.instanceMatrix.needsUpdate = true; // forgetting this = nothing redraws
    mesh.computeBoundingSphere(); // needed for hover picking to work
  }, [pairs, mode, revealed]);

  // Colours: recomputed whenever the mode, reveals or hover change.
  useLayoutEffect(() => {
    const mesh = ref.current;
    pairs.forEach((p, i) => {
      let c: string;
      if (i === hovered) c = colors.hover;
      else if (mode === "replay") {
        const r = revealed?.get(pairKey(p.a, p.b));
        c = r === undefined ? colors.unknown : r ? colors.revealedHit : colors.revealedMiss;
      } else if (mode === "tier" && p.tier) c = colors.tier[p.tier];
      else if (mode !== "dark" && p.hit) c = colors.hit;
      else c = p.mean < 0 ? colors.baseNegative : colors.base;
      mesh.setColorAt(i, tmpColor.set(c));
    });
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [pairs, mode, revealed, hovered]);

  const move = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    if (e.instanceId !== hovered) onHover(e.instanceId ?? null);
  };

  return (
    <instancedMesh
      ref={ref}
      args={[geometry, undefined, pairs.length]}
      onPointerMove={move}
      onPointerOut={() => onHover(null)}
      onClick={(e) => e.instanceId !== undefined && onSelect?.(e.instanceId)}
    >
      <meshStandardMaterial toneMapped={false} roughness={0.6} metalness={0.05} />
    </instancedMesh>
  );
}
