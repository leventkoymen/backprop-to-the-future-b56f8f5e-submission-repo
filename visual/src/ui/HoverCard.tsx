import { dose, drugName, landscape, pairKey } from "../data/load";

/** Card for the hovered/selected pair: names, measured score, share of lung lines hit. */
export function HoverCard({ index, revealedOnly }: { index: number | null; revealedOnly?: boolean }) {
  if (index === null) return null;
  const p = landscape.file.pairs[index];
  return (
    <div className="hover-card panel">
      <div className="card-title">
        {drugName(p.a, p.drug_a)} <span className="plus">+</span> {drugName(p.b, p.drug_b)}
      </div>
      {revealedOnly ? (
        <div className="muted">Result hidden until the agent tests this pair.</div>
      ) : (
        <>
          <Row k="Mean ComboScore" v={p.mean.toFixed(1)} />
          <Row k="Real hit (mean > 50)" v={p.hit ? "Yes" : "No"} />
          <Row k="Lung lines where it worked" v={`${Math.round(p.hit_rate * 100)}% of ${p.n_lines}`} />
          {p.tier && <Row k="Evidence tier" v={p.tier} />}
          {dose.pairs.has(pairKey(p.a, p.b)) && <div className="small accent-text">Dose-response grids available: click, then press 3</div>}
        </>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="row">
      <span className="muted">{k}</span>
      <b>{v}</b>
    </div>
  );
}
