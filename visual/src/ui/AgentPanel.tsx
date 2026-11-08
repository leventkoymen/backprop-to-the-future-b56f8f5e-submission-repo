import type { ReactNode } from "react";
import { drugName, type Run } from "../data/load";
import { Term } from "./Term";
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
  guided?: boolean; // 2b: adds "?" explanations
  highlightApprove?: boolean; // 2b tour: pulse the Approve button
  onMolecules?: (a: number, b: number) => void;
}

/** Scene B side panel: budget, hits vs random, the picks with reasons, and the human Approve step. */
export function AgentPanel({ runs, runName, onRun, compiled, run, state, view, onApprove, onNext, onReset, guided, highlightApprove, onMolecules }: Props) {
  const t = (node: ReactNode, id: Parameters<typeof Term>[0]["id"]) => (guided ? <Term id={id}>{node}</Term> : node);
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
        <Stat k={t(`Budget left (${unit})`, "budget")} v={view.budgetLeft !== undefined ? `${view.budgetLeft}${total ? ` / ${total}` : ""}` : "–"} />
        <Stat k={t("Real hits found", "hit")} v={String(view.hitsTotal)} accent />
        <Stat k={t("Random, same budget", "random")} v={view.randomTotal.toFixed(1)} />
        <Stat k="Round" v={view.current ? `${view.current.round} / ${compiled.rounds.length}` : `– / ${compiled.rounds.length}`} />
      </div>

      <div className="status">{status}</div>
      {guided && state.phase === "ready" && (
        <div className="muted small">Each round the agent proposes a few drug pairs. You approve, then the real lab result is shown. {t("How is this honest?", "replay")}</div>
      )}

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
        <button className={highlightApprove && state.phase === "proposed" ? "primary pulse" : "primary"} disabled={state.phase !== "proposed"} onClick={onApprove}>
          Approve batch
        </button>
        <button onClick={onNext} disabled={state.phase === "proposed" || state.phase === "finished"}>Next</button>
        <button onClick={onReset}>Reset</button>
      </div>
      <div className="muted small keys">Space = next / approve · R = reset</div>
    </aside>
  );
}

function Stat({ k, v, accent }: { k: ReactNode; v: string; accent?: boolean }) {
  return (
    <div className="stat">
      <div className="muted small">{k}</div>
      <div className={accent ? "stat-v accent" : "stat-v"}>{v}</div>
    </div>
  );
}
