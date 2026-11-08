"""
Deterministic gates. These run in plain Python after every model step and
cannot be overridden by any model: a model "pass" never cancels a gate "fail".

  citations_grounded   every PMID / DOI / URL the model wrote appears in the
                       grounding metadata the API returned (url_citation
                       annotations, url_context_result retrievals)
  tier4_refused        no tier-4 (withheld) pair is ranked, researched or
                       offered for approval
  no_clinical_claim    no treatment advice / patient-benefit wording
  synthetic_labelled   any mention of simulation says "synthetic"
  numbers_from_tools   every score-like number in the orchestrator summary
                       exists in the ranker's JSON (the model did no maths)
"""
from __future__ import annotations

import json
import re
import urllib.request

from .gemini import cited_ids, PUBMED_URL_RE


def _gate(name: str, passed: bool, detail=None) -> dict:
    return {"gate": name, "pass": bool(passed), "detail": detail}


# --------------------------------------------------------------------------- #
def citations_grounded(text: str, grounding: list[dict], pubmed_lookup=None,
                       drug_names: tuple[str, ...] = ()) -> dict:
    urls = [g["url"] for g in grounding] + [g["resolved_url"] for g in grounding
                                            if g.get("resolved_url")]
    blob = " ".join(urls).lower()
    g_pmids = set(PUBMED_URL_RE.findall(" ".join(urls)))
    ids = cited_ids(text)
    rows = []
    for p in ids["pmids"]:
        if p in g_pmids:
            rows.append({"id": f"PMID:{p}", "status": "grounded"})
        else:
            st = "unverified"
            info = pubmed_lookup(p) if pubmed_lookup else None
            if info and info.get("exists"):
                title = (info.get("title") or "").lower()
                st = ("exists_in_pubmed_drug_in_title"
                      if any(d.lower() in title for d in drug_names) else
                      "exists_in_pubmed_drug_not_in_title")
            rows.append({"id": f"PMID:{p}", "status": st,
                         "pubmed_title": (info or {}).get("title")})
    for d in ids["dois"]:
        rows.append({"id": f"doi:{d}", "status": "grounded" if d.lower() in blob else "unverified"})
    for u in ids["urls"]:
        if PUBMED_URL_RE.search(u):
            continue                                # counted as a PMID above
        ok = any(u.rstrip("/") == x.rstrip("/") or x.startswith(u.rstrip("/")) for x in urls)
        rows.append({"id": u, "status": "grounded" if ok else "unverified"})
    bad = [r for r in rows if r["status"] != "grounded"]
    return _gate("citations_grounded", not bad,
                 {"cited": rows, "n_grounding_urls": len(grounding),
                  "not_grounded": [r["id"] for r in bad]})


def strip_ungrounded(text: str, not_grounded: list[str]) -> str:
    out = text
    for ident in not_grounded:
        raw = ident.split(":", 1)[1] if ident.startswith(("PMID:", "doi:")) else ident
        if ident.startswith("PMID:"):
            out = re.sub(rf"PMID[:\s#]*{re.escape(raw)}\b", "[citation removed: not in grounding]", out, flags=re.I)
            out = re.sub(rf"https?://pubmed\.ncbi\.nlm\.nih\.gov/{re.escape(raw)}/?",
                         "[citation removed: not in grounding]", out, flags=re.I)
        else:
            out = out.replace(raw, "[citation removed: not in grounding]")
    return out


def pubmed_esummary(pmid: str, timeout: float = 8.0) -> dict | None:
    """Optional extra check against NCBI E-utilities (public, no key)."""
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
           f"?db=pubmed&retmode=json&id={int(pmid)}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        rec = d.get("result", {}).get(str(int(pmid)), {})
        if not rec or "error" in rec:
            return {"exists": False}
        return {"exists": True, "title": rec.get("title")}
    except Exception:
        return None


# --------------------------------------------------------------------------- #
def tier4_refused(ranking: dict, candidates: list[dict]) -> dict:
    withheld = {(r["nsc_a"], r["nsc_b"]) for r in ranking.get("withheld", [])}
    bad_ranked = [r for r in ranking.get("ranked", [])
                  if r.get("tier", 4) >= 4 or r.get("ranked") is False]
    bad_cand = [c for c in candidates
                if (c["nsc_a"], c["nsc_b"]) in withheld or c.get("tier", 4) >= 4]
    return _gate("tier4_refused", not bad_ranked and not bad_cand,
                 {"n_withheld": len(withheld),
                  "tier4_in_ranked": [f'{r["drug_a"]}+{r["drug_b"]}' for r in bad_ranked],
                  "tier4_in_candidates": [f'{c["drug_a"]}+{c["drug_b"]}' for c in bad_cand]})


