import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import type { DoseGrid, DosePoint } from "../data/load";
import { colors } from "../theme";
import { Label } from "../three/Label";

// Scene C: one real experiment = one 3 x 3 dose grid (drug pair x cell line).
// Two views:
//   "growth":  violet = expected % growth if the drugs didn't interact, teal = observed % growth.
//              The vertical gap between them is the synergy.
//   "synergy": a single surface of synergy (expected - observed), floor = 0 = no interaction.
// Surfaces pass exactly through the 9 measured points: no smoothing, no invented values.
export type DoseView = "growth" | "synergy";

const SIZE = 40; // width of the dose floor in scene units
const Y_GROWTH = 0.16; // scene units per % growth
const Y_SYN = 0.12; // scene units per synergy point
const LOW = -110 * Y_GROWTH; // dose labels sit below the lowest possible growth (-100%)

const fmtConc = (c: number) => c.toExponential(0).replace("e-", "e−") + " M";
const gx = (i: number) => (i / 2 - 0.5) * SIZE; // dose index 0..2 -> x
const gz = (j: number) => (j / 2 - 0.5) * SIZE; // dose index 0..2 -> z

function surface(points: DosePoint[], height: (p: DosePoint) => number, colorOf?: (p: DosePoint) => THREE.Color) {
  const at = (i: number, j: number) => points.find((p) => p.ia === i && p.ib === j);
  const positions: number[] = [];
  const cols: number[] = [];
  for (let j = 0; j < 3; j++)
    for (let i = 0; i < 3; i++) {
      const p = at(i, j);
      positions.push(gx(i), p ? height(p) : 0, gz(j));
      if (colorOf) {
        const c = p ? colorOf(p) : new THREE.Color(colors.base);
        cols.push(c.r, c.g, c.b);
      }
    }
  const index: number[] = [];
  for (let j = 0; j < 2; j++)
    for (let i = 0; i < 2; i++) {
      const k = j * 3 + i;
      // only draw a cell when all 4 corners were measured
      if ([at(i, j), at(i + 1, j), at(i, j + 1), at(i + 1, j + 1)].every(Boolean)) index.push(k, k + 3, k + 1, k + 1, k + 3, k + 4);
    }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  if (colorOf) g.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
  g.setIndex(index);
  g.computeVertexNormals();
  return g;
}

const synColor = (s: number) => {
  // teal for synergy, blue for antagonism, grey near zero
  const t = Math.min(Math.abs(s) / 100, 1);
  return new THREE.Color(colors.base).lerp(new THREE.Color(s >= 0 ? colors.hit : colors.tier.T2), t);
};

export function DoseSurface({ grid, view }: { grid: DoseGrid; view: DoseView }) {
  const [hover, setHover] = useState<number | null>(null);
  useEffect(() => setHover(null), [grid.id, view]);

  // dose labels: the actual concentration at each grid index (ladders differ per experiment)
  const concA = useMemo(() => [0, 1, 2].map((i) => grid.points.find((p) => p.ia === i)?.concA), [grid]);
  const concB = useMemo(() => [0, 1, 2].map((j) => grid.points.find((p) => p.ib === j)?.concB), [grid]);

  const geo = useMemo(() => {
    if (view === "growth")
      return {
        main: surface(grid.points, (p) => p.observed * Y_GROWTH),
        ref: surface(grid.points, (p) => p.expected * Y_GROWTH),
      };
    return { main: surface(grid.points, (p) => p.synergy * Y_SYN, (p) => synColor(p.synergy)), ref: null };
  }, [grid, view]);

  const top = (p: DosePoint) => (view === "growth" ? p.observed * Y_GROWTH : p.synergy * Y_SYN);
  const bottom = (p: DosePoint) => (view === "growth" ? p.expected * Y_GROWTH : 0);

  const gaps = useMemo(() => {
    const pts: number[] = [];
    grid.points.forEach((p) => pts.push(gx(p.ia), bottom(p), gz(p.ib), gx(p.ia), top(p), gz(p.ib)));
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, [grid, view]);

  const h = hover !== null ? grid.points[hover] : null;
  const labelY = view === "growth" ? LOW : -100 * Y_SYN;

  return (
    <group key={`${grid.id}|${view}`}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[30, 60, 20]} intensity={1.4} />

      {/* reference plane at 0 */}
      <mesh rotation-x={-Math.PI / 2}>
        <planeGeometry args={[SIZE + 6, SIZE + 6]} />
        <meshBasicMaterial color={colors.grid} transparent opacity={0.35} side={THREE.DoubleSide} />
      </mesh>
      {view === "growth" ? (
        <>
          <Label position={[SIZE / 2 + 4, 0, -SIZE / 2]} className="axis-label small">0% growth (below = cells die)</Label>
          <Label position={[SIZE / 2 + 4, 100 * Y_GROWTH, -SIZE / 2]} className="axis-label small">100% (normal growth)</Label>
        </>
      ) : (
        <Label position={[SIZE / 2 + 4, 0, -SIZE / 2]} className="axis-label small">0 = no interaction (above = synergy)</Label>
      )}

      {geo.ref && (
        <mesh geometry={geo.ref}>
          <meshStandardMaterial color={colors.violet} transparent opacity={0.45} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
      )}
      <mesh geometry={geo.main}>
        {view === "growth" ? (
          <meshStandardMaterial color={colors.accent} transparent opacity={0.85} side={THREE.DoubleSide} flatShading />
        ) : (
          <meshStandardMaterial vertexColors transparent opacity={0.9} side={THREE.DoubleSide} flatShading />
        )}
      </mesh>
      <lineSegments geometry={gaps}>
        <lineBasicMaterial color="#ffffff" transparent opacity={0.7} />
      </lineSegments>

      {grid.points.map((p, i) => (
        <mesh
          key={i}
          position={[gx(p.ia), top(p), gz(p.ib)]}
          onPointerOver={(e) => (e.stopPropagation(), setHover(i))}
          onPointerOut={() => setHover(null)}
        >
          <sphereGeometry args={[i === hover ? 1.1 : 0.8, 16, 16]} />
          <meshStandardMaterial color={i === hover ? "#ffffff" : colors.accent} emissive={colors.accent} emissiveIntensity={0.4} />
        </mesh>
      ))}

      {concA.map((c, i) => c !== undefined && (
        <Label key={`a${i}`} position={[gx(i), labelY, SIZE / 2 + 4]} center className="axis-label small">{fmtConc(c)}</Label>
      ))}
      {concB.map((c, j) => c !== undefined && (
        <Label key={`b${j}`} position={[-SIZE / 2 - 6, labelY, gz(j)]} center className="axis-label small">{fmtConc(c)}</Label>
      ))}
      <Label position={[0, labelY, SIZE / 2 + 10]} center className="axis-label">{grid.drugA} dose →</Label>
      <Label position={[-SIZE / 2 - 18, labelY, 0]} center className="axis-label">{grid.drugB} dose →</Label>

      {h && (
        <Label position={[gx(h.ia), top(h) + 6, gz(h.ib)]} center className="hover-card compact">
          <div>{fmtConc(h.concA)} + {fmtConc(h.concB)}</div>
          <div>Observed growth <b>{h.observed.toFixed(0)}%</b></div>
          <div>Expected <b>{h.expected.toFixed(0)}%</b></div>
          <div>Synergy (expected − observed) <b>{h.synergy.toFixed(0)}</b></div>
        </Label>
      )}
    </group>
  );
}
