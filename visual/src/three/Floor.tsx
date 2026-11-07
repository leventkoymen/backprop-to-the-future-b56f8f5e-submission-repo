import { colors, GRID } from "../theme";

/** Dark floor at score 0 with grid lines. Axis meaning is explained in the legend. */
export function Floor() {
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position-y={-0.02}>
        <planeGeometry args={[GRID + 2, GRID + 2]} />
        <meshStandardMaterial color={colors.floor} transparent opacity={0.85} />
      </mesh>
      <gridHelper args={[GRID + 2, 21, colors.grid, colors.grid]} position-y={0} />
    </group>
  );
}
