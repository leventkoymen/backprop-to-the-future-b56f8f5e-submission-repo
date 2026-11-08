import { drugName, type Run } from "../data/load";
import { molecules } from "../data/molecules";
import type { CompiledRun, ReplayState, ReplayView } from "../state/replay";

interface Props {
  runs: Run[];
  runName: string;
  onRun: (name: string) => void;
  compiled: CompiledRun;
  run: Run;
  state: ReplayState;
  view: ReplayView;
  onApprove: () => void;
  onNext: () => void;
  onReset: () => void;
  onMolecules?: (a: number, b: number) => void;
}

/** Scene B side panel: budget, hits vs random, the picks with reasons, and the human Approve step. */
export function AgentPanel({ runs, runName, onRun, compiled, run, state, view, onApprove, onNext, onReset, onMolecules }: Props) {
  const isDemo = runName === "demo" || compiled.start?.label?.startsWith("DEMO");
  const unit = compiled.start?.budget_unit ?? "experiments";
  const total = compiled.start?.budget_total;
  const status = {
    ready: "Ready. Press Next to let the agent propose a batch.",
    proposed: "Waiting for researcher approval.",
    revealed: "Real results revealed. Press Next for the next round.",
    finished: "Budget used. Run complete.",
  }[state.phase];

  return (
    <aside className="agent-panel panel">
      <div className="gemini-badge-container">
        <div className="gemini-chip">✨ Google Gemini Multi-Agent</div>
        <div className="gemini-subchip">Argon 4 (Orchestrator) · Flash 3.8 (Parallel Research) · Flash-Lite 3.5 (Checker)</div>
      </div>
      <label className="run-picker">
        Run
        <select value={runName} onChange={(e) => onRun(e.target.value)}>
          {runs.map((r) => (
            <option key={r.name} value={r.name}>{r.name}</option>
          ))}
        </select>
      </label>
      {isDemo && <div className="demo-banner">DEMO LOG: picks from the retrospective shortlist; results are measured values. Replace with the agent's real log.</div>}
      {run.errors.length > 0 && (
        <div className="error">Log has {run.errors.length} invalid line(s): {run.errors.slice(0, 2).join("; ")}</div>
      )}

      <div className="stats">
        <Stat k={`Budget left (${unit})`} v={view.budgetLeft !== undefined ? `${view.budgetLeft}${total ? ` / ${total}` : ""}` : "–"} variant="orange" />
        <Stat k="Real hits found" v={String(view.hitsTotal)} variant="teal" />
        <Stat k="Random, same budget" v={view.randomTotal.toFixed(1)} />
        <Stat k="Round" v={view.current ? `${view.current.round} / ${compiled.rounds.length}` : `– / ${compiled.rounds.length}`} />
      </div>

      <div className="status">{status}</div>

      {view.current && (
        <ol className="picks">
          {view.current.propose.pairs.map((p, i) => {
            const res = state.phase !== "proposed" ? view.current!.reveal?.results.find((r) => r.a === p.a && r.b === p.b) : undefined;
            return (
              <li key={`${p.a}-${p.b}`}>
                <div className="pick-name">
                  <span className="pick-num">{i + 1}</span> {drugName(p.a, p.drug_a)} + {drugName(p.b, p.drug_b)}
                  {res && <span className={res.hit ? "badge hit" : "badge miss"}>{res.hit ? `Hit · ${res.score.toFixed(0)}` : `No · ${res.score.toFixed(0)}`}</span>}
                </div>
                <div className="muted small">Why: {p.reason}</div>
                {onMolecules && (molecules.has(p.a) || molecules.has(p.b)) && (
                  <button className="mol-open" onClick={() => onMolecules(p.a, p.b)}>View molecules</button>
                )}
                {p.sources && p.sources.length > 0 && <div className="muted small">Sources: {p.sources.join(", ")}</div>}
              </li>
            );
          })}
        </ol>
      )}
      {view.current?.learnNote && state.phase !== "proposed" && <div className="muted small">Learned: {view.current.learnNote}</div>}

      <div className="actions">
        <button className="primary" disabled={state.phase !== "proposed"} onClick={onApprove}>
          Approve batch
        </button>
        <button onClick={onNext} disabled={state.phase === "proposed" || state.phase === "finished"}>Next</button>
        <button onClick={onReset}>Reset</button>
      </div>
      <div className="muted small keys">Space = next / approve · R = reset</div>
    </aside>
  );
}

function Stat({ k, v, variant }: { k: string; v: string; variant?: "teal" | "orange" }) {
  const vClass = variant === "orange" ? "stat-v accent-orange" : variant === "teal" ? "stat-v accent-teal" : "stat-v";
  return (
    <div className="stat">
      <div className="muted small">{k}</div>
      <div className={vClass}>{v}</div>
    </div>
  );
}