# Treatment advice: never allowed anywhere.
ADVICE = [r"\bshould be (given|prescribed|administered|used) (to|in|for) patients\b",
          r"\brecommend(ed)? (it |this |them )?(for|to) patients\b",
          r"\bwe recommend (treating|prescribing|giving)\b",
          r"\b(dose|dosing) (patients|for patients)\b",
          r"\bpatients should (receive|take|be treated)\b",
          r"\bsafe (and effective )?for patients\b"]
# Benefit claims: not allowed in OUR wording (orchestrator summary / report).
# Research text may report a cited trial result; the checker model reviews it.
BENEFIT = [r"\bimproves? (overall |progression[- ]free )?survival\b",
           r"\bclinical benefit\b", r"\bbenefits? (to |for )?patients\b",
           r"\bwill (work|help|cure)\b", r"\bcures?\b", r"\beffective treatment\b"]


def no_clinical_claim(text: str, strict: bool) -> dict:
    pats = ADVICE + (BENEFIT if strict else [])
    hits = sorted({m.group(0) for p in pats for m in re.finditer(p, text, re.I)})
    return _gate("no_clinical_claim", not hits, {"matched": hits, "strict": strict})


def synthetic_labelled(text: str) -> dict:
    mentions = bool(re.search(r"\bsimulat\w*", text, re.I))
    ok = (not mentions) or bool(re.search(r"\bsynthetic\b", text, re.I))
    return _gate("synthetic_labelled", ok, {"mentions_simulation": mentions})


_NUM = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\d])")


def numbers_from_tools(summary: str, tool_results: list[dict]) -> dict:
    allowed: set[str] = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            allowed.add(f"{float(x):.1f}"); allowed.add(f"{float(x):.2f}")
            allowed.add(f"{float(x):g}")
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk([r["result"] for r in tool_results])
    for s in ("0.89", "0.34", "0.06", "0.04", "0.03"):   # tier precisions in API/README
        allowed.add(s)
    found = _NUM.findall(summary)
    stray = [n for n in found if n not in allowed and f"{float(n):.1f}" not in allowed]
    return _gate("numbers_from_tools", not stray, {"numbers": found, "not_in_tool_output": stray})


def all_pass(gates: list[dict]) -> bool:
    return all(g["pass"] for g in gates)


# --- Scope: drugs the question names that the ranker does not know ----------
# Plain Python, no model. A judge asking about a drug outside the 105-drug
# NCI-ALMANAC panel (e.g. pembrolizumab) must get an explicit refusal for that
# drug, not a silent answer about the other drug only.
_DRUG_SUFFIX = re.compile(
    r"\b[a-z]{3,}(?:mab|nib|ciclib|lisib|parib|rasib|tecan|platin|taxel|rubicin|"
    r"mustine|tabine|trexed|limus|zomib|degib|stat|vir)\b", re.I)
_KNOWN_OUTSIDE_PANEL = {  # common lung-cancer drugs not in NCI-ALMANAC
    "osimertinib", "pembrolizumab", "nivolumab", "atezolizumab", "durvalumab",
    "cemiplimab", "ipilimumab", "alectinib", "brigatinib", "lorlatinib", "crizotinib",
    "sotorasib", "adagrasib", "amivantamab", "ramucirumab", "bevacizumab",
    "afatinib", "dacomitinib", "capmatinib", "tepotinib", "selpercatinib",
    "pralsetinib", "dabrafenib", "trametinib", "tarlatamab", "lurbinectedin",
}


def out_of_scope_drugs(question: str, known_names: list[str]) -> dict:
    known_words = {w for n in known_names for w in re.findall(r"[a-z]+", n.lower())}
    words = set(re.findall(r"[a-z]+", question.lower()))
    cand = {w for w in words if w in _KNOWN_OUTSIDE_PANEL}
    cand |= {m.group(0).lower() for m in _DRUG_SUFFIX.finditer(question)}
    unknown = sorted(w for w in cand if w not in known_words)
    return {"gate": "scope_stated", "pass": True, "unknown_drugs": unknown,
            "detail": ("not in the 105-drug NCI-ALMANAC panel, so no score is given: "
                       + ", ".join(unknown)) if unknown else "all named drugs are in the panel"}
