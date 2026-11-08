#!/usr/bin/env bash
# LungPair API — one command to run it.
#   ./start.sh            serve on :8000
#   PORT=9000 ./start.sh  serve elsewhere
set -euo pipefail
cd "$(dirname "$0")"
export LUNGPAIR="${LUNGPAIR:-../lungpair}"
export LUNGPAIR_DATA="${LUNGPAIR_DATA:-../lungpair/data}"
export NSC_NAMES="${NSC_NAMES:-./nsc_names.csv}"
export SURFACES="${SURFACES:-./surface_dose_response.csv}"
[ -f artifacts/model.joblib ] || { echo "training model first (about 2 min)..."; python train.py; }
echo "starting on http://localhost:${PORT:-8000}"
python api.py
