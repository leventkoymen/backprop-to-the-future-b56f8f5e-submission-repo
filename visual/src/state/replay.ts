import type { Event, ProposeEvent, RevealEvent, RunStartEvent } from "../data/schemas";

// One round of the design-build-test-learn loop, compiled from the event log.
export interface Round {
  round: number;
  propose: ProposeEvent;
  reveal?: RevealEvent;
  approvedBy?: string;
  learnNote?: string;
}

export interface CompiledRun {
  start?: RunStartEvent;
  rounds: Round[];
  end?: Extract<Event, { type: "run_end" }>;
}

export function compileRun(events: Event[]): CompiledRun {
  const byRound = new Map<number, Partial<Round>>();
  const get = (r: number) => byRound.get(r) ?? (byRound.set(r, { round: r }), byRound.get(r)!);
  let start: CompiledRun["start"];
  let end: CompiledRun["end"];
  for (const e of events) {
    switch (e.type) {
      case "run_start": start = e; break;
      case "propose": get(e.round).propose = e; break;
      case "approve": get(e.round).approvedBy = e.approved_by; break;
      case "reveal": get(e.round).reveal = e; break;
      case "learn": get(e.round).learnNote = e.note; break;
      case "run_end": end = e; break;
    }
  }
  const rounds = [...byRound.values()]
    .filter((r): r is Round => Boolean(r.propose))
    .sort((x, y) => x.round - y.round);
  return { start, rounds, end };
}

// ---------- replay state machine ----------
// ready -> proposed (awaiting approval) -> revealed -> proposed (next round) ... -> finished
export type Phase = "ready" | "proposed" | "revealed" | "finished";
export interface ReplayState { index: number; phase: Phase }
export type ReplayAction = { type: "next" } | { type: "approve" } | { type: "reset" };

export const initialReplay: ReplayState = { index: -1, phase: "ready" };

export function makeReducer(run: CompiledRun) {
  return (s: ReplayState, a: ReplayAction): ReplayState => {
    const last = run.rounds.length - 1;
    switch (a.type) {
      case "reset":
        return initialReplay;
      case "approve":
        // The human sign-off: only valid while a batch is waiting for approval.
        return s.phase === "proposed" ? { ...s, phase: "revealed" } : s;
      case "next":
        if (s.phase === "ready") return run.rounds.length ? { index: 0, phase: "proposed" } : s;
        if (s.phase === "proposed") return s; // must be approved first
        if (s.phase === "revealed") return s.index < last ? { index: s.index + 1, phase: "proposed" } : { ...s, phase: "finished" };
        return s;
    }
  };
}

export interface ReplayView {
  current?: Round;
  proposedKeys: { a: number; b: number }[]; // gold, awaiting approval
  revealed: { a: number; b: number; hit: boolean; score: number }[];
  budgetLeft?: number;
  hitsTotal: number;
  randomTotal: number;
  experimentsUsed: number;
}

export function viewOf(run: CompiledRun, s: ReplayState): ReplayView {
  const current = s.index >= 0 ? run.rounds[s.index] : undefined;
  const lastRevealed = s.phase === "revealed" || s.phase === "finished" ? s.index : s.index - 1;
  const revealedRounds = run.rounds.slice(0, lastRevealed + 1);
  const revealed = revealedRounds.flatMap((r) => r.reveal?.results ?? []);
  const lastReveal = revealedRounds.at(-1)?.reveal;
  return {
    current,
    proposedKeys: s.phase === "proposed" && current ? current.propose.pairs.map(({ a, b }) => ({ a, b })) : [],
    revealed,
    budgetLeft: lastReveal?.budget_left ?? run.start?.budget_total,
    hitsTotal: lastReveal?.hits_total ?? 0,
    randomTotal: lastReveal?.random_hits_total ?? 0,
    experimentsUsed: revealed.length,
  };
}
