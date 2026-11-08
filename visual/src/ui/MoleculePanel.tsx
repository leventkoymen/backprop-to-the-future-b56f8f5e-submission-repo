import { useEffect, useState } from "react";
import { drugInfo, drugName } from "../data/load";
import { molecules } from "../data/molecules";
import { bondingColors, groupColors, MoleculeView, type MolMode } from "../three/MoleculeView";

// Opened from a suggested pair in tab 2 / 2b: the two drugs' 3D molecules with their
// chemical groups highlighted, plus a short drug card from drugs.csv.

const fmtMolar = (s: string) => {
  const v = Number(s);
  if (!s.trim() || !Number.isFinite(v) || v <= 0) return null;
  return v < 1e-6 ? `${+(v * 1e9).toPrecision(2)} nM` : `${+(v * 1e6).toPrecision(2)} µM`;
};

export function MoleculePanel({ a, b, onClose, light }: { a: number; b: number; onClose: () => void; light?: boolean }) {
  const [which, setWhich] = useState<number>(molecules.has(a) || !molecules.has(b) ? a : b);
  const [mode, setMode] = useState<MolMode>("groups");
  const [focus, setFocus] = useState<string | null>(null);
  useEffect(() => (setWhich(molecules.has(a) || !molecules.has(b) ? a : b), setFocus(null)), [a, b]);
  useEffect(() => setFocus(null), [which, mode]);

  const mol = molecules.get(which);
  const info = drugInfo.get(which);
  const legend =
    mode === "groups"
      ? (mol?.groups ?? []).map((g) => ({ id: g.id, label: `${g.label}${g.count > 1 ? ` ×${g.count}` : ""}`, color: groupColors[g.id] }))
      : [
          { id: "donor", label: "Can donate a hydrogen bond (H on N or O)", color: bondingColors.donor },
          { id: "acceptor", label: "Can accept a hydrogen bond (N or O)", color: bondingColors.acceptor },
          { id: "aromatic", label: "Flat ring: can stack against rings in a protein", color: bondingColors.aromatic },
        ];

  return (
    <aside className={light ? "mol mol-light" : "mol"}>
      <div className="mol-head">
        <div className="mol-tabs">
          {[a, b].map((n) => (
            <button key={n} className={n === which ? "on" : ""} onClick={() => setWhich(n)}>
              {drugName(n)}
            </button>
          ))}
        </div>
        <button className="link" onClick={onClose} aria-label="Close molecule view">Close</button>
      </div>

      {mol ? (
        <>
          <div className="mol-canvas">
            <MoleculeView mol={mol} mode={mode} focus={focus} light={light} />
          </div>
          <div className="mol-modes">
            <button className={mode === "groups" ? "on" : ""} onClick={() => setMode("groups")}>Chemical groups</button>
            <button className={mode === "bonding" ? "on" : ""} onClick={() => setMode("bonding")}>Could bond to a receptor</button>
          </div>
          <ul className="mol-legend">
            {legend.map((l) => (
              <li key={l.id}>
                <button className={focus === l.id ? "on" : ""} onClick={() => setFocus((f) => (f === l.id ? null : l.id))}>
                  <i style={{ background: l.color }} /> {l.label}
                </button>
              </li>
            ))}
          </ul>
          <p className="mol-caption">
            {mode === "groups"
              ? "Groups found in the molecule itself (computed with RDKit). Click one to highlight it."
              : "Atoms that could form bonds with a receptor, by standard chemistry rules. This is not a measured picture of how the drug binds its target."}
          </p>
        </>
      ) : (
        <p className="mol-empty">No 3D structure for {drugName(which)}. Platinum and arsenic drugs, and bleomycin (too large and flexible), are not modelled.</p>
      )}

      {info ? (
        <dl className="mol-card">
          <dt>Main target</dt>
          <dd>{info.primary_target || "–"} <span className="mol-dim">({info.mechanism_class})</span></dd>
          <dt>How it works</dt>
          <dd>
            {info.how_it_works}
            <div className="mol-dim small">AI-written summary, checked against standard pharmacology.</div>
          </dd>
          <dt>Given as</dt>
          <dd>{info.route}, {info.standard_dose}</dd>
          <dt>Peak blood level</dt>
          <dd>{fmtMolar(info.cmax_molar) ?? "No reliable figure found"}</dd>
        </dl>
      ) : (
        <p className="mol-empty">Target and dosing details are only available for the 13 drugs in the dose-response data.</p>
      )}
      {mol && <p className="mol-dim small">Structure: {mol.source}. Shape only, not where it sits in the tumour.</p>}
    </aside>
  );
}
