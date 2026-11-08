import { drugName, landscape, pairKey, type Run } from "../data/load";
import type { CompiledRun, ReplayState, ReplayView } from "../state/replay";
import { Term } from "./Term";
import { molecules } from "../data/molecules";

// 2b sidebar: a plain, working "next experiments" checklist for a lab user.
// Differences from the judges' AgentPanel: each pair can be unticked before approval,
// rejected pairs are never tested or revealed, and the batch can be downloaded as CSV.

interface Props {
  runs: Run[];
  runName: string;
  onRun: (name: string) => void;
  compiled: CompiledRun;
  run: Run;
  state: ReplayState;
  view: ReplayView; // already filtered for rejected pairs (see App)
  unticked: Set<string>; // pairs the user has unticked in the current batch
  onToggle: (key: string) => void;
  rejected: Set<string>; // pairs the user rejected in earlier batches
  onApprove: () => void;
  onNext: () => void;
  onReset: () => void;
  onMolecules?: (a: number, b: number) => void;
}

const hitRate = landscape.hits / landscape.file.pairs.length;

export function LabPanel({ runs, runName, onRun, compiled, run, state, view, unticked, onToggle, rejected, onApprove, onNext, onReset, onMolecules }: Props) {
  const total = compiled.start?.budget_total ?? 0;
  const unit = compiled.start?.budget_unit ?? "experiments";
  const isDemo = runName === "demo" || compiled.start?.label?.startsWith("DEMO");
  const used = view.revealed.length;
  const left = rejected.size ? total - used : (view.budgetLeft ?? total);
  const hits = rejected.size ? view.revealed.filter((r) => r.hit).length : view.hitsTotal;
  const random = rejected.size ? used * hitRate : view.randomTotal;
  const batch = view.current?.propose.pairs ?? [];
  const selected = batch.filter((p) => !unticked.has(pairKey(p.a, p.b))).length;
  // Results only exist on screen AFTER the user approves (never while the batch is waiting).
  const results = new Map(
    state.phase === "revealed" || state.phase === "finished" ? (view.current?.reveal?.results ?? []).map((r) => [pairKey(r.a, r.b), r]) : [],
  );

  const download = () => {
    const rows = [["drug_a", "drug_b", "nsc_a", "nsc_b", "status", "reason"]];
    batch.forEach((p) => {
      const k = pairKey(p.a, p.b);
      const status = state.phase === "proposed" ? (unticked.has(k) ? "unticked" : "selected") : rejected.has(k) ? "rejected" : "approved";
      rows.push([drugName(p.a, p.drug_a), drugName(p.b, p.drug_b), String(p.a), String(p.b), status, p.reason]);
    });
    const csv = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = `batch-${view.current?.round ?? 0}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <aside className="lab">
      <header className="lab-head">
        <div>
          <div className="lab-title">Next experiments</div>
          {isDemo && <div className="lab-note">Demo data. Picks are from the shortlist, results are real measurements.</div>}
        </div>
        <select value={runName} onChange={(e) => onRun(e.target.value)} aria-label="Agent run">
          {runs.map((r) => (
            <option key={r.name} value={r.name}>{r.name}</option>
          ))}
        </select>
      </header>
      {run.errors.length > 0 && <div className="lab-error">{run.errors.length} line(s) in this log couldn't be read.</div>}

      <section className="lab-budget">
        <div className="lab-row">
          <span><Term id="budget">Budget</Term></span>
          <span><b>{left}</b> of {total} {unit} left</span>
        </div>
        <div className="bar"><div style={{ width: `${total ? (left / total) * 100 : 0}%` }} /></div>
        <div className="lab-row small">
          <span><Term id="hit">Hits</Term> so far: <b>{hits}</b></span>
          <span><Term id="random">Random</Term> would find ~{random.toFixed(1)}</span>
        </div>
      </section>

      <section className="lab-batch">
        <div className="lab-row">
          <b>{view.current ? `Batch ${view.current.round} of ${compiled.rounds.length}` : "No batch yet"}</b>
          {batch.length > 0 && <button className="link" onClick={download}>Download CSV</button>}
        </div>

        {state.phase === "ready" && <p className="lab-empty">Press <b>Get first batch</b> to see what the agent suggests testing.</p>}

        {batch.length > 0 && (
          <ul className="lab-list">
            {batch.map((p) => {
              const k = pairKey(p.a, p.b);
              const r = results.get(k);
              const wasRejected = state.phase !== "proposed" && rejected.has(k);
              return (
                <li key={k} className={wasRejected ? "rejected" : ""}>
                  {state.phase === "proposed" ? (
                    <input type="checkbox" checked={!unticked.has(k)} onChange={() => onToggle(k)} aria-label={`Include ${drugName(p.a, p.drug_a)} and ${drugName(p.b, p.drug_b)}`} />
                  ) : (
                    <span className="lab-tick">{wasRejected ? "–" : "✓"}</span>
                  )}
                  <div className="lab-pair">
                    <div className="lab-names">{drugName(p.a, p.drug_a)} + {drugName(p.b, p.drug_b)}</div>
                    <div className="lab-reason">{p.reason}</div>
                    {onMolecules && (molecules.has(p.a) || molecules.has(p.b)) && (
                      <button className="link small" onClick={() => onMolecules(p.a, p.b)}>View molecules</button>
                    )}
                  </div>
                  <div className="lab-result">
                    {wasRejected ? <span className="tag grey">Not tested</span> : r ? <span className={r.hit ? "tag green" : "tag grey"}>{r.hit ? "Hit" : "No"} · {r.score.toFixed(0)}</span> : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {rejected.size > 0 && <p className="lab-note">You've rejected {rejected.size} pair(s). In this replay the agent's later batches don't change; a live agent would adapt.</p>}
      </section>

      <footer className="lab-actions">
        {state.phase === "ready" && <button className="lab-primary" onClick={onNext}>Get first batch</button>}
        {state.phase === "proposed" && (
          <button className="lab-primary" onClick={onApprove}>
            {selected ? `Test ${selected} selected` : "Reject whole batch"}
          </button>
        )}
        {state.phase === "revealed" && <button className="lab-primary" onClick={onNext}>Next batch</button>}
        {state.phase === "finished" && <span className="lab-note">Budget used up. Run complete.</span>}
        <button className="link" onClick={onReset}>Start over</button>
      </footer>
    </aside>
  );
}
