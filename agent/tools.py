"""
Tools the orchestrator agent may call. Thin wrappers around Duncan's ranker
API (backend/api.py). All scoring, tiers, intervals and refusals come from the
API; nothing here computes a score, and the language model never does either.

Two transports:
  HttpApi       - talks to a running `python backend/api.py` (default :8000)
  InProcessApi  - imports backend/api.py and uses Flask's test client
                  (no server; fits the model on first import, about a minute)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

from . import config


# --------------------------------------------------------------------------- #
# Transports
# --------------------------------------------------------------------------- #
class ApiError(RuntimeError):
    pass


class HttpApi:
    def __init__(self, base: str, timeout: float = config.HTTP_TIMEOUT_S):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.base + path, data=data, method=method,
            headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:      # 400/404 carry a JSON body
            try:
                return {"http_status": e.code, **json.loads(e.read().decode())}
            except Exception:
                raise ApiError(f"{method} {path} -> HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise ApiError(
                f"LungPair API not reachable at {self.base} ({e.reason}). "
                "Start it with `cd backend && python api.py`, or set "
                "LUNGPAIR_API=inprocess.") from e

    def get(self, path: str) -> dict:
        return self._req("GET", path)

    def post(self, path: str, body: dict) -> dict:
        return self._req("POST", path, body)


class InProcessApi:
    def __init__(self):
        backend = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "backend")
        if backend not in sys.path:
            sys.path.insert(0, backend)
        import api as _api                       # noqa: E402  (fits model once)
        self._c = _api.app.test_client()

    def get(self, path: str) -> dict:
        r = self._c.get(path)
        out = r.get_json() or {}
        return out if r.status_code == 200 else {"http_status": r.status_code, **out}

    def post(self, path: str, body: dict) -> dict:
        r = self._c.post(path, json=body)
        out = r.get_json() or {}
        return out if r.status_code == 200 else {"http_status": r.status_code, **out}


def make_api(spec: str | None = None):
    spec = spec or config.LUNGPAIR_API
    return InProcessApi() if spec == "inprocess" else HttpApi(spec)


# --------------------------------------------------------------------------- #
# Tool functions (what the model can call)
# --------------------------------------------------------------------------- #
class LungPairTools:
    """Bound to one API transport. Keeps every raw API result it returned so
    the pipeline builds the final tiered list from API JSON, not model text."""

    def __init__(self, api):
        self.api = api
        self.results: list[dict] = []      # every tool call + raw result
        self._drugs: list[dict] | None = None

    # -- helpers -------------------------------------------------------------
    def _drug_table(self) -> list[dict]:
        if self._drugs is None:
            self._drugs = self.api.get("/drugs").get("drugs", [])
        return self._drugs

    # -- tools ---------------------------------------------------------------
    def list_drugs(self) -> dict:
        """All drugs the ranker knows (NCI-ALMANAC NSCLC panel)."""
        d = self._drug_table()
        return {"count": len(d), "drugs": d}

    def resolve_drugs(self, names: list[str]) -> dict:
        """Map free-text names or NSC numbers to ranker drugs. Exact,
        case-insensitive match only: no fuzzy guessing."""
        table = self._drug_table()
        by_name = {x["name"].lower(): x for x in table}
        by_nsc = {str(x["nsc"]): x for x in table}
        found, unknown = [], []
        for n in names:
            s = str(n).strip()
            hit = by_nsc.get(s) or by_name.get(s.lower())
            (found if hit else unknown).append(hit or s)
        return {"resolved": found, "unknown": unknown,
                "note": "Unknown drugs are not in NCI-ALMANAC as served here "
                        "(e.g. osimertinib) and cannot be ranked."}

    def rank_pairs(self, drugs: list[str], top: int = 20) -> dict:
        """Rank every pair among the given drugs (Duncan's POST /rank)."""
        return self.api.post("/rank", {"drugs": list(drugs), "top": int(top)})

    def rank_partners(self, anchor: str, top: int = 10) -> dict:
        """Rank every known drug as a partner for `anchor`. Calls POST /rank
        with anchor + all known drugs, then keeps pairs containing the anchor.
        Filtering only; scores and tiers are the API's."""
        res = self.resolve_drugs([anchor])
        if not res["resolved"]:
            return {"error": f"'{anchor}' is not a ranker drug",
                    "unknown": res["unknown"], "note": res["note"]}
        a = res["resolved"][0]["nsc"]
        everyone = [x["nsc"] for x in self._drug_table()]
        raw = self.api.post("/rank", {"drugs": everyone, "top": 100000})
        if "error" in raw:
            return raw
        keep = lambda r: a in (r["nsc_a"], r["nsc_b"])          # noqa: E731
        ranked = [r for r in raw.get("ranked", []) if keep(r)]
        for i, r in enumerate(ranked, 1):
            r["partner_rank"] = i
        return {"model_version": raw.get("model_version"),
                "anchor": res["resolved"][0],
                "ranked": ranked[: int(top)],
                "withheld": [r for r in raw.get("withheld", []) if keep(r)],
                "unknown": raw.get("unknown", []),
                "note": raw.get("note")}

    def get_pair(self, drug_a: str, drug_b: str) -> dict:
        """One pair: prediction, 95% interval, tier, measured value if any."""
        res = self.resolve_drugs([drug_a, drug_b])
        if len(res["resolved"]) < 2:
            return {"error": "could not resolve both drugs", **res}
        a, b = (x["nsc"] for x in res["resolved"])
        return self.api.get(f"/pair/{a}/{b}")

    # -- dispatch ------------------------------------------------------------
    def call(self, name: str, args: dict) -> dict:
        fn: Callable[..., dict] | None = {
            "list_drugs": self.list_drugs,
            "resolve_drugs": self.resolve_drugs,
            "rank_pairs": self.rank_pairs,
            "rank_partners": self.rank_partners,
            "get_pair": self.get_pair,
        }.get(name)
        if fn is None:
            out: dict[str, Any] = {"error": f"unknown tool {name}"}
        else:
            try:
                out = fn(**(args or {}))
            except TypeError as e:              # bad arguments from the model
                out = {"error": f"bad arguments for {name}: {e}"}
            except ApiError as e:
                out = {"error": str(e)}
        self.results.append({"tool": name, "args": args, "result": out})
        return out


# Function declarations sent to Gemini (Interactions API "function" tools).
TOOL_DECLARATIONS = [
    {"type": "function", "name": "list_drugs",
     "description": "List every drug the LungPair ranker knows (NCI-ALMANAC "
                    "NSCLC panel), with NSC numbers.",
     "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "resolve_drugs",
     "description": "Resolve drug names or NSC numbers to ranker drugs. Returns "
                    "resolved and unknown lists. Use before ranking.",
     "parameters": {"type": "object", "properties": {
         "names": {"type": "array", "items": {"type": "string"}}},
         "required": ["names"]}},
    {"type": "function", "name": "rank_partners",
     "description": "Rank all known drugs as combination partners for one "
                    "anchor drug. Returns ranked pairs (tier 1-3, score, 95% "
                    "interval) and withheld tier-4 pairs.",
     "parameters": {"type": "object", "properties": {
         "anchor": {"type": "string"},
         "top": {"type": "integer", "description": "how many to return, default 10"}},
         "required": ["anchor"]}},
    {"type": "function", "name": "rank_pairs",
     "description": "Rank every pair among a given list of 2+ drugs. Returns "
                    "ranked pairs and withheld tier-4 pairs.",
     "parameters": {"type": "object", "properties": {
         "drugs": {"type": "array", "items": {"type": "string"}},
         "top": {"type": "integer"}},
         "required": ["drugs"]}},
    {"type": "function", "name": "get_pair",
     "description": "Details for one drug pair: predicted score, 95% interval, "
                    "evidence tier, measured NCI-ALMANAC value if any.",
     "parameters": {"type": "object", "properties": {
         "drug_a": {"type": "string"}, "drug_b": {"type": "string"}},
         "required": ["drug_a", "drug_b"]}},
]
