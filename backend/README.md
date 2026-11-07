# LungPair API

A real backend: the model is fitted once and persisted, then served over HTTP.
Requests are logged to SQLite. Runs on localhost.

**This is not cloud, not secured, not multi-tenant.** It serves public
NCI-ALMANAC data only — no patient data passes through it. The production
design, including the security controls, is a separate document.

## Run it

**Self-contained.** The training data ships as CSV in `data/`, so you do not
need the 615 MB raw file or the pipeline folder.

The model is **fitted on your machine the first time you run it** — about a
minute — then cached. It is not shipped as a pickle, because pickles do not
survive a scikit-learn or pandas version change: a model saved under sklearn
1.9 will not load under 1.8. Fitting locally always matches your versions.

Windows:

    pip install -r requirements.txt
    python api.py

Mac / Linux:

    pip install -r requirements.txt
    ./start.sh

Then open http://localhost:8000/health — if it returns JSON, it is working.
First start takes about a minute (fitting); after that, seconds.

Retraining is only needed if the data changes: put the pipeline's `data/`
directory alongside and run `python train.py`.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Model version, held-out metrics, data classification |
| GET | `/drugs` | All 105 drugs with names |
| POST | `/rank` | `{"drugs": [...]}` → tiered ranking |
| GET | `/pair/<a>/<b>` | One pair: prediction, interval, tier, measured value |
| GET | `/pair/<a>/<b>/surface` | Dose-response grid — **what the 3D viewer calls** |
| GET | `/shortlist?top=N` | Precomputed top N |
| GET | `/submissions` | Recent requests, for audit |

Drugs can be given as NSC numbers or names: `["Docetaxel", "Gefitinib"]` and
`[628503, 715055]` are equivalent.

## The behaviour that matters

`/rank` splits its answer into `ranked` and `withheld`. Tier 4 pairs — where
neither drug has prior measurements — are **not ranked**, because measured
precision there is 0.04 against a 0.03 baseline. The response says so.

    curl -X POST localhost:8000/rank -H 'Content-Type: application/json' \
      -d '{"drugs":["Docetaxel","Gefitinib","Paclitaxel","Carboplatin"]}'

Returns Docetaxel + Gefitinib first, score 160.1, interval [125.1, 195.1],
tier 1 — matching shortlist rank #4.

## For the 3D front end

    GET /pair/3053/180973/surface?cell_line=A549/ATCC

Returns 9 points per cell line with `dose_index_a/b`, `log10_conc_a/b`,
`observed_growth`, `expected_growth` and `synergy`. Plot synergy as Z.

## What it does not do

No auth, no TLS, no rate limiting, no deployment, single process, SQLite.
Those are deliberate — it is a demo service, and saying so is better than
implying otherwise.
