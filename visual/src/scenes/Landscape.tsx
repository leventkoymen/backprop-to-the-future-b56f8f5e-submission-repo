import { useMemo } from "react";
import { pairKey } from "../data/load";
import { Floor } from "../three/Floor";
import { PairColumns, type ColorMode } from "../three/PairColumns";
import { ProposedColumns } from "../three/ProposedColumns";
import type { ReplayView } from "../state/replay";

interface Props {
  mode: ColorMode;
  view?: ReplayView; // present in Scene B
  hovered: number | null;
  onHover: (i: number | null) => void;
  onSelect: (i: number) => void;
}

/** Scene A ("the haystack") and Scene B ("the agent at work") share this landscape. */
export function Landscape({ mode, view, hovered, onHover, onSelect }: Props) {
  const revealed = useMemo(
    () => (view ? new Map(view.revealed.map((r) => [pairKey(r.a, r.b), r.hit])) : undefined),
    [view],
  );
  const picks = useMemo(() => {
    if (!view?.current || !view.proposedKeys.length) return [];
    return view.current.propose.pairs;
  }, [view]);

  return (
    <group>
      <ambientLight intensity={0.55} />
      <directionalLight position={[60, 120, 40]} intensity={1.6} />
      <directionalLight position={[-80, 40, -60]} intensity={0.4} color="#a9c4e8" />
      <Floor />
      <PairColumns mode={mode} revealed={revealed} hovered={hovered} onHover={onHover} onSelect={onSelect} />
      {picks.length > 0 && <ProposedColumns picks={picks} />}
    </group>
  );
}
