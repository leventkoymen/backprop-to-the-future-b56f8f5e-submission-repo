"""
CLI:  python -m agent.run "Which partner should a lab screen with gefitinib next?"

  --no-llm         ranking + approval only, no Gemini call (Wi-Fi fallback;
                   output is labelled as such)
  --approve 1,3    non-interactive approval (else you are asked)
  --approver NAME  recorded in the log
  --top-k N        pairs sent to the research agent (default 5)
  --api URL|inprocess
"""
from __future__ import annotations

import argparse
import getpass
import sys

from . import config
from .gemini import make_client, MissingKey
from .pipeline import run_pipeline
from .runlog import RunLog
from .tools import LungPairTools, make_api


def _fmt_iv(iv):
    return f"[{iv[0]}, {iv[1]}]" if iv else "-"


def print_table(cands: list[dict]):
    print(f"\n{'#':>2}  {'pair':<36} {'tier':>4} {'score':>7} {'95% interval':>16}  evidence")
    for i, c in enumerate(cands, 1):
        ev = (c.get("evidence") or {}).get("status", "-")
        print(f"{i:>2}  {c['drug_a'] + ' + ' + c['drug_b']:<36} {c['tier']:>4} "
              f"{c['score']:>7} {_fmt_iv(c.get('interval_95')):>16}  {ev}")


def interactive_approve(approver: str, preset: str | None):
    def _approve(cands: list[dict]) -> dict:
        print_table(cands)
        if preset is not None:
            raw = preset
        else:
            raw = input("\nHuman sign-off: which pairs go into the next screening batch? "
                        "(e.g. 1,3  or 'none'): ").strip()
        picks = [] if raw.lower() in ("", "none", "0") else \
            sorted({int(x) for x in raw.replace(" ", "").split(",") if x.isdigit()
                    and 1 <= int(x) <= len(cands)})
        return {"approved": picks, "approver": approver, "raw_input": raw,
                "note": "approved for the next screening batch (lab decision, not clinical)"}
    return _approve


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent.run")
    ap.add_argument("question")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--approve", default=None)
    ap.add_argument("--approver", default=None)
    ap.add_argument("--top-k", type=int, default=config.RESEARCH_TOP_K)
    ap.add_argument("--api", default=None)
    ap.add_argument("--no-pubmed-check", action="store_true",
                    help="skip the extra NCBI E-utilities lookup of ungrounded PMIDs")
    a = ap.parse_args(argv)

    client = None
    if not a.no_llm:
        try:
            client = make_client()
        except MissingKey as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
    log = RunLog(mode="no-llm" if a.no_llm else "live")
    tools = LungPairTools(make_api(a.api))
    approver = a.approver or getpass.getuser()
    print(f"run {log.run_id}  mode={log.mode}  receipt={log.path}")
    if client:
        print(f"models: orchestrator={config.ORCHESTRATOR_MODEL} research={config.RESEARCH_MODEL} "
              f"checker={config.CHECKER_MODEL}")
    rep = run_pipeline(a.question, tools, log, client=client, top_k=a.top_k,
                       approve=interactive_approve(approver, a.approve),
                       pubmed_check=not a.no_pubmed_check)
    if rep.get("error"):
        print("ERROR:", rep["error"]); return 1

    print(f"\nranking source: {rep['ranking_source']}  |  ranker model {rep.get('ranker_model_version')}")
    if rep.get("unknown"):
        print("not in NCI-ALMANAC panel:", rep["unknown"])
    print(f"withheld (tier 4, refused): {len(rep['withheld'])}   tier-4 gate: "
          f"{'PASS' if rep['tier4_gate']['pass'] else 'FAIL'}")
    o = rep.get("orchestrator")
    if o:
        print(f"\n[orchestrator {o.get('model')} | {o.get('status')}]\n{o.get('summary')}")
        for g in o.get("gates", []):
            if not g["pass"]:
                print("  gate FAIL:", g["gate"], g["detail"])
    for i, c in enumerate(rep.get("candidates", []), 1):
        ev = c.get("evidence") or {}
        print(f"\n--- {i}. {c['drug_a']} + {c['drug_b']}  [{ev.get('status')}]")
        print(ev.get("text", ""))
        for g in ev.get("gates", []):
            if not g["pass"]:
                print("  gate FAIL:", g["gate"], (g["detail"] or {}).get("not_grounded", g["detail"]))
    hd = rep["human_decision"]
    print(f"\napproved by {hd.get('approver')}: "
          f"{[p['drug_a'] + ' + ' + p['drug_b'] for p in hd['approved_pairs']] or 'none'}")
    print(f"\n{rep['disclaimer']}\nreceipt: {log.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
